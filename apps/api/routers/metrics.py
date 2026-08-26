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
    """Retrieve active provider configuration, capability matrix, and health without exposing secrets."""
    openai_configured = bool(settings.embedding_api_key or settings.reasoner_api_key)
    anthropic_configured = bool(settings.anthropic_api_key or settings.reasoner_api_key)
    gemini_configured = bool(
        settings.gemini_api_key or settings.embedding_api_key or settings.reasoner_api_key
    )

    registry_summary = ProviderCapabilityRegistry.get_registered_capabilities(
        openai_key_present=openai_configured,
        anthropic_key_present=anthropic_configured,
        gemini_key_present=gemini_configured,
        active_reasoner=settings.reasoner_provider,
        active_embedder=settings.embedding_provider,
    )

    is_emb_configured = True
    if settings.embedding_provider in ("openai", "openai_compatible"):
        is_emb_configured = bool(settings.embedding_api_key)
    elif settings.embedding_provider in ("gemini", "google"):
        is_emb_configured = bool(settings.gemini_api_key or settings.embedding_api_key)

    is_reas_configured = True
    if settings.reasoner_provider in ("openai", "openai_compatible", "llm"):
        is_reas_configured = bool(settings.reasoner_api_key)
    elif settings.reasoner_provider in ("anthropic", "claude"):
        is_reas_configured = bool(settings.anthropic_api_key or settings.reasoner_api_key)
    elif settings.reasoner_provider in ("gemini", "google"):
        is_reas_configured = bool(settings.gemini_api_key or settings.reasoner_api_key)

    return ProviderStatusResponse(
        embedding_provider=settings.embedding_provider,
        embedding_model=settings.embedding_model,
        embedding_configured=is_emb_configured,
        reasoner_provider=settings.reasoner_provider,
        reasoner_model=settings.reasoner_model,
        reasoner_configured=is_reas_configured,
        has_fallback=True,
        environment=settings.app_env,
        hardware_device=settings.asr_device,
        capabilities=registry_summary.providers,
    )
