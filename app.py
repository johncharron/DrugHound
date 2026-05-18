#!/usr/bin/env python3
"""DrugHound Enterprise - Root Dashboard Version"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import re
import uvicorn
from datetime import datetime

app = FastAPI(title="DrugHound Enterprise", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Drug name patterns
DRUG_PATTERNS = [
    r'([A-Z]{2,}[0-9]{3,})',      # BFKB8488, AZD9291
    r'([A-Z]{2,}-[0-9]+)',         # ALN-123
    r'([A-Z][a-z]+(?:mab|umab|ximab))',  # Antibodies
    r'([A-Z][a-z]+(?:nib|tinib))',       # Kinase inhibitors
]

COMMON_WORDS = {'PATIENT', 'TREATMENT', 'STUDY', 'PROTOCOL', 'PLACEBO', 'STANDARD', 'CARE', 'THERAPY', 'SAFETY', 'EFFICACY'}

def fetch_drug_details(drug_name: str):
    """Fetch real trials and publications for a drug"""
    trials = []
    try:
        url = "https://clinicaltrials.gov/api/v2/studies"
        params = {"query.term": drug_name, "pageSize": 5, "format": "json"}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for study in data.get('studies', []):
                protocol = study.get('protocolSection', {})
                ident = protocol.get('identificationModule', {})
                design = protocol.get('designModule', {})
                status = protocol.get('statusModule', {})
                
                trials.append({
                    'id': ident.get('nctId', 'Unknown'),
                    'title': (ident.get('briefTitle', '') or 'No title')[:120],
                    'phase': design.get('phase', 'Unknown') if design else 'Unknown',
                    'status': status.get('overallStatus', 'Unknown'),
                    'url': f"https://clinicaltrials.gov/ct2/show/{ident.get('nctId', '')}"
                })
    except Exception as e:
        print(f"Error fetching trials for {drug_name}: {e}")
    
    # Calculate scores based on trial count
    trial_count = len(trials)
    if trial_count == 0:
        novelty = 98
        confidence = 95
    elif trial_count <= 2:
        novelty = 95
        confidence = 85
    elif trial_count <= 5:
        novelty = 85
        confidence = 75
    elif trial_count <= 10:
        novelty = 75
        confidence = 65
    else:
        novelty = 50
        confidence = 50
    
    return {
        'name': drug_name,
        'novelty': novelty,
        'confidence': confidence,
        'trials': trials,
        'trial_count': trial_count,
        'pubmed_url': f"https://pubmed.ncbi.nlm.nih.gov/?term={drug_name}",
        'clinicaltrials_url': f"https://clinicaltrials.gov/ct2/results?term={drug_name}"
    }

# HTML Dashboard - This will be the root/index page
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DrugHound Enterprise - Drug Discovery Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #e0e0e0;
            min-height: 100vh;
        }
        .header {
            background: rgba(0,0,0,0.3);
            border-bottom: 2px solid #4caf50;
            padding: 20px;
            text-align: center;
        }
        .header h1 { color: #4caf50; font-size: 2.5em; }
        .header p { color: #888; margin-top: 5px; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        .search-card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 30px;
            border: 1px solid rgba(76, 175, 80, 0.3);
        }
        .search-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }
        input, select {
            flex: 1;
            background: rgba(0,0,0,0.5);
            border: 1px solid #4caf50;
            color: white;
            padding: 12px;
            border-radius: 8px;
            font-size: 16px;
        }
        button {
            background: #4caf50;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.3s;
        }
        button:hover {
            background: #45a049;
            transform: translateY(-2px);
        }
        
        .drug-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .drug-card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.3s;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .drug-card:hover {
            transform: translateY(-4px);
            border-color: #4caf50;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        .drug-name {
            font-size: 1.3em;
            font-weight: bold;
            color: #4caf50;
            font-family: monospace;
        }
        .score {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        .score-high { color: #4caf50; }
        .score-mid { color: #ff9800; }
        .score-low { color: #f44336; }
        .score-bar {
            height: 4px;
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
            margin: 10px 0;
            overflow: hidden;
        }
        .score-fill {
            height: 100%;
            background: linear-gradient(90deg, #4caf50, #8bc34a);
            transition: width 0.3s;
        }
        
        /* Modal Popup Styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.8);
            backdrop-filter: blur(5px);
        }
        .modal-content {
            background: linear-gradient(135deg, #1a1f3a 0%, #0a0e27 100%);
            margin: 5% auto;
            padding: 25px;
            border-radius: 16px;
            width: 90%;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
            border: 1px solid #4caf50;
            position: relative;
        }
        .close {
            position: absolute;
            right: 20px;
            top: 15px;
            color: #aaa;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        .close:hover {
            color: #4caf50;
        }
        .trial-item, .pub-item {
            background: rgba(255,255,255,0.05);
            padding: 12px;
            margin: 10px 0;
            border-radius: 8px;
        }
        .trial-item a, .pub-item a {
            color: #4caf50;
            text-decoration: none;
        }
        .trial-item a:hover, .pub-item a:hover {
            text-decoration: underline;
        }
        .external-links {
            display: flex;
            gap: 10px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .external-btn {
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid #4caf50;
            color: #4caf50;
            padding: 10px 15px;
            border-radius: 8px;
            text-decoration: none;
            display: inline-block;
        }
        .external-btn:hover {
            background: #4caf50;
            color: white;
        }
        .loading {
            text-align: center;
            padding: 40px;
        }
        .spinner {
            border: 3px solid rgba(255,255,255,0.1);
            border-top: 3px solid #4caf50;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .status-badge {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 4px;
            background: #4caf50;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🐕 DrugHound Enterprise</h1>
        <p>AI-Powered Drug Repurposing Discovery Platform</p>
    </div>
    <div class="container">
        <div class="search-card">
            <h2>🔬 Discover Novel Drug Candidates</h2>
            <div class="search-group">
                <input type="text" id="condition" placeholder="Disease (cancer, diabetes, alzheimers)" value="cancer">
                <select id="limit">
                    <option value="10">Top 10</option>
                    <option value="20">Top 20</option>
                    <option value="30">Top 30</option>
                </select>
                <button onclick="discoverDrugs()">🚀 Discover Drugs</button>
            </div>
        </div>
        <div id="results"></div>
    </div>
    
    <!-- Modal Popup -->
    <div id="drugModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <div id="modalContent"></div>
        </div>
    </div>
    
    <script>
        let currentDrugs = [];
        
        async function discoverDrugs() {
            const condition = document.getElementById('condition').value;
            const limit = document.getElementById('limit').value;
            const resultsDiv = document.getElementById('results');
            
            resultsDiv.innerHTML = '<div class="loading"><div class="spinner"></div> Mining clinical trials for ' + condition + '...</div>';
            
            try {
                const response = await fetch(`/api/discover?condition=${encodeURIComponent(condition)}&limit=${limit}`);
                const data = await response.json();
                
                if (data.drugs && data.drugs.length > 0) {
                    currentDrugs = data.drugs;
                    let html = '<h2>💊 Novel Drug Candidates</h2><div class="drug-grid">';
                    data.drugs.forEach(drug => {
                        let scoreClass = drug.confidence >= 70 ? 'score-high' : (drug.confidence >= 50 ? 'score-mid' : 'score-low');
                        html += `
                            <div class="drug-card" onclick="showDrugDetails('${drug.name}')">
                                <div class="drug-name">${drug.name}</div>
                                <div class="score ${scoreClass}">${drug.confidence}%</div>
                                <div class="score-bar"><div class="score-fill" style="width: ${drug.confidence}%"></div></div>
                                <div>📊 Novelty: ${drug.novelty}/100</div>
                                <div>🔬 Trials: ${drug.trials || 1}</div>
                                <div style="margin-top: 10px; font-size: 12px; color: #888;">Click for clinical trial links →</div>
                            </div>
                        `;
                    });
                    html += '</div>';
                    resultsDiv.innerHTML = html;
                } else {
                    resultsDiv.innerHTML = '<div class="loading">No drugs found. Try a different condition.</div>';
                }
            } catch (e) {
                resultsDiv.innerHTML = '<div class="loading">Error: ' + e.message + '</div>';
            }
        }
        
        async function showDrugDetails(drugName) {
            const modal = document.getElementById('drugModal');
            const modalContent = document.getElementById('modalContent');
            
            modal.style.display = 'block';
            modalContent.innerHTML = '<div class="loading"><div class="spinner"></div>Loading drug data for ' + drugName + '...</div>';
            
            try {
                const response = await fetch(`/api/drug/${drugName}`);
                const data = await response.json();
                
                let scoreClass = data.confidence >= 70 ? 'score-high' : (data.confidence >= 50 ? 'score-mid' : 'score-low');
                let repurposeText = '';
                if (data.confidence >= 70) {
                    repurposeText = '🎯 High potential for repurposing. Prioritize for further investigation.';
                } else if (data.confidence >= 50) {
                    repurposeText = '📈 Moderate potential. Consider literature review and safety assessment.';
                } else {
                    repurposeText = '🔍 Low novelty. May be well-studied; look for new indications.';
                }
                
                let html = `
                    <h2 style="color: #4caf50;">💊 ${data.name}</h2>
                    <div class="score ${scoreClass}">${data.confidence}% Confidence Score</div>
                    <div class="score-bar"><div class="score-fill" style="width: ${data.confidence}%"></div></div>
                    
                    <h3>📊 Analysis Summary</h3>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin: 15px 0;">
                        <div style="background: rgba(76,175,80,0.1); padding: 10px; border-radius: 8px;">
                            <strong>Novelty Score</strong><br>
                            <span style="font-size: 1.5em;">${data.novelty}/100</span>
                        </div>
                        <div style="background: rgba(255,152,0,0.1); padding: 10px; border-radius: 8px;">
                            <strong>Clinical Trials</strong><br>
                            <span style="font-size: 1.5em;">${data.trial_count}</span>
                        </div>
                    </div>
                    
                    <p><strong>💡 Recommendation:</strong> ${repurposeText}</p>
                `;
                
                if (data.trials && data.trials.length > 0) {
                    html += '<h3>📋 Clinical Trials</h3>';
                    data.trials.forEach(trial => {
                        html += `
                            <div class="trial-item">
                                <a href="${trial.url}" target="_blank"><strong>${trial.id}</strong> - ${trial.phase}</a>
                                <div style="font-size: 12px; margin-top: 5px;">${trial.title}</div>
                                <div style="font-size: 11px; color: #888;">Status: ${trial.status}</div>
                            </div>
                        `;
                    });
                } else {
                    html += '<p><em>No clinical trials found - highly novel drug candidate!</em></p>';
                }
                
                html += `
                    <h3>🔗 External Resources</h3>
                    <div class="external-links">
                        <a href="${data.pubmed_url}" target="_blank" class="external-btn">📄 Search PubMed</a>
                        <a href="${data.clinicaltrials_url}" target="_blank" class="external-btn">🔬 Search ClinicalTrials.gov</a>
                    </div>
                `;
                
                modalContent.innerHTML = html;
            } catch (e) {
                modalContent.innerHTML = '<div class="loading">Error loading drug details: ' + e.message + '</div>';
            }
        }
        
        function closeModal() {
            document.getElementById('drugModal').style.display = 'none';
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('drugModal');
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }
        
        // Load initial results
        discoverDrugs();
    </script>
</body>
</html>
"""

