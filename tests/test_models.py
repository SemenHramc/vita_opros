import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta, timezone

from bot.models import Employee, Client, EmployeeClient, Response, ClientResponse
from tests.conftest import make_employee, make_client, make_response, make_client_response


class TestEmployeeModel:
    @pytest.mark.asyncio
    async def test_create_employee(self, db_session):
        emp = make_employee()
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)
        assert emp.id is not None
        assert emp.telegram_id == 12345
        assert emp.role == "employee"

    @pytest.mark.asyncio
    async def test_employee_unique_telegram_id(self, db_session):
        emp1 = make_employee(telegram_id=999)
        emp2 = make_employee(telegram_id=999, full_name="Another User")
        db_session.add(emp1)
        await db_session.commit()
        db_session.add(emp2)
        with pytest.raises(Exception):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_employee_default_role(self, db_session):
        emp = Employee(telegram_id=555, full_name="Test")
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)
        assert emp.role == "employee"

    @pytest.mark.asyncio
    async def test_admin_role(self, db_session):
        emp = make_employee(role="admin")
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)
        assert emp.role == "admin"


class TestClientModel:
    @pytest.mark.asyncio
    async def test_create_client(self, db_session):
        client = make_client()
        db_session.add(client)
        await db_session.commit()
        await db_session.refresh(client)
        assert client.id is not None
        assert client.name == "Test Client"

    @pytest.mark.asyncio
    async def test_client_unique_name(self, db_session):
        c1 = make_client(name="Unique Corp")
        c2 = make_client(name="Unique Corp")
        db_session.add(c1)
        await db_session.commit()
        db_session.add(c2)
        with pytest.raises(Exception):
            await db_session.commit()


class TestEmployeeClient:
    @pytest.mark.asyncio
    async def test_assign_client_to_employee(self, db_session):
        emp = make_employee()
        client = make_client()
        db_session.add_all([emp, client])
        await db_session.commit()
        await db_session.refresh(emp)
        await db_session.refresh(client)

        ec = EmployeeClient(employee_id=emp.id, client_id=client.id)
        db_session.add(ec)
        await db_session.commit()

        result = await db_session.get(EmployeeClient, (emp.id, client.id))
        assert result is not None


class TestResponseModel:
    @pytest.mark.asyncio
    async def test_create_response(self, db_session, sample_week):
        emp = make_employee()
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        r = make_response(employee_id=emp.id, week_start=sample_week)
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)
        assert r.id is not None
        assert r.week_start == sample_week

    @pytest.mark.asyncio
    async def test_response_unique_employee_week(self, db_session, sample_week):
        emp = make_employee()
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        r1 = make_response(employee_id=emp.id, week_start=sample_week)
        r2 = make_response(employee_id=emp.id, week_start=sample_week)
        db_session.add(r1)
        await db_session.commit()
        db_session.add(r2)
        with pytest.raises(Exception):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_response_different_weeks_same_employee(self, db_session, sample_week, prev_week):
        emp = make_employee()
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        r1 = make_response(employee_id=emp.id, week_start=sample_week)
        r2 = make_response(employee_id=emp.id, week_start=prev_week)
        db_session.add_all([r1, r2])
        await db_session.commit()
        assert r1.id != r2.id

    @pytest.mark.asyncio
    async def test_response_incomplete(self, db_session, sample_week):
        emp = make_employee()
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        r = make_response(
            employee_id=emp.id,
            week_start=sample_week,
            score_workload=None,
            completed_at=None,
        )
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)
        assert r.completed_at is None
        assert r.score_workload is None

    @pytest.mark.asyncio
    async def test_response_score_constraints(self, db_session, sample_week):
        emp = make_employee()
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        r = make_response(employee_id=emp.id, week_start=sample_week, score_workload=1)
        db_session.add(r)
        await db_session.commit()

        r2 = make_response(
            employee_id=emp.id,
            week_start=sample_week + timedelta(weeks=1),
            score_workload=6,
        )
        db_session.add(r2)
        with pytest.raises(Exception):
            await db_session.commit()


class TestClientResponseModel:
    @pytest.mark.asyncio
    async def test_create_client_response(self, db_session, sample_week):
        emp = make_employee()
        client = make_client()
        db_session.add_all([emp, client])
        await db_session.commit()
        await db_session.refresh(emp)
        await db_session.refresh(client)

        r = make_response(employee_id=emp.id, week_start=sample_week)
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        cr = make_client_response(response_id=r.id, client_id=client.id)
        db_session.add(cr)
        await db_session.commit()
        await db_session.refresh(cr)
        assert cr.id is not None
        assert cr.score_workload == 4
        assert cr.updated_at is None

    @pytest.mark.asyncio
    async def test_client_response_with_updated_at(self, db_session, sample_week):
        emp = make_employee()
        client = make_client()
        db_session.add_all([emp, client])
        await db_session.commit()
        await db_session.refresh(emp)
        await db_session.refresh(client)

        r = make_response(employee_id=emp.id, week_start=sample_week)
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        now = datetime.now(timezone.utc)
        cr = make_client_response(
            response_id=r.id,
            client_id=client.id,
            updated_at=now,
        )
        db_session.add(cr)
        await db_session.commit()
        await db_session.refresh(cr)
        assert cr.updated_at is not None

    @pytest.mark.asyncio
    async def test_client_response_unique_response_client(self, db_session, sample_week):
        emp = make_employee()
        client = make_client()
        db_session.add_all([emp, client])
        await db_session.commit()
        await db_session.refresh(emp)
        await db_session.refresh(client)

        r = make_response(employee_id=emp.id, week_start=sample_week)
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        cr1 = make_client_response(response_id=r.id, client_id=client.id)
        db_session.add(cr1)
        await db_session.commit()

        cr2 = make_client_response(response_id=r.id, client_id=client.id)
        db_session.add(cr2)
        with pytest.raises(Exception):
            await db_session.commit()
