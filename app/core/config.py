from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    # Cloudinary
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

    # Email / Resend
    resend_api_key: str
    resend_from_email: str
    resend_from_name: str = "EnergyMaxGroup"
    frontend_base_url: str = "https://energymaxgroup.in"

    # Admin authentication
    jwt_secret_key: str
    admin_user_id: str
    admin_password: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CLOUDFLARE Turnstile
    cloudflare_turnstile_secret_key: str
    cloudflare_turnstile_expected_hostname: str = "energymaxgroup.in"

    # Cashfree Payments
    cashfree_app_id: str
    cashfree_secret_key: str
    cashfree_environment: str = "sandbox"
    cashfree_api_version: str = "2025-01-01"
    cashfree_webhook_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()