from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "MeetingOS API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    app_debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://meetingos:meetingos_secret_password@localhost:5432/meetingos_db"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Storage & Uploads
    upload_storage_dir: str = Field(default="./data/uploads")
    max_upload_size_mb: int = Field(default=500)

    # Speech / ML Providers
    asr_provider: str = "mock"
    diarizer_provider: str = "mock"
    ner_provider: str = "mock"
    classifier_provider: str = "mock"
    embedding_provider: str = Field(default="mock", alias="MEETINGOS_EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="local-semantic-v1", alias="MEETINGOS_EMBEDDING_MODEL")
    reasoner_provider: str = Field(default="mock", alias="MEETINGOS_REASONER_PROVIDER")
    reasoner_model: str = Field(default="local-reasoner-v1", alias="MEETINGOS_REASONER_MODEL")

    # Connector Configuration
    teams_enabled: bool = False
    teams_tenant_id: str | None = None
    teams_client_id: str | None = None
    teams_client_secret: str | None = None

    zoom_enabled: bool = False
    zoom_account_id: str | None = None
    zoom_client_id: str | None = None
    zoom_client_secret: str | None = None

    google_meet_enabled: bool = False
    google_client_id: str | None = None
    google_client_secret: str | None = None


settings = Settings()
