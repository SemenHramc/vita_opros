import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, update

from bot.models import Employee, Client, EmployeeClient, Response, ClientResponse
from bot.utils import get_week_start
from tests.conftest import make_employee, make_client, make_response, make_client_response


@pytest.fixture
def sample_week():
    return date(2026, 5, 11)


class TestUpdateCreatePartialResponse:
    @pytest.mark.asyncio
    async def test_midweek_update_creates_response_if_none(self, db_session, sample_week):
        emp = make_employee()
        client = make_client()
        db_session.add_all([emp, client])
        await db_session.commit()
        await db_session.refresh(emp)
        await db_session.refresh(client)

        ec = EmployeeClient(employee_id=emp.id, client_id=client.id)
        db_session.add(ec)
        await db_session.commit()

        result = await db_session.execute(
            select(Response).where(
                Response.employee_id == emp.id,
                Response.week_start == sample_week,
            )
        )
        assert result.scalar_one_or_none() is None

        r = Response(
            employee_id=emp.id,
            week_start=sample_week,
        )
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        assert r.id is not None
        assert r.score_workload is None
        assert r.completed_at is None

    @pytest.mark.asyncio
    async def test_midweek_update_adds_client_response(self, db_session, sample_week):
        emp = make_employee()
        client = make_client()
        db_session.add_all([emp, client])
        await db_session.commit()
        await db_session.refresh(emp)
        await db_session.refresh(client)

        r = make_response(
            employee_id=emp.id,
            week_start=sample_week,
            score_workload=3,
            score_deadlines=4,
            completed_at=datetime.now(timezone.utc),
        )
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        cr = ClientResponse(
            response_id=r.id,
            client_id=client.id,
            score_workload=5,
            has_blockers=True,
            blocker_text="Urgent deadline",
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(cr)
        await db_session.commit()
        await db_session.refresh(cr)

        assert cr.id is not None
        assert cr.score_workload == 5
        assert cr.has_blockers is True
        assert cr.updated_at is not None


class TestUpdateExistingClientResponse:
    @pytest.mark.asyncio
    async def test_midweek_update_overwrites_score(self, db_session, sample_week):
        emp = make_employee()
        client = make_client()
        db_session.add_all([emp, client])
        await db_session.commit()
        await db_session.refresh(emp)
        await db_session.refresh(client)

        r = make_response(employee_id=emp.id, week_start=sample_week, completed_at=datetime.now(timezone.utc))
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        cr = ClientResponse(
            response_id=r.id,
            client_id=client.id,
            score_workload=3,
            has_blockers=False,
            blocker_text="",
        )
        db_session.add(cr)
        await db_session.commit()
        await db_session.refresh(cr)

        await db_session.execute(
            update(ClientResponse)
            .where(ClientResponse.id == cr.id)
            .values(score_workload=5, updated_at=datetime.now(timezone.utc))
        )
        await db_session.commit()

        await db_session.refresh(cr)
        assert cr.score_workload == 5
        assert cr.updated_at is not None

    @pytest.mark.asyncio
    async def test_full_survey_overwrites_midweek(self, db_session, sample_week):
        emp = make_employee()
        client1 = make_client(name="Client X")
        client2 = make_client(name="Client Y")
        db_session.add_all([emp, client1, client2])
        await db_session.commit()
        await db_session.refresh(emp)
        await db_session.refresh(client1)
        await db_session.refresh(client2)

        r = make_response(employee_id=emp.id, week_start=sample_week, completed_at=datetime.now(timezone.utc))
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        cr1 = ClientResponse(
            response_id=r.id, client_id=client1.id, score_workload=3,
            has_blockers=False, blocker_text="", updated_at=datetime.now(timezone.utc),
        )
        db_session.add(cr1)
        await db_session.commit()
        await db_session.refresh(cr1)

        from sqlalchemy import delete
        await db_session.execute(
            delete(ClientResponse).where(ClientResponse.response_id == r.id)
        )
        await db_session.commit()

        new_cr1 = ClientResponse(
            response_id=r.id, client_id=client1.id, score_workload=4,
            has_blockers=False, blocker_text="",
        )
        new_cr2 = ClientResponse(
            response_id=r.id, client_id=client2.id, score_workload=2,
            has_blockers=True, blocker_text="Delayed",
        )
        db_session.add_all([new_cr1, new_cr2])
        await db_session.commit()

        result = await db_session.execute(
            select(ClientResponse).where(ClientResponse.response_id == r.id)
        )
        all_crs = result.scalars().all()
        assert len(all_crs) == 2
        scores = {cr.client_id: cr.score_workload for cr in all_crs}
        assert scores[client1.id] == 4
        assert scores[client2.id] == 2


class TestUpdateRateLimit:
    @pytest.mark.asyncio
    async def test_one_update_per_client_per_day(self, db_session, sample_week):
        emp = make_employee()
        client = make_client()
        db_session.add_all([emp, client])
        await db_session.commit()
        await db_session.refresh(emp)
        await db_session.refresh(client)

        r = make_response(employee_id=emp.id, week_start=sample_week, completed_at=datetime.now(timezone.utc))
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        now = datetime.now(timezone.utc)
        cr = ClientResponse(
            response_id=r.id, client_id=client.id, score_workload=3,
            updated_at=now,
        )
        db_session.add(cr)
        await db_session.commit()
        await db_session.refresh(cr)

        await db_session.execute(
            update(ClientResponse)
            .where(ClientResponse.id == cr.id)
            .values(score_workload=5, updated_at=datetime.now(timezone.utc))
        )
        await db_session.commit()
        await db_session.refresh(cr)
        assert cr.score_workload == 5