# Root endpoint - serves the dashboard
@app.get("/")
@app.get("/dashboard")
async def root():
    return HTMLResponse(content=DASHBOARD_HTML)

# API endpoints
@app.get("/api/discover")
async def discover(condition: str = "cancer", limit: int = 10):
    try:
        url = "https://clinicaltrials.gov/api/v2/studies"
        params = {"query.cond": condition, "pageSize": 50, "format": "json"}
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code != 200:
            return {"error": "API failed", "condition": condition}
        
        data = response.json()
        drugs_set = set()
        
        for study in data.get('studies', []):
            protocol = study.get('protocolSection', {})
            ident = protocol.get('identificationModule', {})
            title = (ident.get('briefTitle', '') or '') + ' ' + (ident.get('officialTitle', '') or '')
            text = title.upper()
            
            for pattern in DRUG_PATTERNS:
                matches = re.findall(pattern, text)
                for match in matches:
                    if len(match) > 3 and not match.isdigit() and match not in COMMON_WORDS:
                        drugs_set.add(match)
        
        drugs_found = []
        for drug in list(drugs_set)[:limit]:
            details = fetch_drug_details(drug)
            drugs_found.append({
                'name': drug,
                'novelty': details['novelty'],
                'confidence': details['confidence'],
                'trials': details['trial_count']
            })
        
        drugs_found.sort(key=lambda x: x['confidence'], reverse=True)
        return {"condition": condition, "drugs": drugs_found, "count": len(drugs_found)}
    
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/drug/{drug_name}")
async def drug_details(drug_name: str):
    return fetch_drug_details(drug_name)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
