from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str
    database_url: str = "sqlite+aiosqlite:///./vita_opros.db"
    redis_url: str = "redis://localhost:6379/0"
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8000
    postgres_password: str = "changeme"

    # Survey settings
    clients_per_page: int = 8
    reminder_hours: int = 12
    reminder_interval_hours: int = 4
    friday_reminder_hour: int = 13
    friday_reminder_minute: int = 0
    max_blocker_text_length: int = 1000
    max_comment_text_length: int = 1000
    max_client_blocker_text_length: int = 1000

    # Rate limiting
    rate_limit_messages: int = 10
    rate_limit_window: int = 60  # seconds

    # Dashboard security
    dashboard_allowed_origins: str = "http://localhost:3000"
    dashboard_api_key: str = "change-me-in-production"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()