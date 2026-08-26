from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import create_token, current_user, hash_password, verify_password
from app.models import Activity, Integration, Notification, Project, SyncConflict, SyncLog, Task, User
from app.schemas.api import ConflictResolution, Login, NotificationOut, ProjectIn, ProjectOut, Register, TaskIn, TaskOut, Token, UserOut
from app.services.deadlines import deadline_status
from app.services.planner import schedule, score

router=APIRouter(prefix="/api")

@router.post("/auth/register",response_model=UserOut,status_code=201)
def register(body:Register,db:Session=Depends(get_db)):
    if db.scalar(select(User).where(User.email==body.email.lower())): raise HTTPException(409,"Email already registered")
    user=User(email=body.email.lower(),name=body.name,password_hash=hash_password(body.password)); db.add(user); db.commit(); db.refresh(user); return user

@router.post("/auth/login",response_model=Token)
def login(body:Login,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==body.email.lower()))
    if not user or not verify_password(body.password,user.password_hash): raise HTTPException(401,"Invalid email or password")
    return Token(access_token=create_token(user.id),refresh_token=create_token(user.id,"refresh"))

@router.get("/auth/me",response_model=UserOut)
def me(user:User=Depends(current_user)): return user

@router.get("/projects",response_model=list[ProjectOut])
def projects(source:str|None=None,status:str|None=None,priority:str|None=None,q:str|None=None,db:Session=Depends(get_db),_=Depends(current_user)):
    stmt=select(Project)
    if source: stmt=stmt.where(Project.source==source)
    if status: stmt=stmt.where(Project.status==status)
    if priority: stmt=stmt.where(Project.priority==priority)
    if q: stmt=stmt.where(or_(Project.name.ilike(f"%{q}%"),Project.client.ilike(f"%{q}%")))
    return db.scalars(stmt.order_by(Project.deadline.asc().nullslast())).all()

