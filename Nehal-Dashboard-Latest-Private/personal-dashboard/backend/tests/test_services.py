from datetime import date,timedelta
from types import SimpleNamespace
from app.services.deadlines import deadline_status
from app.services.planner import schedule

def test_deadline_states():
    today=date(2026,8,19)
    assert deadline_status(today-timedelta(days=2),0,today)["days_overdue"]==2
    assert deadline_status(today,0,today)["status"]=="DUE_TODAY"
    assert deadline_status(today+timedelta(days=1),0,today)["status"]=="DUE_TOMORROW"
    assert deadline_status(today,100,today)["status"]=="COMPLETED"
def test_planner_respects_capacity():
    p=SimpleNamespace(value="HIGH"); t=SimpleNamespace(id="1",name="Ship",deadline=date(2026,8,21),priority=p,progress=0,estimated_hours=10,status="TODO",dependencies=[])
    result=schedule([t],date(2026,8,19),daily_capacity=4)
    assert sum(d["planned"] for d in result["days"])==10
    assert all(d["planned"]<=4 for d in result["days"])
