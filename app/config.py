from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FONT_", extra="ignore")

    database_url: str = "postgresql+asyncpg://font:font@localhost:5432/font"
    max_upload_bytes: int = 20 * 1024 * 1024
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
