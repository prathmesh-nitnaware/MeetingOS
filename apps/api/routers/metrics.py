from typing import Any

from apps.api.auth import UserIdentity, require_viewer
from apps.api.config import settings
from fastapi import APIRouter, Depends
from packages.providers.registry import (
    ProviderCapability,
    ProviderCapabilityRegistry,
)
from packages.providers.usage import UsageSummary, global_usage_tracker
from pydantic import BaseModel, Field

router = APIRouter(prefix="/admin", tags=["Admin & Observability"])


class ProviderStatusResponse(BaseModel):
    """Current model provider configuration status without credential leakage."""

    embedding_provider: str
    embedding_model: str
    embedding_configured: bool
    reasoner_provider: str
    reasoner_model: str
    reasoner_configured: bool
    has_fallback: bool
    environment: str
    hardware_device: str = "cpu"
    asr_provider: str = "whisper"
    asr_model: str = ""
    asr_ready: bool = False
    diarizer_provider: str = "none"
    capabilities: list[ProviderCapability] = Field(default_factory=list)


@router.get("/metrics/usage", response_model=UsageSummary)
async def get_provider_usage_metrics(
    _user: UserIdentity = Depends(require_viewer),
) -> Any:
    """Retrieve aggregate token, cost, and latency metrics across all providers."""
    return global_usage_tracker.get_summary()


@router.get("/providers/status", response_model=ProviderStatusResponse)
async def get_providers_status(
    _user: UserIdentity = Depends(require_viewer),
) -> Any:
    """Active provider configuration and capability matrix, without exposing secrets.

    "configured" is only true when a real (non-placeholder) API key is present for a cloud
    provider; local and mock providers need no key.
    """
    import importlib.util

    registry_summary = ProviderCapabilityRegistry.get_registered_capabilities(
        openai_key_present=bool(settings.openai_reasoner_key or settings.openai_embedding_key),
        anthropic_key_present=bool(settings.anthropic_key),
        gemini_key_present=bool(settings.gemini_reasoner_key or settings.gemini_embedding_key),
        active_reasoner=settings.reasoner_provider,
        active_embedder=settings.embedding_provider,
    )

    emb = settings.embedding_provider.lower()
    if emb in ("openai", "openai_compatible"):
        emb_configured, emb_model = bool(settings.openai_embedding_key), settings.embedding_model
    elif emb in ("gemini", "google"):
        emb_configured, emb_model = (
            bool(settings.gemini_embedding_key),
            settings.gemini_embedding_model,
        )
    else:
        emb_configured, emb_model = True, settings.embedding_model

    reas = settings.reasoner_provider.lower()
    if reas in ("openai", "openai_compatible", "llm"):
        reas_configured, reas_model = bool(settings.openai_reasoner_key), settings.reasoner_model
    elif reas in ("anthropic", "claude"):
        reas_configured, reas_model = bool(settings.anthropic_key), settings.anthropic_model
    elif reas in ("gemini", "google"):
        reas_configured, reas_model = bool(settings.gemini_reasoner_key), settings.gemini_model
    else:
        reas_configured, reas_model = True, settings.reasoner_model

    asr = settings.asr_provider.lower()
    whisper_installed = importlib.util.find_spec("faster_whisper") is not None

    return ProviderStatusResponse(
        embedding_provider=settings.embedding_provider,
        embedding_model=emb_model,
        embedding_configured=emb_configured,
        reasoner_provider=settings.reasoner_provider,
        reasoner_model=reas_model,
        reasoner_configured=reas_configured,
        has_fallback=reas not in ("mock", "local", "local_evidence", "real"),
        environment=settings.app_env,
        hardware_device=settings.asr_device,
        asr_provider=settings.asr_provider,
        asr_model=settings.whisper_model if asr != "mock" else "mock (canned demo transcript)",
        asr_ready=asr == "mock" or whisper_installed,
        diarizer_provider=settings.diarizer_provider,
        capabilities=registry_summary.providers,
    )
