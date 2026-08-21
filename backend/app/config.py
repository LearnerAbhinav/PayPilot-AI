from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://paypilot:paypilot_secret@localhost:5432/paypilot_db"
    DATABASE_URL_SYNC: str = "postgresql://paypilot:paypilot_secret@localhost:5432/paypilot_db"
    JWT_SECRET: str = "change-me-to-a-random-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 1440

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_async_db_url(cls, v: str) -> str:
        if not v:
            return v
        url = str(v).strip()
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        # asyncpg requires ssl=require instead of sslmode=require
        url = url.replace("sslmode=require", "ssl=require")
        return url

    @field_validator("DATABASE_URL_SYNC", mode="before")
    @classmethod
    def assemble_sync_db_url(cls, v: str) -> str:
        if not v:
            return v
        url = str(v).strip()
        if url.startswith("postgresql+asyncpg://"):
            url = "postgresql://" + url[len("postgresql+asyncpg://"):]
        # Sync psycopg2 uses sslmode=require
        url = url.replace("ssl=require", "sslmode=require")
        return url

    @model_validator(mode="after")
    def sync_database_urls(self):
        # If DATABASE_URL_SYNC is default but DATABASE_URL was custom provided, derive it
        if self.DATABASE_URL and "localhost" not in self.DATABASE_URL and "localhost" in self.DATABASE_URL_SYNC:
            sync_url = self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
            sync_url = sync_url.replace("ssl=require", "sslmode=require")
            self.DATABASE_URL_SYNC = sync_url
        return self

    # AI Provider — supports "groq" or "openai"
    LLM_PROVIDER: str = "groq"
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_API_KEY: str = ""

    # Groq-specific (aliases for LLM_* when provider=groq)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    # OpenAI-specific (used when LLM_PROVIDER=openai)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Agent behavior
    AGENT_MAX_TOOL_ROUNDS: int = 8
    AGENT_MAX_TOKENS: int = 4096
    AGENT_TEMPERATURE: float = 0.2
    SIMULATION_MODE: bool = True  # Never execute real financial transactions

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def effective_llm_api_key(self) -> str:
        """Return the right API key based on the configured provider."""
        if self.LLM_PROVIDER == "groq":
            return self.GROQ_API_KEY or self.LLM_API_KEY
        elif self.LLM_PROVIDER == "openai":
            return self.OPENAI_API_KEY or self.LLM_API_KEY
        return self.LLM_API_KEY

    @property
    def effective_llm_model(self) -> str:
        """Return the right model based on the configured provider."""
        if self.LLM_PROVIDER == "groq":
            return self.GROQ_MODEL or self.LLM_MODEL
        elif self.LLM_PROVIDER == "openai":
            return self.OPENAI_MODEL or self.LLM_MODEL
        return self.LLM_MODEL

    class Config:
        env_file = ("../.env", ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
