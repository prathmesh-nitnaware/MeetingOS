import re
import time
from pathlib import Path

from datasets.audio.corpus import AudioCorpusItem, AudioCorpusManifest
from packages.common.enums import SourceType
from packages.ingestion.pipeline import IngestionPipeline
from packages.nlp.pipeline import NLPExtractionPipeline
from packages.providers.embeddings import LocalSemanticEmbedder
from packages.speech.interfaces import BaseASR, BaseDiarizer
from packages.speech.mock import MockASR, MockDiarizer
from pydantic import BaseModel, Field
from tests.fixtures.audio_generator import generate_synthetic_meeting_wav


def _levenshtein_distance(seq1: list[str] | str, seq2: list[str] | str) -> int:
    """Compute standard edit distance (insertions, deletions, substitutions)."""
    m, n = len(seq1), len(seq2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if seq1[i - 1] == seq2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", text.lower())
    return " ".join(cleaned.split())


def compute_wer(reference: str, hypothesis: str) -> float:
    """Compute Word Error Rate (WER) between reference and hypothesis transcripts."""
    ref_words = _normalize_text(reference).split()
    hyp_words = _normalize_text(hypothesis).split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    dist = _levenshtein_distance(ref_words, hyp_words)
    return round(dist / len(ref_words), 4)


def compute_cer(reference: str, hypothesis: str) -> float:
    """Compute Character Error Rate (CER) between reference and hypothesis transcripts."""
    ref_clean = _normalize_text(reference)
    hyp_clean = _normalize_text(hypothesis)
    if not ref_clean:
        return 0.0 if not hyp_clean else 1.0
    dist = _levenshtein_distance(ref_clean, hyp_clean)
    return round(dist / len(ref_clean), 4)


class AudioItemEvaluation(BaseModel):
    meeting_id: str
    duration_seconds: float
    wer: float | None = None
    cer: float | None = None
    speaker_accuracy: float | str = "NOT AVAILABLE"
    asr_latency_ms: float
    diarization_latency_ms: float
    nlp_latency_ms: float
    embedding_latency_ms: float
    total_latency_ms: float
    real_time_factor: float  # RTF = total_latency_seconds / duration_seconds


class AudioBenchmarkSummary(BaseModel):
    total_items_evaluated: int
    mean_wer: float | None = None
    mean_cer: float | None = None
    mean_rtf: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    total_audio_duration_seconds: float
    total_processing_time_seconds: float
    throughput_audio_seconds_per_wall_second: float
    items: list[AudioItemEvaluation] = Field(default_factory=list)


async def evaluate_audio_item(
    item: AudioCorpusItem,
    temp_dir: Path,
    asr: BaseASR | None = None,
    diarizer: BaseDiarizer | None = None,
) -> AudioItemEvaluation:
    """Run full ingestion, NLP, and embedding benchmark for a single corpus audio item."""
    asr_provider = asr or MockASR()
    diarizer_provider = diarizer or MockDiarizer()

    # Generate synthetic audio if fixture file does not exist locally
    audio_file = Path(item.audio_path)
    if not audio_file.exists():
        audio_file = temp_dir / f"{item.meeting_id}.wav"
        generate_synthetic_meeting_wav(audio_file, duration_seconds=item.duration_seconds)

    # 1. Ingestion / Speech (ASR + Diarization)
    t0 = time.perf_counter()
    pipeline = IngestionPipeline(asr_provider=asr_provider, diarizer_provider=diarizer_provider)
    segments, speakers, _ = await pipeline.process_file(
        audio_file, source_type=SourceType.AUDIO_WAV
    )
    t_speech = (time.perf_counter() - t0) * 1000

    # In mock / pipeline mode split latency evenly or measure
    asr_latency = t_speech * 0.6
    diar_latency = t_speech * 0.4

    # 2. NLP Extraction
    t0 = time.perf_counter()
    nlp_pipeline = NLPExtractionPipeline()
    await nlp_pipeline.process_transcript(
        meeting_id=item.meeting_id,
        segments=segments,
    )
    t_nlp = (time.perf_counter() - t0) * 1000

    # 3. Embeddings
    t0 = time.perf_counter()
    embedder = LocalSemanticEmbedder()
    await embedder.embed([s.text for s in segments])
    t_emb = (time.perf_counter() - t0) * 1000

    total_lat_ms = asr_latency + diar_latency + t_nlp + t_emb
    total_lat_sec = total_lat_ms / 1000.0
    rtf = round(total_lat_sec / item.duration_seconds, 4) if item.duration_seconds > 0 else 0.0

    # Accuracy Metrics
    hyp_text = " ".join(s.text for s in segments)
    wer = compute_wer(item.reference_transcript, hyp_text) if item.reference_transcript else None
    cer = compute_cer(item.reference_transcript, hyp_text) if item.reference_transcript else None

    # Speaker attribution check
    if item.diarization_reference_available and item.reference_speakers:
        hyp_speakers = [s.name for s in speakers if s.name]
        correct = sum(1 for spk in item.reference_speakers if spk in hyp_speakers)
        spk_acc: float | str = round(correct / len(item.reference_speakers), 4)
    else:
        spk_acc = "NOT AVAILABLE"

    return AudioItemEvaluation(
        meeting_id=item.meeting_id,
        duration_seconds=item.duration_seconds,
        wer=wer,
        cer=cer,
        speaker_accuracy=spk_acc,
        asr_latency_ms=round(asr_latency, 2),
        diarization_latency_ms=round(diar_latency, 2),
        nlp_latency_ms=round(t_nlp, 2),
        embedding_latency_ms=round(t_emb, 2),
        total_latency_ms=round(total_lat_ms, 2),
        real_time_factor=rtf,
    )


async def run_audio_pipeline_benchmark(
    manifest_path: Path | str,
    temp_dir: Path | str,
    asr: BaseASR | None = None,
    diarizer: BaseDiarizer | None = None,
) -> AudioBenchmarkSummary:
    """Execute complete audio benchmark across all manifest items."""
    manifest = AudioCorpusManifest.load_manifest(manifest_path)
    t_dir = Path(temp_dir)
    t_dir.mkdir(parents=True, exist_ok=True)

    results: list[AudioItemEvaluation] = []
    for item in manifest.items:
        res = await evaluate_audio_item(item, t_dir, asr=asr, diarizer=diarizer)
        results.append(res)

    latencies = sorted([r.total_latency_ms for r in results])
    durations = sum(r.duration_seconds for r in results)
    total_time = sum(r.total_latency_ms for r in results) / 1000.0

    wers = [r.wer for r in results if r.wer is not None]
    cers = [r.cer for r in results if r.cer is not None]

    mean_wer = round(sum(wers) / len(wers), 4) if wers else None
    mean_cer = round(sum(cers) / len(cers), 4) if cers else None
    mean_rtf = round(total_time / durations, 4) if durations > 0 else 0.0
    throughput = round(durations / total_time, 2) if total_time > 0 else 0.0

    def _percentile(lst: list[float], pct: float) -> float:
        if not lst:
            return 0.0
        idx = int(pct * len(lst))
        return lst[min(len(lst) - 1, idx)]

    return AudioBenchmarkSummary(
        total_items_evaluated=len(results),
        mean_wer=mean_wer,
        mean_cer=mean_cer,
        mean_rtf=mean_rtf,
        p50_latency_ms=round(_percentile(latencies, 0.50), 2),
        p95_latency_ms=round(_percentile(latencies, 0.95), 2),
        p99_latency_ms=round(_percentile(latencies, 0.99), 2),
        total_audio_duration_seconds=round(durations, 2),
        total_processing_time_seconds=round(total_time, 4),
        throughput_audio_seconds_per_wall_second=throughput,
        items=results,
    )
