import pytest
from apps.api.config import Settings
from pydantic import ValidationError


def test_settings_defaults():
    s = Settings()
    assert s.app_name == "MeetingOS API"
    assert s.api_v1_prefix == "/api/v1"
    assert "postgresql+asyncpg" in s.database_url
    assert "redis://" in s.redis_url
    assert s.asr_provider == "mock"
    assert s.ner_provider == "mock"


def test_invalid_provider_validation():
    with pytest.raises(ValidationError) as exc:
        Settings(MEETINGOS_EMBEDDING_PROVIDER="unsupported_provider_xyz")  # pyright: ignore[reportCallIssue]
    assert "Invalid MEETINGOS_EMBEDDING_PROVIDER" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        Settings(MEETINGOS_REASONER_PROVIDER="unsupported_reasoner_xyz")  # pyright: ignore[reportCallIssue]
    assert "Invalid MEETINGOS_REASONER_PROVIDER" in str(exc.value)


def test_production_mode_security_validation():
    # Production with default password must be rejected
    with pytest.raises(ValidationError) as exc:
        Settings(
            app_env="production",
            database_url="postgresql+asyncpg://meetingos:meetingos_secret_password@db:5432/meetingos_db",
        )
    assert "default insecure database password" in str(exc.value)

    # Production with debug True must be rejected
    with pytest.raises(ValidationError) as exc:
        Settings(
            app_env="production",
            database_url="postgresql+asyncpg://meetingos:secure_prod_password@db:5432/meetingos_db",
            app_debug=True,
        )
    assert "app_debug must be False" in str(exc.value)

    # Production with unconfigured OpenAI keys must be rejected
    with pytest.raises(ValidationError) as exc:
        Settings(
            app_env="production",
            database_url="postgresql+asyncpg://meetingos:secure_prod_password@db:5432/meetingos_db",
            app_debug=False,
            MEETINGOS_SECRET_KEY="A_Valid_Production_Secret_Key_12345!",
            MEETINGOS_ALLOWED_ORIGINS=["https://app.meetingos.internal"],
            MEETINGOS_EMBEDDING_PROVIDER="openai",  # pyright: ignore[reportCallIssue]
            MEETINGOS_EMBEDDING_API_KEY=None,  # pyright: ignore[reportCallIssue]
        )
    assert "MEETINGOS_EMBEDDING_API_KEY" in str(exc.value)
