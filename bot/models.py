from datetime import date, datetime, timezone

from sqlalchemy import (
    String, Integer, BigInteger, Boolean, Text, Date, DateTime, ForeignKey,
    CheckConstraint, UniqueConstraint, Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    telegram_username: Mapped[str | None] = mapped_column(String, nullable=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False, default="employee")
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_vacation_days: Mapped[int | None] = mapped_column(Integer, nullable=True, default=28)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    employee_clients: Mapped[list["EmployeeClient"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    responses: Mapped[list["Response"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    vacation_periods: Mapped[list["VacationPeriod"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("role IN ('employee', 'admin')", name="ck_employee_role"),
    )


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    employee_clients: Mapped[list["EmployeeClient"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    client_responses: Mapped[list["ClientResponse"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )


class EmployeeClient(Base):
    __tablename__ = "employee_clients"

    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True
    )
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    employee: Mapped["Employee"] = relationship(back_populates="employee_clients")
    client: Mapped["Client"] = relationship(back_populates="employee_clients")

    __table_args__ = (
        Index("ix_employee_client_employee", "employee_id"),
    )


class Response(Base):
    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    score_workload: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_deadlines: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_communication: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_blockers: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    blocker_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_energy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_comment: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    comment_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    employee: Mapped["Employee"] = relationship(back_populates="responses")
    client_responses: Mapped[list["ClientResponse"]] = relationship(
        back_populates="response", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("employee_id", "week_start", name="uq_employee_week"),
        CheckConstraint(
            "score_workload IS NULL OR score_workload BETWEEN 1 AND 5",
            name="ck_score_workload",
        ),
        CheckConstraint(
            "score_deadlines IS NULL OR score_deadlines BETWEEN 1 AND 5",
            name="ck_score_deadlines",
        ),
        CheckConstraint(
            "score_communication IS NULL OR score_communication BETWEEN 1 AND 5",
            name="ck_score_communication",
        ),
        CheckConstraint(
            "score_energy IS NULL OR score_energy BETWEEN 1 AND 5",
            name="ck_score_energy",
        ),
        Index("ix_response_week", "week_start"),
    )


class ClientResponse(Base):
    __tablename__ = "client_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    response_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("responses.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    score_workload: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_blockers: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    blocker_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    response: Mapped["Response"] = relationship(back_populates="client_responses")
    client: Mapped["Client"] = relationship(back_populates="client_responses")

    __table_args__ = (
        UniqueConstraint("response_id", "client_id", name="uq_response_client"),
        CheckConstraint(
            "score_workload IS NULL OR score_workload BETWEEN 1 AND 5",
            name="ck_client_score_workload",
        ),
    )


class VacationPeriod(Base):
    __tablename__ = "vacation_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    days_count: Mapped[int] = mapped_column(Integer, nullable=False)
    application_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    employee: Mapped["Employee"] = relationship(back_populates="vacation_periods")

    __table_args__ = (
        CheckConstraint("period_number BETWEEN 1 AND 5", name="ck_period_number"),
        CheckConstraint("days_count > 0", name="ck_days_count"),
        Index("ix_vacation_employee_year", "employee_id", "year"),
    )