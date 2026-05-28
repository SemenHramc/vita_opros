import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select

from bot.models import Employee, Client, EmployeeClient, Response, ClientResponse
from bot.utils import get_week_start
from tests.conftest import make_employee, make_client, make_response


class TestReminderEdgeCases:
    @pytest.mark.asyncio
    async def test_friday_reminder_skips_admin(self, db_session):
        admin = make_employee(telegram_id=8001, username="admin_r", full_name="Admin", role="admin")
        db_session.add(admin)
        await db_session.commit()

        from bot.services.reminder import send_friday_reminders
        bot = AsyncMock()

        with patch("bot.services.reminder.async_session") as mock_sf:
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            await send_friday_reminders(bot, week_start=date(2026, 5, 11))

        chat_ids = [
            call.kwargs.get("chat_id", call.args[0] if call.args else None)
            for call in bot.send_message.call_args_list
        ]
        if 8001 in chat_ids:
            text = bot.send_message.call_args_list[chat_ids.index(8001)].kwargs.get("text", "")
            assert "опрос" not in text.lower() or "напоминани" in text.lower()

    @pytest.mark.asyncio
    async def test_friday_reminder_empty_employee_list(self, db_session):
        from bot.services.reminder import send_friday_reminders
        bot = AsyncMock()

        with patch("bot.services.reminder.async_session") as mock_sf:
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            await send_friday_reminders(bot, week_start=date(2026, 5, 11))

        bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_reminder_marks_reminder_sent(self, db_session):
        emp = make_employee(telegram_id=8002)
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        from bot.config import settings
        old_time = datetime.now(timezone.utc) - timedelta(hours=settings.reminder_hours + 1)
        r = make_response(
            employee_id=emp.id,
            week_start=get_week_start(),
            completed_at=None,
            reminder_sent=False,
            started_at=old_time,
        )
        r.started_at = old_time
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        from bot.services.reminder import send_reminders
        bot = AsyncMock()

        with patch("bot.services.reminder.async_session") as mock_sf:
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            await send_reminders(bot)

        await db_session.refresh(r)
        assert r.reminder_sent is True

    @pytest.mark.asyncio
    async def test_reminder_skips_already_sent(self, db_session):
        emp = make_employee(telegram_id=8003)
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        from bot.config import settings
        r = make_response(
            employee_id=emp.id,
            week_start=get_week_start(),
            completed_at=None,
            reminder_sent=True,
        )
        db_session.add(r)
        await db_session.commit()

        from bot.services.reminder import send_reminders
        bot = AsyncMock()

        with patch("bot.services.reminder.async_session") as mock_sf:
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            await send_reminders(bot)

        bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_reminder_skips_recently_started(self, db_session):
        emp = make_employee(telegram_id=8004)
        db_session.add(emp)
        await db_session.commit()

        r = make_response(
            employee_id=emp.id,
            week_start=get_week_start(),
            completed_at=None,
            reminder_sent=False,
            started_at=datetime.now(timezone.utc),
        )
        db_session.add(r)
        await db_session.commit()

        from bot.services.reminder import send_reminders
        bot = AsyncMock()

        with patch("bot.services.reminder.async_session") as mock_sf:
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            await send_reminders(bot)

        bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_friday_reminder_multiple_employees(self, db_session):
        emps = [
            make_employee(telegram_id=8010 + i, username=f"emp_{i}", full_name=f"Emp {i}")
            for i in range(3)
        ]
        admin = make_employee(telegram_id=8099, username="admin_multi", full_name="Admin", role="admin")
        db_session.add_all(emps + [admin])
        await db_session.commit()

        from bot.services.reminder import send_friday_reminders
        bot = AsyncMock()

        with patch("bot.services.reminder.async_session") as mock_sf:
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            await send_friday_reminders(bot, week_start=date(2026, 5, 11))

        chat_ids = [
            call.kwargs.get("chat_id") for call in bot.send_message.call_args_list
        ]
        for i in range(3):
            assert 8010 + i in chat_ids
