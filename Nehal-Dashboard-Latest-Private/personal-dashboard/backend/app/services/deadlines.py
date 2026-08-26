from datetime import date

def deadline_status(deadline: date | None, progress: float = 0, today: date | None = None) -> dict:
    today = today or date.today()
    if progress >= 100: return {"status": "COMPLETED", "days_remaining": None, "days_overdue": 0}
    if not deadline: return {"status": "ON_TRACK", "days_remaining": None, "days_overdue": 0}
    delta = (deadline - today).days
    status = "OVERDUE" if delta < 0 else "DUE_TODAY" if delta == 0 else "DUE_TOMORROW" if delta == 1 else "DUE_SOON" if delta <= 3 else "ON_TRACK"
    return {"status": status, "days_remaining": max(delta, 0), "days_overdue": abs(min(delta, 0))}

