import os
import json
import logging
import hashlib
import hmac
import secrets
import xmlrpc.client
import urllib.request
import urllib.parse
import csv
import io
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Union

from fastapi import FastAPI, Request, HTTPException, Query, Depends, Response, Header, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, field_validator
from supabase import create_client, Client
from dotenv import load_dotenv
import jwt

load_dotenv()

# Configuration & Secrets
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "nehal-command-center-super-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

app = FastAPI(title="Nehal Multi-Tenant Command Center & Integrations API")
logger = logging.getLogger("VercelApp")
logging.basicConfig(level=logging.INFO)

# Setup Jinja2 Templates
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

# In-Memory Cache Fallback when Supabase is not connected
IN_MEMORY_STORE = {
    "users": {},           # email -> user dict
    "tokens": {},          # api_token -> tenant_id
    "projects": [],        # list of project dicts
    "configs": {},         # tenant_id -> provider -> config dict
    "scraped_messages": [],# list of scraped msg dicts
    "odoo_records": []     # list of odoo record dicts
}

# --- Password & Token Security Utilities ---

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
    return f"{salt}${pwd_hash}"

def verify_password(password: str, hashed: str) -> bool:
    try:
        if "$" not in hashed:
            return False
        salt, pwd_hash = hashed.split("$", 1)
        check_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        return hmac.compare_digest(check_hash, pwd_hash)
    except Exception:
        return False

def create_jwt_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_jwt_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None

def simple_encrypt(plain_text: str) -> str:
    """Simple obfuscation/encryption for stored credentials."""
    if not plain_text:
        return ""
    key = SECRET_KEY.encode('utf-8')
    masked = []
    for i, c in enumerate(plain_text.encode('utf-8')):
        masked.append(c ^ key[i % len(key)])
    return secrets.token_hex(4) + bytes(masked).hex()

def simple_decrypt(cipher_text: str) -> str:
    """Decrypt obfuscated credentials."""
    if not cipher_text or len(cipher_text) < 8:
        return cipher_text
    try:
        raw_hex = cipher_text[8:]
        raw_bytes = bytes.fromhex(raw_hex)
        key = SECRET_KEY.encode('utf-8')
        unmasked = bytearray()
        for i, c in enumerate(raw_bytes):
            unmasked.append(c ^ key[i % len(key)])
        return unmasked.decode('utf-8')
    except Exception:
        return cipher_text

# --- Current User Dependency ---

async def get_current_user(request: Request) -> Optional[dict]:
    # Check Cookie first, then Authorization Header
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        return None
    
    payload = decode_jwt_token(token)
    if not payload or "email" not in payload:
        return None
    
    email = payload["email"]
    client = get_supabase()
    if client:
        try:
            res = client.table("users").select("*").eq("email", email).execute()
            if res and res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error fetching user from Supabase: {e}")
    
    # Check in-memory fallback
    if email in IN_MEMORY_STORE["users"]:
        return IN_MEMORY_STORE["users"][email]
    
    # Return payload as basic user context
    return {
        "id": payload.get("sub", payload.get("user_id")),
        "tenant_id": payload.get("tenant_id"),
        "email": payload.get("email"),
        "name": payload.get("name", "Demo User"),
        "role": payload.get("role", "CLIENT"),
        "company_name": payload.get("company_name", "Demo Corp"),
        "api_token": payload.get("api_token")
    }

# --- Pydantic Schemas ---

class RegisterSchema(BaseModel):
    email: str
    password: str
    name: str
    company_name: Optional[str] = "Company Workspace"
    role: Optional[str] = "CLIENT"

class LoginSchema(BaseModel):
    email: str
    password: str

class OdooTestSchema(BaseModel):
    base_url: str
    db_name: str
    username: str
    password: str

class OdooSaveSchema(BaseModel):
    base_url: str
    db_name: str
    username: str
    password: str
    auto_sync: Optional[bool] = False

class OdooSyncSchema(BaseModel):
    model_name: Optional[str] = "sale.order"

class GoogleSheetsTestSchema(BaseModel):
    sheet_url: str
    sheet_name: Optional[str] = "Sheet1"

