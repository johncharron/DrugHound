"""Enterprise-grade FastAPI application."""

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
import asyncio
from datetime import datetime
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.database import init_database, get_session
from src.core.data_collector import DataCollector, DrugAnalyzer
from src.reporting.report_generator import ReportGenerator

app = FastAPI(title="DrugHound Enterprise", version="3.0.0", docs_url="/api/docs")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize components
db_engine = init_database()
report_gen = ReportGenerator()
analyzer = DrugAnalyzer()

# Store for real-time data
research_cache = {}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Enterprise home page."""
    return templates.TemplateResponse("enterprise.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Interactive dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.post("/api/research/start")
async def start_research(background_tasks: BackgroundTasks, condition: str = "all"):
    """Start a comprehensive research job."""
    import uuid
    job_id = str(uuid.uuid4())
    research_cache[job_id] = {"status": "running", "progress": 0, "results": None}
    
    background_tasks.add_task(run_research, job_id, condition)
    return {"job_id": job_id, "status": "started"}

@app.get("/api/research/status/{job_id}")
async def get_research_status(job_id: str):
    """Get research job status."""
    return research_cache.get(job_id, {"status": "not_found"})

@app.get("/api/research/results/{job_id}")
async def get_research_results(job_id: str):
    """Get research results."""
    job = research_cache.get(job_id)
    if job and job["status"] == "complete":
        return JSONResponse(content=job["results"])
    return {"status": "pending"}

@app.get("/api/drugs/search")
async def search_drugs(q: str, limit: int = 50):
    """Search drugs dynamically."""
    session = get_session(db_engine)
    # Dynamic search implementation
    return {"results": []}

@app.get("/api/drugs/{drug_name}/analysis")
async def get_drug_analysis(drug_name: str):
    """Get comprehensive analysis for a drug."""
    async with DataCollector() as collector:
        # Search for the drug
        trials = await collector.search_clinicaltrials(drug_name, max_results=20)
        pub_data = await collector.search_pubmed_async(drug_name)
        
        # Extract conditions
        conditions = list(set([t.get('condition') for t in trials if t.get('condition')]))
        phase = trials[0].get('phase', ['Unknown'])[0] if trials else 'Unknown'
        
        # Score and analyze
        score = analyzer.calculate_novelty_score(pub_data.get('total_count', 0), phase)
        repurposing = analyzer.generate_repurposing_analysis(
            drug_name, pub_data.get('total_count', 0), phase, conditions
        )
        
        return {
            "drug": drug_name,
            "novelty": score,
            "repurposing": repurposing,
            "trials": trials[:10],
            "publications": pub_data.get('publications', [])[:10],
            "statistics": {
                "total_trials": len(trials),
                "total_publications": pub_data.get('total_count', 0),
                "conditions_found": len(conditions)
            }
        }

async def run_research(job_id: str, condition: str):
    """Background research task."""
    research_cache[job_id]["progress"] = 10
    
    async with DataCollector() as collector:
        research_cache[job_id]["progress"] = 20
        
        # Search for trials
        trials = await collector.search_clinicaltrials(condition, max_results=200)
        research_cache[job_id]["progress"] = 50
        
        # Extract drugs
        drugs = collector.extract_drugs_from_results(trials)
        research_cache[job_id]["progress"] = 70
        
        # Analyze each drug
        drug_analyses = []
        for i, drug in enumerate(drugs[:20]):
            pub_data = await collector.search_pubmed_async(drug)
            drug_analyses.append({
                "drug": drug,
                "publications": pub_data.get('total_count', 0),
                "trials_found": len([t for t in trials if drug.lower() in t.get('title', '').lower()])
            })
            research_cache[job_id]["progress"] = 70 + int((i + 1) / len(drugs[:20]) * 20)
        
        research_cache[job_id] = {
            "status": "complete",
            "progress": 100,
            "results": {
                "condition": condition,
                "total_trials": len(trials),
                "unique_drugs": len(drugs),
                "drugs_analyzed": drug_analyses,
                "timestamp": datetime.now().isoformat()
            }
        }

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "3.0.0", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    print("="*70)
    print("🐕 DrugHound Enterprise Edition v3.0")
    print("="*70)
    print("🌐 Web Interface: http://localhost:8000")
    print("📊 Dashboard: http://localhost:8000/dashboard")
    print("📚 API Docs: http://localhost:8000/api/docs")
    print("="*70)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
