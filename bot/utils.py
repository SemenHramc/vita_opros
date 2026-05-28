from datetime import date, timedelta

from sqlalchemy import select

from bot.models import Employee


def get_week_start(d: date | None = None) -> date:
    if d is None:
        d = date.today()
    return d - timedelta(days=d.weekday())


async def get_employee(session, telegram_id: int) -> Employee | None:
    result = await session.execute(
        select(Employee).where(Employee.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()