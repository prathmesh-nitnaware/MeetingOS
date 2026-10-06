"""Builds the AI / speech providers selected in settings.

Every code path (API, agents, Celery workers) must obtain providers from here so that the
MEETINGOS_REASONER_PROVIDER / MEETINGOS_EMBEDDING_PROVIDER / ASR_PROVIDER settings take effect.
"""

from functools import lru_cache
from typing import TYPE_CHECKING

from apps.api.config import settings
from packages.nlp.interfaces import BaseEmbedder
from packages.reasoning.interfaces import BaseReasoner
from packages.speech.interfaces import BaseASR, BaseDiarizer

if TYPE_CHECKING:
    from packages.connectors.models import ConnectorConfig

LOCAL_REASONER_DEFAULT = "local-reasoner-v1"
LOCAL_EMBEDDING_DEFAULT = "local-semantic-v1"
OPENAI_REASONER_DEFAULT = "gpt-4o-mini"
OPENAI_EMBEDDING_DEFAULT = "text-embedding-3-small"


def _configured_model(default_for_provider: str, local_default: str, configured: str) -> str:
    """The generic *_MODEL setting defaults to a local model name; ignore it for cloud providers."""
    return default_for_provider if configured == local_default else configured


@lru_cache(maxsize=8)
def _reasoner_for(provider: str, key_fingerprint: str) -> BaseReasoner:
    _ = key_fingerprint  # part of the cache key so changed credentials rebuild the provider
    from packages.providers.reasoning import get_reasoner

    if provider in ("openai", "openai_compatible", "llm"):
        return get_reasoner(
            "openai",
            model_name=_configured_model(
                OPENAI_REASONER_DEFAULT, LOCAL_REASONER_DEFAULT, settings.reasoner_model
            ),
            base_url=settings.reasoner_base_url,
            api_key=settings.openai_reasoner_key,
        )
    if provider in ("anthropic", "claude"):
        return get_reasoner(
            "anthropic",
            model_name=settings.anthropic_model,
            base_url=settings.anthropic_base_url,
            api_key=settings.anthropic_key,
        )
    if provider in ("gemini", "google"):
        return get_reasoner(
            "gemini",
            model_name=settings.gemini_model,
            base_url=settings.gemini_base_url,
            api_key=settings.gemini_reasoner_key,
        )
    if provider == "mock":
        return get_reasoner("mock")
    return get_reasoner("local", model_name=settings.reasoner_model)


def build_reasoner() -> BaseReasoner:
    provider = settings.reasoner_provider.lower()
    key = (
        settings.openai_reasoner_key or settings.anthropic_key or settings.gemini_reasoner_key or ""
    )
    return _reasoner_for(provider, str(hash(key)))


@lru_cache(maxsize=8)
def _embedder_for(provider: str, key_fingerprint: str) -> BaseEmbedder:
    _ = key_fingerprint
    from packages.providers.embeddings import get_embedder

    if provider in ("openai", "openai_compatible"):
        return get_embedder(
            "openai",
            dimension=1536,
            model_name=_configured_model(
                OPENAI_EMBEDDING_DEFAULT, LOCAL_EMBEDDING_DEFAULT, settings.embedding_model
            ),
            base_url=settings.embedding_base_url,
            api_key=settings.openai_embedding_key,
        )
    if provider in ("gemini", "google"):
        return get_embedder(
            "gemini",
            dimension=768,
            model_name=settings.gemini_embedding_model,
            base_url=settings.gemini_base_url,
            api_key=settings.gemini_embedding_key,
        )
    if provider in ("sentence_transformers", "st"):
        return get_embedder(
            "sentence_transformers",
            model_name=_configured_model(
                "all-MiniLM-L6-v2", LOCAL_EMBEDDING_DEFAULT, settings.embedding_model
            ),
        )
    if provider == "mock":
        return get_embedder("mock")
    return get_embedder("local", dimension=384, model_name=settings.embedding_model)


def build_embedder() -> BaseEmbedder:
    provider = settings.embedding_provider.lower()
    key = settings.openai_embedding_key or settings.gemini_embedding_key or ""
    return _embedder_for(provider, str(hash(key)))


def build_speech_providers(
    asr_name: str | None = None, diarizer_name: str | None = None
) -> tuple[BaseASR, BaseDiarizer]:
    """ASR + diarizer for the configured (or explicitly requested) provider names."""
    from packages.speech.mock import MockASR, MockDiarizer
    from packages.speech.whisper import SingleSpeakerDiarizer, WhisperASR

    asr_choice = (asr_name or settings.asr_provider).lower()
    diarizer_choice = (diarizer_name or settings.diarizer_provider).lower()

    asr: BaseASR
    if asr_choice == "mock":
        asr = MockASR()
    else:
        asr = WhisperASR(
            model_size=settings.whisper_model,
            device="auto" if settings.asr_device == "auto" else settings.asr_device,
            compute_type=settings.whisper_compute_type,
            language=settings.whisper_language,
        )

    diarizer: BaseDiarizer = (
        MockDiarizer() if diarizer_choice == "mock" else SingleSpeakerDiarizer()
    )
    return asr, diarizer


def build_connector_config(provider: str) -> "ConnectorConfig":
    """Connector credentials from settings. Built wherever needed (API or worker) so secrets
    are never passed around in task arguments."""
    from packages.connectors.models import ConnectorConfig

    p = provider.lower()
    if p == "teams":
        return ConnectorConfig(
            provider="teams",
            enabled=settings.teams_enabled,
            tenant_id=settings.teams_tenant_id,
            client_id=settings.teams_client_id,
            client_secret=settings.teams_client_secret,
        )
    if p == "zoom":
        return ConnectorConfig(
            provider="zoom",
            enabled=settings.zoom_enabled,
            account_id=settings.zoom_account_id,
            client_id=settings.zoom_client_id,
            client_secret=settings.zoom_client_secret,
        )
    if p == "google_meet":
        return ConnectorConfig(
            provider="google_meet",
            enabled=settings.google_meet_enabled,
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
    raise ValueError(f"Unknown provider: {provider}")
