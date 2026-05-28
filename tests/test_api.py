import pytest
import pytest_asyncio
from datetime import date
from unittest.mock import patch

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.models import Employee, Client, EmployeeClient, Response, ClientResponse
from tests.conftest import make_employee, make_client, make_response, make_client_response


API_KEY = "change-me-in-production"


@pytest_asyncio.fixture
async def api_client(db_session, engine):
    from dashboard.api import routes
    from dashboard.api.main import app
    from bot.services import export as export_module

    test_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    routes.async_session = test_session_factory
    export_module.async_session = test_session_factory

    with patch("dashboard.api.main.engine", engine):
        transport = ASGITransport(app=app)
        client = AsyncClient(transport=transport, base_url="http://test", headers={"X-API-Key": API_KEY})
        yield client
        await client.aclose()


@pytest_asyncio.fixture
async def setup_data(db_session):
    emp1 = make_employee(telegram_id=1001, username="alice", full_name="Alice Smith")
    emp2 = make_employee(telegram_id=1002, username="bob", full_name="Bob Jones")
    db_session.add_all([emp1, emp2])
    await db_session.commit()
    await db_session.refresh(emp1)
    await db_session.refresh(emp2)

    c1 = make_client(name="Client A")
    c2 = make_client(name="Client B")
    c3 = make_client(name="Client C")
    db_session.add_all([c1, c2, c3])
    await db_session.commit()
    await db_session.refresh(c1)
    await db_session.refresh(c2)
    await db_session.refresh(c3)

    ec1 = EmployeeClient(employee_id=emp1.id, client_id=c1.id)
    ec2 = EmployeeClient(employee_id=emp1.id, client_id=c2.id)
    ec3 = EmployeeClient(employee_id=emp2.id, client_id=c1.id)
    ec4 = EmployeeClient(employee_id=emp2.id, client_id=c3.id)
    db_session.add_all([ec1, ec2, ec3, ec4])
    await db_session.commit()

    w1 = date(2026, 5, 11)
    w2 = date(2026, 5, 4)

    r1 = make_response(
        employee_id=emp1.id, week_start=w1,
        score_workload=4, score_deadlines=3, score_communication=5,
        has_blockers=True, blocker_text="Too much work",
        score_energy=2, has_comment=True, comment_text="Need help",
    )
    r2 = make_response(
        employee_id=emp2.id, week_start=w1,
        score_workload=3, score_deadlines=5, score_communication=4,
        has_blockers=False, blocker_text="",
        score_energy=4, has_comment=False, comment_text="",
    )
    r3 = make_response(
        employee_id=emp1.id, week_start=w2,
        score_workload=2, score_deadlines=4, score_communication=3,
        has_blockers=False, blocker_text="",
        score_energy=5, has_comment=False, comment_text="",
    )
    db_session.add_all([r1, r2, r3])
    await db_session.commit()
    await db_session.refresh(r1)
    await db_session.refresh(r2)
    await db_session.refresh(r3)

    cr1 = make_client_response(response_id=r1.id, client_id=c1.id, score_workload=5, has_blockers=True, blocker_text="Deadline pressure")
    cr2 = make_client_response(response_id=r1.id, client_id=c2.id, score_workload=3, has_blockers=False, blocker_text="")
    cr3 = make_client_response(response_id=r2.id, client_id=c1.id, score_workload=2, has_blockers=False, blocker_text="")
    cr4 = make_client_response(response_id=r2.id, client_id=c3.id, score_workload=4, has_blockers=False, blocker_text="")
    cr5 = make_client_response(response_id=r3.id, client_id=c1.id, score_workload=2, has_blockers=False, blocker_text="")
    db_session.add_all([cr1, cr2, cr3, cr4, cr5])
    await db_session.commit()

    return {
        "employees": [emp1, emp2],
        "clients": [c1, c2, c3],
        "responses": [r1, r2, r3],
        "weeks": [w1, w2],
    }


class TestAPIEndpoints:
    @pytest.mark.asyncio
    async def test_get_weeks(self, api_client, setup_data):
        resp = await api_client.get("/api/weeks")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_get_employees(self, api_client, setup_data):
        resp = await api_client.get("/api/employees")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = [e["full_name"] for e in data]
        assert "Alice Smith" in names

    @pytest.mark.asyncio
    async def test_get_clients(self, api_client, setup_data):
        resp = await api_client.get("/api/clients")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_get_week_summary(self, api_client, setup_data):
        resp = await api_client.get("/api/summary/2026-05-11")
        assert resp.status_code == 200
        data = resp.json()
        assert data["week_start"] == "2026-05-11"
        assert data["completed_surveys"] == 2
        assert data["avg_workload"] is not None
        assert len(data["blockers"]) == 1

    @pytest.mark.asyncio
    async def test_get_week_responses(self, api_client, setup_data):
        resp = await api_client.get("/api/responses/2026-05-11")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        for r in data:
            assert "client_responses" in r
            assert "has_midweek_updates" in r

    @pytest.mark.asyncio
    async def test_get_heatmap(self, api_client, setup_data):
        resp = await api_client.get("/api/heatmap/2026-05-11")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3

    @pytest.mark.asyncio
    async def test_get_dynamics(self, api_client, setup_data):
        resp = await api_client.get("/api/dynamics")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_summary_empty_week(self, api_client, setup_data):
        resp = await api_client.get("/api/summary/2025-01-06")
        assert resp.status_code == 200
        data = resp.json()
        assert data["completed_surveys"] == 0
        assert data["avg_workload"] is None