@router.post("/projects",response_model=ProjectOut,status_code=201)
def create_project(body:ProjectIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    item=Project(**body.model_dump()); db.add(item); db.flush(); db.add(Activity(entity_type="project",entity_id=item.id,actor_id=user.id,action="CREATED",new_value=body.model_dump(mode="json"))); db.commit(); db.refresh(item); return item

@router.get("/projects/{item_id}")
def project(item_id:str,db:Session=Depends(get_db),_=Depends(current_user)):
    item=db.get(Project,item_id)
    if not item: raise HTTPException(404,"Project not found")
    return {"project":ProjectOut.model_validate(item),"tasks":[TaskOut.model_validate(x) for x in item.tasks],"deadline":deadline_status(item.deadline,item.progress),"activity":db.scalars(select(Activity).where(Activity.entity_id==item_id).order_by(Activity.created_at.desc())).all()}

@router.patch("/projects/{item_id}",response_model=ProjectOut)
def update_project(item_id:str,body:ProjectIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    item=db.get(Project,item_id)
    if not item: raise HTTPException(404,"Project not found")
    old={k:getattr(item,k) for k in body.model_dump()}; [setattr(item,k,v) for k,v in body.model_dump().items()]; db.add(Activity(entity_type="project",entity_id=item.id,actor_id=user.id,action="UPDATED",old_value={k:str(v) if v is not None else None for k,v in old.items()},new_value=body.model_dump(mode="json"))); db.commit(); db.refresh(item); return item

@router.delete("/projects/{item_id}",status_code=204)
def delete_project(item_id:str,db:Session=Depends(get_db),_=Depends(current_user)):
    item=db.get(Project,item_id)
    if not item: raise HTTPException(404,"Project not found")
    db.delete(item); db.commit()

@router.get("/tasks",response_model=list[TaskOut])
def tasks(project_id:str|None=None,priority:str|None=None,status:str|None=None,db:Session=Depends(get_db),_=Depends(current_user)):
    stmt=select(Task)
    if project_id: stmt=stmt.where(Task.project_id==project_id)
    if priority: stmt=stmt.where(Task.priority==priority)
    if status: stmt=stmt.where(Task.status==status)
    return db.scalars(stmt.order_by(Task.deadline.asc().nullslast())).all()

@router.post("/tasks",response_model=TaskOut,status_code=201)
def create_task(body:TaskIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    if not db.get(Project,body.project_id): raise HTTPException(404,"Project not found")
    item=Task(**body.model_dump()); db.add(item); db.flush(); db.add(Activity(entity_type="task",entity_id=item.id,actor_id=user.id,action="CREATED",new_value=body.model_dump(mode="json")))
    if body.priority.value in {"CRITICAL","HIGH"}: db.add(Notification(user_id=user.id,type="HIGH_PRIORITY",title=f"{body.priority.value.title()} priority task",message=body.name,task_id=item.id,project_id=item.project_id))
    db.commit(); db.refresh(item); return item

@router.patch("/tasks/{item_id}",response_model=TaskOut)
def update_task(item_id:str,body:TaskIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    item=db.get(Task,item_id)
    if not item: raise HTTPException(404,"Task not found")
    old={k:getattr(item,k) for k in body.model_dump()}; [setattr(item,k,v) for k,v in body.model_dump().items()]; db.add(Activity(entity_type="task",entity_id=item.id,actor_id=user.id,action="UPDATED",old_value={k:str(v) if v is not None else None for k,v in old.items()},new_value=body.model_dump(mode="json"))); db.commit(); db.refresh(item); return item

@router.delete("/tasks/{item_id}",status_code=204)
def delete_task(item_id:str,db:Session=Depends(get_db),_=Depends(current_user)):
    item=db.get(Task,item_id)
    if not item: raise HTTPException(404,"Task not found")
    db.delete(item); db.commit()

@router.get("/dashboard")
def dashboard(db:Session=Depends(get_db),_=Depends(current_user)):
    ps=db.scalars(select(Project)).all(); ts=db.scalars(select(Task).where(Task.progress<100)).all(); today=date.today()
    classified=[(t,deadline_status(t.deadline,t.progress,today)) for t in ts]
    focus=sorted(ts,key=lambda t:score(t,today),reverse=True)[:5]
    return {"metrics":{"total_projects":len(ps),"active_projects":sum(p.status=="ACTIVE" for p in ps),"completed":sum(p.progress>=100 for p in ps),"overdue":sum(x[1]["status"]=="OVERDUE" for x in classified),"due_today":sum(x[1]["status"]=="DUE_TODAY" for x in classified),"due_soon":sum(x[1]["status"] in {"DUE_TOMORROW","DUE_SOON"} for x in classified)},"focus":[{"task":TaskOut.model_validate(t),"deadline":deadline_status(t.deadline,t.progress,today)} for t in focus],"integrations":integration_health(db)}

@router.get("/planner")
def planner(daily_capacity:float=Query(8,gt=0,le=24),db:Session=Depends(get_db),_=Depends(current_user)): return schedule(list(db.scalars(select(Task)).all()),daily_capacity=daily_capacity)

@router.get("/calendar")
def calendar(start:date,end:date,db:Session=Depends(get_db),_=Depends(current_user)):
    tasks=db.scalars(select(Task).where(Task.deadline.between(start,end))).all(); projects=db.scalars(select(Project).where(Project.deadline.between(start,end))).all()
    return [{"id":x.id,"title":x.name,"date":x.deadline,"kind":"task","priority":x.priority} for x in tasks]+[{"id":x.id,"title":x.name,"date":x.deadline,"kind":"project","priority":x.priority} for x in projects]

@router.get("/notifications",response_model=list[NotificationOut])
def notifications(db:Session=Depends(get_db),user:User=Depends(current_user)): return db.scalars(select(Notification).where(Notification.user_id==user.id).order_by(Notification.created_at.desc())).all()
@router.post("/notifications/{item_id}/read",status_code=204)
def read_notification(item_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    item=db.scalar(select(Notification).where(Notification.id==item_id,Notification.user_id==user.id));
    if not item: raise HTTPException(404,"Notification not found")
    item.is_read=True; db.commit()
@router.post("/notifications/read-all",status_code=204)
def read_all(db:Session=Depends(get_db),user:User=Depends(current_user)):
    for item in db.scalars(select(Notification).where(Notification.user_id==user.id,Notification.is_read==False)): item.is_read=True
    db.commit()

def integration_health(db):
    records={x.provider:x for x in db.scalars(select(Integration)).all()}
    return {p:{"status":records[p].status if p in records else "DISCONNECTED","last_sync":records[p].last_sync if p in records else None} for p in ["ODOO","GOOGLE_SHEETS"]}

@router.get("/integrations")
def integrations(db:Session=Depends(get_db),_=Depends(current_user)): return integration_health(db)
@router.get("/sync/logs")
def sync_logs(db:Session=Depends(get_db),_=Depends(current_user)): return db.scalars(select(SyncLog).order_by(SyncLog.started_at.desc()).limit(100)).all()
@router.get("/conflicts")
def conflicts(db:Session=Depends(get_db),_=Depends(current_user)): return db.scalars(select(SyncConflict).where(SyncConflict.status=="OPEN").order_by(SyncConflict.created_at.desc())).all()
@router.post("/conflicts/{item_id}/resolve")
def resolve(item_id:str,body:ConflictResolution,db:Session=Depends(get_db),_=Depends(current_user)):
    item=db.get(SyncConflict,item_id)
    if not item: raise HTTPException(404,"Conflict not found")
    allowed={"ODOO":item.odoo_value,"GOOGLE_SHEETS":item.google_value,"MANUAL":body.value,"LATEST":body.value}
    if body.strategy not in allowed: raise HTTPException(422,"Unknown resolution strategy")
    item.status="RESOLVED"; item.resolution=body.strategy; item.resolved_value=allowed[body.strategy]; item.resolved_at=datetime.utcnow(); db.commit(); return item

