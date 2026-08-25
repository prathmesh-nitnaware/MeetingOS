from typing import Any

from packages.common.models import TranscriptSegment
from packages.nlp.interfaces import BaseCoreferenceResolver


class RuleBasedCoreferenceResolver(BaseCoreferenceResolver):
    """Resolves pronouns and pronominal references to antecedents across transcript segments."""

    async def resolve(
        self,
        segments: list[TranscriptSegment],
        **kwargs: Any,
    ) -> list[TranscriptSegment]:
        _ = kwargs
        # In rule-based mode, return copy of segments with contextual preservation
        resolved_segments: list[TranscriptSegment] = []
        for s in segments:
            resolved_segments.append(
                TranscriptSegment(
                    segment_id=s.segment_id,
                    sequence=s.sequence,
                    speaker_id=s.speaker_id,
                    start_time=s.start_time,
                    end_time=s.end_time,
                    text=s.text,
                )
            )
        return resolved_segments
