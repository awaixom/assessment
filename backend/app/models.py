import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RemittanceStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TimeEntryStatus(str, enum.Enum):
    APPROVED = "approved"
    EXCLUDED = "excluded"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hourly_rate_cents: Mapped[int] = mapped_column(Integer, default=5000)

    worklogs: Mapped[list["WorkLog"]] = relationship(back_populates="user")
    remittances: Mapped[list["Remittance"]] = relationship(back_populates="user")
    adjustments: Mapped[list["Adjustment"]] = relationship(back_populates="user")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512))

    worklogs: Mapped[list["WorkLog"]] = relationship(back_populates="task")


class WorkLog(Base):
    __tablename__ = "worklogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    task: Mapped["Task"] = relationship(back_populates="worklogs")
    user: Mapped["User"] = relationship(back_populates="worklogs")
    time_entries: Mapped[list["TimeEntry"]] = relationship(
        back_populates="worklog", cascade="all, delete-orphan"
    )


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    worklog_id: Mapped[int] = mapped_column(ForeignKey("worklogs.id"), index=True)
    occurred_on: Mapped[date] = mapped_column(Date, index=True)
    hours: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TimeEntryStatus] = mapped_column(
        Enum(TimeEntryStatus), default=TimeEntryStatus.APPROVED
    )
    settled_remittance_id: Mapped[int | None] = mapped_column(
        ForeignKey("remittances.id"), nullable=True, index=True
    )

    worklog: Mapped["WorkLog"] = relationship(back_populates="time_entries")
    settled_remittance: Mapped["Remittance | None"] = relationship(
        back_populates="settled_entries", foreign_keys=[settled_remittance_id]
    )


class Adjustment(Base):
    __tablename__ = "adjustments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    worklog_id: Mapped[int | None] = mapped_column(
        ForeignKey("worklogs.id"), nullable=True, index=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text)
    relates_to_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    relates_to_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    applied_remittance_id: Mapped[int | None] = mapped_column(
        ForeignKey("remittances.id"), nullable=True, index=True
    )

    user: Mapped["User"] = relationship(back_populates="adjustments")
    applied_remittance: Mapped["Remittance | None"] = relationship(
        back_populates="applied_adjustments", foreign_keys=[applied_remittance_id]
    )


class Remittance(Base):
    __tablename__ = "remittances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    total_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[RemittanceStatus] = mapped_column(
        Enum(RemittanceStatus), default=RemittanceStatus.PENDING
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="remittances")
    settled_entries: Mapped[list["TimeEntry"]] = relationship(
        back_populates="settled_remittance",
        foreign_keys=[TimeEntry.settled_remittance_id],
    )
    applied_adjustments: Mapped[list["Adjustment"]] = relationship(
        back_populates="applied_remittance",
        foreign_keys=[Adjustment.applied_remittance_id],
    )
