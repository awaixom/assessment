from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Adjustment, TimeEntry, User
from app.schemas import (
    GenerateRemittancesBody,
    GenerateRemittanceItemOut,
    GenerateRemittancesResponse,
    SettlementPreviewBatchOut,
    SettlementPreviewResponse,
)
from app.services.remittance import generate_remittances_for_period, plan_settlement_batches

router = APIRouter(tags=["remittances"])


@router.post("/preview-settlement", response_model=SettlementPreviewResponse)
def preview_settlement(body: GenerateRemittancesBody, db: Session = Depends(get_db)):
    plans = plan_settlement_batches(
        db,
        body.period_start,
        body.period_end,
        set(body.exclude_worklog_ids),
        set(body.exclude_user_ids),
    )
    batches = [
        SettlementPreviewBatchOut(
            user_id=p.user.id,
            freelancer_name=p.user.display_name,
            time_entry_ids=[e.id for e in p.entries],
            adjustment_ids=[a.id for a in p.adjustments],
            entry_total_cents=p.entry_total_cents,
            adjustment_total_cents=p.adjustment_total_cents,
            total_cents=p.total_cents,
        )
        for p in plans
    ]
    grand_total_cents = sum(b.total_cents for b in batches)
    return SettlementPreviewResponse(
        period_start=body.period_start,
        period_end=body.period_end,
        batches=batches,
        grand_total_cents=grand_total_cents,
    )


@router.post("/generate-remittances", response_model=GenerateRemittancesResponse)
def generate_remittances(body: GenerateRemittancesBody, db: Session = Depends(get_db)):
    created = generate_remittances_for_period(
        db,
        body.period_start,
        body.period_end,
        set(body.exclude_worklog_ids),
        set(body.exclude_user_ids),
    )
    db.commit()
    items: list[GenerateRemittanceItemOut] = []
    for r in created:
        user = db.get(User, r.user_id)
        settled_ids = [
            e.id
            for e in db.query(TimeEntry)
            .filter(TimeEntry.settled_remittance_id == r.id)
            .all()
        ]
        adj_ids = [
            a.id
            for a in db.query(Adjustment)
            .filter(Adjustment.applied_remittance_id == r.id)
            .all()
        ]
        items.append(
            GenerateRemittanceItemOut(
                remittance_id=r.id,
                user_id=r.user_id,
                freelancer_name=user.display_name if user else "",
                total_cents=r.total_cents,
                status=r.status.value,
                failure_reason=r.failure_reason,
                settled_entry_ids=settled_ids,
                applied_adjustment_ids=adj_ids,
            )
        )
    return GenerateRemittancesResponse(
        period_start=body.period_start,
        period_end=body.period_end,
        remittances=items,
    )
