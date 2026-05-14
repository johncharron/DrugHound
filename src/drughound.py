#!/usr/bin/env python3
"""
DrugHound - Drug Repurposing Discovery Engine
Based on working discovery_engine_v2.py
"""

import requests
import json
import time
import pandas as pd
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict
import ollama

# Create output directory
os.makedirs('output', exist_ok=True)

class DrugHound:
    def __init__(self, pubmed_api_key: str = None):
        self.model = "qwen2.5:7b"
        self.pubmed_api_key = pubmed_api_key
        
    def discover_from_clinicaltrials(self, days_back: int = 365) -> List[Dict]:
        """Mine ClinicalTrials.gov for recent studies."""
        print(f"\n🔍 Mining ClinicalTrials.gov (last {days_back} days)...")
        
        base_url = "https://clinicaltrials.gov/api/v2/studies"
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        params = {
            'query.cond': 'cancer OR diabetes OR inflammation OR autoimmune',
            'filter.overallStatus': 'COMPLETED,ACTIVE_NOT_RECRUITING',
            'pageSize': '50',
            'format': 'json'
        }
        
        all_trials = []
        
        try:
            response = requests.get(base_url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                studies = data.get('studies', [])
                print(f"   Found {len(studies)} studies")
                
                for study in studies[:50]:
                    protocol = study.get('protocolSection', {})
                    
                    interventions = []
                    arms = protocol.get('armsInterventionsModule', {})
                    for arm in arms.get('armGroupList', []):
                        interventions.extend(arm.get('interventionList', []))
                    
                    drug_names = self.extract_drug_names(interventions)
                    
                    if drug_names:
                        trial_data = {
                            'nct_id': protocol.get('identificationModule', {}).get('nctId', ''),
                            'title': protocol.get('identificationModule', {}).get('briefTitle', ''),
                            'condition': protocol.get('conditionsModule', {}).get('conditions', [''])[0],
                            'phase': ', '.join(protocol.get('designModule', {}).get('phaseList', [])),
                            'drugs': drug_names,
                        }
                        all_trials.append(trial_data)
        except Exception as e:
            print(f"   API Error: {e}")
        
        print(f"   Found {len(all_trials)} trials with drugs")
        return all_trials
    
    def extract_drug_names(self, interventions: List[str]) -> List[str]:
        """Extract drug names from intervention strings."""
        drug_patterns = [
            r'([A-Z][a-z]+(?:umab|imumab|ximab|zumab|mab|nib|tinib|ciclib))',
            r'([A-Z][a-z]+(?:statin|dipine|pril|sartan|olol|oxacin|mycin|navir|previr))',
            r'([A-Z][a-z]+[A-Z][a-z]+(?:ine|ole|ate|ide|one|ane))'
        ]
        
        drug_names = set()
        for intervention in interventions:
            if not isinstance(intervention, str):
                continue
            for pattern in drug_patterns:
                matches = re.findall(pattern, intervention)
                drug_names.update(matches)
        
        exclude = {'Placebo', 'Control', 'Standard', 'Usual', 'Sham', 'None'}
        return [d for d in drug_names if d not in exclude][:3]
    
    def get_expanded_drugs(self) -> List[Dict]:
        """Fallback database of promising drugs."""
        return [
            # Novel/understudied drugs
            {'drugs': ['Olorofim'], 'condition': 'Fungal Infections', 'phase': 'Phase 2', 'pubmed_count': 5},
            {'drugs': ['Epetraborole'], 'condition': 'Bacterial Infections', 'phase': 'Phase 2', 'pubmed_count': 8},
            {'drugs': ['Ganaxolone'], 'condition': 'Seizures', 'phase': 'Phase 3', 'pubmed_count': 45},
            {'drugs': ['PYX-201'], 'condition': 'Solid Tumors', 'phase': 'Phase 1', 'pubmed_count': 2},
            {'drugs': ['AL01211'], 'condition': 'Fabry Disease', 'phase': 'Phase 2', 'pubmed_count': 3},
            {'drugs': ['Risdiplam'], 'condition': 'SMA', 'phase': 'Phase 3', 'pubmed_count': 32},
            {'drugs': ['Vosoritide'], 'condition': 'Achondroplasia', 'phase': 'Phase 3', 'pubmed_count': 28},
            {'drugs': ['Lumasiran'], 'condition': 'Hyperoxaluria', 'phase': 'Phase 3', 'pubmed_count': 15},
            # Repurposing candidates
            {'drugs': ['Metformin'], 'condition': 'Aging', 'phase': 'Phase 2', 'pubmed_count': 1500},
            {'drugs': ['Rapamycin'], 'condition': 'Longevity', 'phase': 'Phase 2', 'pubmed_count': 1200},
            {'drugs': ['Lithium'], 'condition': 'Neuroprotection', 'phase': 'Phase 2', 'pubmed_count': 800},
            {'drugs': ['Doxycycline'], 'condition': 'Aneurysm', 'phase': 'Phase 2', 'pubmed_count': 600},
            {'drugs': ['Minoxidil'], 'condition': 'Hair Growth', 'phase': 'Phase 4', 'pubmed_count': 400},
            {'drugs': ['Ivermectin'], 'condition': 'Antiviral', 'phase': 'Phase 2', 'pubmed_count': 350},
            {'drugs': ['Curcumin'], 'condition': 'Inflammation', 'phase': 'Phase 2', 'pubmed_count': 500},
            {'drugs': ['Resveratrol'], 'condition': 'Metabolic', 'phase': 'Phase 2', 'pubmed_count': 300},
            {'drugs': ['Berberine'], 'condition': 'Diabetes', 'phase': 'Phase 4', 'pubmed_count': 250},
            {'drugs': ['Quercetin'], 'condition': 'Senolytics', 'phase': 'Phase 1', 'pubmed_count': 80},
            {'drugs': ['Niacin'], 'condition': 'NAD+', 'phase': 'Phase 2', 'pubmed_count': 200},
            {'drugs': ['Melatonin'], 'condition': 'Sleep', 'phase': 'Phase 4', 'pubmed_count': 600},
        ]
    
    def search_pubmed_count(self, drug: str) -> int:
        """Get publication count from PubMed."""
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {
            'db': 'pubmed',
            'term': f'"{drug}"',
            'retmax': 0,
            'format': 'json',
            'tool': 'DrugHound',
            'email': 'drughound@example.com'
        }
        if self.pubmed_api_key:
            params['api_key'] = self.pubmed_api_key
        
        try:
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return int(data.get('esearchresult', {}).get('count', 0))
        except:
            pass
        return 0
    
    def run(self):
        """Run discovery pipeline."""
        print("="*70)
        print("🐕 DRUGHOUND - Drug Repurposing Discovery Engine")
        print("="*70)
        
        # Try API first, fallback to database
        trials = self.discover_from_clinicaltrials()
        
        drug_map = defaultdict(list)
        if trials:
            for trial in trials:
                for drug in trial.get('drugs', []):
                    if len(drug) > 3:
                        drug_map[drug].append(trial)
        
        # If API failed, use fallback database
        if not drug_map:
            print("\n⚠️ Using curated drug database...")
            for drug_entry in self.get_expanded_drugs():
                drug = drug_entry['drugs'][0]
                drug_map[drug].append({
                    'condition': drug_entry['condition'],
                    'phase': drug_entry['phase'],
                    'pubmed_count': drug_entry.get('pubmed_count', 0)
                })
        
        print(f"\n💊 Unique drugs found: {len(drug_map)}")
        
        # Score drugs
        results = []
        for drug, drug_trials in list(drug_map.items())[:40]:
            # Get publication count
            pubmed_count = self.search_pubmed_count(drug)
            if not pubmed_count and drug_trials:
                pubmed_count = drug_trials[0].get('pubmed_count', 0)
            
            # Calculate novelty
            if pubmed_count < 10:
                novelty_score = 95
                novelty_label = "VERY HIGH"
            elif pubmed_count < 50:
                novelty_score = 80
                novelty_label = "HIGH"
            elif pubmed_count < 200:
                novelty_score = 60
                novelty_label = "MODERATE"
            else:
                novelty_score = 40
                novelty_label = "LOW"
            
            conditions = list(set([t.get('condition', '') for t in drug_trials]))
            phases = [t.get('phase', '') for t in drug_trials]
            
            results.append({
                'Drug': drug,
                'Novelty_Score': novelty_score,
                'Novelty_Level': novelty_label,
                'PubMed_Count': pubmed_count,
                'Trials': len(drug_trials),
                'Phase': phases[0] if phases else 'Unknown',
                'Primary_Condition': conditions[0] if conditions else 'Multiple'
            })
        
        # Sort by novelty score
        df = pd.DataFrame(results)
        if not df.empty:
            df = df.sort_values('Novelty_Score', ascending=False)
        
        # Save results
        csv_path = 'output/top_novel_drugs.csv'
        df.to_csv(csv_path, index=False)
        print(f"\n✅ Saved to: {csv_path}")
        
        # Display results
        print("\n" + "="*70)
        print("🏆 TOP DRUG CANDIDATES FOR REPURPOSING")
        print("="*70)
        print(df.head(15).to_string(index=False))
        
        return df

def main():
    api_key = os.environ.get('PUBMED_API_KEY', '47327a0a6ef2906781237c9e8d8d1f978308')
    
    engine = DrugHound(pubmed_api_key=api_key)
    results = engine.run()
    
    print("\n✅ DrugHound complete!")
    print("📁 Results saved to: output/top_novel_drugs.csv")

if __name__ == "__main__":
    main()
