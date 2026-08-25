from packages.common.models import SpeakerInfo, TranscriptSegment
from packages.ingestion.normalizer import (
    merge_speech_results,
    normalize_plain_text,
    normalize_srt_content,
    parse_srt_timestamp,
)


def test_parse_srt_timestamp():
    assert parse_srt_timestamp("00:00:05,500") == 5.5
    assert parse_srt_timestamp("01:02:03.450") == 3723.45
    assert parse_srt_timestamp("02:30") == 150.0
    assert parse_srt_timestamp("12.5") == 12.5


def test_normalize_srt_content():
    srt_data = """1
00:00:01,000 --> 00:00:04,500
Rahul: Hello team, let us begin the meeting.

2
00:00:05,000 --> 00:00:09,000
Priya: Today we will choose our database.
"""
    segments, speakers = normalize_srt_content(srt_data)
    assert len(segments) == 2
    assert segments[0].sequence == 0
    assert segments[0].start_time == 1.0
    assert segments[0].end_time == 4.5
    assert segments[0].speaker_id == "spk_rahul"
    assert "Hello team" in segments[0].text

    assert segments[1].sequence == 1
    assert segments[1].speaker_id == "spk_priya"
    assert len(speakers) == 2


def test_normalize_plain_text_with_timestamps():
    text_data = """[00:00 - 00:10] Alice: Welcome everyone.
[00:11 - 00:25] Bob: Let us discuss the deployment timeline.
"""
    segments, speakers = normalize_plain_text(text_data)
    assert len(segments) == 2
    assert segments[0].start_time == 0.0
    assert segments[0].end_time == 10.0
    assert segments[0].speaker_id == "spk_alice"
    assert segments[1].start_time == 11.0
    assert segments[1].end_time == 25.0
    assert len(speakers) == 2


def test_normalize_plain_text_without_timestamps():
    raw_lines = """Rahul: We decided on PostgreSQL.
Sarah: Great, I will start the benchmarks.
"""
    segments, speakers = normalize_plain_text(raw_lines)
    assert len(segments) == 2
    assert segments[0].sequence == 0
    assert segments[0].end_time > segments[0].start_time
    assert segments[1].start_time == segments[0].end_time
    assert len(speakers) == 2


def test_merge_speech_results():
    asr_raw = [
        TranscriptSegment(
            segment_id="s1",
            sequence=0,
            speaker_id="spk_0",
            start_time=0.0,
            end_time=4.0,
            text="Hello",
        ),
        TranscriptSegment(
            segment_id="s2",
            sequence=1,
            speaker_id="spk_1",
            start_time=4.5,
            end_time=8.0,
            text="World",
        ),
    ]
    diarization_raw = [
        SpeakerInfo(speaker_id="spk_0", name="Speaker 0"),
        SpeakerInfo(speaker_id="spk_1", name="Speaker 1"),
    ]

    segments, speakers = merge_speech_results(asr_raw, diarization_raw)
    assert len(segments) == 2
    assert len(speakers) == 2
    assert segments[0].sequence == 0
    assert segments[1].sequence == 1
