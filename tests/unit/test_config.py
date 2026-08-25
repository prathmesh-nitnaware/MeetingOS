from apps.api.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.app_name == "MeetingOS API"
    assert s.api_v1_prefix == "/api/v1"
    assert "postgresql+asyncpg" in s.database_url
    assert "redis://" in s.redis_url
    assert s.asr_provider == "mock"
    assert s.ner_provider == "mock"
