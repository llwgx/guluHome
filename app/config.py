from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    onenet_token: str = "change_me"
    onenet_skip_verify: bool = False
    database_url: str = "postgresql+asyncpg://onenet:onenet_secret@db:5432/onenet_db"
    app_port: int = 8000


settings = Settings()
