import re
from uuid import uuid4

from packages.common.models import SpeakerInfo, TranscriptSegment


def parse_srt_timestamp(ts_str: str) -> float:
    """Parse SRT timestamp 'HH:MM:SS,mmm' or 'HH:MM:SS.mmm' into seconds float."""
    clean = ts_str.strip().replace(",", ".")
    parts = clean.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return float(hours) * 3600.0 + float(minutes) * 60.0 + float(seconds)
    elif len(parts) == 2:
        minutes, seconds = parts
        return float(minutes) * 60.0 + float(seconds)
    return float(clean)


def normalize_srt_content(srt_text: str) -> tuple[list[TranscriptSegment], list[SpeakerInfo]]:
    """Parse SRT subtitle format into timestamped CMF transcript segments."""
    segments: list[TranscriptSegment] = []
    speakers_map: dict[str, str] = {}

    # Regex matching SRT blocks
    pattern = re.compile(
        r"(\d+)\s*\n"
        r"(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*\n"
        r"([\s\S]*?)(?=\n\s*\n|\Z)",
        re.MULTILINE,
    )

    matches = pattern.findall(srt_text)
    seq = 0

    for _, start_str, end_str, content in matches:
        text = " ".join(content.strip().split())
        if not text:
            continue

        start_time = parse_srt_timestamp(start_str)
        end_time = parse_srt_timestamp(end_str)
        if end_time < start_time:
            end_time = start_time + 1.0

        # Check for inline speaker indicator e.g. "Rahul: Let's adopt PostgreSQL"
        speaker_id = "spk_0"
        speaker_name = None
        if ":" in text:
            potential_speaker, rest = text.split(":", 1)
            potential_speaker = potential_speaker.strip()
            if 1 <= len(potential_speaker) <= 50 and not any(
                c in potential_speaker for c in "[]{}()"
            ):
                speaker_name = potential_speaker
                speaker_id = f"spk_{speaker_name.lower().replace(' ', '_')}"
                text = rest.strip()
                speakers_map[speaker_id] = speaker_name

        if speaker_id not in speakers_map:
            speakers_map[speaker_id] = speaker_name or f"Speaker {speaker_id}"

        segments.append(
            TranscriptSegment(
                segment_id=f"seg-{uuid4()}",
                sequence=seq,
                speaker_id=speaker_id,
                start_time=start_time,
                end_time=end_time,
                text=text,
            )
        )
        seq += 1

    speakers = [
        SpeakerInfo(speaker_id=spk_id, name=spk_name) for spk_id, spk_name in speakers_map.items()
    ]
    return segments, speakers


def normalize_plain_text(raw_text: str) -> tuple[list[TranscriptSegment], list[SpeakerInfo]]:
    """Parse plain text meeting transcript into CMF segments."""
    segments: list[TranscriptSegment] = []
    speakers_map: dict[str, str] = {}
    lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]

    # Pattern for timestamp prefix like [00:05 - 00:15] or (00:05)
    ts_pattern = re.compile(
        r"^\[?(\d{1,2}:\d{2}(?::\d{2})?)\s*(?:-|–|-->)\s*(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*(.*)$"
    )

    current_time = 0.0
    seq = 0

    for line in lines:
        match = ts_pattern.match(line)
        if match:
            start_str, end_str, remaining = match.groups()
            start_time = parse_srt_timestamp(start_str)
            end_time = parse_srt_timestamp(end_str)
            text_body = remaining.strip()
        else:
            start_time = current_time
            # Estimate 3 seconds per line or proportional to words
            word_count = max(1, len(line.split()))
            duration = max(2.0, round(word_count * 0.4, 2))
            end_time = round(start_time + duration, 2)
            text_body = line

        current_time = end_time

        speaker_id = "spk_0"
        speaker_name = None
        if ":" in text_body:
            potential_speaker, rest = text_body.split(":", 1)
            potential_speaker = potential_speaker.strip()
            if 1 <= len(potential_speaker) <= 50:
                speaker_name = potential_speaker
                speaker_id = f"spk_{speaker_name.lower().replace(' ', '_')}"
                text_body = rest.strip()
                speakers_map[speaker_id] = speaker_name

        if speaker_id not in speakers_map:
            speakers_map[speaker_id] = speaker_name or f"Speaker {speaker_id}"

        segments.append(
            TranscriptSegment(
                segment_id=f"seg-{uuid4()}",
                sequence=seq,
                speaker_id=speaker_id,
                start_time=start_time,
                end_time=end_time,
                text=text_body if text_body else line,
            )
        )
        seq += 1

    speakers = [
        SpeakerInfo(speaker_id=spk_id, name=spk_name) for spk_id, spk_name in speakers_map.items()
    ]
    return segments, speakers


def merge_speech_results(
    asr_segments: list[TranscriptSegment],
    diarization_speakers: list[SpeakerInfo],
) -> tuple[list[TranscriptSegment], list[SpeakerInfo]]:
    """Ensure sequence ordering, timestamps, and speaker metadata are cleanly aligned."""
    normalized_segments: list[TranscriptSegment] = []
    for i, seg in enumerate(asr_segments):
        normalized_segments.append(
            TranscriptSegment(
                segment_id=seg.segment_id or f"seg-{uuid4()}",
                sequence=i,
                speaker_id=seg.speaker_id,
                start_time=seg.start_time,
                end_time=seg.end_time,
                text=seg.text,
            )
        )

    return normalized_segments, list(diarization_speakers)
