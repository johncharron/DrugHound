#!/usr/bin/env python3
"""DrugHound Enterprise - Working Dynamic Discovery (Restored)"""

import requests
import re
import uuid
import time
import json
import os
from collections import defaultdict
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
import threading

app = FastAPI(title="DrugHound Enterprise")
research_cache = {}

class ResearchRequest(BaseModel):
    condition: str

# ============ DRUG EXTRACTION - THE WORKING PATTERNS ============
# These patterns successfully found BFKB8488 and GrafixPRIME
DRUG_PATTERNS = [
    r'([A-Z]{2,}[0-9]{3,})',           # BFKB8488, AZD9291, LY123456
    r'([A-Z]{2,}-[0-9]+)',              # ALN-123, PF-123456
    r'([A-Z][a-z]+(?:umab|mab|ximab))', # Pembrolizumab, antibodies
    r'([A-Z][a-z]+(?:nib|tinib))',      # Kinase inhibitors
    r'([A-Z][a-z]+(?:statin|dipine|pril|sartan|olol))', # Small molecules
    r'([A-Z][a-z]+(?:cycline|mycin|vir|navir))', # Anti-infectives
]

# Common words to filter out
NON_DRUGS = {
    'PLACEBO', 'CONTROL', 'SHAM', 'SALINE', 'WATER', 'PATIENT', 'PATIENTS',
    'TREATMENT', 'THERAPY', 'STUDY', 'TRIAL', 'DRUG', 'MEDICATION', 'DOSE',
    'SAFETY', 'EFFICACY', 'RESPONSE', 'OUTCOME', 'RESULT', 'EFFECT', 'LEVEL',
    'VALUE', 'CHANGE', 'INCREASE', 'DECREASE', 'IMPROVE', 'REDUCE', 'PREVENT'
}

def extract_drug_names(text):
    """Extract drug names - uses patterns that found BFKB8488"""
    if not text:
        return []
    
    drugs = set()
    text_upper = text.upper()
    
    for pattern in DRUG_PATTERNS:
        matches = re.findall(pattern, text_upper, re.IGNORECASE)
        for m in matches:
            m_clean = m.upper()
            if len(m_clean) >= 4 and m_clean not in NON_DRUGS:
                # Keep original case for display
                drugs.add(m if m.isupper() else m.capitalize())
    
    return list(drugs)[:15]

def fetch_clinical_trials(condition):
    """Fetch trials from ClinicalTrials.gov API"""
    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        'query.cond': condition,
        'pageSize': 50,
        'format': 'json',
        'sort': 'LastUpdatePostDate:desc'  # Get most recent first
    }
    
    trials = []
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            for study in data.get('studies', []):
                protocol = study.get('protocolSection', {})
                
                # Collect ALL intervention text
                intervention_texts = []
                arms = protocol.get('armsInterventionsModule', {})
                
                for arm in arms.get('armGroupList', []):
                    for inv in arm.get('interventionList', []):
                        if isinstance(inv, dict):
                            name = inv.get('interventionName', '')
                            desc = inv.get('description', '')
                            intervention_texts.append(name)
                            intervention_texts.append(desc)
                        elif isinstance(inv, str):
                            intervention_texts.append(inv)
                
                # Also check the title for drug names
                title = protocol.get('identificationModule', {}).get('briefTitle', '')
                
                trials.append({
                    'nct_id': protocol.get('identificationModule', {}).get('nctId', ''),
                    'title': title,
                    'condition': protocol.get('conditionsModule', {}).get('conditions', [''])[0],
                    'phase': ', '.join(protocol.get('designModule', {}).get('phaseList', [])),
                    'interventions': ' '.join(intervention_texts),
                    'url': f"https://clinicaltrials.gov/study/{protocol.get('identificationModule', {}).get('nctId', '')}"
                })
    except Exception as e:
        print(f"API error: {e}")
    return trials

