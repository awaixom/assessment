import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Adjustment, Task, TimeEntry, TimeEntryStatus, User, WorkLog


def load_seed_if_empty(db: Session) -> None:
    if db.query(User).first():
        return
    path = Path("/app/seed/worklogs.json")
    if not path.exists():
        path = Path(__file__).resolve().parents[2] / "seed" / "worklogs.json"
    if not path.exists():
        return
    data = json.loads(path.read_text())
    users_by_ext: dict[str, User] = {}
    for u in data.get("users", []):
        user = User(
            external_id=u["external_id"],
            display_name=u["display_name"],
            email=u["email"],
            hourly_rate_cents=int(u.get("hourly_rate_cents", 5000)),
        )
        db.add(user)
        db.flush()
        users_by_ext[u["external_id"]] = user
    tasks_by_ext: dict[str, Task] = {}
    for t in data.get("tasks", []):
        task = Task(external_id=t["external_id"], title=t["title"])
        db.add(task)
        db.flush()
        tasks_by_ext[t["external_id"]] = task
    wlogs_by_ext: dict[str, WorkLog] = {}
    for w in data.get("worklogs", []):
        wl = WorkLog(
            external_id=w["external_id"],
            task_id=tasks_by_ext[w["task_external_id"]].id,
            user_id=users_by_ext[w["user_external_id"]].id,
        )
        db.add(wl)
        db.flush()
        wlogs_by_ext[w["external_id"]] = wl
    for e in data.get("time_entries", []):
        te = TimeEntry(
            worklog_id=wlogs_by_ext[e["worklog_external_id"]].id,
            occurred_on=date.fromisoformat(e["occurred_on"]),
            hours=Decimal(str(e["hours"])),
            memo=e.get("memo"),
            status=TimeEntryStatus(e.get("status", "approved")),
        )
        db.add(te)
    for a in data.get("adjustments", []):
        adj = Adjustment(
            user_id=users_by_ext[a["user_external_id"]].id,
            worklog_id=wlogs_by_ext[a["worklog_external_id"]].id
            if a.get("worklog_external_id")
            else None,
            amount_cents=int(a["amount_cents"]),
            reason=a["reason"],
            relates_to_period_start=date.fromisoformat(a["relates_to_period_start"])
            if a.get("relates_to_period_start")
            else None,
            relates_to_period_end=date.fromisoformat(a["relates_to_period_end"])
            if a.get("relates_to_period_end")
            else None,
        )
        db.add(adj)
    db.commit()