class GoogleSheetsSaveSchema(BaseModel):
    sheet_url: str
    sheet_name: Optional[str] = "Sheet1"
    column_mapping: Dict[str, str] # e.g. {"name": "Col A", "status": "Col B"}

class WhatsAppIngestSchema(BaseModel):
    api_token: Optional[str] = None
    messages: List[Dict[str, Any]]

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

# Helper DB Aggregation with Tenant Filter
def fetch_kpis(client: Optional[Client], tenant_id: Optional[str] = None) -> Dict[str, Any]:
    default_kpis = {
        "total_projects": 0,
        "urgent_projects": 0,
        "has_daily_report": 0,
        "avg_progress": 0.0,
        "completed_projects": 0
    }
    if not client:
        # Calculate from in-memory store
        items = IN_MEMORY_STORE["projects"]
        if tenant_id:
            items = [p for p in items if p.get("tenant_id") == tenant_id]
        total = len(items)
        if total == 0:
            return default_kpis
        urgent = sum(1 for p in items if p.get("priority") in ["CRITICAL", "HIGH"])
        reports = sum(1 for p in items if p.get("daily_report") and str(p["daily_report"]).strip())
        avg_prog = round(sum(float(p.get("progress", 0)) for p in items) / total, 1)
        completed = sum(1 for p in items if float(p.get("progress", 0)) >= 100.0 or p.get("status") == "التسليم")
        return {
            "total_projects": total,
            "urgent_projects": urgent,
            "has_daily_report": reports,
            "avg_progress": avg_prog,
            "completed_projects": completed
        }

    try:
        params = {}
        if tenant_id:
            params["p_tenant_id"] = tenant_id
        res = client.rpc("get_dashboard_kpis", params).execute()
        if res and res.data and isinstance(res.data, dict):
            data = res.data
            if "completed_projects" not in data:
                data["completed_projects"] = 0
            return data
    except Exception as e:
        logger.warning(f"RPC get_dashboard_kpis fallback triggered: {e}")
    
    try:
        query = client.table("projects").select("priority, daily_report, progress, status")
        if tenant_id:
            query = query.eq("tenant_id", tenant_id)
        res = query.execute()
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

# --- Page Routes ---

@app.get("/login", response_class=HTMLResponse)
async def render_login(request: Request):
    return templates.TemplateResponse(request, "login.html", {})

@app.get("/", response_class=HTMLResponse)
async def render_dashboard(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    tenant_id = user.get("tenant_id")
    client = get_supabase()
    projects = []
    supabase_connected = client is not None
    
    if client:
        try:
            query = client.table("projects").select("*").order("created_at", desc=True)
            if tenant_id and user.get("role") != "ADMIN":
                query = query.eq("tenant_id", tenant_id)
            res = query.execute()
            if res and res.data:
                projects = res.data
        except Exception as e:
            logger.error(f"Error fetching projects from Supabase: {e}")
    else:
        projects = [p for p in IN_MEMORY_STORE["projects"] if not tenant_id or p.get("tenant_id") == tenant_id]

    kpis = fetch_kpis(client, tenant_id if user.get("role") != "ADMIN" else None)

    # Get client integration configs
    odoo_config = {}
    google_config = {}
    whatsapp_config = {}
    if client and tenant_id:
        try:
            res = client.table("client_configs").select("*").eq("tenant_id", tenant_id).execute()
            if res and res.data:
                for row in res.data:
                    prov = row.get("provider")
                    if prov == "ODOO":
                        odoo_config = row
                    elif prov == "GOOGLE_SHEETS":
                        google_config = row
                    elif prov == "WHATSAPP":
                        whatsapp_config = row
        except Exception as e:
            logger.error(f"Error fetching integration configs: {e}")

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": user,
            "projects": projects,
            "kpis": kpis,
            "stages": STAGES,
            "supabase_connected": supabase_connected,
            "odoo_config": odoo_config,
            "google_config": google_config,
            "whatsapp_config": whatsapp_config
        }
    )

# --- Authentication Endpoints ---

