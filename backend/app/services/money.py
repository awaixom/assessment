from decimal import Decimal

from app.models import TimeEntry, TimeEntryStatus, User


def entry_amount_cents(entry: TimeEntry, user: User) -> int:
    if entry.status != TimeEntryStatus.APPROVED:
        return 0
    cents = (Decimal(entry.hours) * Decimal(user.hourly_rate_cents)).quantize(Decimal("1"))
    return int(cents)
