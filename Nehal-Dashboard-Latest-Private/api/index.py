import os
import json
import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Nehal Command Center - Vercel Python Supabase")
logger = logging.getLogger("VercelApp")

# Setup Jinja2 Templates
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)

STAGES = ["التحليل", "التصميم", "البرمجة", "الاختبار والمراجعة", "التسليم", "الدعم الفني"]

# Supabase Client Factory
def get_supabase() -> Optional[Client]:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key or "your-project" in url:
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Supabase connection error: {e}")
        return None

# Pydantic Schemas
class ProjectSchema(BaseModel):
    name: str
    client: Optional[str] = None
    status: str = "التحليل"
    priority: str = "MEDIUM"
    start_date: Optional[str] = None
    deadline: Optional[str] = None
    assigned_to: Optional[str] = None
    progress: float = 0.0
    daily_report: Optional[str] = None
    description: Optional[str] = None

class ProjectUpdateSchema(BaseModel):
    name: Optional[str] = None
    client: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    start_date: Optional[str] = None
    deadline: Optional[str] = None
    assigned_to: Optional[str] = None
    progress: Optional[float] = None
    daily_report: Optional[str] = None
    description: Optional[str] = None

# Helper DB Aggregation
def fetch_kpis(client: Optional[Client]) -> Dict[str, Any]:
    default_kpis = {"total_projects": 0, "urgent_projects": 0, "has_daily_report": 0, "avg_progress": 0.0}
    if not client:
        return default_kpis
    try:
        res = client.rpc("get_dashboard_kpis", {}).execute()
        if res and res.data:
            return res.data
    except Exception:
        try:
            res = client.table("projects").select("priority, daily_report, progress").execute()
            if res and res.data:
                items = res.data
                total = len(items)
                urgent = sum(1 for p in items if p.get("priority") in ["CRITICAL", "HIGH"])
                reports = sum(1 for p in items if p.get("daily_report") and str(p["daily_report"]).strip())
                avg_prog = round(sum(float(p.get("progress", 0)) for p in items) / total, 1) if total > 0 else 0
                return {"total_projects": total, "urgent_projects": urgent, "has_daily_report": reports, "avg_progress": avg_prog}
        except Exception:
            pass
    return default_kpis

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def render_dashboard(request: Request):
    client = get_supabase()
    projects = []
    kpis = {"total_projects": 0, "urgent_projects": 0, "has_daily_report": 0, "avg_progress": 0.0}
    
    if client:
        try:
            res = client.table("projects").select("*").order("created_at", desc=True).execute()
            if res and res.data:
                projects = res.data
            kpis = fetch_kpis(client)
        except Exception as e:
            logger.error(f"Error fetching data from Supabase: {e}")

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "projects": projects,
        "kpis": kpis,
        "stages": STAGES
    })

@app.get("/api/projects")
async def list_projects():
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        res = client.table("projects").select("*").order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects")
async def create_project(item: ProjectSchema):
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        payload = item.model_dump(exclude_unset=True)
        res = client.table("projects").insert(payload).execute()
        return res.data[0] if res and res.data else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/projects/{project_id}")
async def update_project(project_id: str, item: ProjectUpdateSchema):
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        payload = item.model_dump(exclude_unset=True)
        res = client.table("projects").update(payload).eq("id", project_id).execute()
        return res.data[0] if res and res.data else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        client.table("projects").delete().eq("id", project_id).execute()
        return {"status": "success", "id": project_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