@app.post("/api/auth/register")
async def register(payload: RegisterSchema, response: Response):
    client = get_supabase()
    tenant_id = str(secrets.token_hex(16))
    api_token = f"wh_tok_{secrets.token_hex(20)}"
    password_h = hash_password(payload.password)
    
    user_data = {
        "tenant_id": tenant_id,
        "email": payload.email.lower().strip(),
        "password_hash": password_h,
        "name": payload.name,
        "role": payload.role or "CLIENT",
        "company_name": payload.company_name or "Client Workspace",
        "api_token": api_token
    }

    if client:
        try:
            # Check existing
            existing = client.table("users").select("id").eq("email", user_data["email"]).execute()
            if existing and existing.data and len(existing.data) > 0:
                raise HTTPException(status_code=400, detail="User with this email already exists.")
            
            res = client.table("users").insert(user_data).execute()
            if res and res.data:
                user_data["id"] = res.data[0]["id"]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error registering user in Supabase: {e}")
            user_data["id"] = str(secrets.token_hex(16))
    else:
        if user_data["email"] in IN_MEMORY_STORE["users"]:
            raise HTTPException(status_code=400, detail="User with this email already exists.")
        user_data["id"] = str(secrets.token_hex(16))
        IN_MEMORY_STORE["users"][user_data["email"]] = user_data
        IN_MEMORY_STORE["tokens"][api_token] = tenant_id

    # Create JWT Token
    jwt_data = {
        "sub": user_data.get("id"),
        "tenant_id": tenant_id,
        "email": user_data["email"],
        "name": user_data["name"],
        "role": user_data["role"],
        "company_name": user_data["company_name"],
        "api_token": api_token
    }
    token = create_jwt_token(jwt_data)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400 * 7, samesite="lax")
    
    return {
        "status": "success",
        "access_token": token,
        "user": {
            "id": user_data.get("id"),
            "tenant_id": tenant_id,
            "email": user_data["email"],
            "name": user_data["name"],
            "role": user_data["role"],
            "company_name": user_data["company_name"],
            "api_token": api_token
        }
    }

@app.post("/api/auth/login")
async def login(payload: LoginSchema, response: Response):
    email = payload.email.lower().strip()
    client = get_supabase()
    user = None

    if client:
        try:
            res = client.table("users").select("*").eq("email", email).execute()
            if res and res.data and len(res.data) > 0:
                user = res.data[0]
        except Exception as e:
            logger.error(f"Supabase login query error: {e}")

    if not user and email in IN_MEMORY_STORE["users"]:
        user = IN_MEMORY_STORE["users"][email]

    # Demo fallback user if brand new setup
    if not user and email in ["demo@example.com", "admin@nehal.com"]:
        tenant_id = str(secrets.token_hex(16))
        api_token = f"wh_tok_{secrets.token_hex(20)}"
        user = {
            "id": str(secrets.token_hex(16)),
            "tenant_id": tenant_id,
            "email": email,
            "password_hash": hash_password(payload.password),
            "name": "Demo Admin" if "admin" in email else "Demo Client",
            "role": "ADMIN" if "admin" in email else "CLIENT",
            "company_name": "Nehal Enterprises",
            "api_token": api_token
        }
        IN_MEMORY_STORE["users"][email] = user
        IN_MEMORY_STORE["tokens"][api_token] = tenant_id

    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Ensure api_token exists
    if not user.get("api_token"):
        user["api_token"] = f"wh_tok_{secrets.token_hex(20)}"
        if client:
            try:
                client.table("users").update({"api_token": user["api_token"]}).eq("id", user["id"]).execute()
            except Exception:
                pass

    jwt_data = {
        "sub": user.get("id"),
        "tenant_id": user.get("tenant_id"),
        "email": user.get("email"),
        "name": user.get("name"),
        "role": user.get("role", "CLIENT"),
        "company_name": user.get("company_name"),
        "api_token": user.get("api_token")
    }
    token = create_jwt_token(jwt_data)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400 * 7, samesite="lax")

    return {
        "status": "success",
        "access_token": token,
        "user": jwt_data
    }

@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "success", "message": "Logged out successfully."}

