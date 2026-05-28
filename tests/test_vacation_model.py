import pytest
import pytest_asyncio
from datetime import date

from bot.models import Employee, VacationPeriod
from tests.conftest import make_employee


class TestVacationPeriodModel:
    @pytest.mark.asyncio
    async def test_create_vacation_period(self, db_session):
        emp = make_employee()
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        vp = VacationPeriod(
            employee_id=emp.id,
            year=2026,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 14),
            days_count=14,
            period_number=1,
        )
        db_session.add(vp)
        await db_session.commit()
        await db_session.refresh(vp)

        assert vp.id is not None
        assert vp.year == 2026
        assert vp.days_count == 14

    @pytest.mark.asyncio
    async def test_vacation_period_employee_relationship(self, db_session):
        emp = make_employee()
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        vp1 = VacationPeriod(
            employee_id=emp.id,
            year=2026,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 14),
            days_count=14,
            period_number=1,
        )
        vp2 = VacationPeriod(
            employee_id=emp.id,
            year=2026,
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 14),
            days_count=14,
            period_number=2,
        )
        db_session.add_all([vp1, vp2])
        await db_session.commit()

        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await db_session.execute(
            select(Employee)
            .where(Employee.id == emp.id)
            .options(selectinload(Employee.vacation_periods))
        )
        loaded_emp = result.scalar_one()
        assert len(loaded_emp.vacation_periods) == 2

    @pytest.mark.asyncio
    async def test_vacation_remaining_days(self, db_session):
        emp = make_employee()
        emp.total_vacation_days = 28
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        vp = VacationPeriod(
            employee_id=emp.id,
            year=2026,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 14),
            days_count=14,
            period_number=1,
        )
        db_session.add(vp)
        await db_session.commit()

        assert emp.total_vacation_days == 28
        remaining = emp.total_vacation_days - vp.days_count
        assert remaining == 14

    @pytest.mark.asyncio
    async def test_vacation_cascade_delete(self, db_session):
        emp = make_employee()
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        vp = VacationPeriod(
            employee_id=emp.id,
            year=2026,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 14),
            days_count=14,
            period_number=1,
        )
        db_session.add(vp)
        await db_session.commit()

        await db_session.delete(emp)
        await db_session.commit()

        from sqlalchemy import select
        result = await db_session.execute(
            select(VacationPeriod).where(VacationPeriod.employee_id == emp.id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_vacation_multiple_years(self, db_session):
        emp = make_employee()
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        vp_2025 = VacationPeriod(
            employee_id=emp.id,
            year=2025,
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 28),
            days_count=28,
            period_number=1,
        )
        vp_2026 = VacationPeriod(
            employee_id=emp.id,
            year=2026,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 14),
            days_count=14,
            period_number=1,
        )
        db_session.add_all([vp_2025, vp_2026])
        await db_session.commit()

        from sqlalchemy import select

        result_2025 = await db_session.execute(
            select(VacationPeriod).where(VacationPeriod.year == 2025)
        )
        assert len(result_2025.scalars().all()) == 1

        result_2026 = await db_session.execute(
            select(VacationPeriod).where(VacationPeriod.year == 2026)
        )
        assert len(result_2026.scalars().all()) == 1
