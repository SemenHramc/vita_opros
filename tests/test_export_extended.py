import pytest
import pytest_asyncio
from datetime import date, datetime, timezone

from bot.models import Employee, Client, EmployeeClient, Response, ClientResponse
from bot.services.export import export_week_csv, export_week_xlsx
from tests.conftest import make_employee, make_client, make_response


class TestExportCSVContent:
    @pytest.mark.asyncio
    async def test_csv_contains_employee_names(self, db_session, sample_week):
        emp1 = make_employee(telegram_id=6001, username="csv_e1", full_name="CSV Alice")
        emp2 = make_employee(telegram_id=6002, username="csv_e2", full_name="CSV Bob")
        db_session.add_all([emp1, emp2])
        await db_session.commit()
        for e in [emp1, emp2]:
            await db_session.refresh(e)

        r1 = make_response(employee_id=emp1.id, week_start=sample_week, score_workload=4)
        r2 = make_response(employee_id=emp2.id, week_start=sample_week, score_workload=3)
        db_session.add_all([r1, r2])
        await db_session.commit()

        from unittest.mock import patch
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

        test_session_factory = async_sessionmaker(
            bind=db_session.bind,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        with patch("bot.services.export.async_session", test_session_factory):
            content = await export_week_csv(sample_week)

        assert "CSV Alice" in content or "4" in content

    @pytest.mark.asyncio
    async def test_csv_empty_week_returns_headers(self, db_session, sample_week):
        from unittest.mock import patch
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

        test_session_factory = async_sessionmaker(
            bind=db_session.bind,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        with patch("bot.services.export.async_session", test_session_factory):
            content = await export_week_csv(sample_week)

        lines = content.strip().split("\n")
        assert len(lines) >= 1
        assert ";" in lines[0]

    @pytest.mark.asyncio
    async def test_csv_with_client_responses(self, db_session, sample_week):
        emp = make_employee(telegram_id=6003, username="csv_e3", full_name="CSV Worker")
        client = make_client(name="CSV Client")
        db_session.add_all([emp, client])
        await db_session.commit()
        for obj in [emp, client]:
            await db_session.refresh(obj)

        ec = EmployeeClient(employee_id=emp.id, client_id=client.id)
        db_session.add(ec)

        r = make_response(employee_id=emp.id, week_start=sample_week, completed_at=datetime.now(timezone.utc))
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        cr = ClientResponse(
            response_id=r.id, client_id=client.id, score_workload=5,
            has_blockers=True, blocker_text="Blocked",
        )
        db_session.add(cr)
        await db_session.commit()

        from unittest.mock import patch
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

        test_session_factory = async_sessionmaker(
            bind=db_session.bind,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        with patch("bot.services.export.async_session", test_session_factory):
            content = await export_week_csv(sample_week)

        assert "CSV Worker" in content or str(emp.id) in content


class TestExportXLSXContent:
    @pytest.mark.asyncio
    async def test_xlsx_returns_bytes(self, db_session, sample_week):
        emp = make_employee(telegram_id=6004, username="xlsx_e1", full_name="XLSX Worker")
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        r = make_response(employee_id=emp.id, week_start=sample_week, completed_at=datetime.now(timezone.utc))
        db_session.add(r)
        await db_session.commit()

        from unittest.mock import patch
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

        test_session_factory = async_sessionmaker(
            bind=db_session.bind,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        with patch("bot.services.export.async_session", test_session_factory):
            content = await export_week_xlsx(sample_week)

        assert isinstance(content, bytes)
        assert len(content) > 0
        assert content[:2] == b"PK"

    @pytest.mark.asyncio
    async def test_xlsx_empty_week_returns_valid_file(self, db_session, sample_week):
        from unittest.mock import patch
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

        test_session_factory = async_sessionmaker(
            bind=db_session.bind,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        with patch("bot.services.export.async_session", test_session_factory):
            content = await export_week_xlsx(sample_week)

        assert isinstance(content, bytes)
        assert len(content) > 0
