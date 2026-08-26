from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Project Command Center"
    environment: str = "development"
    database_url: str = "sqlite:///./dashboard.db"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 30
    encryption_key: str = ""
    frontend_url: str = "http://localhost:3000"
    sync_interval_minutes: int = 5
    odoo_url: str = ""
    odoo_database: str = ""
    odoo_username: str = ""
    odoo_password: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/integrations/google/callback"
    whatsapp_dashboard_url: str = "https://nehal-work-status.pm-gala.chatgpt.site/api/whatsapp"
    whatsapp_dashboard_token: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
