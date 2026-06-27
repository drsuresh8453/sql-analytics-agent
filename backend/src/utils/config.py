# src/utils/config.py
# Author: Suresh D R | AI Product Developer & Technology Mentor
#
# Single source of truth for all configuration. Reads from environment
# variables only -- never hardcode credentials anywhere else in the codebase.

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenAI
    OPENAI_API_KEY: str

    # AWS
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "eu-north-1"

    # RDS PostgreSQL (read-only user)
    RDS_HOST: str
    RDS_PORT: str = "5432"
    RDS_DB: str = "supportagent"
    RDS_USER: str = "sql_agent_readonly"
    RDS_PASSWORD: str

    # ElastiCache for Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    CACHE_ENABLED: bool = True
    CACHE_TTL_QUERY_SECONDS: int = 600       # 10 minutes
    CACHE_TTL_SCHEMA_SECONDS: int = 3600     # 1 hour

    # LangSmith (observability)
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "sql-analytics-agent"

    # Rate limiting / circuit breaker
    RATE_LIMIT_PER_MINUTE: int = 30
    INVESTIGATIVE_CALL_LIMIT_PER_SESSION: int = 30
    INVESTIGATIVE_CALL_WINDOW_SECONDS: int = 300

    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.RDS_USER}:{self.RDS_PASSWORD}"
            f"@{self.RDS_HOST}:{self.RDS_PORT}/{self.RDS_DB}"
        )

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
