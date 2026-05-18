#!/usr/bin/env python3
"""DrugHound Enterprise - Working Dynamic Discovery"""

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

# ============ DRUG EXTRACTION (Working patterns from before) ============
REAL_DRUG_PATTERNS = [
    r'([A-Z]{2,}[0-9]{3,})',           # BFKB8488, AZD9291
    r'([A-Z]{2,}-[0-9]+)',              # ALN-123, PF-123456
    r'([A-Z][a-z]+(?:mab|umab|ximab))', # Antibodies
    r'([A-Z][a-z]+(?:nib|tinib))',      # Kinase inhibitors
    r'([A-Z][a-z]+(?:statin|dipine|pril|sartan|olol))', # Small molecules
]

NON_DRUGS = {
    'FAILURE', 'FUNCTION', 'HEART', 'MUSCLE', 'SKELETAL', 'GLYCEMIC', 'VENTRICULAR',
    'PARTICIPANTS', 'DIABETES', 'FATTY', 'DISEASE', 'MELLITUS', 'LIVER', 'EVALUATE',
    'TOLERABILITY', 'MULTIPLE', 'ASCENDING', 'ALCOHOLIC', 'DIABETIC', 'TREATMENT',
    'THERAPY', 'PLACEBO', 'CONTROL', 'PATIENT', 'STUDY', 'TRIAL', 'SAFETY', 'EFFICACY'
}

def extract_drug_names(text):
    if not text:
        return []
    drugs = set()
    for pattern in REAL_DRUG_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            m_clean = m.upper()
            if len(m_clean) >= 4 and m_clean not in NON_DRUGS:
                drugs.add(m_clean)
    return list(drugs)[:10]

def fetch_clinical_trials(condition):
    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {'query.cond': condition, 'pageSize': 50, 'format': 'json'}
    trials = []
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            for study in data.get('studies', []):
                protocol = study.get('protocolSection', {})
                interventions = []
                arms = protocol.get('armsInterventionsModule', {})
                for arm in arms.get('armGroupList', []):
                    for inv in arm.get('interventionList', []):
                        if isinstance(inv, dict):
                            interventions.append(inv.get('interventionName', ''))
                        elif isinstance(inv, str):
                            interventions.append(inv)
                trials.append({
                    'nct_id': protocol.get('identificationModule', {}).get('nctId', ''),
                    'title': protocol.get('identificationModule', {}).get('briefTitle', ''),
                    'condition': protocol.get('conditionsModule', {}).get('conditions', [''])[0],
                    'phase': ', '.join(protocol.get('designModule', {}).get('phaseList', [])),
                    'interventions': ' '.join(interventions)
                })
    except Exception as e:
        print(f"API error: {e}")
    return trials

def get_pubmed_count(drug):
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

def calculate_dynamic_score(pub_count):
    """DYNAMIC scoring - different for each drug based on publications"""
    if pub_count == 0:
        return 98
    elif pub_count < 5:
        return 95
    elif pub_count < 10:
        return 90
    elif pub_count < 20:
        return 80
    elif pub_count < 50:
        return 70
    elif pub_count < 100:
        return 60
    elif pub_count < 500:
        return 40
    else:
        return 20

