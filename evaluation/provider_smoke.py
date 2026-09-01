import argparse
import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apps.api.config import settings
from packages.common.enums import SourceType
from packages.common.models import EvidenceItem
from packages.nlp.interfaces import BaseEmbedder
from packages.providers.anthropic import AnthropicReasoner
from packages.providers.embeddings import (
    LocalSemanticEmbedder,
    OpenAICompatibleEmbedder,
    SentenceTransformerEmbedder,
)
from packages.providers.gemini import GeminiEmbedder, GeminiReasoner
from packages.providers.reasoning import (
    BaseReasoner,
    LocalEvidenceReasoner,
    OpenAICompatibleReasoner,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("meetingos.smoke")


def _sanitize_secrets(text: str) -> str:
    """Ensure no API keys appear in report strings."""
    keys_to_scrub = [
        settings.embedding_api_key,
        settings.reasoner_api_key,
        settings.anthropic_api_key,
        settings.gemini_api_key,
        settings.teams_client_secret,
        settings.zoom_client_secret,
        settings.google_client_secret,
    ]
    scrubbed = text
    for k in keys_to_scrub:
        if k and len(k) > 4:
            scrubbed = scrubbed.replace(k, "[REDACTED_SECRET]")
    return scrubbed


async def smoke_test_embedder(_name: str, embedder: BaseEmbedder) -> dict[str, Any]:
    """Execute minimal embedding test with latency and dimensionality checks."""
    t0 = time.perf_counter()
    sample_text = ["MeetingOS production verification and semantic embedding validation."]
    try:
        vectors = await embedder.embed(sample_text)
        lat_ms = (time.perf_counter() - t0) * 1000
        if not vectors or len(vectors) == 0:
            return {"status": "FAILED", "error": "Empty vector output", "latency_ms": lat_ms}
        dim = len(vectors[0])
        return {
            "status": "PASSED",
            "latency_ms": round(lat_ms, 2),
            "dimension": dim,
            "sample_vector_norm": round(sum(x * x for x in vectors[0][:10]), 4),
        }
    except Exception as exc:
        lat_ms = (time.perf_counter() - t0) * 1000
        return {
            "status": "FAILED",
            "error": _sanitize_secrets(str(exc)),
            "latency_ms": round(lat_ms, 2),
        }


async def smoke_test_reasoner(
    _name: str, reasoner: BaseReasoner, sample_evidence: list[EvidenceItem]
) -> dict[str, Any]:
    """Execute minimal reasoning test with structured output validation."""
    t0 = time.perf_counter()
    query = "What database was selected for the organizational memory layer?"
    try:
        ans = await reasoner.reason(query, sample_evidence)
        lat_ms = (time.perf_counter() - t0) * 1000
        if not ans or not ans.answer:
            return {"status": "FAILED", "error": "Empty answer returned", "latency_ms": lat_ms}
        return {
            "status": "PASSED",
            "latency_ms": round(lat_ms, 2),
            "confidence": round(ans.confidence, 4),
            "answer_preview": _sanitize_secrets(ans.answer[:120]),
            "evidence_count": len(ans.evidence),
        }
    except Exception as exc:
        lat_ms = (time.perf_counter() - t0) * 1000
        return {
            "status": "FAILED",
            "error": _sanitize_secrets(str(exc)),
            "latency_ms": round(lat_ms, 2),
        }


def _is_real_key(key: str | None) -> bool:
    if not key:
        return False
    k = key.lower().strip()
    if any(p in k for p in ("your-", "local-", "dev-", "test-", "dummy", "fake", "placeholder")):
        return False
    return len(key) >= 16


async def run_provider_smoke_suite(output_dir: str = "evaluation/reports") -> dict[str, Any]:
    """Run non-destructive production smoke tests for all configured local & cloud AI providers."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("\n=======================================================")
    print("MeetingOS Multi-Provider Production Smoke Test Suite")
    print("=======================================================\n")

    sample_evidence = [
        EvidenceItem(
            meeting_id="smoke-meet-001",
            segment_id="smoke-seg-001",
            start_time=12.0,
            end_time=24.5,
            text_snapshot="The engineering architecture council approved PostgreSQL with pgvector as the primary organizational memory store.",
            source_type=SourceType.AUDIO_WAV,
        )
    ]

    results: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": settings.app_env,
        "embedders": {},
        "reasoners": {},
    }

    # 1. Local Providers (Always Available)
    print("Testing [LocalSemanticEmbedder]...")
    local_emb = LocalSemanticEmbedder(dimension=384)
    results["embedders"]["local_semantic"] = await smoke_test_embedder(
        "LocalSemanticEmbedder", local_emb
    )

    print("Testing [LocalEvidenceReasoner]...")
    local_reas = LocalEvidenceReasoner()
    results["reasoners"]["local_evidence"] = await smoke_test_reasoner(
        "LocalEvidenceReasoner", local_reas, sample_evidence
    )

    # 2. Sentence Transformers (Optional local model)
    print("Testing [SentenceTransformerEmbedder]...")
    st_emb = SentenceTransformerEmbedder(model_name="all-MiniLM-L6-v2")
    results["embedders"]["sentence_transformers"] = await smoke_test_embedder(
        "SentenceTransformerEmbedder", st_emb
    )

    # 3. OpenAI-Compatible Embedder & Reasoner
    has_openai_emb = _is_real_key(settings.embedding_api_key)
    has_openai_reas = _is_real_key(settings.reasoner_api_key)
    if has_openai_emb or has_openai_reas:
        print("Testing [OpenAICompatibleEmbedder]...")
        openai_emb = OpenAICompatibleEmbedder(
            api_key=settings.embedding_api_key or settings.reasoner_api_key,
            base_url=settings.embedding_base_url or "https://api.openai.com/v1",
        )
        results["embedders"]["openai"] = await smoke_test_embedder(
            "OpenAICompatibleEmbedder", openai_emb
        )

        print("Testing [OpenAICompatibleReasoner]...")
        openai_reas = OpenAICompatibleReasoner(
            api_key=settings.reasoner_api_key or settings.embedding_api_key,
            base_url=settings.reasoner_base_url or "https://api.openai.com/v1",
        )
        results["reasoners"]["openai"] = await smoke_test_reasoner(
            "OpenAICompatibleReasoner", openai_reas, sample_evidence
        )
    else:
        print("Skipping [OpenAI] — No real API key configured.")
        results["embedders"]["openai"] = {
            "status": "SKIPPED",
            "reason": "No real API key configured",
        }
        results["reasoners"]["openai"] = {
            "status": "SKIPPED",
            "reason": "No real API key configured",
        }

    # 4. Anthropic Claude Reasoner
    if _is_real_key(settings.anthropic_api_key):
        print("Testing [AnthropicReasoner]...")
        anthropic_reas = AnthropicReasoner(
            api_key=settings.anthropic_api_key,
            base_url=settings.anthropic_base_url,
        )
        results["reasoners"]["anthropic"] = await smoke_test_reasoner(
            "AnthropicReasoner", anthropic_reas, sample_evidence
        )
    else:
        print("Skipping [Anthropic] — No real API key configured.")
        results["reasoners"]["anthropic"] = {
            "status": "SKIPPED",
            "reason": "No real API key configured",
        }

    # 5. Google Gemini Reasoner & Embedder
    if _is_real_key(settings.gemini_api_key):
        print("Testing [GeminiEmbedder]...")
        gemini_emb = GeminiEmbedder(
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
        )
        results["embedders"]["gemini"] = await smoke_test_embedder("GeminiEmbedder", gemini_emb)

        print("Testing [GeminiReasoner]...")
        gemini_reas = GeminiReasoner(
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
        )
        results["reasoners"]["gemini"] = await smoke_test_reasoner(
            "GeminiReasoner", gemini_reas, sample_evidence
        )
    else:
        print("Skipping [Gemini] — No real API key configured.")
        results["embedders"]["gemini"] = {
            "status": "SKIPPED",
            "reason": "No real API key configured",
        }
        results["reasoners"]["gemini"] = {
            "status": "SKIPPED",
            "reason": "No real API key configured",
        }

    # Write Markdown & JSON Reports
    json_path = out_path / "provider_smoke.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    md_path = out_path / "provider_smoke_report.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# MeetingOS Multi-Provider Smoke Test Report\n\n")
        f.write(f"**Execution Timestamp:** {results['timestamp']}\n")
        f.write(f"**Target Environment:** {results['environment']}\n\n")
        f.write("## 1. Embedder Providers Status\n\n")
        f.write("| Provider | Status | Latency | Dimension | Notes |\n")
        f.write("| :--- | :---: | :---: | :---: | :--- |\n")
        for k, v in results["embedders"].items():
            lat = f"{v.get('latency_ms', 'N/A')} ms" if "latency_ms" in v else "N/A"
            dim = v.get("dimension", "N/A")
            note = v.get("reason", v.get("error", "OK"))
            f.write(f"| **{k}** | `{v['status']}` | {lat} | {dim} | {note} |\n")

        f.write("\n## 2. Reasoner Providers Status\n\n")
        f.write("| Provider | Status | Latency | Confidence | Notes |\n")
        f.write("| :--- | :---: | :---: | :---: | :--- |\n")
        for k, v in results["reasoners"].items():
            lat = f"{v.get('latency_ms', 'N/A')} ms" if "latency_ms" in v else "N/A"
            conf = f"{v.get('confidence', 'N/A')}" if "confidence" in v else "N/A"
            note = v.get("reason", v.get("error", "OK"))
            f.write(f"| **{k}** | `{v['status']}` | {lat} | {conf} | {note} |\n")

    print(f"\n[OK] Smoke test execution finished. Reports saved to '{output_dir}'.")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MeetingOS Provider Smoke Test Runner")
    parser.add_argument("--output", default="evaluation/reports")
    args = parser.parse_args()

    asyncio.run(run_provider_smoke_suite(output_dir=args.output))
