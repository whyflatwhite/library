from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://library_user:library_pass@localhost:5432/library"
    app_env: str = "local"
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
