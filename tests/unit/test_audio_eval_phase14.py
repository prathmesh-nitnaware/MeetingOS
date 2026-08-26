from datasets.audio.corpus import AudioCorpusItem, AudioCorpusManifest
from evaluation.audio_eval import compute_cer, compute_wer


def test_compute_wer():
    ref = "The database architecture was chosen as PostgreSQL"
    hyp_exact = "The database architecture was chosen as PostgreSQL"
    assert compute_wer(ref, hyp_exact) == 0.0

    hyp_sub = "The database architecture was chosen as MongoDB"
    assert compute_wer(ref, hyp_sub) > 0.0

    hyp_del = "The database architecture was chosen"
    assert compute_wer(ref, hyp_del) > 0.0


def test_compute_cer():
    ref = "PostgreSQL"
    hyp = "Postgre"
    assert compute_cer(ref, hyp) > 0.0
    assert compute_cer(ref, "PostgreSQL") == 0.0


def test_audio_manifest_schema():
    manifest = AudioCorpusManifest(
        items=[
            AudioCorpusItem(
                meeting_id="audio-test-01",
                audio_path="datasets/audio/fixtures/test.wav",
                duration_seconds=12.5,
                expected_speakers=2,
                source_type="synthetic",
                license="CC0-1.0",
                transcript_available=True,
                reference_transcript="Testing audio pipeline transcript.",
            )
        ]
    )
    assert len(manifest.items) == 1
    item = manifest.get_item("audio-test-01")
    assert item is not None
    assert item.duration_seconds == 12.5
    assert item.diarization_reference_available is False
