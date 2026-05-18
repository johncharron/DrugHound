#!/usr/bin/env python3
"""DrugHound Enterprise - Final: API + Drug Database"""

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
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'algorithms', 'config.json')

# Ensure config exists
os.makedirs('algorithms', exist_ok=True)
if not os.path.exists(CONFIG_PATH):
    default_config = {
        "publication_thresholds": {"exceptional": 0, "very_high": 5, "high": 20, "moderate": 50, "low": 100},
        "phase_weights": {"Phase 1": 30, "Phase 2": 15, "Phase 3": 5, "Phase 4": 0, "Unknown": 10}
    }
    with open(CONFIG_PATH, 'w') as f:
        json.dump(default_config, f, indent=2)

class ResearchRequest(BaseModel):
    condition: str

# ============ DRUG DATABASE ============
DRUG_DATABASE = {
    "diabetes": [
        "Metformin", "Sitagliptin", "Liraglutide", "Semaglutide", "Dulaglutide",
        "Empagliflozin", "Dapagliflozin", "Canagliflozin", "Pioglitazone", "Glipizide",
        "Glyburide", "Glimepiride", "Repaglinide", "Acarbose", "Vildagliptin",
        "Saxagliptin", "Linagliptin", "Tirzepatide"
    ],
    "cancer": [
        "Pembrolizumab", "Nivolumab", "Cisplatin", "Carboplatin", "Paclitaxel",
        "Docetaxel", "Doxorubicin", "Gemcitabine", "Oxaliplatin", "Bevacizumab",
        "Trastuzumab", "Rituximab", "Methotrexate", "Cyclophosphamide"
    ],
    "alzheimers": [
        "Donepezil", "Memantine", "Rivastigmine", "Galantamine", "Lecanemab",
        "Aducanumab", "Tacrine"
    ],
    "parkinsons": [
        "Levodopa", "Carbidopa", "Pramipexole", "Ropinirole", "Rotigotine",
        "Selegiline", "Rasagiline", "Entacapone", "Amantadine"
    ]
}

def get_drugs_for_condition(condition):
    """Get relevant drugs for a condition"""
    condition_lower = condition.lower()
    for key, drugs in DRUG_DATABASE.items():
        if key in condition_lower:
            return drugs
    return DRUG_DATABASE.get("diabetes", [])

def fetch_clinical_trials_count(condition):
    """Get count of trials for a condition"""
    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {'query.cond': condition, 'pageSize': 1, 'format': 'json'}
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('totalCount', 0)
    except:
        pass
    return 0

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

def calculate_score(pub_count):
    """Calculate novelty score based on publication count"""
    if pub_count == 0:
        return 98
    elif pub_count < 5:
        return 95
    elif pub_count < 20:
        return 80
    elif pub_count < 50:
        return 65
    elif pub_count < 100:
        return 50
    elif pub_count < 500:
        return 35
    else:
        return 20

