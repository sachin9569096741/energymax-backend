from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str


        # Email / Resend
    resend_api_key: str
    resend_from_email: str
    resend_from_name: str = "EnergyMax"
    
    ##admin authentication
    jwt_secret_key: str
    admin_user_id: str
    admin_password: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    ##razorpay
    razorpay_key_id: str
    razorpay_key_secret: str
    razorpay_webhook_secret: str


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