import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock

from bot.models import Employee, Client, EmployeeClient, Response, ClientResponse
from bot.services.export import export_week_csv, export_week_xlsx
from tests.conftest import make_employee, make_client, make_response, make_client_response


@pytest.fixture
def sample_week():
    return date(2026, 5, 11)


class TestExportCSV:
    @pytest.mark.asyncio
    async def test_export_csv_headers(self, db_session, sample_week):
        emp = make_employee(telegram_id=8001, full_name="Export Test")
        client = make_client(name="Export Client")
        db_session.add_all([emp, client])
        await db_session.commit()
        await db_session.refresh(emp)
        await db_session.refresh(client)

        ec = EmployeeClient(employee_id=emp.id, client_id=client.id)
        db_session.add(ec)

        r = make_response(
            employee_id=emp.id,
            week_start=sample_week,
            completed_at=datetime(2026, 5, 13, 10, 30),
        )
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        cr = make_client_response(response_id=r.id, client_id=client.id)
        db_session.add(cr)
        await db_session.commit()

        from unittest.mock import patch
        with patch("bot.services.export.async_session") as mock_sf:
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await export_week_csv(sample_week)

        assert "Сотрудник" in result
        assert "Нагрузка" in result
        assert "Клиент" in result

    @pytest.mark.asyncio
    async def test_export_csv_empty_week(self, db_session):
        from unittest.mock import patch, AsyncMock
        week = date(2025, 1, 6)
        with patch("bot.services.export.async_session") as mock_sf:
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await export_week_csv(week)

        assert "Сотрудник" in result


class TestExportXLSX:
    @pytest.mark.asyncio
    async def test_export_xlsx_returns_bytes(self, db_session, sample_week):
        from unittest.mock import patch, AsyncMock

        emp = make_employee(telegram_id=8002, full_name="XLSX Test")
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        r = make_response(employee_id=emp.id, week_start=sample_week, completed_at=datetime.now(timezone.utc))
        db_session.add(r)
        await db_session.commit()

        with patch("bot.services.export.async_session") as mock_sf:
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await export_week_xlsx(sample_week)

        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result[:4] == b"PK\x03\x04"
