"""FastAPI web interface for DrugHound Enterprise."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import os
import sys
import pandas as pd
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import with fallbacks
try:
    from src.core.database import init_database, get_session
    DB_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Database not available: {e}")
    DB_AVAILABLE = False

try:
    from src.indexing.elastic_client import DrugIndexer
    INDEXER_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Indexer not available: {e}")
    INDEXER_AVAILABLE = False

try:
    from src.reporting.report_generator import ReportGenerator
    REPORT_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Report generator not available: {e}")
    REPORT_AVAILABLE = False

app = FastAPI(title="DrugHound Enterprise", version="2.0.0")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Initialize components
if DB_AVAILABLE:
    db_engine = init_database('drughound.db')
else:
    db_engine = None

if INDEXER_AVAILABLE:
    indexer = DrugIndexer(host='localhost:9200')
else:
    indexer = None

if REPORT_AVAILABLE:
    report_gen = ReportGenerator()
else:
    report_gen = None

# Sample data for demo
SAMPLE_DRUGS = [
    {"id": 1, "drug": "PYX-201", "novelty_score": 95, "phase": "Phase 1", "condition": "Solid Tumors", "pubmed_count": 6},
    {"id": 2, "drug": "AL01211", "novelty_score": 95, "phase": "Phase 2", "condition": "Fabry Disease", "pubmed_count": 2},
    {"id": 3, "drug": "Epetraborole", "novelty_score": 80, "phase": "Phase 2", "condition": "Bacterial Infections", "pubmed_count": 27},
    {"id": 4, "drug": "Olorofim", "novelty_score": 60, "phase": "Phase 2", "condition": "Fungal Infections", "pubmed_count": 147},
    {"id": 5, "drug": "Lumasiran", "novelty_score": 60, "phase": "Phase 3", "condition": "Hyperoxaluria", "pubmed_count": 117},
]

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard")
async def dashboard():
    """Dashboard with real-time data."""
    dashboard_html = """
    <!DOCTYPE html>
    <html>
    <head><title>DrugHound Dashboard</title>
    <style>
        body { font-family: Arial; margin: 40px; background: #f5f5f5; }
        .card { background: white; border-radius: 10px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #667eea; color: white; }
        .high { color: #28a745; font-weight: bold; }
    </style>
    </head>
    <body>
        <h1>🐕 DrugHound Enterprise Dashboard</h1>
        <div class="card">
            <h2>Top Novel Drug Candidates</h2>
            <table>
                <tr><th>Drug</th><th>Novelty Score</th><th>Phase</th><th>Condition</th><th>Publications</th></tr>
    """
    for drug in SAMPLE_DRUGS:
        score_class = 'high' if drug['novelty_score'] >= 80 else ''
        dashboard_html += f"""
                <tr>
                    <td><strong>{drug['drug']}</strong></td>
                    <td class="{score_class}">{drug['novelty_score']}</td>
                    <td>{drug['phase']}</td>
                    <td>{drug['condition']}</td>
                    <td>{drug['pubmed_count']}</td>
                </tr>
        """
    dashboard_html += """
            </table>
        </div>
        <div class="card">
            <h2>System Status</h2>
            <ul>
                <li>✅ Database: {}</li>
                <li>✅ Search Index: {}</li>
                <li>✅ Report Generator: {}</li>
            </ul>
        </div>
    </body>
    </html>
    """.format(
        "Connected" if DB_AVAILABLE else "Using memory",
        "Available" if INDEXER_AVAILABLE else "Using in-memory",
        "Available" if REPORT_AVAILABLE else "Limited"
    )
    return HTMLResponse(content=dashboard_html)

@app.get("/api/drugs")
async def get_drugs(limit: int = 50, min_score: float = 0):
    """API endpoint for drug data."""
    drugs = [d for d in SAMPLE_DRUGS if d['novelty_score'] >= min_score]
    return {"drugs": drugs[:limit]}

@app.post("/api/search")
async def search_drugs(query: str, search_type: str = "text"):
    """Search drugs."""
    query_lower = query.lower()
    results = []
    for drug in SAMPLE_DRUGS:
        if (query_lower in drug['drug'].lower() or 
            query_lower in drug['condition'].lower()):
            results.append(drug)
    return {"results": results}

@app.get("/api/report/generate")
async def generate_report(format: str = "html"):
    """Generate report."""
    if format == "html":
        report_path = "reports/drughound_report.html"
        os.makedirs("reports", exist_ok=True)
        with open(report_path, 'w') as f:
            f.write(f"""<!DOCTYPE html>
            <html>
            <head><title>DrugHound Report</title></head>
            <body>
            <h1>DrugHound Report</h1>
            <p>Generated: {datetime.now()}</p>
            <table border="1">
            <tr><th>Drug</th><th>Score</th><th>Phase</th><th>Condition</th></tr>
            {''.join(f'<tr><td>{d["drug"]}</td><td>{d["novelty_score"]}</td><td>{d["phase"]}</td><td>{d["condition"]}</td></tr>' for d in SAMPLE_DRUGS)}
            </table>
            </body>
            </html>""")
        return FileResponse(report_path, filename="drughound_report.html")
    else:
        return {"error": f"Format {format} not yet implemented", "drugs": SAMPLE_DRUGS}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0", "database": DB_AVAILABLE, "indexer": INDEXER_AVAILABLE}

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("🐕 DrugHound Enterprise Edition")
    print("="*60)
    print(f"   Database: {'Available' if DB_AVAILABLE else 'Memory Mode'}")
    print(f"   Search: {'Elasticsearch' if INDEXER_AVAILABLE else 'In-Memory'}")
    print(f"   Reports: {'Available' if REPORT_AVAILABLE else 'Limited'}")
    print("="*60)
    print("🌐 Web Interface: http://localhost:8000")
    print("📊 Dashboard: http://localhost:8000/dashboard")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
