import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from unittest.mock import patch

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.models import Employee, Client, EmployeeClient, Response, ClientResponse, VacationPeriod
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
        client = AsyncClient(transport=transport, base_url="http://test")
        yield client
        await client.aclose()


class TestAPIAuth:
    @pytest.mark.asyncio
    async def test_health_check_no_auth_required(self, api_client):
        resp = await api_client.get("/health")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_api_requires_auth(self, api_client):
        resp = await api_client.get("/api/weeks")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_api_with_valid_key(self, api_client):
        resp = await api_client.get("/api/weeks", headers={"X-API-Key": API_KEY})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_api_with_invalid_key(self, api_client):
        resp = await api_client.get("/api/weeks", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_api_employees_with_auth(self, api_client, db_session):
        emp = make_employee(telegram_id=2001, full_name="Auth Test User")
        db_session.add(emp)
        await db_session.commit()

        resp = await api_client.get("/api/employees", headers={"X-API-Key": API_KEY})
        assert resp.status_code == 200
        data = resp.json()
        assert any(e["full_name"] == "Auth Test User" for e in data)


class TestAPIVacations:
    @pytest.mark.asyncio
    async def test_get_vacations_empty(self, api_client, db_session):
        resp = await api_client.get("/api/vacations", headers={"X-API-Key": API_KEY})
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_post_vacations_creates_periods(self, api_client, db_session):
        emp = make_employee(telegram_id=3001, full_name="Vacation Employee")
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        payload = [
            {
                "year": "2026",
                "name": "Test 2026",
                "employees": [
                    {
                        "employee_id": emp.id,
                        "periods": [
                            {
                                "start": "2026-06-01",
                                "end": "2026-06-14",
                                "days": 14,
                                "period_number": 1,
                            }
                        ],
                    }
                ],
            }
        ]

        resp = await api_client.post(
            "/api/vacations",
            json=payload,
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        resp = await api_client.get("/api/vacations", headers={"X-API-Key": API_KEY})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["year"] == "2026"
        assert len(data[0]["employees"]) == 1
        assert data[0]["employees"][0]["periods"][0]["days"] == 14

    @pytest.mark.asyncio
    async def test_post_vacations_replaces_existing(self, api_client, db_session):
        emp = make_employee(telegram_id=3002, full_name="Replace Employee")
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        payload_v1 = [
            {
                "year": "2026",
                "name": "Replace Test",
                "employees": [
                    {
                        "employee_id": emp.id,
                        "periods": [
                            {
                                "start": "2026-03-01",
                                "end": "2026-03-14",
                                "days": 14,
                                "period_number": 1,
                            }
                        ],
                    }
                ],
            }
        ]

        await api_client.post(
            "/api/vacations",
            json=payload_v1,
            headers={"X-API-Key": API_KEY},
        )

        payload_v2 = [
            {
                "year": "2026",
                "name": "Replace Test",
                "employees": [
                    {
                        "employee_id": emp.id,
                        "periods": [
                            {
                                "start": "2026-07-01",
                                "end": "2026-07-28",
                                "days": 28,
                                "period_number": 1,
                            }
                        ],
                    }
                ],
            }
        ]

        resp = await api_client.post(
            "/api/vacations",
            json=payload_v2,
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 200

        resp = await api_client.get("/api/vacations", headers={"X-API-Key": API_KEY})
        data = resp.json()
        year_data = [d for d in data if d["year"] == "2026"][0]
        periods = year_data["employees"][0]["periods"]
        assert len(periods) == 1
        assert periods[0]["days"] == 28


class TestAPIExport:
    @pytest.mark.asyncio
    async def test_export_csv_with_auth(self, api_client, db_session, sample_week):
        resp = await api_client.get(
            f"/api/export/{sample_week.isoformat()}/csv",
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_export_xlsx_with_auth(self, api_client, db_session, sample_week):
        resp = await api_client.get(
            f"/api/export/{sample_week.isoformat()}/xlsx",
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_export_csv_without_auth(self, api_client, sample_week):
        resp = await api_client.get(f"/api/export/{sample_week.isoformat()}/csv")
        assert resp.status_code in (401, 403)


class TestAPIClientBlockers:
    @pytest.mark.asyncio
    async def test_client_blockers_endpoint(self, api_client, db_session, sample_week):
        emp = make_employee(telegram_id=4001, full_name="Blocker Emp")
        client = make_client(name="Blocker Client")
        db_session.add_all([emp, client])
        await db_session.commit()
        await db_session.refresh(emp)
        await db_session.refresh(client)

        ec = EmployeeClient(employee_id=emp.id, client_id=client.id)
        db_session.add(ec)

        r = make_response(employee_id=emp.id, week_start=sample_week)
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        cr = ClientResponse(
            response_id=r.id,
            client_id=client.id,
            score_workload=5,
            has_blockers=True,
            blocker_text="Big blocker",
        )
        db_session.add(cr)
        await db_session.commit()

        resp = await api_client.get(
            f"/api/client-blockers/{sample_week.isoformat()}",
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["blocker_text"] == "Big blocker"

    @pytest.mark.asyncio
    async def test_client_blockers_filter_by_client(self, api_client, db_session, sample_week):
        emp = make_employee(telegram_id=4002, full_name="Filter Emp")
        c1 = make_client(name="Filter Client A")
        c2 = make_client(name="Filter Client B")
        db_session.add_all([emp, c1, c2])
        await db_session.commit()
        await db_session.refresh(emp)
        await db_session.refresh(c1)
        await db_session.refresh(c2)

        ec1 = EmployeeClient(employee_id=emp.id, client_id=c1.id)
        ec2 = EmployeeClient(employee_id=emp.id, client_id=c2.id)
        db_session.add_all([ec1, ec2])

        r = make_response(employee_id=emp.id, week_start=sample_week)
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        cr1 = ClientResponse(
            response_id=r.id, client_id=c1.id, score_workload=4,
            has_blockers=True, blocker_text="A blocker",
        )
        cr2 = ClientResponse(
            response_id=r.id, client_id=c2.id, score_workload=2,
            has_blockers=False, blocker_text="",
        )
        db_session.add_all([cr1, cr2])
        await db_session.commit()

        resp = await api_client.get(
            f"/api/client-blockers/{sample_week.isoformat()}?client_id={c1.id}",
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["client_name"] == "Filter Client A"
