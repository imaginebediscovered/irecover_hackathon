"""
iRecover Configuration Management
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache
from pathlib import Path

# Compute a repo-relative absolute path for the SQLite DB so
# running scripts from different working directories still resolves.
_BASE_DIR = Path(__file__).resolve().parents[1]  # backend/
_DEFAULT_DB_PATH = _BASE_DIR / "irecover.db"
_DEFAULT_DB_URI = f"sqlite+aiosqlite:///{_DEFAULT_DB_PATH.as_posix()}"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="iRecover", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    
    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")
    
    # Database (defaults to SQLite for local development without Docker)
    database_url: str = Field(
        default="sqlite+aiosqlite:////backend/irecover.db",
        alias="DATABASE_URL"
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    
    # OpenAI
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", alias="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.1, alias="OPENAI_TEMPERATURE")
    
    # Google Gemini API
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL")
    gemini_temperature: float = Field(default=0.3, alias="GEMINI_TEMPERATURE")
    
    # AWS Bedrock
    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")
    aws_session_token: Optional[str] = Field(default=None, alias="AWS_SESSION_TOKEN")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    bedrock_model_id: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0", alias="BEDROCK_MODEL_ID")
    bedrock_temperature: float = Field(default=0.3, alias="BEDROCK_TEMPERATURE")
    bedrock_max_tokens: int = Field(default=2048, alias="BEDROCK_MAX_TOKENS")
    
    # LLM Provider Selection (options: "openai", "gemini", "bedrock")
    llm_provider: str = Field(default="bedrock", alias="LLM_PROVIDER")
    
    # JWT Authentication
    jwt_secret_key: str = Field(
        default="change-this-secret-in-production",
        alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=60,
        alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    
    # Kafka (optional)
    kafka_bootstrap_servers: Optional[str] = Field(
        default=None,
        alias="KAFKA_BOOTSTRAP_SERVERS"
    )
    kafka_consumer_group: str = Field(
        default="irecover-consumers",
        alias="KAFKA_CONSUMER_GROUP"
    )
    
    # Notifications (optional)
    sendgrid_api_key: Optional[str] = Field(default=None, alias="SENDGRID_API_KEY")
    twilio_account_sid: Optional[str] = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: Optional[str] = Field(default=None, alias="TWILIO_FROM_NUMBER")
    
    # Observability
    otel_exporter_endpoint: Optional[str] = Field(
        default=None,
        alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_service_name: str = Field(
        default="irecover-backend",
        alias="OTEL_SERVICE_NAME"
    )
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def is_development(self) -> bool:
        return self.app_env == "development"
    
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
