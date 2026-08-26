import logging
import sys
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("meetingos.config")

VALID_EMBEDDING_PROVIDERS = {
    "mock",
    "real",
    "local",
    "local_semantic",
    "sentence_transformers",
    "st",
    "openai",
    "openai_compatible",
    "gemini",
    "google",
}

VALID_REASONER_PROVIDERS = {
    "mock",
    "real",
    "local",
    "local_evidence",
    "openai",
    "openai_compatible",
    "llm",
    "anthropic",
    "claude",
    "gemini",
    "google",
}


class Settings(BaseSettings):
    """Application configuration loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Core Application
    app_name: str = "MeetingOS API"
    app_version: str = "0.1.0"
    app_env: Literal["development", "test", "staging", "production"] = "development"
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
    max_upload_size_mb: int = Field(default=500, gt=0)

    # Speech / ML Providers
    asr_provider: str = "mock"
    diarizer_provider: str = "mock"
    ner_provider: str = "mock"
    classifier_provider: str = "mock"

    # Generic Embedding & Reasoner Selection
    embedding_provider: str = Field(default="mock", alias="MEETINGOS_EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="local-semantic-v1", alias="MEETINGOS_EMBEDDING_MODEL")
    embedding_base_url: str | None = Field(default=None, alias="MEETINGOS_EMBEDDING_BASE_URL")
    embedding_api_key: str | None = Field(default=None, alias="MEETINGOS_EMBEDDING_API_KEY")

    reasoner_provider: str = Field(default="mock", alias="MEETINGOS_REASONER_PROVIDER")
    reasoner_model: str = Field(default="local-reasoner-v1", alias="MEETINGOS_REASONER_MODEL")
    reasoner_base_url: str | None = Field(default=None, alias="MEETINGOS_REASONER_BASE_URL")
    reasoner_api_key: str | None = Field(default=None, alias="MEETINGOS_REASONER_API_KEY")

    # Provider-Specific Configs
    # Anthropic
    anthropic_api_key: str | None = Field(default=None, alias="MEETINGOS_ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022", alias="MEETINGOS_ANTHROPIC_MODEL"
    )
    anthropic_base_url: str = Field(
        default="https://api.anthropic.com/v1", alias="MEETINGOS_ANTHROPIC_BASE_URL"
    )

    # Google Gemini
    gemini_api_key: str | None = Field(default=None, alias="MEETINGOS_GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="MEETINGOS_GEMINI_MODEL")
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com", alias="MEETINGOS_GEMINI_BASE_URL"
    )

    # Scalable Worker & Hardware Acceleration
    asr_device: Literal["cpu", "cuda", "auto"] = Field(default="cpu", alias="MEETINGOS_ASR_DEVICE")
    asr_workers: int = Field(default=1, ge=1, alias="MEETINGOS_ASR_WORKERS")
    nlp_workers: int = Field(default=2, ge=1, alias="MEETINGOS_NLP_WORKERS")
    embedding_workers: int = Field(default=2, ge=1, alias="MEETINGOS_EMBEDDING_WORKERS")

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

    @model_validator(mode="after")
    def validate_provider_and_environment(self) -> "Settings":
        # Validate provider selections
        emb = self.embedding_provider.lower()
        if emb not in VALID_EMBEDDING_PROVIDERS:
            raise ValueError(
                f"Invalid MEETINGOS_EMBEDDING_PROVIDER: '{self.embedding_provider}'. "
                f"Allowed: {sorted(VALID_EMBEDDING_PROVIDERS)}"
            )

        reas = self.reasoner_provider.lower()
        if reas not in VALID_REASONER_PROVIDERS:
            raise ValueError(
                f"Invalid MEETINGOS_REASONER_PROVIDER: '{self.reasoner_provider}'. "
                f"Allowed: {sorted(VALID_REASONER_PROVIDERS)}"
            )

        # Validate production environment security constraints
        if self.app_env == "production":
            if "meetingos_secret_password" in self.database_url:
                raise ValueError(
                    "Production configuration error: default insecure database password detected."
                )
            if self.app_debug:
                raise ValueError(
                    "Production configuration error: app_debug must be False in production."
                )
            if emb in ("openai", "openai_compatible") and not self.embedding_api_key:
                raise ValueError(
                    "Production configuration error: OpenAI embedding provider configured without MEETINGOS_EMBEDDING_API_KEY."
                )
            if emb in ("gemini", "google") and not (self.gemini_api_key or self.embedding_api_key):
                raise ValueError(
                    "Production configuration error: Gemini embedding provider configured without MEETINGOS_GEMINI_API_KEY."
                )
            if reas in ("openai", "openai_compatible", "llm") and not self.reasoner_api_key:
                raise ValueError(
                    "Production configuration error: OpenAI reasoner provider configured without MEETINGOS_REASONER_API_KEY."
                )
            if reas in ("anthropic", "claude") and not (
                self.anthropic_api_key or self.reasoner_api_key
            ):
                raise ValueError(
                    "Production configuration error: Anthropic reasoner configured without MEETINGOS_ANTHROPIC_API_KEY."
                )
            if reas in ("gemini", "google") and not (self.gemini_api_key or self.reasoner_api_key):
                raise ValueError(
                    "Production configuration error: Gemini reasoner configured without MEETINGOS_GEMINI_API_KEY."
                )
            if self.teams_enabled and (not self.teams_client_id or not self.teams_client_secret):
                raise ValueError(
                    "Production configuration error: Teams connector enabled without credentials."
                )
            if self.zoom_enabled and (not self.zoom_client_id or not self.zoom_client_secret):
                raise ValueError(
                    "Production configuration error: Zoom connector enabled without credentials."
                )
            if self.google_meet_enabled and (
                not self.google_client_id or not self.google_client_secret
            ):
                raise ValueError(
                    "Production configuration error: Google Meet connector enabled without credentials."
                )

        return self


settings = Settings()


def validate_config() -> int:
    """CLI helper to validate the active configuration."""
    try:
        current_settings = Settings()
        print(f"[OK] Configuration valid for environment: '{current_settings.app_env}'")
        print(f"     App Version: {current_settings.app_version}")
        print(
            f"     Embedding Provider: {current_settings.embedding_provider} ({current_settings.embedding_model})"
        )
        print(
            f"     Reasoner Provider: {current_settings.reasoner_provider} ({current_settings.reasoner_model})"
        )
        print(
            f"     ASR Hardware Device: {current_settings.asr_device} (Workers: {current_settings.asr_workers})"
        )
        print(
            f"     Database URL: {current_settings.database_url.split('@')[-1] if '@' in current_settings.database_url else 'configured'}"
        )
        print(f"     Redis URL: {current_settings.redis_url}")
        return 0
    except Exception as exc:
        print(f"[ERROR] Configuration validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(validate_config())
