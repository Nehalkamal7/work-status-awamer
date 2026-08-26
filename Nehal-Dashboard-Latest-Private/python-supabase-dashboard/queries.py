import logging
from typing import Dict, Any, List, Optional
from supabase_client import get_supabase_client

logger = logging.getLogger("DatabaseQueries")

def fetch_dashboard_kpis() -> Dict[str, Any]:
    """
    Calls the Supabase database-level stored procedure 'get_dashboard_kpis'
    to return aggregated metrics without loading full raw rows into memory.
    """
    client = get_supabase_client()
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
        response = client.rpc("get_dashboard_kpis", {}).execute()
        if response and response.data:
            return response.data
    except Exception as e:
        logger.warning(f"RPC get_dashboard_kpis failed or function not created yet. Fallback to SQL aggregate. Error: {e}")
        try:
            res = client.table("projects").select("id, priority, daily_report, progress, status").execute()
            if res and res.data:
                items = res.data
                total = len(items)
                urgent = sum(1 for p in items if p.get("priority") in ["CRITICAL", "HIGH"])
                reports = sum(1 for p in items if p.get("daily_report") and str(p["daily_report"]).strip())
                avg_prog = round(sum(float(p.get("progress", 0)) for p in items) / total, 1) if total > 0 else 0
                completed = sum(1 for p in items if p.get("progress") == 100 or p.get("status") == "التسليم")
                return {
                    "total_projects": total,
                    "urgent_projects": urgent,
                    "has_daily_report": reports,
                    "avg_progress": avg_prog,
                    "completed_projects": completed
                }
        except Exception as inner_e:
            logger.error(f"Fallback aggregation failed: {inner_e}")

    return default_kpis

def fetch_projects(
    search_query: str = "",
    stage_filter: str = "ALL",
    priority_filter: str = "ALL",
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Fetches filtered and paginated projects directly from Supabase DB.
    """
    client = get_supabase_client()
    if not client:
        return []

    try:
        query = client.table("projects").select("*")

        # Database-level filtering
        if search_query and search_query.strip():
            q = f"%{search_query.strip()}%"
            query = query.or_(f"name.ilike.{q},client.ilike.{q},daily_report.ilike.{q},source_id.ilike.{q}")

        if stage_filter and stage_filter != "ALL":
            query = query.eq("status", stage_filter)

        if priority_filter and priority_filter != "ALL":
            query = query.eq("priority", priority_filter)

        # Ordering & Pagination
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        response = query.execute()

        return response.data if response and response.data else []
    except Exception as e:
        logger.error(f"Error fetching projects from Supabase: {str(e)}")
        return []

def create_project(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Inserts a new project into Supabase.
    """
    client = get_supabase_client()
    if not client:
        return None

    try:
        # Clean null values if empty string
        cleaned_data = {k: (None if v == "" else v) for k, v in data.items()}
        response = client.table("projects").insert(cleaned_data).execute()
        if response and response.data:
            return response.data[0]
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        raise e
    return None

def update_project(project_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Updates an existing project by ID in Supabase.
    """
    client = get_supabase_client()
    if not client:
        return None

    try:
        cleaned_data = {k: (None if v == "" else v) for k, v in data.items()}
        response = client.table("projects").update(cleaned_data).eq("id", project_id).execute()
        if response and response.data:
            return response.data[0]
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {str(e)}")
        raise e
    return None

def delete_project(project_id: str) -> bool:
    """
    Deletes a project by ID from Supabase.
    """
    client = get_supabase_client()
    if not client:
        return False

    try:
        client.table("projects").delete().eq("id", project_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {str(e)}")
        return False

def fetch_tasks_by_project(project_id: str) -> List[Dict[str, Any]]:
    """
    Fetches all tasks associated with a specific project ID.
    """
    client = get_supabase_client()
    if not client:
        return []

    try:
        response = client.table("tasks").select("*").eq("project_id", project_id).order("created_at").execute()
        return response.data if response and response.data else []
    except Exception as e:
        logger.error(f"Error fetching tasks for project {project_id}: {str(e)}")
        return []
