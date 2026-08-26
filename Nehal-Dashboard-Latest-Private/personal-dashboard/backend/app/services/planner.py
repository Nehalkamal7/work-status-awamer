from datetime import date, timedelta
from app.models import Task

WEIGHTS = {"CRITICAL": 40, "HIGH": 25, "MEDIUM": 12, "LOW": 4}

def workdays(start: date, count: int, allowed={0,1,2,3,4}):
    result=[]; cursor=start
    while len(result)<count:
        if cursor.weekday() in allowed: result.append(cursor)
        cursor += timedelta(days=1)
    return result

def score(task: Task, today: date) -> float:
    due = (task.deadline-today).days if task.deadline else 365
    urgency = 80 + abs(due)*4 if due < 0 else max(0, 60-due*5)
    remaining = task.estimated_hours * max(0, 1-task.progress/100)
    return urgency + WEIGHTS.get(task.priority.value if hasattr(task.priority,"value") else task.priority, 0) + remaining + (100-task.progress)/10

def schedule(tasks: list[Task], start: date | None=None, daily_capacity: float=8, days: int=5):
    start=start or date.today(); dates=workdays(start,days); capacity={d:daily_capacity for d in dates}; plan={d:[] for d in dates}; overload=[]
    completed={t.id for t in tasks if t.progress>=100}
    ordered=sorted([t for t in tasks if t.progress<100 and t.status.upper() not in {"DONE","CANCELLED"}], key=lambda t: score(t,start), reverse=True)
    for task in ordered:
        remaining=max(.25, task.estimated_hours*(1-task.progress/100)); deps=set(task.dependencies or [])
        eligible=[d for d in dates if not deps or deps.issubset(completed)] or dates
        if task.deadline: eligible=[d for d in eligible if d<=task.deadline] or [dates[0]]
        for d in eligible:
            if remaining<=0: break
            hours=min(remaining,capacity[d])
            if hours>0: plan[d].append({"task_id":task.id,"name":task.name,"hours":round(hours,2),"priority":task.priority.value}); capacity[d]-=hours; remaining-=hours
        if remaining>0: overload.append({"task_id":task.id,"name":task.name,"hours":round(remaining,2)})
        completed.add(task.id)
    return {"days":[{"date":d.isoformat(),"capacity":daily_capacity,"planned":round(daily_capacity-capacity[d],2),"items":plan[d]} for d in dates],"overload_hours":round(sum(x["hours"] for x in overload),2),"overload_tasks":overload}

