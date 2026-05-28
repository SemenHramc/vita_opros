from datetime import date, timedelta

from bot.utils import get_week_start


class TestGetWeekStart:
    def test_monday_returns_same_day(self):
        monday = date(2026, 5, 11)
        assert get_week_start(monday).weekday() == 0
        assert get_week_start(monday) == monday

    def test_sunday_returns_previous_monday(self):
        sunday = date(2026, 5, 17)
        result = get_week_start(sunday)
        assert result == date(2026, 5, 11)

    def test_wednesday_returns_monday(self):
        wednesday = date(2026, 5, 13)
        result = get_week_start(wednesday)
        assert result == date(2026, 5, 11)

    def test_friday_returns_monday(self):
        friday = date(2026, 5, 15)
        result = get_week_start(friday)
        assert result == date(2026, 5, 11)

    def test_saturday_returns_monday(self):
        saturday = date(2026, 5, 16)
        result = get_week_start(saturday)
        assert result == date(2026, 5, 11)

    def test_default_is_today(self):
        result = get_week_start()
        expected = date.today() - timedelta(days=date.today().weekday())
        assert result == expected

    def test_week_start_across_month_boundary(self):
        thursday = date(2026, 5, 1)
        result = get_week_start(thursday)
        assert result == date(2026, 4, 27)

    def test_week_start_across_year_boundary(self):
        friday = date(2026, 1, 2)
        result = get_week_start(friday)
        assert result == date(2025, 12, 29)
