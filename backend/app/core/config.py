from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CommerceHub API"
    app_env: str = "development"
    database_url: str = (
        "mysql+pymysql://commercehub:commercehub_dev_password@localhost:3306/commercehub"
        "?charset=utf8mb4"
    )
    test_database_url: str = (
        "mysql+pymysql://commercehub:commercehub_dev_password@localhost:3306/commercehub_test"
        "?charset=utf8mb4"
    )
    jwt_secret: str = Field(
        default="local-development-secret-change-before-deployment",
        min_length=32,
    )
    jwt_access_token_minutes: int = 30
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "commercehub"
    jwt_audience: str = "commercehub-web"
    auth_cookie_name: str = "commercehub_access"
    backend_cors_origins: list[AnyHttpUrl] = Field(
        default_factory=lambda: [AnyHttpUrl("http://localhost:3000")]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
