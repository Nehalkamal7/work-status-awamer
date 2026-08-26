import csv
import io
from datetime import date, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Integration, Priority, Project, Source

def parse_date(value: str):
    value=(value or "").strip()
    if not value: return None
    for fmt in ("%Y-%m-%d","%Y/%m/%d","%d/%m/%Y","%m/%d/%Y"):
        try: return datetime.strptime(value,fmt).date()
        except ValueError: pass
    return None

def rank(satisfaction: str, notes: str, penalty: str):
    text=f"{satisfaction} {notes} {penalty}"
    if any(x in text for x in ("غير راضي","متعصب","أولوية","شرط جزائي","الأهم")): return Priority.critical
    if any(x in text for x in ("مقبول","مستعجل","تأخير","مهم")): return Priority.high
    return Priority.medium

def import_tsv(db: Session, raw_text: str):
    rows=list(csv.reader(io.StringIO(raw_text),delimiter="\t")); created=updated=skipped=0
    for row in rows:
        if len(row)<31 or not row[3].strip() or not row[4].strip(): skipped+=1; continue
        code=row[3].strip(); item=db.scalar(select(Project).where(Project.source==Source.google_sheets,Project.source_id==code))
        if not item: item=Project(source=Source.google_sheets,source_id=code,name=row[4].strip());db.add(item);created+=1
        else: updated+=1
        note=row[30].strip(); idea=row[5].strip(); item.name=row[4].strip(); item.client=row[1].strip() or None
        item.description="\n\n".join(x for x in (idea,note and f"Latest note: {note}") if x)
        item.status=row[25].strip() or row[24].strip() or "ACTIVE"; item.priority=rank(row[27],note,row[28])
        item.start_date=parse_date(row[18]) or parse_date(row[0]); item.deadline=parse_date(row[22]) or parse_date(row[21])
        item.assigned_to=row[26].strip() or None; item.progress=0; item.last_synced_at=datetime.utcnow()
    integration=db.scalar(select(Integration).where(Integration.provider=="GOOGLE_SHEETS"))
    if not integration: integration=Integration(provider="GOOGLE_SHEETS");db.add(integration)
    integration.status="IMPORTED";integration.last_sync=datetime.utcnow();integration.configuration={"mode":"PASTED_TSV","rows":created+updated}
    db.commit();return {"created":created,"updated":updated,"skipped":skipped,"total":created+updated}