def get_pubmed_count(drug):
    """Get publication count from PubMed"""
    try:
        resp = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={'db': 'pubmed', 'term': f'"{drug}"', 'retmax': 0, 'format': 'json'},
            timeout=15
        )
        if resp.status_code == 200:
            return int(resp.json().get('esearchresult', {}).get('count', 0))
    except:
        pass
    return 0

def calculate_novelty_score(pub_count):
    """Calculate novelty score - fewer publications = higher score"""
    if pub_count == 0:
        return 98
    elif pub_count < 5:
        return 95
    elif pub_count < 10:
        return 90
    elif pub_count < 20:
        return 85
    elif pub_count < 50:
        return 75
    elif pub_count < 100:
        return 65
    elif pub_count < 200:
        return 55
    elif pub_count < 500:
        return 45
    elif pub_count < 1000:
        return 35
    else:
        return 25

def run_research(job_id, condition):
    """Background research task"""
    research_cache[job_id] = {"status": "running", "progress": 0, "message": f"Searching trials for {condition}..."}
    
    # Fetch recent trials
    trials = fetch_clinical_trials(condition)
    research_cache[job_id]["progress"] = 30
    research_cache[job_id]["message"] = f"Found {len(trials)} trials, extracting drugs..."
    
    # Extract drugs from trials
    drug_trials = defaultdict(list)
    for trial in trials:
        drugs = extract_drug_names(trial.get('interventions', '') + " " + trial.get('title', ''))
        for drug in drugs:
            drug_trials[drug].append(trial)
    
    research_cache[job_id]["progress"] = 50
    research_cache[job_id]["message"] = f"Found {len(drug_trials)} unique drugs, analyzing..."
    
    # Analyze each drug
    analyses = []
    for i, (drug, drug_trials_list) in enumerate(list(drug_trials.items())[:30]):
        pub_count = get_pubmed_count(drug)
        score = calculate_novelty_score(pub_count)
        
        research_cache[job_id]["progress"] = 50 + int((i / min(len(drug_trials), 30)) * 40)
        research_cache[job_id]["message"] = f"Analyzing {drug} ({pub_count} pubs) - Score: {score}"
        
        # Get the most relevant trial info
        first_trial = drug_trials_list[0]
        
        analyses.append({
            "drug": drug,
            "score": score,
            "condition": first_trial.get('condition', condition),
            "publications": pub_count,
            "trials_found": len(drug_trials_list),
            "phase": first_trial.get('phase', 'Unknown'),
            "trial_url": first_trial.get('url', '#'),
            "nct_id": first_trial.get('nct_id', ''),
            "title": first_trial.get('title', '')[:100]
        })
        time.sleep(0.15)
    
    analyses.sort(key=lambda x: x["score"], reverse=True)
    
    research_cache[job_id] = {
        "status": "complete",
        "progress": 100,
        "message": f"Found {len(analyses)} novel drug candidates",
        "results": {
            "condition": condition,
            "total_trials": len(trials),
            "unique_drugs": len(analyses),
            "drugs_analyzed": analyses
        }
    }

# ============ API ENDPOINTS ============
@app.post("/api/research/start")
async def start_research(request: ResearchRequest):
    job_id = str(uuid.uuid4())
    thread = threading.Thread(target=run_research, args=(job_id, request.condition))
    thread.start()
    return {"job_id": job_id}

@app.get("/api/research/status/{job_id}")
async def get_status(job_id: str):
    return research_cache.get(job_id, {"status": "running", "progress": 0})

@app.get("/api/research/results/{job_id}")
async def get_results(job_id: str):
    job = research_cache.get(job_id, {})
    return job.get("results", {"drugs_analyzed": []})

@app.get("/api/drugs/{drug_name}")
async def get_drug_info(drug_name: str):
    pub_count = get_pubmed_count(drug_name)
    score = calculate_novelty_score(pub_count)
    return {
        "drug": drug_name,
        "score": score,
        "publications": pub_count,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/?term={drug_name}",
        "clinicaltrials_url": f"https://clinicaltrials.gov/ct2/results?term={drug_name}"
    }