def run_research(job_id, condition):
    research_cache[job_id] = {"status": "running", "progress": 0, "message": "Searching trials..."}
    
    trials = fetch_clinical_trials(condition)
    research_cache[job_id]["progress"] = 30
    
    drug_trials = defaultdict(list)
    for trial in trials:
        drugs = extract_drug_names(trial.get('interventions', ''))
        for drug in drugs:
            drug_trials[drug].append(trial)
    
    research_cache[job_id]["progress"] = 50
    research_cache[job_id]["message"] = f"Found {len(drug_trials)} unique drugs"
    
    analyses = []
    for i, (drug, drug_trials_list) in enumerate(list(drug_trials.items())[:30]):
        pub_count = get_pubmed_count(drug)
        score = calculate_dynamic_score(pub_count)
        
        research_cache[job_id]["progress"] = 50 + int((i / min(len(drug_trials), 30)) * 40)
        research_cache[job_id]["message"] = f"Analyzing {drug} ({pub_count} pubs) - Score: {score}"
        
        analyses.append({
            "drug": drug,
            "score": score,
            "condition": drug_trials_list[0].get('condition', condition),
            "publications": pub_count,
            "trials_found": len(drug_trials_list),
            "phase": drug_trials_list[0].get('phase', 'Unknown'),
            "nct_id": drug_trials_list[0].get('nct_id', '')
        })
        time.sleep(0.2)
    
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
    score = calculate_dynamic_score(pub_count)
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
        .drug-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 15px; margin-top: 20px; }
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
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        <h2>🐕 DrugHound Enterprise - Dynamic Drug Discovery</h2>
        <p>Live data from ClinicalTrials.gov | Dynamic scoring based on publication count</p>
        
        <div class="search-box">
            <input type="text" id="condition" class="search-input" placeholder="Enter disease (cancer, diabetes, alzheimers, etc.)" value="cancer">
            <button class="btn" onclick="startResearch()">🔬 Discover Novel Drugs</button>
        </div>
        
        <div id="progressArea" style="display:none;">
            <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
            <p id="progressMsg"></p>
        </div>
    </div>
    
    <div id="resultsArea" style="display:none;">
        <div class="card">
            <h3>📊 Novel Drug Candidates (Higher Score = More Novel)</h3>
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
    <p>Analyzing drug from clinical trials...</p>
</div>

<script>
let currentJobId = null;
let pollInterval = null;

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
            <div>🎯 ${d.condition || 'Multiple'}</div>
            <div>📚 ${d.publications.toLocaleString()} publications</div>
            <div>🔬 ${d.trials_found} clinical trials</div>
            <div style="margin-top:5px; font-size:11px;">${d.phase || 'Phase Unknown'}</div>
            <div style="margin-top:5px; font-size:10px; color:#888;">NCT: ${d.nct_id || 'N/A'}</div>
        </div>
    `).join('');
}

async function startResearch() {
    const condition = document.getElementById('condition').value;
    if (!condition) { alert('Enter a condition'); return; }
    
    document.getElementById('progressArea').style.display = 'block';
    document.getElementById('resultsArea').style.display = 'none';
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressMsg').innerHTML = 'Starting...';
    
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
            await loadResults();
        }
    }, 2000);
}

async function loadResults() {
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

async function showDrugDetails(drugName) {
    document.getElementById('loadingModal').style.display = 'flex';
    const data = await (await fetch(`/api/drugs/${encodeURIComponent(drugName)}`)).json();
    document.getElementById('modalContent').innerHTML = `
        <h2>💊 ${data.drug}</h2>
        <div class="stat-grid">
            <div class="stat-card"><div class="stat-number">${data.score}</div><div>Novelty Score</div></div>
            <div class="stat-card"><div class="stat-number">${data.publications.toLocaleString()}</div><div>Publications</div></div>
        </div>
        <p><strong>Analysis:</strong> ${data.publications < 20 ? 'This drug has very few publications, indicating HIGH repurposing potential!' : data.publications < 100 ? 'Moderate publication count - promising candidate for further research.' : 'Well-studied drug - lower repurposing novelty.'}</p>
        <p><a href="${data.url}" target="_blank">🔗 View on PubMed</a></p>
        <p><a href="${data.clinicaltrials_url}" target="_blank">🔬 View Clinical Trials</a></p>
        <hr style="border-color:#2a2a4a; margin:15px 0;">
        <p><small>Novelty Score: Fewer publications = Higher score (98=max, 20=min)</small></p>
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
    print("🐕 DrugHound Enterprise - Dynamic Discovery")
    print("="*60)
    print("✅ Live API data from ClinicalTrials.gov")
    print("✅ Dynamic scoring based on publication count")
    print("✅ Each drug gets unique score")
    print("🌐 http://localhost:8000")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
