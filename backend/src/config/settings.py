"""Runtime configuration (env override allowed for every field)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    DB_NAME: str = "churnmod_db"
    DB_USER: str = "churnmod_user"
    DB_PASSWORD: str = "churnmod_pwd"
    DB_HOST: str = "db"
    DB_PORT: int = 5432

    JWT_SECRET: str = "churnmod_dev_jwt_secret_change_me_0612"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 8

    REDIS_URL: str = "redis://redis:6379/0"

    # --- scoring policy defaults (seeded / overridable from the UI) ---
    DEFAULT_THRESHOLD: float = 0.35
    DEFAULT_BUDGET: float = 12500.0
    COST_PER_ACCOUNT: float = 500.0
    EXPECTED_RETENTION_LIFT: float = 0.35

    # --- limits ---
    RATE_WINDOW_SECONDS: int = 60
    RATE_WINDOW_MAX: int = 120

    SEED_DEMO: bool = True

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
