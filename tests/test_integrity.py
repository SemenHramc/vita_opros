import pytest
import pytest_asyncio
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from bot.models import Employee, Client, EmployeeClient, Response, ClientResponse
from tests.conftest import make_employee, make_client, make_response


class TestResponseUniqueConstraint:
    @pytest.mark.asyncio
    async def test_duplicate_response_raises_integrity_error(self, db_session, sample_week):
        emp = make_employee(telegram_id=5001, full_name="Dup Emp")
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        r1 = Response(employee_id=emp.id, week_start=sample_week, completed_at=datetime.now(timezone.utc))
        db_session.add(r1)
        await db_session.commit()

        r2 = Response(employee_id=emp.id, week_start=sample_week)
        db_session.add(r2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_same_employee_different_weeks_ok(self, db_session, sample_week, prev_week):
        emp = make_employee(telegram_id=5002, full_name="Weeks Emp")
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        r1 = Response(employee_id=emp.id, week_start=sample_week)
        r2 = Response(employee_id=emp.id, week_start=prev_week)
        db_session.add_all([r1, r2])
        await db_session.commit()
        assert r1.id != r2.id

    @pytest.mark.asyncio
    async def test_different_employees_same_week_ok(self, db_session, sample_week):
        e1 = make_employee(telegram_id=5003, full_name="Emp A")
        e2 = make_employee(telegram_id=5004, full_name="Emp B")
        db_session.add_all([e1, e2])
        await db_session.commit()
        await db_session.refresh(e1)
        await db_session.refresh(e2)

        r1 = Response(employee_id=e1.id, week_start=sample_week)
        r2 = Response(employee_id=e2.id, week_start=sample_week)
        db_session.add_all([r1, r2])
        await db_session.commit()
        assert r1.id != r2.id


class TestClientResponseUniqueConstraint:
    @pytest.mark.asyncio
    async def test_duplicate_client_response_raises_error(self, db_session, sample_week):
        emp = make_employee(telegram_id=5101, full_name="CR Dup Emp")
        client = make_client(name="CR Dup Client")
        db_session.add_all([emp, client])
        await db_session.commit()
        await db_session.refresh(emp)
        await db_session.refresh(client)

        r = make_response(employee_id=emp.id, week_start=sample_week)
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        cr1 = ClientResponse(response_id=r.id, client_id=client.id, score_workload=3)
        db_session.add(cr1)
        await db_session.commit()

        cr2 = ClientResponse(response_id=r.id, client_id=client.id, score_workload=5)
        db_session.add(cr2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_same_response_different_clients_ok(self, db_session, sample_week):
        emp = make_employee(telegram_id=5102, full_name="CR Diff Emp")
        c1 = make_client(name="CR Client A")
        c2 = make_client(name="CR Client B")
        db_session.add_all([emp, c1, c2])
        await db_session.commit()
        for obj in [emp, c1, c2]:
            await db_session.refresh(obj)

        r = make_response(employee_id=emp.id, week_start=sample_week)
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        cr1 = ClientResponse(response_id=r.id, client_id=c1.id, score_workload=3)
        cr2 = ClientResponse(response_id=r.id, client_id=c2.id, score_workload=4)
        db_session.add_all([cr1, cr2])
        await db_session.commit()
        assert cr1.id != cr2.id

    @pytest.mark.asyncio
    async def test_same_client_different_responses_ok(self, db_session, sample_week, prev_week):
        emp = make_employee(telegram_id=5103, full_name="CR Diff Week")
        client = make_client(name="CR Client C")
        db_session.add_all([emp, client])
        await db_session.commit()
        for obj in [emp, client]:
            await db_session.refresh(obj)

        r1 = make_response(employee_id=emp.id, week_start=sample_week)
        r2 = make_response(employee_id=emp.id, week_start=prev_week)
        db_session.add_all([r1, r2])
        await db_session.commit()
        await db_session.refresh(r1)
        await db_session.refresh(r2)

        cr1 = ClientResponse(response_id=r1.id, client_id=client.id, score_workload=3)
        cr2 = ClientResponse(response_id=r2.id, client_id=client.id, score_workload=4)
        db_session.add_all([cr1, cr2])
        await db_session.commit()
        assert cr1.id != cr2.id


class TestIntegrityErrorRecovery:
    @pytest.mark.asyncio
    async def test_rollback_and_refetch_response(self, db_session, sample_week):
        emp = make_employee(telegram_id=5201, full_name="Rollback Emp")
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        r = Response(employee_id=emp.id, week_start=sample_week)
        db_session.add(r)
        await db_session.commit()

        async with db_session.begin_nested():
            r_dup = Response(employee_id=emp.id, week_start=sample_week)
            db_session.add(r_dup)
            with pytest.raises(IntegrityError):
                await db_session.flush()

        result = await db_session.execute(
            select(Response).where(Response.employee_id == emp.id, Response.week_start == sample_week)
        )
        existing = result.scalar_one_or_none()
        assert existing is not None
        assert existing.id == r.id

    @pytest.mark.asyncio
    async def test_rollback_and_refetch_client_response(self, db_session, sample_week):
        emp = make_employee(telegram_id=5202, full_name="CR Rollback Emp")
        client = make_client(name="CR Rollback Client")
        db_session.add_all([emp, client])
        await db_session.commit()
        for obj in [emp, client]:
            await db_session.refresh(obj)

        r = make_response(employee_id=emp.id, week_start=sample_week)
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        cr = ClientResponse(response_id=r.id, client_id=client.id, score_workload=3)
        db_session.add(cr)
        await db_session.commit()

        async with db_session.begin_nested():
            cr_dup = ClientResponse(response_id=r.id, client_id=client.id, score_workload=5)
            db_session.add(cr_dup)
            with pytest.raises(IntegrityError):
                await db_session.flush()

        result = await db_session.execute(
            select(ClientResponse).where(
                ClientResponse.response_id == r.id,
                ClientResponse.client_id == client.id,
            )
        )
        existing = result.scalar_one_or_none()
        assert existing is not None
        assert existing.score_workload == 3

    @pytest.mark.asyncio
    async def test_upsert_pattern_response(self, db_session, sample_week):
        emp = make_employee(telegram_id=5203, full_name="Upsert Emp")
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        r = Response(employee_id=emp.id, week_start=sample_week, score_workload=3)
        db_session.add(r)
        await db_session.commit()

        async with db_session.begin_nested():
            r2 = Response(employee_id=emp.id, week_start=sample_week, score_workload=5)
            db_session.add(r2)
            with pytest.raises(IntegrityError):
                await db_session.flush()

        result = await db_session.execute(
            select(Response).where(Response.employee_id == emp.id, Response.week_start == sample_week)
        )
        existing = result.scalar_one()
        existing.score_workload = 5
        await db_session.commit()

        result = await db_session.execute(
            select(Response).where(Response.employee_id == emp.id, Response.week_start == sample_week)
        )
        final = result.scalar_one()
        assert final.score_workload == 5

    @pytest.mark.asyncio
    async def test_upsert_pattern_client_response(self, db_session, sample_week):
        emp = make_employee(telegram_id=5204, full_name="Upsert CR Emp")
        client = make_client(name="Upsert CR Client")
        db_session.add_all([emp, client])
        await db_session.commit()
        for obj in [emp, client]:
            await db_session.refresh(obj)

        r = make_response(employee_id=emp.id, week_start=sample_week)
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        cr = ClientResponse(response_id=r.id, client_id=client.id, score_workload=3)
        db_session.add(cr)
        await db_session.commit()

        async with db_session.begin_nested():
            cr_dup = ClientResponse(response_id=r.id, client_id=client.id, score_workload=5)
            db_session.add(cr_dup)
            with pytest.raises(IntegrityError):
                await db_session.flush()

        result = await db_session.execute(
            select(ClientResponse).where(
                ClientResponse.response_id == r.id,
                ClientResponse.client_id == client.id,
            )
        )
        existing = result.scalar_one()
        existing.score_workload = 5
        await db_session.commit()

        result = await db_session.execute(
            select(ClientResponse).where(
                ClientResponse.response_id == r.id,
                ClientResponse.client_id == client.id,
            )
        )
        final = result.scalar_one()
        assert final.score_workload == 5


class TestEmployeeUniqueConstraints:
    @pytest.mark.asyncio
    async def test_duplicate_telegram_id_raises_error(self, db_session):
        e1 = make_employee(telegram_id=5301, username="unique_tg", full_name="First")
        db_session.add(e1)
        await db_session.commit()

        e2 = make_employee(telegram_id=5301, username="different", full_name="Second")
        db_session.add(e2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_duplicate_client_name_raises_error(self, db_session):
        c1 = make_client(name="UniqueClient")
        db_session.add(c1)
        await db_session.commit()

        c2 = make_client(name="UniqueClient")
        db_session.add(c2)
        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestEmployeeClientConstraints:
    @pytest.mark.asyncio
    async def test_duplicate_employee_client_raises_error(self, db_session):
        emp = make_employee(telegram_id=5401, full_name="EC Emp")
        client = make_client(name="EC Client")
        db_session.add_all([emp, client])
        await db_session.commit()
        await db_session.refresh(emp)
        await db_session.refresh(client)

        ec1 = EmployeeClient(employee_id=emp.id, client_id=client.id)
        db_session.add(ec1)
        await db_session.commit()

        ec2 = EmployeeClient(employee_id=emp.id, client_id=client.id)
        db_session.add(ec2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_employee_can_have_multiple_clients(self, db_session):
        emp = make_employee(telegram_id=5402, full_name="Multi EC Emp")
        c1 = make_client(name="EC Client A")
        c2 = make_client(name="EC Client B")
        db_session.add_all([emp, c1, c2])
        await db_session.commit()
        for obj in [emp, c1, c2]:
            await db_session.refresh(obj)

        ec1 = EmployeeClient(employee_id=emp.id, client_id=c1.id)
        ec2 = EmployeeClient(employee_id=emp.id, client_id=c2.id)
        db_session.add_all([ec1, ec2])
        await db_session.commit()
        assert ec1 is not None
        assert ec2 is not None