@app.get("/api/auth/me")
async def get_me(current_user: Optional[dict] = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return current_user

# --- Odoo Integration Endpoints ---

@app.post("/api/integrations/odoo/test")
async def test_odoo_connection(payload: OdooTestSchema):
    url = payload.base_url.rstrip("/")
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"

    common_url = f"{url}/xmlrpc/2/common"
    try:
        common = xmlrpc.client.ServerProxy(common_url, allow_none=True)
        version_info = common.version()
        uid = common.authenticate(payload.db_name, payload.username, payload.password, {})
        
        if uid:
            return {
                "success": True,
                "uid": uid,
                "odoo_version": version_info.get("server_version", "Unknown"),
                "message": f"Successfully authenticated with Odoo (User ID: {uid})"
            }
        else:
            return {
                "success": False,
                "message": "Odoo Authentication failed. Please check Database, Username, or Password/API Key."
            }
    except Exception as e:
        logger.error(f"Odoo connection test failed: {e}")
        return {
            "success": False,
            "message": f"Connection error: {str(e)}"
        }

@app.post("/api/integrations/odoo/save")
async def save_odoo_config(
    payload: OdooSaveSchema,
    current_user: Optional[dict] = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    tenant_id = current_user.get("tenant_id")
    client = get_supabase()

    enc_password = simple_encrypt(payload.password)
    credentials_payload = {
        "base_url": payload.base_url,
        "db_name": payload.db_name,
        "username": payload.username,
        "enc_password": enc_password
    }
    settings_payload = {
        "auto_sync": payload.auto_sync
    }

    if client:
        try:
            res = client.table("client_configs").upsert({
                "tenant_id": tenant_id,
                "provider": "ODOO",
                "credentials": credentials_payload,
                "settings": settings_payload,
                "status": "CONNECTED",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }, on_conflict="tenant_id,provider").execute()
            return {"status": "success", "data": res.data}
        except Exception as e:
            logger.error(f"Error saving Odoo config to Supabase: {e}")
    
    # Memory fallback
    if "configs" not in IN_MEMORY_STORE:
        IN_MEMORY_STORE["configs"] = {}
    if tenant_id not in IN_MEMORY_STORE["configs"]:
        IN_MEMORY_STORE["configs"][tenant_id] = {}
    
    IN_MEMORY_STORE["configs"][tenant_id]["ODOO"] = {
        "provider": "ODOO",
        "credentials": credentials_payload,
        "settings": settings_payload,
        "status": "CONNECTED"
    }
    return {"status": "success", "message": "Odoo integration settings saved."}

@app.post("/api/integrations/odoo/sync")
async def sync_odoo_data(
    payload: OdooSyncSchema,
    current_user: Optional[dict] = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    tenant_id = current_user.get("tenant_id")
    client = get_supabase()
    config = None

    if client:
        try:
            res = client.table("client_configs").select("*").eq("tenant_id", tenant_id).eq("provider", "ODOO").execute()
            if res and res.data and len(res.data) > 0:
                config = res.data[0]
        except Exception as e:
            logger.error(f"Error fetching Odoo config: {e}")

    if not config and tenant_id in IN_MEMORY_STORE.get("configs", {}):
        config = IN_MEMORY_STORE["configs"][tenant_id].get("ODOO")

    if not config or not config.get("credentials"):
        raise HTTPException(status_code=400, detail="Odoo ERP credentials not configured. Please save settings first.")

    creds = config["credentials"]
    base_url = creds.get("base_url", "").rstrip("/")
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = f"https://{base_url}"
    
    db_name = creds.get("db_name")
    username = creds.get("username")
    password = simple_decrypt(creds.get("enc_password", ""))

    model_name = payload.model_name or "sale.order"
    try:
        common = xmlrpc.client.ServerProxy(f"{base_url}/xmlrpc/2/common", allow_none=True)
        uid = common.authenticate(db_name, username, password, {})
        if not uid:
            raise HTTPException(status_code=401, detail="Failed to authenticate with Odoo API.")
        
        models = xmlrpc.client.ServerProxy(f"{base_url}/xmlrpc/2/object", allow_none=True)
        records = models.execute_kw(
            db_name, uid, password,
            model_name, 'search_read',
            [[]],
            {'limit': 50, 'fields': ['id', 'name', 'display_name', 'create_date', 'state', 'amount_total', 'partner_id']}
        )

        synced_count = 0
        now_str = datetime.now(timezone.utc).isoformat()
        
        if client:
            for rec in records:
                rec_id = rec.get("id")
                rec_name = rec.get("display_name") or rec.get("name") or f"Record #{rec_id}"
                try:
                    client.table("odoo_records").upsert({
                        "tenant_id": tenant_id,
                        "model_name": model_name,
                        "odoo_id": rec_id,
                        "record_name": rec_name,
                        "data": rec,
                        "last_synced_at": now_str
                    }, on_conflict="tenant_id,model_name,odoo_id").execute()
                    synced_count += 1
                except Exception as ex:
                    logger.error(f"Error upserting odoo record: {ex}")
            
            # Update last synced
            client.table("client_configs").update({
                "last_synced_at": now_str
            }).eq("tenant_id", tenant_id).eq("provider", "ODOO").execute()
        else:
            synced_count = len(records)

        return {
            "status": "success",
            "model_name": model_name,
            "synced_count": synced_count,
            "records": records[:10]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Odoo sync error: {e}")
        raise HTTPException(status_code=500, detail=f"Odoo Sync Error: {str(e)}")

@app.get("/api/integrations/odoo/records")
async def get_odoo_records(current_user: Optional[dict] = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    tenant_id = current_user.get("tenant_id")
    client = get_supabase()
    if client:
        try:
            res = client.table("odoo_records").select("*").eq("tenant_id", tenant_id).order("last_synced_at", desc=True).limit(100).execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error fetching odoo records: {e}")
    return []

# --- Google Sheets Integration Endpoints ---

def extract_spreadsheet_id(url_or_id: str) -> str:
    """Extract Spreadsheet ID from Google Sheets URL or return ID."""
    if "/d/" in url_or_id:
        parts = url_or_id.split("/d/")
        return parts[1].split("/")[0]
    return url_or_id.strip()

@app.post("/api/integrations/google-sheets/test")
async def test_google_sheets(payload: GoogleSheetsTestSchema):
    spreadsheet_id = extract_spreadsheet_id(payload.sheet_url)
    sheet_name = payload.sheet_name or "Sheet1"
    
    # Construct published CSV export URL
    csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(sheet_name)}"
    
    try:
        req = urllib.request.Request(
            csv_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8')
            
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        
        if not rows or len(rows) == 0:
            return {
                "success": False,
                "message": "Google Sheet accessed, but no rows or content found."
            }
        
        headers = rows[0]
        preview_rows = rows[1:6] if len(rows) > 1 else []
        
        return {
            "success": True,
            "spreadsheet_id": spreadsheet_id,
            "headers": headers,
            "rows_preview": preview_rows,
            "total_rows": len(rows) - 1,
            "message": f"Successfully connected to Google Sheet ({len(headers)} columns, {len(rows)-1} rows found)"
        }
    except Exception as e:
        logger.error(f"Google Sheets test error: {e}")
        return {
            "success": False,
            "message": f"Unable to fetch Google Sheet. Please make sure the sheet is shared as 'Anyone with the link can view'. Error: {str(e)}"
        }

@app.post("/api/integrations/google-sheets/save")
async def save_google_sheets_config(
    payload: GoogleSheetsSaveSchema,
    current_user: Optional[dict] = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    tenant_id = current_user.get("tenant_id")
    client = get_supabase()
    spreadsheet_id = extract_spreadsheet_id(payload.sheet_url)

    credentials_payload = {
        "sheet_url": payload.sheet_url,
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": payload.sheet_name or "Sheet1"
    }

    if client:
        try:
            res = client.table("client_configs").upsert({
                "tenant_id": tenant_id,
                "provider": "GOOGLE_SHEETS",
                "credentials": credentials_payload,
                "column_mapping": payload.column_mapping,
                "status": "CONNECTED",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }, on_conflict="tenant_id,provider").execute()
            return {"status": "success", "data": res.data}
        except Exception as e:
            logger.error(f"Error saving Google Sheets config: {e}")
    
    # Memory fallback
    if "configs" not in IN_MEMORY_STORE:
        IN_MEMORY_STORE["configs"] = {}
    if tenant_id not in IN_MEMORY_STORE["configs"]:
        IN_MEMORY_STORE["configs"][tenant_id] = {}
        
    IN_MEMORY_STORE["configs"][tenant_id]["GOOGLE_SHEETS"] = {
        "provider": "GOOGLE_SHEETS",
        "credentials": credentials_payload,
        "column_mapping": payload.column_mapping,
        "status": "CONNECTED"
    }
    return {"status": "success", "message": "Google Sheets configuration saved."}

@app.post("/api/integrations/google-sheets/sync")
async def sync_google_sheets_data(current_user: Optional[dict] = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    tenant_id = current_user.get("tenant_id")
    client = get_supabase()
    config = None

    if client:
        try:
            res = client.table("client_configs").select("*").eq("tenant_id", tenant_id).eq("provider", "GOOGLE_SHEETS").execute()
            if res and res.data and len(res.data) > 0:
                config = res.data[0]
        except Exception as e:
            logger.error(f"Error fetching Google Sheets config: {e}")

    if not config and tenant_id in IN_MEMORY_STORE.get("configs", {}):
        config = IN_MEMORY_STORE["configs"][tenant_id].get("GOOGLE_SHEETS")

    if not config or not config.get("credentials"):
        raise HTTPException(status_code=400, detail="Google Sheets integration not configured.")

    creds = config["credentials"]
    mapping = config.get("column_mapping", {})
    spreadsheet_id = creds.get("spreadsheet_id")
    sheet_name = creds.get("sheet_name", "Sheet1")

    csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(sheet_name)}"

    try:
        req = urllib.request.Request(
            csv_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8')
            
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        if len(rows) <= 1:
            return {"status": "success", "synced_count": 0, "message": "No data rows found in Google Sheet."}

        headers = rows[0]
        col_indices = {h.strip(): idx for idx, h in enumerate(headers)}

        synced_count = 0
        for row in rows[1:]:
            if not any(row):
                continue
            
            # Map columns
            name_val = row[col_indices[mapping["name"]]] if mapping.get("name") in col_indices and col_indices[mapping["name"]] < len(row) else None
            client_val = row[col_indices[mapping["client"]]] if mapping.get("client") in col_indices and col_indices[mapping["client"]] < len(row) else None
            status_val = row[col_indices[mapping["status"]]] if mapping.get("status") in col_indices and col_indices[mapping["status"]] < len(row) else "التحليل"
            priority_val = row[col_indices[mapping["priority"]]] if mapping.get("priority") in col_indices and col_indices[mapping["priority"]] < len(row) else "MEDIUM"
            deadline_val = row[col_indices[mapping["deadline"]]] if mapping.get("deadline") in col_indices and col_indices[mapping["deadline"]] < len(row) else None

            if not name_val or not name_val.strip():
                continue

            project_data = {
                "tenant_id": tenant_id,
                "name": name_val.strip(),
                "client": client_val.strip() if client_val else None,
                "status": status_val.strip() if status_val else "التحليل",
                "priority": priority_val.strip() if priority_val and priority_val in ["CRITICAL", "HIGH", "MEDIUM", "LOW"] else "MEDIUM",
                "deadline": deadline_val.strip() if deadline_val else None,
                "source": "GOOGLE_SHEETS",
                "source_id": f"gs_{spreadsheet_id}_{synced_count}"
            }

            if client:
                try:
                    client.table("projects").insert(project_data).execute()
                    synced_count += 1
                except Exception as ex:
                    logger.error(f"Error inserting mapped project: {ex}")
            else:
                project_data["id"] = str(secrets.token_hex(16))
                project_data["created_at"] = datetime.now(timezone.utc).isoformat()
                IN_MEMORY_STORE["projects"].append(project_data)
                synced_count += 1

        now_str = datetime.now(timezone.utc).isoformat()
        if client:
            client.table("client_configs").update({"last_synced_at": now_str}).eq("tenant_id", tenant_id).eq("provider", "GOOGLE_SHEETS").execute()

        return {
            "status": "success",
            "synced_count": synced_count,
            "message": f"Successfully imported {synced_count} project records from Google Sheets."
        }
    except Exception as e:
        logger.error(f"Google Sheets sync error: {e}")
        raise HTTPException(status_code=500, detail=f"Google Sheets Sync Error: {str(e)}")

@app.post("/api/integrations/sync-all")
async def sync_all_sources(current_user: Optional[dict] = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    tenant_id = current_user.get("tenant_id")
    results = {
        "odoo": {"status": "skipped", "message": "Not configured"},
        "google_sheets": {"status": "skipped", "message": "Not configured"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Try Odoo sync
    try:
        odoo_res = await sync_odoo_data(OdooSyncSchema(model_name="sale.order"), current_user)
        results["odoo"] = {"status": "success", "synced_count": odoo_res.get("synced_count", 0)}
    except Exception as e:
        results["odoo"] = {"status": "error", "message": str(e)}

    # Try Google Sheets sync
    try:
        sheets_res = await sync_google_sheets_data(current_user)
        results["google_sheets"] = {"status": "success", "synced_count": sheets_res.get("synced_count", 0)}
    except Exception as e:
        results["google_sheets"] = {"status": "error", "message": str(e)}

    return {
        "status": "success",
        "message": "Live 1-minute auto-sync executed across all configured sources.",
        "results": results
    }

# --- Client Extension Token Generator ---


@app.post("/api/integrations/token/generate")
async def generate_api_token(current_user: Optional[dict] = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    tenant_id = current_user.get("tenant_id")
    new_token = f"wh_tok_{secrets.token_hex(20)}"
    client = get_supabase()

    if client:
        try:
            client.table("users").update({"api_token": new_token}).eq("id", current_user.get("id")).execute()
        except Exception as e:
            logger.error(f"Error updating user api token: {e}")

    current_user["api_token"] = new_token
    IN_MEMORY_STORE["tokens"][new_token] = tenant_id

    return {
        "status": "success",
        "api_token": new_token,
        "tenant_id": tenant_id
    }

# --- WhatsApp Web Scraping Extension Webhook Endpoints ---

@app.post("/api/whatsapp/ingest")
async def ingest_whatsapp_messages(
    payload: WhatsAppIngestSchema,
    x_client_token: Optional[str] = Header(None)
):
    token = payload.api_token or x_client_token
    if not token:
        raise HTTPException(status_code=401, detail="Client API Token missing.")
    
    client = get_supabase()
    tenant_id = None

    if client:
        try:
            res = client.table("users").select("tenant_id").eq("api_token", token).execute()
            if res and res.data and len(res.data) > 0:
                tenant_id = res.data[0]["tenant_id"]
        except Exception as e:
            logger.error(f"Error verifying API token with Supabase: {e}")

    if not tenant_id and token in IN_MEMORY_STORE["tokens"]:
        tenant_id = IN_MEMORY_STORE["tokens"][token]

    if not tenant_id:
        # Fallback to test/demo tenant if matching token pattern
        if token.startswith("wh_tok_"):
            tenant_id = "00000000-0000-0000-0000-000000000000"
        else:
            raise HTTPException(status_code=401, detail="Invalid or expired Client API Token.")

    ingested_count = 0
    now_str = datetime.now(timezone.utc).isoformat()

    for msg in payload.messages:
        group_name = msg.get("group_name", "General Group")
        message_text = msg.get("message_text", "").strip()
        if not message_text:
            continue

        record = {
            "tenant_id": tenant_id,
            "group_name": group_name,
            "group_id": msg.get("group_id", group_name),
            "sender_name": msg.get("sender_name", "Unknown Sender"),
            "sender_number": msg.get("sender_number", ""),
            "message_text": message_text,
            "msg_timestamp": msg.get("msg_timestamp", now_str),
            "raw_payload": msg,
            "created_at": now_str
        }

        if client:
            try:
                client.table("scraped_messages").insert(record).execute()
                ingested_count += 1
            except Exception as ex:
                logger.error(f"Error inserting scraped message: {ex}")
        else:
            record["id"] = str(secrets.token_hex(16))
            IN_MEMORY_STORE["scraped_messages"].append(record)
            ingested_count += 1

    return {
        "status": "success",
        "ingested_count": ingested_count,
        "message": f"Successfully ingested {ingested_count} WhatsApp messages."
    }

@app.get("/api/whatsapp/messages")
async def get_whatsapp_messages(
    group_name: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    current_user: Optional[dict] = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    tenant_id = current_user.get("tenant_id")
    client = get_supabase()

    if client:
        try:
            query = client.table("scraped_messages").select("*")
            if current_user.get("role") != "ADMIN":
                query = query.eq("tenant_id", tenant_id)
            if group_name:
                query = query.eq("group_name", group_name)
            res = query.order("created_at", desc=True).limit(100).execute()
            items = res.data or []
            if q:
                term = q.lower()
                items = [m for m in items if term in m.get("message_text", "").lower() or term in m.get("sender_name", "").lower()]
            return items
        except Exception as e:
            logger.error(f"Error querying scraped_messages: {e}")

    items = IN_MEMORY_STORE["scraped_messages"]
    if current_user.get("role") != "ADMIN":
        items = [m for m in items if m.get("tenant_id") == tenant_id]
    if group_name:
        items = [m for m in items if m.get("group_name") == group_name]
    if q:
        term = q.lower()
        items = [m for m in items if term in m.get("message_text", "").lower() or term in m.get("sender_name", "").lower()]
    
    return items

# --- Multi-Tenant Projects CRUD Endpoints ---

@app.get("/api/projects")
async def list_projects(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    current_user: Optional[dict] = Depends(get_current_user)
):
    client = get_supabase()
    tenant_id = current_user.get("tenant_id") if current_user else None

    if client:
        try:
            query = client.table("projects").select("*").order("created_at", desc=True)
            if current_user and current_user.get("role") != "ADMIN" and tenant_id:
                query = query.eq("tenant_id", tenant_id)
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
    
    items = IN_MEMORY_STORE["projects"]
    if current_user and current_user.get("role") != "ADMIN" and tenant_id:
        items = [p for p in items if p.get("tenant_id") == tenant_id]
    if status and status != "ALL":
        items = [p for p in items if p.get("status") == status]
    if priority and priority != "ALL":
        items = [p for p in items if p.get("priority") == priority]
    if q:
        term = q.strip().lower()
        items = [p for p in items if term in str(p.get("name", "")).lower() or term in str(p.get("client", "")).lower()]
    
    return items

@app.post("/api/projects")
async def create_project(
    item: ProjectSchema,
    current_user: Optional[dict] = Depends(get_current_user)
):
    client = get_supabase()
    tenant_id = current_user.get("tenant_id") if current_user else "00000000-0000-0000-0000-000000000000"
    payload = item.model_dump(exclude_unset=True)
    payload["tenant_id"] = tenant_id

    if client:
        try:
            res = client.table("projects").insert(payload).execute()
            return res.data[0] if res and res.data else {}
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    payload["id"] = str(secrets.token_hex(16))
    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    IN_MEMORY_STORE["projects"].append(payload)
    return payload

@app.patch("/api/projects/{project_id}")
async def update_project(
    project_id: str,
    item: ProjectUpdateSchema,
    current_user: Optional[dict] = Depends(get_current_user)
):
    client = get_supabase()
    payload = item.model_dump(exclude_unset=True)

    if client:
        try:
            res = client.table("projects").update(payload).eq("id", project_id).execute()
            return res.data[0] if res and res.data else {}
        except Exception as e:
            logger.error(f"Error updating project {project_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    for p in IN_MEMORY_STORE["projects"]:
        if p.get("id") == project_id:
            p.update(payload)
            return p
    raise HTTPException(status_code=404, detail="Project not found.")

@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: Optional[dict] = Depends(get_current_user)
):
    client = get_supabase()
    if client:
        try:
            client.table("projects").delete().eq("id", project_id).execute()
            return {"status": "success", "id": project_id}
        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    IN_MEMORY_STORE["projects"] = [p for p in IN_MEMORY_STORE["projects"] if p.get("id") != project_id]
    return {"status": "success", "id": project_id}
