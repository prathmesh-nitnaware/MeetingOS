from typing import Any

from apps.api.auth import UserIdentity, require_viewer
from apps.api.config import settings
from fastapi import APIRouter, Depends
from packages.providers.usage import UsageSummary, global_usage_tracker
from pydantic import BaseModel

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
    """Retrieve active provider configuration and health without exposing sensitive credentials."""
    return ProviderStatusResponse(
        embedding_provider=settings.embedding_provider,
        embedding_model=settings.embedding_model,
        embedding_configured=bool(
            settings.embedding_provider != "openai" or settings.embedding_api_key
        ),
        reasoner_provider=settings.reasoner_provider,
        reasoner_model=settings.reasoner_model,
        reasoner_configured=bool(
            settings.reasoner_provider != "openai" or settings.reasoner_api_key
        ),
        has_fallback=True,
        environment=settings.app_env,
    )
