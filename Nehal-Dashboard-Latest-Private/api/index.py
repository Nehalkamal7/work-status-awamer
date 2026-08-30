import os
import json
import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, field_validator
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Nehal Command Center - Vercel Python Supabase")
logger = logging.getLogger("VercelApp")

# Setup Jinja2 Templates with robust root path resolution
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates_dir = os.path.join(BASE_DIR, "templates")
if not os.path.exists(templates_dir):
    templates_dir = os.path.join(os.getcwd(), "templates")

templates = Jinja2Templates(directory=templates_dir)

STAGES = ["التحليل", "التصميم", "البرمجة", "الاختبار والمراجعة", "التسليم", "الدعم الفني"]

# Supabase Client Singleton
_supabase_client: Optional[Client] = None
_supabase_initialized: bool = False

def get_supabase() -> Optional[Client]:
    global _supabase_client, _supabase_initialized
    if _supabase_initialized:
        return _supabase_client
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key or "your-project" in url:
        _supabase_client = None
        _supabase_initialized = True
        return None
    try:
        _supabase_client = create_client(url, key)
    except Exception as e:
        logger.error(f"Supabase connection error: {e}")
        _supabase_client = None
    
    _supabase_initialized = True
    return _supabase_client

# Pydantic Schemas with Date & Number Sanitization
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

    @field_validator("start_date", "deadline", mode="before")
    @classmethod
    def sanitize_dates(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("progress", mode="before")
    @classmethod
    def sanitize_progress(cls, v):
        if v is None:
            return 0.0
        try:
            val = float(v)
            return max(0.0, min(100.0, val))
        except (ValueError, TypeError):
            return 0.0

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

    @field_validator("start_date", "deadline", mode="before")
    @classmethod
    def sanitize_dates(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("progress", mode="before")
    @classmethod
    def sanitize_progress(cls, v):
        if v is None:
            return None
        try:
            val = float(v)
            return max(0.0, min(100.0, val))
        except (ValueError, TypeError):
            return 0.0

# Helper DB Aggregation
def fetch_kpis(client: Optional[Client]) -> Dict[str, Any]:
    default_kpis = {
        "total_projects": 0,
        "urgent_projects": 0,
        "has_daily_report": 0,
        "avg_progress": 0.0,
        "completed_projects": 0
    }
    if not client:
        return default_kpis
    try:
        res = client.rpc("get_dashboard_kpis", {}).execute()
        if res and res.data and isinstance(res.data, dict):
            # Ensure completed_projects is in dict
            data = res.data
            if "completed_projects" not in data:
                data["completed_projects"] = 0
            return data
    except Exception as e:
        logger.warning(f"RPC get_dashboard_kpis fallback triggered: {e}")
    
    try:
        res = client.table("projects").select("priority, daily_report, progress, status").execute()
        if res and res.data:
            items = res.data
            total = len(items)
            urgent = sum(1 for p in items if p.get("priority") in ["CRITICAL", "HIGH"])
            reports = sum(1 for p in items if p.get("daily_report") and str(p["daily_report"]).strip())
            avg_prog = round(sum(float(p.get("progress", 0)) for p in items) / total, 1) if total > 0 else 0.0
            completed = sum(1 for p in items if float(p.get("progress", 0)) >= 100.0 or p.get("status") == "التسليم")
            return {
                "total_projects": total,
                "urgent_projects": urgent,
                "has_daily_report": reports,
                "avg_progress": avg_prog,
                "completed_projects": completed
            }
    except Exception as e:
        logger.error(f"Fallback KPI query failed: {e}")

    return default_kpis

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def render_dashboard(request: Request):
    client = get_supabase()
    projects = []
    kpis = {
        "total_projects": 0,
        "urgent_projects": 0,
        "has_daily_report": 0,
        "avg_progress": 0.0,
        "completed_projects": 0
    }
    supabase_connected = client is not None
    
    if client:
        try:
            res = client.table("projects").select("*").order("created_at", desc=True).execute()
            if res and res.data:
                projects = res.data
            kpis = fetch_kpis(client)
        except Exception as e:
            logger.error(f"Error fetching data from Supabase: {e}")

    try:
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "projects": projects,
                "kpis": kpis,
                "stages": STAGES,
                "supabase_connected": supabase_connected
            }
        )
    except Exception as e:
        logger.error(f"Template rendering error: {e}")
        return HTMLResponse(f"<h1>Dashboard Rendering Error</h1><p>{str(e)}</p>", status_code=500)

@app.get("/api/projects")
async def list_projects(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    q: Optional[str] = Query(None)
):
    client = get_supabase()
    if not client:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured. Please set SUPABASE_URL and SUPABASE_KEY environment variables."
        )
    try:
        query = client.table("projects").select("*").order("created_at", desc=True)
        if status:
            query = query.eq("status", status)
        if priority:
            query = query.eq("priority", priority)
        
        res = query.execute()
        items = res.data or []
        
        if q:
            term = q.strip().lower()
            items = [
                item for item in items
                if term in str(item.get("name", "")).lower()
                or term in str(item.get("client", "")).lower()
                or term in str(item.get("assigned_to", "")).lower()
                or term in str(item.get("description", "")).lower()
            ]
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects")
async def create_project(item: ProjectSchema):
    client = get_supabase()
    if not client:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured. Please set SUPABASE_URL and SUPABASE_KEY environment variables."
        )
    try:
        payload = item.model_dump(exclude_unset=True)
        res = client.table("projects").insert(payload).execute()
        return res.data[0] if res and res.data else {}
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/projects/{project_id}")
async def update_project(project_id: str, item: ProjectUpdateSchema):
    client = get_supabase()
    if not client:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured. Please set SUPABASE_URL and SUPABASE_KEY environment variables."
        )
    try:
        payload = item.model_dump(exclude_unset=True)
        res = client.table("projects").update(payload).eq("id", project_id).execute()
        return res.data[0] if res and res.data else {}
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    client = get_supabase()
    if not client:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured. Please set SUPABASE_URL and SUPABASE_KEY environment variables."
        )
    try:
        client.table("projects").delete().eq("id", project_id).execute()
        return {"status": "success", "id": project_id}
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
