from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Adjustment, TimeEntry, User
from app.schemas import GenerateRemittancesBody, GenerateRemittanceItemOut, GenerateRemittancesResponse
from app.services.remittance import generate_remittances_for_period

router = APIRouter(tags=["remittances"])


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