# HTML Page
HTML_PAGE = '''<!DOCTYPE html>
<html>
<head>
    <title>DrugHound Enterprise - Dynamic Discovery</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #0f0f23; color: #e0e0e0; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .card { background: #1a1a3e; border-radius: 15px; padding: 25px; margin-bottom: 20px; }
        .search-box { display: flex; gap: 15px; margin: 20px 0; flex-wrap: wrap; }
        .search-input { flex: 1; padding: 15px; background: #2a2a4a; border: 1px solid #3a3a5a; border-radius: 8px; color: white; font-size: 16px; }
        .btn { background: #00d4ff; color: #0f0f23; padding: 15px 30px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 16px; }
        .progress-bar { height: 10px; background: #2a2a4a; border-radius: 5px; margin: 15px 0; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #00d4ff, #00ff88); width: 0%; transition: width 0.5s; }
        .drug-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 15px; margin-top: 20px; }
        .drug-card { background: linear-gradient(135deg, #1a1a3e, #0f0f23); border-radius: 10px; padding: 15px; cursor: pointer; border: 1px solid #2a2a4a; transition: all 0.3s; }
        .drug-card:hover { border-color: #00d4ff; transform: translateY(-3px); }
        .drug-name { font-size: 18px; font-weight: bold; color: #00d4ff; margin-bottom: 8px; }
        .score { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; background: #00ff8844; color: #00ff88; margin-bottom: 8px; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; align-items: center; justify-content: center; }
        .modal-content { background: #1a1a3e; max-width: 600px; width: 90%; padding: 25px; border-radius: 15px; }
        .close { float: right; font-size: 28px; cursor: pointer; color: #00d4ff; }
        .spinner { width: 50px; height: 50px; border: 3px solid #2a2a4a; border-top-color: #00d4ff; border-radius: 50%; animation: spin 1s linear infinite; margin: 20px auto; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 15px 0; }
        .stat-card { background: #2a2a4a; padding: 15px; border-radius: 10px; text-align: center; }
        .stat-number { font-size: 28px; font-weight: bold; color: #00d4ff; }
        .loading { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 999; align-items: center; justify-content: center; flex-direction: column; }
        a { color: #00d4ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .trial-link { font-size: 11px; color: #888; margin-top: 8px; }
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        <h2>🐕 DrugHound Enterprise - Dynamic Discovery</h2>
        <p>Mining recent clinical trials for NOVEL drug candidates | Higher score = More novel (fewer publications)</p>
        
        <div class="search-box">
            <input type="text" id="condition" class="search-input" placeholder="Enter disease (cancer, diabetes, alzheimers)" value="cancer">
            <button class="btn" onclick="startResearch()">🔬 Discover Novel Drugs</button>
        </div>
        
        <div id="progressArea" style="display:none;">
            <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
            <p id="progressMsg"></p>
        </div>
    </div>
    
    <div id="resultsArea" style="display:none;">
        <div class="card">
            <h3>📊 Novel Drug Candidates (from recent trials)</h3>
            <div id="resultsSummary"></div>
            <div id="drugResults" class="drug-grid"></div>
        </div>
    </div>
</div>

<div id="drugModal" class="modal">
    <div class="modal-content">
        <span class="close" onclick="closeModal()">&times;</span>
        <div id="modalContent"></div>
    </div>
</div>

<div id="loadingModal" class="loading">
    <div class="spinner"></div>
    <p>Analyzing clinical trials...</p>
</div>

<script>
let currentJobId = null, pollInterval = null;

function displayDrugCards(drugs, containerId) {
    const container = document.getElementById(containerId);
    if (!drugs || drugs.length === 0) {
        container.innerHTML = '<p>No novel drugs found. Try a different condition.</p>';
        return;
    }
    container.innerHTML = drugs.map(d => `
        <div class="drug-card" onclick="showDrugDetails('${d.drug}')">
            <div class="drug-name">💊 ${d.drug}</div>
            <span class="score">Novelty Score: ${d.score}</span>
            <div>📚 ${d.publications.toLocaleString()} publications</div>
            <div>🔬 ${d.trials_found} clinical ${d.trials_found === 1 ? 'trial' : 'trials'}</div>
            <div class="trial-link">📋 ${d.nct_id || 'N/A'} - ${d.title ? d.title.substring(0, 60) + '...' : ''}</div>
        </div>
    `).join('');
}

async function startResearch() {
    const condition = document.getElementById('condition').value;
    if (!condition) { alert('Enter a condition'); return; }
    
    document.getElementById('progressArea').style.display = 'block';
    document.getElementById('resultsArea').style.display = 'none';
    document.getElementById('progressFill').style.width = '0%';
    
    const resp = await fetch('/api/research/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ condition: condition })
    });
    const data = await resp.json();
    currentJobId = data.job_id;
    
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(async () => {
        const status = await (await fetch(`/api/research/status/${currentJobId}`)).json();
        document.getElementById('progressFill').style.width = `${status.progress}%`;
        document.getElementById('progressMsg').innerHTML = status.message || `${status.progress}%`;
        if (status.status === 'complete') {
            clearInterval(pollInterval);
            const results = await (await fetch(`/api/research/results/${currentJobId}`)).json();
            document.getElementById('resultsSummary').innerHTML = `
                <div class="stat-grid">
                    <div class="stat-card"><div class="stat-number">${results.unique_drugs || 0}</div><div>Novel Drugs Found</div></div>
                    <div class="stat-card"><div class="stat-number">${results.total_trials || 0}</div><div>Trials Analyzed</div></div>
                </div>
            `;
            if (results.drugs_analyzed) displayDrugCards(results.drugs_analyzed, 'drugResults');
            document.getElementById('resultsArea').style.display = 'block';
        }
    }, 2000);
}

async function showDrugDetails(drugName) {
    document.getElementById('loadingModal').style.display = 'flex';
    const data = await (await fetch(`/api/drugs/${encodeURIComponent(drugName)}`)).json();
    document.getElementById('modalContent').innerHTML = `
        <h2>💊 ${data.drug}</h2>
        <div class="stat-grid">
            <div class="stat-card"><div class="stat-number">${data.score}</div><div>Novelty Score</div></div>
            <div class="stat-card"><div class="stat-number">${data.publications.toLocaleString()}</div><div>Publications</div></div>
        </div>
        <p><strong>Repurposing Potential:</strong> ${data.publications < 20 ? '🔥 EXCELLENT - Very understudied drug' : data.publications < 100 ? '📈 GOOD - Promising candidate' : '📊 MODERATE - More research needed'}</p>
        <p><a href="${data.url}" target="_blank">📚 View on PubMed</a></p>
        <p><a href="${data.clinicaltrials_url}" target="_blank">🔬 View Clinical Trials</a></p>
        <hr>
        <p><small>Novelty Score Formula: Fewer publications = Higher score (0 pubs = 98, 500+ pubs = 45)</small></p>
    `;
    document.getElementById('drugModal').style.display = 'flex';
    document.getElementById('loadingModal').style.display = 'none';
}

function closeModal() { document.getElementById('drugModal').style.display = 'none'; }
</script>
</body>
</html>'''

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(content=HTML_PAGE)

if __name__ == "__main__":
    print("="*60)
    print("🐕 DrugHound Enterprise - Dynamic Discovery (Restored)")
    print("="*60)
    print("✅ Extracts drug codes like BFKB8488 from recent trials")
    print("✅ Links to specific trial pages (not just search)")
    print("✅ Scores based on publication count (fewer = more novel)")
    print("🌐 http://localhost:8000")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
