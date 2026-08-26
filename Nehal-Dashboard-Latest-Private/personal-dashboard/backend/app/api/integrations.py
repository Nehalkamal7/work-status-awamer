from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import current_user
from app.integrations.odoo.client import OdooClient, OdooError
from app.integrations.google_sheets.client import GoogleSheetsClient, SCOPES
from app.models import Integration, Project, Source
from app.schemas.api import GoogleSelection, ProjectOut, SheetPasteImport
from app.integrations.google_sheets.import_text import import_tsv

router=APIRouter(prefix="/api/integrations",tags=["integrations"])
def upsert(db,provider):
    row=db.scalar(select(Integration).where(Integration.provider==provider))
    if not row: row=Integration(provider=provider); db.add(row); db.flush()
    return row

@router.post("/odoo/test")
def test_odoo(db:Session=Depends(get_db),_=Depends(current_user)):
    try: uid=OdooClient().authenticate()
    except OdooError as e: raise HTTPException(502,str(e))
    row=upsert(db,"ODOO"); row.status="CONNECTED"; db.commit(); return {"connected":True,"user_id":uid}

def flow():
    s=get_settings()
    if not s.google_client_id or not s.google_client_secret: raise HTTPException(503,"Google OAuth configuration is incomplete")
    return Flow.from_client_config({"web":{"client_id":s.google_client_id,"client_secret":s.google_client_secret,"auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","redirect_uris":[s.google_redirect_uri]}},scopes=SCOPES,redirect_uri=s.google_redirect_uri)

@router.get("/google/authorize")
def authorize(user=Depends(current_user)):
    url,state=flow().authorization_url(access_type="offline",include_granted_scopes="true",prompt="consent",state=user.id); return {"authorization_url":url,"state":state}

@router.get("/google/callback")
def callback(code:str,state:str,db:Session=Depends(get_db)):
    f=flow(); f.fetch_token(code=code); c=f.credentials; row=upsert(db,"GOOGLE_SHEETS"); row.status="CONNECTED"; row.credentials={"token":c.token,"refresh_token":c.refresh_token,"token_uri":c.token_uri,"client_id":c.client_id,"client_secret":c.client_secret,"scopes":c.scopes}; row.updated_at=datetime.utcnow(); db.commit(); return RedirectResponse(get_settings().frontend_url+"/google-sheets?connected=1")

@router.post("/google/configure")
def configure(body:GoogleSelection,db:Session=Depends(get_db),_=Depends(current_user)):
    row=upsert(db,"GOOGLE_SHEETS"); row.configuration=body.model_dump(); db.commit(); return {"configured":True}

@router.post("/google/test")
def test_google(db:Session=Depends(get_db),_=Depends(current_user)):
    row=db.scalar(select(Integration).where(Integration.provider=="GOOGLE_SHEETS"))
    if not row or not row.credentials: raise HTTPException(409,"Connect your Google account first")
    config=row.configuration or {}
    if not config.get("spreadsheet_id") or not config.get("worksheet"): raise HTTPException(409,"Add a spreadsheet and worksheet first")
    try:
        client=GoogleSheetsClient(row.credentials); rows=client.rows(config["spreadsheet_id"],config["worksheet"])
    except Exception as e: raise HTTPException(502,f"Unable to read Google Sheet: {e}")
    row.status="CONNECTED"; db.commit()
    return {"connected":True,"rows":max(0,len(rows)-1),"headers":rows[0] if rows else []}

@router.post("/google/import-text")
def import_sheet_text(body:SheetPasteImport,db:Session=Depends(get_db),_=Depends(current_user)):
    return import_tsv(db,body.raw_text)

@router.get("/google/imported-projects",response_model=list[ProjectOut])
def imported_projects(db:Session=Depends(get_db),_=Depends(current_user)):
    return db.scalars(select(Project).where(Project.source==Source.google_sheets).order_by(Project.deadline.asc().nullslast(),Project.name)).all()

def client_mood(messages:list[str]):
    text=" ".join(messages).lower()
    if any(word in text for word in ["زعلان","غير راضي","اعتراض","مش عاجب","تأخير","متأخر"]): return "غير راضٍ ويحتاج احتواء","negative"
    if any(word in text for word in ["مستعجل","ضروري","اليوم","فين","متى","عاجل"]): return "مستعجل ويحتاج ردًا سريعًا","urgent"
    if any(word in text for word in ["شكرا","شكرًا","تمام","ممتاز","موافق","اعتمد","مناسب"]): return "متعاون أو راضٍ","positive"
    if any(word in text for word in ["هراجع","أراجع","انتظر","مراجعة","هرد","سأراجع"]): return "في مرحلة مراجعة أو انتظار","waiting"
    return "متابعة عادية — لا توجد إشارة حاسمة","neutral"

@router.get("/whatsapp/daily-report")
def whatsapp_daily_report(db:Session=Depends(get_db),_=Depends(current_user)):
    settings=get_settings()
    if not settings.whatsapp_dashboard_token: raise HTTPException(503,"WhatsApp dashboard connection is incomplete")
    try:
        response=httpx.get(settings.whatsapp_dashboard_url,params={"period":"day"},headers={"Authorization":f"Bearer {settings.whatsapp_dashboard_token}"},timeout=20)
        response.raise_for_status(); updates=response.json().get("updates",[])
    except Exception as exc: raise HTTPException(502,f"Unable to read WhatsApp updates: {exc}")
    cairo=ZoneInfo("Africa/Cairo"); today=datetime.now(cairo).date(); rows=[row for row in updates if datetime.fromisoformat(row["messageDate"].replace("Z","+00:00")).astimezone(cairo).date()==today]
    grouped={}
    for row in rows:
        code=row["projectCode"]; item=grouped.setdefault(code,{"project_code":code,"opened":False,"incoming":[],"outgoing":[],"last_activity":row["messageDate"]})
        direction=row.get("direction"); item["opened"]|=direction=="opened"
        if direction=="incoming": item["incoming"].append(row["summary"])
        elif direction=="outgoing": item["outgoing"].append(row["summary"])
        if row["messageDate"]>item["last_activity"]: item["last_activity"]=row["messageDate"]
    projects=db.scalars(select(Project)).all(); names={(p.source_id or "").upper():p.name for p in projects if p.source_id}
    report=[]
    for code,item in grouped.items():
        mood,mood_key=client_mood(item["incoming"]); actions=item["outgoing"][:3]
        report.append({**item,"project_name":names.get(code.upper(),code),"client_status":mood,"client_status_key":mood_key,"work_summary":actions or (["تم فتح المحادثة للمتابعة، ولم تُسجل رسالة صادرة بعدها."] if item["opened"] else [])})
    report.sort(key=lambda item:item["last_activity"],reverse=True)
    return {"date":str(today),"total_chats":len(report),"incoming_count":sum(len(x["incoming"]) for x in report),"outgoing_count":sum(len(x["outgoing"]) for x in report),"projects":report}

@router.get("/daily-plan")
def daily_plan(_=Depends(current_user)):
    try:
        response=httpx.get("https://nehal-work-status.pm-gala.chatgpt.site/api/daily-plan",timeout=25)
        response.raise_for_status(); return response.json()
    except Exception as exc: raise HTTPException(502,f"Unable to read today's plan: {exc}")
