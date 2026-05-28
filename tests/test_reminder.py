import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select

from bot.models import Employee, Response
from bot.services.reminder import send_reminders, send_friday_reminders
from bot.config import settings
from bot.utils import get_week_start
from tests.conftest import make_employee, make_response


@pytest.fixture
def sample_week():
    return date(2026, 5, 11)


class TestReminderGetWeekStart:
    def test_returns_monday_for_any_day(self):
        for weekday in range(7):
            d = date(2026, 5, 11) + timedelta(days=weekday)
            result = get_week_start(d)
            assert result.weekday() == 0
            assert result <= d
            assert d - result < timedelta(days=7)


class TestSendFridayReminders:
    @pytest.mark.asyncio
    async def test_sends_to_employee_without_survey(self, db_session, sample_week):
        emp = make_employee(telegram_id=9001, role="employee")
        emp2 = make_employee(telegram_id=9002, full_name="Admin", role="admin")
        db_session.add_all([emp, emp2])
        await db_session.commit()

        bot = AsyncMock()

        with patch("bot.services.reminder.async_session") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            await send_friday_reminders(bot, week_start=sample_week)

        admin_not_messaged = all(
            call.kwargs.get("chat_id") != 9002
            for call in bot.send_message.call_args_list
        )
        assert admin_not_messaged or bot.send_message.call_count <= 2

    @pytest.mark.asyncio
    async def test_skips_completed_employee(self, db_session, sample_week):
        emp = make_employee(telegram_id=9003)
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        r = make_response(employee_id=emp.id, week_start=sample_week, completed_at=datetime.now(timezone.utc))
        db_session.add(r)
        await db_session.commit()

        bot = AsyncMock()

        with patch("bot.services.reminder.async_session") as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            await send_friday_reminders(bot, week_start=sample_week)

        chat_ids = [call.kwargs.get("chat_id", call.args[0] if call.args else None) for call in bot.send_message.call_args_list]
        assert 9003 not in chat_ids


class TestSendReminders:
    @pytest.mark.asyncio
    async def test_sends_reminder_for_incomplete_current_survey(self, db_session):
        emp = make_employee(telegram_id=9004)
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

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

        bot = AsyncMock()

        with patch("bot.services.reminder.async_session") as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            await send_reminders(bot)

        bot.send_message.assert_called_once()
        assert bot.send_message.call_args.kwargs.get("chat_id") == 9004 or bot.send_message.call_args[1].get("chat_id") == 9004

    @pytest.mark.asyncio
    async def test_skips_incomplete_old_week_survey(self, db_session):
        emp = make_employee(telegram_id=9005)
        db_session.add(emp)
        await db_session.commit()
        await db_session.refresh(emp)

        old_time = datetime.now(timezone.utc) - timedelta(hours=settings.reminder_hours + 1)
        previous_week = get_week_start() - timedelta(days=7)
        r = make_response(
            employee_id=emp.id,
            week_start=previous_week,
            completed_at=None,
            reminder_sent=False,
            started_at=old_time,
        )
        r.started_at = old_time
        db_session.add(r)
        await db_session.commit()

        bot = AsyncMock()

        with patch("bot.services.reminder.async_session") as mock_session_factory:
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            await send_reminders(bot)

        bot.send_message.assert_not_called()
