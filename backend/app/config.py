from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SECRET_KEY: str = "intelliopticloud-fyp-secret-2026"
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_MINUTES: int = 60
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    PKR_USD_RATE: float = 278.0
    DATABASE_URL: str = ""  # empty = local SQLite file; set it to use Postgres


settings = Settings()