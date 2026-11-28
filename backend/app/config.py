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

    # AWS Lambda list prices (US East, USD). Graviton (arm64) is 20% cheaper per GB-second.
    PRICE_GBS_X86: float = 0.0000166667
    PRICE_GBS_ARM: float = 0.0000133334
    PRICE_PER_REQUEST: float = 0.0000002

    # Applying changes to AWS is OFF unless explicitly enabled, and is limited to
    # functions whose name starts with the allowed prefix (a second safety layer
    # on top of the IAM policy).
    APPLY_ENABLED: bool = False
    APPLY_ALLOWED_PREFIX: str = "ioc-demo-"

    # Secret used by the scheduled job (GitHub Actions) to call /api/system/run-cycle
    CRON_TOKEN: str = ""


settings = Settings()
