import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.models import Base, Employee, Client, EmployeeClient, Response, ClientResponse, VacationPeriod


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def make_employee(telegram_id=12345, username="testuser", full_name="Test User", role="employee"):
    return Employee(
        telegram_id=telegram_id,
        telegram_username=username,
        full_name=full_name,
        role=role,
    )


def make_client(name="Test Client"):
    return Client(name=name)


def make_response(employee_id, week_start=None, **kwargs):
    if week_start is None:
        week_start = date.today() - timedelta(days=date.today().weekday())
    defaults = dict(
        employee_id=employee_id,
        week_start=week_start,
        score_workload=3,
        score_deadlines=4,
        score_communication=5,
        has_blockers=False,
        blocker_text="",
        score_energy=4,
        has_comment=False,
        comment_text="",
        completed_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Response(**defaults)


def make_client_response(response_id, client_id, **kwargs):
    defaults = dict(
        response_id=response_id,
        client_id=client_id,
        score_workload=4,
        has_blockers=False,
        blocker_text="",
    )
    defaults.update(kwargs)
    return ClientResponse(**defaults)


@pytest.fixture
def sample_week():
    return date(2026, 5, 11)


@pytest.fixture
def prev_week():
    return date(2026, 5, 4)


def make_vacation_period(employee_id, year=2026, start_date=None, end_date=None, days_count=14, **kwargs):
    if start_date is None:
        start_date = date(year, 6, 1)
    if end_date is None:
        end_date = start_date + timedelta(days=days_count - 1)
    defaults = dict(
        employee_id=employee_id,
        year=year,
        start_date=start_date,
        end_date=end_date,
        days_count=days_count,
    )
    defaults.update(kwargs)
    return VacationPeriod(**defaults)