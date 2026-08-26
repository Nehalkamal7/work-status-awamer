from celery import Celery
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.sync.engine import SyncEngine

s=get_settings(); celery=Celery("dashboard",broker=s.redis_url,backend=s.redis_url)
celery.conf.beat_schedule={"sync-odoo":{"task":"sync.odoo","schedule":s.sync_interval_minutes*60}}
@celery.task(name="sync.odoo",autoretry_for=(Exception,),retry_backoff=True,retry_kwargs={"max_retries":3})
def sync_odoo():
    with SessionLocal() as db: return SyncEngine(db).odoo().id

