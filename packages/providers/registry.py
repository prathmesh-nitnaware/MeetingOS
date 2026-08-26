from pydantic import BaseModel, Field


class ProviderCapability(BaseModel):
    """Capability specification for a specific AI model provider."""

    name: str
    display_name: str
    default_model: str
    supports_reasoning: bool
    supports_embeddings: bool
    supports_structured_output: bool
    supports_token_telemetry: bool
    supports_cost_tracking: bool
    supports_retry: bool
    supports_fallback: bool
    is_configured: bool
    description: str


class ProviderRegistrySummary(BaseModel):
    providers: list[ProviderCapability] = Field(default_factory=list)
    active_reasoner: str
    active_embedder: str


class ProviderCapabilityRegistry:
    """Central registry tracking all AI provider capabilities, health, and metadata."""

    @staticmethod
    def get_registered_capabilities(
        openai_key_present: bool = False,
        anthropic_key_present: bool = False,
        gemini_key_present: bool = False,
        active_reasoner: str = "mock",
        active_embedder: str = "mock",
    ) -> ProviderRegistrySummary:
        caps = [
            ProviderCapability(
                name="mock",
                display_name="Mock Deterministic Provider",
                default_model="mock-v1",
                supports_reasoning=True,
                supports_embeddings=True,
                supports_structured_output=True,
                supports_token_telemetry=True,
                supports_cost_tracking=False,
                supports_retry=False,
                supports_fallback=False,
                is_configured=True,
                description="Fast in-memory deterministic provider for unit tests and CI pipelines.",
            ),
            ProviderCapability(
                name="local",
                display_name="MeetingOS Local Neural Provider",
                default_model="local-reasoner-v1 / local-semantic-v1",
                supports_reasoning=True,
                supports_embeddings=True,
                supports_structured_output=True,
                supports_token_telemetry=True,
                supports_cost_tracking=True,
                supports_retry=False,
                supports_fallback=False,
                is_configured=True,
                description="Offline 384-dim subword semantic embeddings and multi-hop chronological lifecycle reasoning.",
            ),
            ProviderCapability(
                name="sentence_transformers",
                display_name="SentenceTransformers (HuggingFace)",
                default_model="all-MiniLM-L6-v2",
                supports_reasoning=False,
                supports_embeddings=True,
                supports_structured_output=False,
                supports_token_telemetry=False,
                supports_cost_tracking=False,
                supports_retry=False,
                supports_fallback=True,
                is_configured=True,
                description="Dense local PyTorch embeddings with automatic fallback to local semantic vectors.",
            ),
            ProviderCapability(
                name="openai",
                display_name="OpenAI Compatible Provider",
                default_model="gpt-4o-mini / text-embedding-3-small",
                supports_reasoning=True,
                supports_embeddings=True,
                supports_structured_output=True,
                supports_token_telemetry=True,
                supports_cost_tracking=True,
                supports_retry=True,
                supports_fallback=True,
                is_configured=openai_key_present,
                description="Cloud OpenAI-compatible reasoning and embeddings with SHA-256 caching and retries.",
            ),
            ProviderCapability(
                name="anthropic",
                display_name="Anthropic Claude Provider",
                default_model="claude-3-5-sonnet-20241022",
                supports_reasoning=True,
                supports_embeddings=False,
                supports_structured_output=True,
                supports_token_telemetry=True,
                supports_cost_tracking=True,
                supports_retry=True,
                supports_fallback=True,
                is_configured=anthropic_key_present,
                description="Anthropic Claude Messages API with structured JSON output and graceful local fallback.",
            ),
            ProviderCapability(
                name="gemini",
                display_name="Google Gemini Provider",
                default_model="gemini-1.5-flash / text-embedding-004",
                supports_reasoning=True,
                supports_embeddings=True,
                supports_structured_output=True,
                supports_token_telemetry=True,
                supports_cost_tracking=True,
                supports_retry=True,
                supports_fallback=True,
                is_configured=gemini_key_present,
                description="Google Gemini multimodal/reasoning and batch embedding API with SHA-256 caching.",
            ),
        ]

        return ProviderRegistrySummary(
            providers=caps,
            active_reasoner=active_reasoner,
            active_embedder=active_embedder,
        )
