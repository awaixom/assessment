from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import (
    Adjustment,
    Remittance,
    RemittanceStatus,
    TimeEntry,
    TimeEntryStatus,
    User,
    WorkLog,
)
from app.services.money import entry_amount_cents


def simulate_payout_success() -> bool:
    return not settings.payout_simulate_failure


@dataclass
class PlannedBatch:
    user: User
    entries: list[TimeEntry]
    adjustments: list[Adjustment]
    entry_total_cents: int
    adjustment_total_cents: int
    total_cents: int


def plan_settlement_batches(
    db: Session,
    period_start: date,
    period_end: date,
    exclude_worklog_ids: set[int],
    exclude_user_ids: set[int],
) -> list[PlannedBatch]:
    """Read-only plan: eligible entries in-window plus unapplied adjustments (same rules as payout)."""
    entries_q = (
        db.query(TimeEntry)
        .join(WorkLog)
        .join(User)
        .options(joinedload(TimeEntry.worklog).joinedload(WorkLog.user))
        .filter(
            TimeEntry.status == TimeEntryStatus.APPROVED,
            TimeEntry.settled_remittance_id.is_(None),
            TimeEntry.occurred_on >= period_start,
            TimeEntry.occurred_on <= period_end,
        )
    )
    if exclude_worklog_ids:
        entries_q = entries_q.filter(~WorkLog.id.in_(exclude_worklog_ids))
    if exclude_user_ids:
        entries_q = entries_q.filter(~User.id.in_(exclude_user_ids))

    entries_by_user: dict[int, list[TimeEntry]] = defaultdict(list)
    for e in entries_q.all():
        uid = e.worklog.user_id
        if uid in exclude_user_ids:
            continue
        if e.worklog_id in exclude_worklog_ids:
            continue
        entries_by_user[uid].append(e)

    adj_q = db.query(Adjustment).filter(Adjustment.applied_remittance_id.is_(None))
    if exclude_user_ids:
        adj_q = adj_q.filter(~Adjustment.user_id.in_(exclude_user_ids))
    if exclude_worklog_ids:
        adj_q = adj_q.filter(
            or_(
                Adjustment.worklog_id.is_(None),
                ~Adjustment.worklog_id.in_(exclude_worklog_ids),
            )
        )
    adjustments_by_user: dict[int, list[Adjustment]] = defaultdict(list)
    for a in adj_q.all():
        adjustments_by_user[a.user_id].append(a)

    user_ids = set(entries_by_user.keys()) | set(adjustments_by_user.keys())
    plans: list[PlannedBatch] = []

    for uid in sorted(user_ids):
        user_entries = entries_by_user.get(uid, [])
        user_adjustments = adjustments_by_user.get(uid, [])
        user = db.get(User, uid)
        if not user:
            continue
        entry_total = sum(
            entry_amount_cents(te, te.worklog.user) for te in user_entries
        )
        adj_total = sum(a.amount_cents for a in user_adjustments)
        total_cents = entry_total + adj_total
        if total_cents == 0:
            continue
        plans.append(
            PlannedBatch(
                user=user,
                entries=user_entries,
                adjustments=user_adjustments,
                entry_total_cents=entry_total,
                adjustment_total_cents=adj_total,
                total_cents=total_cents,
            )
        )
    return plans


def generate_remittances_for_period(
    db: Session,
    period_start: date,
    period_end: date,
    exclude_worklog_ids: set[int],
    exclude_user_ids: set[int],
) -> list[Remittance]:
    plans = plan_settlement_batches(
        db, period_start, period_end, exclude_worklog_ids, exclude_user_ids
    )
    created: list[Remittance] = []

    for plan in plans:
        rem = Remittance(
            user_id=plan.user.id,
            period_start=period_start,
            period_end=period_end,
            total_cents=plan.total_cents,
            status=RemittanceStatus.PENDING,
        )
        db.add(rem)
        db.flush()

        if simulate_payout_success():
            rem.status = RemittanceStatus.COMPLETED
            for te in plan.entries:
                te.settled_remittance_id = rem.id
            for adj in plan.adjustments:
                adj.applied_remittance_id = rem.id
        else:
            rem.status = RemittanceStatus.FAILED
            rem.failure_reason = "Simulated payout provider failure"

        created.append(rem)

    return created
