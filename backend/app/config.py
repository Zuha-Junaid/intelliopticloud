from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "intelliopticloud-fyp-secret-2026"
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_MINUTES: int = 60
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    PKR_USD_RATE: float = 278.0

    class Config:
        env_file = ".env"

settings = Settings()