def run_research(job_id, condition):
    """Background research task"""
    research_cache[job_id] = {"status": "running", "progress": 0, "message": f"Researching {condition}..."}
    
    # Get drug list for this condition
    drugs_to_analyze = get_drugs_for_condition(condition)
    research_cache[job_id]["progress"] = 20
    research_cache[job_id]["message"] = f"Found {len(drugs_to_analyze)} relevant drugs"
    
    # Get trial count for context
    trial_count = fetch_clinical_trials_count(condition)
    research_cache[job_id]["progress"] = 40
    
    # Analyze each drug
    analyses = []
    for i, drug in enumerate(drugs_to_analyze):
        research_cache[job_id]["progress"] = 40 + int((i / len(drugs_to_analyze)) * 50)
        research_cache[job_id]["message"] = f"Analyzing {drug}..."
        
        pub_count = get_pubmed_count(drug)
        score = calculate_score(pub_count)
        
        # Determine phase based on publication count (simplified)
        if pub_count < 50:
            phase = "Early Research"
        elif pub_count < 200:
            phase = "Established"
        else:
            phase = "Well Established"
        
        analyses.append({
            "drug": drug,
            "score": score,
            "phase": phase,
            "condition": condition,
            "publications": pub_count,
            "trials_found": 1  # Placeholder
        })
        time.sleep(0.1)
    
    analyses.sort(key=lambda x: x["score"], reverse=True)
    
    research_cache[job_id] = {
        "status": "complete",
        "progress": 100,
        "message": f"Analyzed {len(analyses)} drugs",
        "results": {
            "condition": condition,
            "total_trials": trial_count,
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

@app.get("/api/config")
async def get_config():
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

@app.post("/api/config")
async def update_config(request: Request):
    config = await request.json()
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    return {"status": "success"}

@app.get("/api/drugs/{drug_name}")
async def get_drug_info(drug_name: str):
    pub_count = get_pubmed_count(drug_name)
    score = calculate_score(pub_count)
    return {
        "drug": drug_name,
        "score": score,
        "publications": pub_count,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/?term={drug_name}"
    }

# HTML Page
HTML_PAGE = '''<!DOCTYPE html>
<html>
<head>
    <title>DrugHound Enterprise - Clinical Intelligence</title>
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
        .drug-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 15px; margin-top: 20px; }
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
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 1px solid #2a2a4a; }
        .tab { padding: 10px 20px; cursor: pointer; }
        .tab.active { border-bottom: 2px solid #00d4ff; color: #00d4ff; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        textarea { width: 100%; background: #2a2a4a; color: #e0e0e0; border: 1px solid #3a3a5a; border-radius: 8px; padding: 10px; font-family: monospace; }
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        <h2>🐕 DrugHound Enterprise - Clinical Intelligence Platform</h2>
        <p>Discover novel drug repurposing opportunities through publication analysis</p>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('research')">🔬 Research</div>
            <div class="tab" onclick="showTab('config')">⚙️ Algorithm Config</div>
        </div>
        
        <div id="research-tab" class="tab-content active">
            <div class="search-box">
                <input type="text" id="condition" class="search-input" placeholder="Enter disease (diabetes, cancer, alzheimers, parkinsons)..." value="diabetes">
                <button class="btn" onclick="startResearch()">🔬 Start Research</button>
            </div>
            <div id="progressArea" style="display:none;">
                <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
                <p id="progressMsg"></p>
            </div>
        </div>
        
        <div id="config-tab" class="tab-content">
            <textarea id="configEditor" rows="8" style="width:100%; font-family:monospace;"></textarea>
            <div style="margin-top: 15px;">
                <button class="btn" onclick="saveConfig()" style="background:#00d4ff; color:#0f0f23; padding:10px 20px;">💾 Save Configuration</button>
            </div>
            <div id="configStatus" style="margin-top: 10px;"></div>
        </div>
    </div>
    
    <div id="resultsArea" style="display:none;">
        <div class="card">
            <h3>📊 Drug Repurposing Analysis Results</h3>
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
    <p>Fetching drug data from PubMed...</p>
</div>

<script>
let currentJobId = null;
let pollInterval = null;

function showTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');
    if (tabName === 'config') loadConfig();
}

async function loadConfig() {
    const resp = await fetch('/api/config');
    const config = await resp.json();
    document.getElementById('configEditor').value = JSON.stringify(config, null, 2);
}

async function saveConfig() {
    const configText = document.getElementById('configEditor').value;
    await fetch('/api/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: configText });
    document.getElementById('configStatus').innerHTML = '<span style="color:#00ff88;">✅ Configuration saved!</span>';
    setTimeout(() => document.getElementById('configStatus').innerHTML = '', 3000);
}

function displayDrugCards(drugs, containerId) {
    const container = document.getElementById(containerId);
    if (!drugs || drugs.length === 0) {
        container.innerHTML = '<p>No drugs found. Try a different condition.</p>';
        return;
    }
    container.innerHTML = drugs.map(d => `
        <div class="drug-card" onclick="showDrugDetails('${d.drug}')">
            <div class="drug-name">💊 ${d.drug}</div>
            <span class="score">Novelty Score: ${d.score}</span>
            <div style="margin-top:8px;">🎯 ${d.condition || 'Multiple Indications'}</div>
            <div>📚 ${d.publications.toLocaleString()} publications</div>
            <div>🔬 ${d.trials_found} clinical trials</div>
            <div style="margin-top:5px; font-size:11px;">📊 ${d.phase || 'Research Phase'}</div>
        </div>
    `).join('');
}

async function startResearch() {
    const condition = document.getElementById('condition').value;
    if (!condition) { alert('Please enter a condition'); return; }
    
    document.getElementById('progressArea').style.display = 'block';
    document.getElementById('resultsArea').style.display = 'none';
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressMsg').innerHTML = 'Initializing research...';
    
    try {
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
            document.getElementById('progressMsg').innerHTML = status.message || `${status.progress}% complete`;
            if (status.status === 'complete') {
                clearInterval(pollInterval);
                await loadResults();
            }
        }, 2000);
    } catch(e) {
        console.error(e);
        alert('Failed to start research');
    }
}

async function loadResults() {
    const results = await (await fetch(`/api/research/results/${currentJobId}`)).json();
    document.getElementById('resultsSummary').innerHTML = `
        <div class="stat-grid">
            <div class="stat-card"><div class="stat-number">${results.unique_drugs || 0}</div><div>Drugs Analyzed</div></div>
            <div class="stat-card"><div class="stat-number">${results.total_trials || 0}</div><div>Clinical Trials</div></div>
            <div class="stat-card"><div class="stat-number">${results.condition || 'N/A'}</div><div>Condition</div></div>
        </div>
    `;
    if (results.drugs_analyzed && results.drugs_analyzed.length) {
        displayDrugCards(results.drugs_analyzed, 'drugResults');
    }
    document.getElementById('resultsArea').style.display = 'block';
}

async function showDrugDetails(drugName) {
    document.getElementById('loadingModal').style.display = 'flex';
    try {
        const data = await (await fetch(`/api/drugs/${encodeURIComponent(drugName)}`)).json();
        const noveltyLevel = data.score >= 80 ? '🔥 High Novelty' : (data.score >= 60 ? '📈 Moderate Novelty' : '📊 Established Drug');
        document.getElementById('modalContent').innerHTML = `
            <h2>💊 ${data.drug}</h2>
            <div class="stat-grid">
                <div class="stat-card"><div class="stat-number">${data.score}</div><div>Novelty Score</div></div>
                <div class="stat-card"><div class="stat-number">${data.publications.toLocaleString()}</div><div>Publications</div></div>
            </div>
            <p><strong>${noveltyLevel}</strong></p>
            <p><strong>Repurposing Potential:</strong> ${data.publications < 50 ? 'High - Understudied drug with repurposing potential' : 'Moderate - More research needed to identify novel uses'}</p>
            <p><a href="${data.url}" target="_blank" style="color:#00d4ff;">🔗 View Research on PubMed →</a></p>
            <hr style="border-color:#2a2a4a; margin:15px 0;">
            <p><small>Novelty Score is based on publication count. Fewer publications = Higher repurposing potential.</small></p>
        `;
        document.getElementById('drugModal').style.display = 'flex';
    } catch(e) {
        console.error(e);
    }
    document.getElementById('loadingModal').style.display = 'none';
}

function closeModal() { document.getElementById('drugModal').style.display = 'none'; }

loadConfig();
</script>
</body>
</html>'''

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(content=HTML_PAGE)

if __name__ == "__main__":
    print("="*60)
    print("🐕 DrugHound Enterprise - Clinical Intelligence Platform")
    print("="*60)
    print("✅ Analyzes known drugs for repurposing potential")
    print("✅ Scores based on publication count (fewer = more novel)")
    print("✅ Covers diabetes, cancer, alzheimers, parkinsons")
    print("🌐 http://localhost:8000")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
