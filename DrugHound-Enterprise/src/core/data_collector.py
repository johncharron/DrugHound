"""Dynamic data collection from multiple sources."""

import asyncio
import aiohttp
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re
from collections import defaultdict

class DataCollector:
    """Collects drug data from multiple sources dynamically."""
    
    def __init__(self):
        self.session = None
        self.results = defaultdict(list)
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
    
    async def search_clinicaltrials(self, condition: str, max_results: int = 100) -> List[Dict]:
        """Search ClinicalTrials.gov dynamically."""
        url = "https://clinicaltrials.gov/api/v2/studies"
        params = {
            'query.cond': condition,
            'pageSize': max_results,
            'format': 'json',
            'sort': 'LastUpdatePostDate'
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    studies = []
                    for study in data.get('studies', []):
                        protocol = study.get('protocolSection', {})
                        studies.append({
                            'nct_id': protocol.get('identificationModule', {}).get('nctId'),
                            'title': protocol.get('identificationModule', {}).get('briefTitle'),
                            'condition': protocol.get('conditionsModule', {}).get('conditions', [''])[0],
                            'phase': protocol.get('designModule', {}).get('phaseList', []),
                            'status': protocol.get('statusModule', {}).get('overallStatus'),
                            'start_date': protocol.get('statusModule', {}).get('studyFirstSubmitDate'),
                            'url': f"https://clinicaltrials.gov/ct2/show/{protocol.get('identificationModule', {}).get('nctId')}"
                        })
                    return studies
        except Exception as e:
            print(f"Error searching ClinicalTrials: {e}")
        return []
    
    async def search_pubmed_async(self, drug: str, years_back: int = 5) -> Dict:
        """Search PubMed for drug publications."""
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            'db': 'pubmed',
            'term': f'"{drug}"',
            'retmax': 100,
            'format': 'json',
            'sort': 'date'
        }
        
        try:
            async with self.session.get(base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    ids = data.get('esearchresult', {}).get('idlist', [])
                    
                    # Fetch details for top publications
                    publications = []
                    for pmid in ids[:20]:
                        pub = await self.fetch_pubmed_details(pmid)
                        if pub:
                            publications.append(pub)
                    
                    return {
                        'drug': drug,
                        'total_count': len(ids),
                        'recent_count': len([p for p in publications if p.get('year', 0) >= datetime.now().year - years_back]),
                        'publications': publications
                    }
        except Exception as e:
            print(f"Error searching PubMed for {drug}: {e}")
        return {'drug': drug, 'total_count': 0, 'publications': []}
    
    async def fetch_pubmed_details(self, pmid: str) -> Optional[Dict]:
        """Fetch detailed publication info."""
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        params = {
            'db': 'pubmed',
            'id': pmid,
            'format': 'json'
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get('result', {}).get(pmid, {})
                    return {
                        'pmid': pmid,
                        'title': result.get('title', ''),
                        'journal': result.get('fulljournalname', ''),
                        'year': result.get('pubdate', '').split()[0] if result.get('pubdate') else '',
                        'authors': result.get('authors', []),
                        'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    }
        except Exception as e:
            print(f"Error fetching details for {pmid}: {e}")
        return None
    
    def extract_drugs_from_results(self, studies: List[Dict]) -> List[str]:
        """Extract drug names from study results."""
        drug_patterns = [
            r'([A-Z][a-z]+(?:umab|mab|nib|tinib|ciclib))',
            r'([A-Z][a-z]+(?:statin|dipine|pril|sartan|olol))',
            r'([A-Z][a-z]+(?:cycline|mycin|navir|previr))',
            r'([A-Z][a-z]{3,}in\w*)',
            r'([A-Z][a-z]{3,}ol\w*)',
        ]
        
        drugs = set()
        for study in studies:
            title = study.get('title', '')
            condition = study.get('condition', '')
            text = f"{title} {condition}"
            
            for pattern in drug_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                drugs.update([m for m in matches if len(m) > 3])
        
        # Filter common non-drugs
        exclude = {'Placebo', 'Control', 'Sham', 'Saline', 'Water', 'None', 'Standard'}
        return [d for d in drugs if d not in exclude][:50]

class DrugAnalyzer:
    """Analyzes collected data for repurposing opportunities."""
    
    def __init__(self, ollama_model: str = "qwen2.5:7b"):
        self.model = ollama_model
        
    def calculate_novelty_score(self, pubmed_count: int, phase: str) -> Dict:
        """Calculate comprehensive novelty score."""
        # Publication component (0-50)
        if pubmed_count == 0:
            pub_score = 50
            pub_level = "EXCEPTIONAL"
        elif pubmed_count < 5:
            pub_score = 45
            pub_level = "VERY HIGH"
        elif pubmed_count < 20:
            pub_score = 35
            pub_level = "HIGH"
        elif pubmed_count < 50:
            pub_score = 25
            pub_level = "MODERATE"
        elif pubmed_count < 100:
            pub_score = 15
            pub_level = "LOW"
        else:
            pub_score = 5
            pub_level = "VERY LOW"
        
        # Phase component (0-30)
        phase_scores = {
            'Phase 1': 30, 'Early Phase 1': 30,
            'Phase 1/2': 25, 'Phase 2': 15,
            'Phase 2/3': 8, 'Phase 3': 3,
            'Phase 4': 0
        }
        phase_score = phase_scores.get(phase, 10)
        
        # Calculate total
        total_score = pub_score + phase_score
        
        return {
            'total': total_score,
            'publication_score': pub_score,
            'publication_level': pub_level,
            'phase_score': phase_score,
            'level': 'VERY HIGH' if total_score >= 80 else 'HIGH' if total_score >= 60 else 'MODERATE' if total_score >= 40 else 'LOW'
        }
    
    def generate_repurposing_analysis(self, drug: str, pubmed_count: int, phase: str, conditions: List[str]) -> Dict:
        """Generate AI-powered repurposing analysis."""
        import ollama
        
        prompt = f"""Analyze {drug} for drug repurposing opportunities:

Current Data:
- Publications: {pubmed_count}
- Clinical Phase: {phase}
- Current Conditions: {', '.join(conditions[:3])}

Provide a comprehensive repurposing analysis in JSON format:
{{
  "primary_mechanism": "brief mechanism description",
  "repurposing_opportunities": [
    {{"condition": "disease", "rationale": "why it works", "confidence": 0.0-1.0}}
  ],
  "competitive_landscape": ["other drugs targeting same pathways"],
  "development_pathway": "recommended next steps",
  "estimated_success_probability": "0-100%"
}}
"""
        
        try:
            response = ollama.generate(model=self.model, prompt=prompt, options={"temperature": 0.3})
            import json
            import re
            json_match = re.search(r'\{.*\}', response['response'], re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"Analysis error: {e}")
        
        return {
            "primary_mechanism": "Unknown",
            "repurposing_opportunities": [],
            "competitive_landscape": [],
            "development_pathway": "Further research needed",
            "estimated_success_probability": "Unknown"
        }
