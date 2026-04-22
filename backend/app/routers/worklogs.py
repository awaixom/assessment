from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, exists
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import RemittanceStatus, TimeEntry, TimeEntryStatus, WorkLog
from app.schemas import PatchTimeEntryBody, RemittanceFilter, TimeEntryOut, WorkLogDetailOut, WorkLogSummaryOut
from app.services.money import entry_amount_cents

router = APIRouter(prefix="/worklogs", tags=["worklogs"])


def _summarize_worklog(
    wl: WorkLog,
    period_start: date | None = None,
    period_end: date | None = None,
) -> tuple[Decimal, int, int, int, RemittanceFilter]:
    total_hours = Decimal("0")
    amount_cents = 0
    remitted_cents = 0
    unremitted_cents = 0
    for te in wl.time_entries:
        if te.status != TimeEntryStatus.APPROVED:
            continue
        if period_start is not None and period_end is not None:
            if te.occurred_on < period_start or te.occurred_on > period_end:
                continue
        total_hours += te.hours
        ac = entry_amount_cents(te, wl.user)
        amount_cents += ac
        if te.settled_remittance_id is not None:
            r = te.settled_remittance
            if r and r.status == RemittanceStatus.COMPLETED:
                remitted_cents += ac
            else:
                unremitted_cents += ac
        else:
            unremitted_cents += ac
    if amount_cents == 0:
        status = RemittanceFilter.REMITTED
    elif unremitted_cents == 0:
        status = RemittanceFilter.REMITTED
    else:
        status = RemittanceFilter.UNREMITTED
    return total_hours, amount_cents, remitted_cents, unremitted_cents, status


@router.get("", response_model=list[WorkLogSummaryOut])
def list_worklogs(
    db: Session = Depends(get_db),
    remittance_status: RemittanceFilter | None = Query(None),
    user_id: int | None = Query(None),
    period_start: date | None = Query(None),
    period_end: date | None = Query(None),
):
    q = db.query(WorkLog).options(
        joinedload(WorkLog.task),
        joinedload(WorkLog.user),
        joinedload(WorkLog.time_entries).joinedload(TimeEntry.settled_remittance),
    )
    if user_id is not None:
        q = q.filter(WorkLog.user_id == user_id)

    if period_start is not None and period_end is not None:
        q = q.filter(
            exists().where(
                and_(
                    TimeEntry.worklog_id == WorkLog.id,
                    TimeEntry.occurred_on >= period_start,
                    TimeEntry.occurred_on <= period_end,
                    TimeEntry.status == TimeEntryStatus.APPROVED,
                )
            )
        )
    elif period_start is not None or period_end is not None:
        raise HTTPException(
            status_code=400, detail="Provide both period_start and period_end"
        )

    if period_start is not None and period_end is not None and period_end < period_start:
        raise HTTPException(
            status_code=400, detail="period_end must be on or after period_start"
        )

    rows: list[WorkLogSummaryOut] = []
    for wl in q.order_by(WorkLog.id).all():
        th, amt, rem, unrem, st = _summarize_worklog(wl, period_start, period_end)
        if remittance_status is not None and st != remittance_status:
            continue
        rows.append(
            WorkLogSummaryOut(
                id=wl.id,
                external_id=wl.external_id,
                task_id=wl.task_id,
                task_title=wl.task.title,
                user_id=wl.user_id,
                freelancer_name=wl.user.display_name,
                freelancer_email=wl.user.email,
                total_hours=th,
                amount_cents=amt,
                remitted_amount_cents=rem,
                unremitted_amount_cents=unrem,
                remittance_status=st,
            )
        )
    return rows


@router.patch("/time-entries/{entry_id}")
def patch_time_entry(entry_id: int, body: PatchTimeEntryBody, db: Session = Depends(get_db)):
    te = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not te:
        raise HTTPException(status_code=404, detail="Time entry not found")
    if body.status.lower() == "approved":
        te.status = TimeEntryStatus.APPROVED
    elif body.status.lower() == "excluded":
        te.status = TimeEntryStatus.EXCLUDED
    else:
        raise HTTPException(status_code=400, detail="status must be approved or excluded")
    db.commit()
    return {"ok": True, "id": entry_id, "status": te.status.value}


@router.get("/{worklog_id}", response_model=WorkLogDetailOut)
def get_worklog(worklog_id: int, db: Session = Depends(get_db)):
    wl = (
        db.query(WorkLog)
        .options(
            joinedload(WorkLog.task),
            joinedload(WorkLog.user),
            joinedload(WorkLog.time_entries).joinedload(TimeEntry.settled_remittance),
        )
        .filter(WorkLog.id == worklog_id)
        .first()
    )
    if not wl:
        raise HTTPException(status_code=404, detail="Worklog not found")
    th, amt, rem, unrem, st = _summarize_worklog(wl)
    entries = [
        TimeEntryOut(
            id=te.id,
            occurred_on=te.occurred_on,
            hours=te.hours,
            memo=te.memo,
            status=te.status.value,
            amount_cents=entry_amount_cents(te, wl.user),
            settled_remittance_id=te.settled_remittance_id,
        )
        for te in sorted(wl.time_entries, key=lambda x: (x.occurred_on, x.id))
    ]
    return WorkLogDetailOut(
        id=wl.id,
        external_id=wl.external_id,
        task_id=wl.task_id,
        task_title=wl.task.title,
        user_id=wl.user_id,
        freelancer_name=wl.user.display_name,
        freelancer_email=wl.user.email,
        total_hours=th,
        amount_cents=amt,
        remitted_amount_cents=rem,
        unremitted_amount_cents=unrem,
        remittance_status=st,
        time_entries=entries,
    )
