from datetime import date, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.integrations.odoo.client import OdooClient
from app.models import Integration, Priority, Project, Source, SyncLog, Task

def priority(value): return Priority.critical if str(value)=="3" else Priority.high if str(value)=="2" else Priority.medium if str(value)=="1" else Priority.low
def relation(value): return str(value[1]) if isinstance(value,list) and len(value)>1 else None
def parse_date(value):
    if not value: return None
    try: return date.fromisoformat(str(value)[:10])
    except ValueError: return None

class SyncEngine:
    def __init__(self,db:Session): self.db=db
    def odoo(self):
        log=SyncLog(provider="ODOO",operation="PULL",status="RUNNING"); self.db.add(log); self.db.commit()
        created=updated=0
        try:
            client=OdooClient(); projects=client.projects(); tasks=client.tasks(); project_map={}
            for raw in projects:
                item=self.db.scalar(select(Project).where(Project.source==Source.odoo,Project.source_id==str(raw["id"])))
                if not item: item=Project(source=Source.odoo,source_id=str(raw["id"]),name=raw["name"]); self.db.add(item); created+=1
                else: updated+=1
                item.name=raw["name"]; item.client=relation(raw.get("partner_id")); item.assigned_to=relation(raw.get("user_id")); item.start_date=parse_date(raw.get("date_start")); item.deadline=parse_date(raw.get("date")); item.source_url=f"{client.url}/web#id={raw['id']}&model=project.project"; item.last_synced_at=datetime.utcnow(); self.db.flush(); project_map[raw["id"]]=item.id
            for raw in tasks:
                pid=raw.get("project_id",[None])[0] if raw.get("project_id") else None
                if pid not in project_map:
                    external_id=str(pid) if pid else "unassigned"
                    fallback=self.db.scalar(select(Project).where(Project.source==Source.odoo,Project.source_id==external_id))
                    if not fallback:
                        label=relation(raw.get("project_id")) or "Odoo Inbox / Unassigned Tasks"
                        fallback=Project(source=Source.odoo,source_id=external_id,name=label,status="ACTIVE",last_synced_at=datetime.utcnow())
                        self.db.add(fallback); self.db.flush(); created+=1
                    project_map[pid]=fallback.id
                item=self.db.scalar(select(Task).where(Task.source==Source.odoo,Task.source_id==str(raw["id"])))
                if not item: item=Task(source=Source.odoo,source_id=str(raw["id"]),project_id=project_map[pid],name=raw["name"]); self.db.add(item); created+=1
                else: updated+=1
                item.name=raw["name"]; item.priority=priority(raw.get("priority")); item.deadline=parse_date(raw.get("date_deadline")); item.estimated_hours=raw.get("allocated_hours") or 0; item.actual_hours=raw.get("effective_hours") or 0; item.progress=raw.get("progress") or 0; item.assigned_to=", ".join(map(str,raw.get("user_ids") or [])) or None; item.status=relation(raw.get("stage_id")) or "TODO"; item.source_url=f"{client.url}/web#id={raw['id']}&model=project.task"; item.last_synced_at=datetime.utcnow()
            row=self.db.scalar(select(Integration).where(Integration.provider=="ODOO")) or Integration(provider="ODOO"); self.db.add(row); row.status="CONNECTED"; row.last_sync=datetime.utcnow(); log.status="SUCCESS"; log.records_created=created; log.records_updated=updated
        except Exception as e: log.status="FAILED"; log.error_message=str(e); self.db.rollback(); self.db.add(log); raise
        finally: log.completed_at=datetime.utcnow(); self.db.commit()
        return log
