from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class RemittanceFilter(str, Enum):
    REMITTED = "REMITTED"
    UNREMITTED = "UNREMITTED"


class GenerateRemittancesBody(BaseModel):
    period_start: date
    period_end: date
    exclude_worklog_ids: list[int] = Field(default_factory=list)
    exclude_user_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def period_order(self):
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self


class TimeEntryOut(BaseModel):
    id: int
    occurred_on: date
    hours: Decimal
    memo: str | None
    status: str
    amount_cents: int
    settled_remittance_id: int | None

    model_config = {"from_attributes": True}


class WorkLogSummaryOut(BaseModel):
    id: int
    external_id: str
    task_id: int
    task_title: str
    user_id: int
    freelancer_name: str
    freelancer_email: str
    total_hours: Decimal
    amount_cents: int
    remitted_amount_cents: int
    unremitted_amount_cents: int
    remittance_status: RemittanceFilter


class WorkLogDetailOut(WorkLogSummaryOut):
    time_entries: list[TimeEntryOut]


class GenerateRemittanceItemOut(BaseModel):
    remittance_id: int
    user_id: int
    freelancer_name: str
    total_cents: int
    status: str
    failure_reason: str | None = None
    settled_entry_ids: list[int]
    applied_adjustment_ids: list[int]


class GenerateRemittancesResponse(BaseModel):
    period_start: date
    period_end: date
    remittances: list[GenerateRemittanceItemOut]


class SettlementPreviewBatchOut(BaseModel):
    user_id: int
    freelancer_name: str
    time_entry_ids: list[int]
    adjustment_ids: list[int]
    entry_total_cents: int
    adjustment_total_cents: int
    total_cents: int


class SettlementPreviewResponse(BaseModel):
    period_start: date
    period_end: date
    batches: list[SettlementPreviewBatchOut]
    grand_total_cents: int


class PatchTimeEntryBody(BaseModel):
    status: str  # approved | excluded
