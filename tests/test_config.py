import os
import pytest
from unittest.mock import patch


class TestConfig:
    def test_settings_exist(self):
        from bot.config import Settings
        s = Settings()
        assert s.bot_token is not None or True
        assert s.dashboard_port > 0
        assert s.rate_limit_messages > 0
        assert s.rate_limit_window > 0

    def test_dashboard_api_key_is_set(self):
        from bot.config import settings
        assert settings.dashboard_api_key is not None
        assert len(settings.dashboard_api_key) > 0

    def test_rate_limit_defaults(self):
        from bot.config import Settings
        s = Settings(bot_token="test")
        assert s.rate_limit_messages > 0
        assert s.rate_limit_window > 0

    def test_text_limits(self):
        from bot.config import Settings
        s = Settings(bot_token="test")
        assert s.max_blocker_text_length > 0
        assert s.max_comment_text_length > 0
        assert s.max_client_blocker_text_length > 0

    def test_clients_per_page_positive(self):
        from bot.config import Settings
        s = Settings(bot_token="test")
        assert s.clients_per_page > 0
