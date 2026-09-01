import pytest
from apps.api.config import Settings
from pydantic import ValidationError


def test_production_config_rejects_insecure_secret_key():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            app_debug=False,
            MEETINGOS_SECRET_KEY="insecure-default-key",  # pyright: ignore[reportCallIssue]
            database_url="postgresql+asyncpg://prod_user:StrongPassword987!@localhost:5432/prod_db",
            MEETINGOS_ALLOWED_ORIGINS=["https://app.meetingos.internal"],  # pyright: ignore[reportCallIssue]
        )
    assert "MEETINGOS_SECRET_KEY" in str(exc_info.value)


def test_production_config_rejects_wildcard_cors():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            app_debug=False,
            MEETINGOS_SECRET_KEY="A_Very_Strong_Production_Secret_Key_12345!",  # pyright: ignore[reportCallIssue]
            database_url="postgresql+asyncpg://prod_user:StrongPassword987!@localhost:5432/prod_db",
            MEETINGOS_ALLOWED_ORIGINS=["*"],  # pyright: ignore[reportCallIssue]
        )
    assert "MEETINGOS_ALLOWED_ORIGINS" in str(exc_info.value)


def test_production_config_rejects_debug_true():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            app_debug=True,
            MEETINGOS_SECRET_KEY="A_Very_Strong_Production_Secret_Key_12345!",  # pyright: ignore[reportCallIssue]
            database_url="postgresql+asyncpg://prod_user:StrongPassword987!@localhost:5432/prod_db",
            MEETINGOS_ALLOWED_ORIGINS=["https://app.meetingos.internal"],  # pyright: ignore[reportCallIssue]
        )
    assert "app_debug must be False" in str(exc_info.value)


def test_production_config_rejects_missing_openai_key():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            app_debug=False,
            MEETINGOS_SECRET_KEY="A_Very_Strong_Production_Secret_Key_12345!",  # pyright: ignore[reportCallIssue]
            database_url="postgresql+asyncpg://prod_user:StrongPassword987!@localhost:5432/prod_db",
            MEETINGOS_ALLOWED_ORIGINS=["https://app.meetingos.internal"],  # pyright: ignore[reportCallIssue]
            MEETINGOS_REASONER_PROVIDER="openai",  # pyright: ignore[reportCallIssue]
            MEETINGOS_REASONER_API_KEY=None,  # pyright: ignore[reportCallIssue]
        )
    assert "MEETINGOS_REASONER_API_KEY" in str(exc_info.value)


def test_production_config_valid():
    cfg = Settings(
        app_env="production",
        app_debug=False,
        MEETINGOS_SECRET_KEY="A_Very_Strong_Production_Secret_Key_12345!",  # pyright: ignore[reportCallIssue]
        database_url="postgresql+asyncpg://prod_user:StrongPassword987!@localhost:5432/prod_db",
        MEETINGOS_ALLOWED_ORIGINS=["https://app.meetingos.internal"],  # pyright: ignore[reportCallIssue]
        MEETINGOS_EMBEDDING_PROVIDER="local",  # pyright: ignore[reportCallIssue]
        MEETINGOS_REASONER_PROVIDER="local",  # pyright: ignore[reportCallIssue]
    )
    assert cfg.app_env == "production"
    assert cfg.app_debug is False
