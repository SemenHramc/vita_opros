import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select, update

from bot.models import Employee, Client, EmployeeClient, Response, ClientResponse
from bot.utils import get_week_start
from tests.conftest import make_employee, make_client, make_response


@pytest.fixture
def sample_week():
    return date(2026, 5, 11)


class TestSurveyWeekStart:
    def test_get_week_start_monday(self):
        assert get_week_start(date(2026, 5, 11)) == date(2026, 5, 11)

    def test_get_week_start_friday(self):
        assert get_week_start(date(2026, 5, 15)) == date(2026, 5, 11)

    def test_get_week_start_sunday(self):
        assert get_week_start(date(2026, 5, 17)) == date(2026, 5, 11)


class TestSurveyCompletedCheck:
    @pytest.mark.asyncio
    async def test_completed_survey_prevents_new(self, db_session, sample_week):
        emp = make_employee()
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        r = make_response(employee_id=emp.id, week_start=sample_week, completed_at=datetime.now(timezone.utc))
        db_session.add(r)
        await db_session.commit()

        result = await db_session.execute(
            select(Response).where(
                Response.employee_id == emp.id,
                Response.week_start == sample_week,
                Response.completed_at.isnot(None),
            )
        )
        completed = result.scalar_one_or_none()
        assert completed is not None
        assert completed.completed_at is not None


class TestSurveyIncompleteResponse:
    @pytest.mark.asyncio
    async def test_incomplete_survey_exists(self, db_session, sample_week):
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

        result = await db_session.execute(
            select(Response).where(
                Response.employee_id == emp.id,
                Response.week_start == sample_week,
                Response.completed_at.is_(None),
            )
        )
        incomplete = result.scalar_one_or_none()
        assert incomplete is not None
        assert incomplete.completed_at is None


class TestSurveyResumeState:
    @pytest.mark.asyncio
    async def test_response_stores_state_fields(self, db_session, sample_week):
        emp = make_employee()
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        r = make_response(
            employee_id=emp.id,
            week_start=sample_week,
            score_workload=4,
            score_deadlines=None,
            completed_at=None,
        )
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        assert r.score_workload == 4
        assert r.score_deadlines is None


class TestSurveyNoDuplicates:
    @pytest.mark.asyncio
    async def test_cannot_create_duplicate_response(self, db_session, sample_week):
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
    async def test_can_create_response_different_weeks(self, db_session, sample_week, prev_week):
        emp = make_employee()
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        r1 = make_response(employee_id=emp.id, week_start=sample_week)
        r2 = make_response(employee_id=emp.id, week_start=prev_week)
        db_session.add_all([r1, r2])
        await db_session.commit()
        assert r1.id != r2.id
