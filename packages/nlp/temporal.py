import re
from datetime import UTC, datetime, timedelta
from typing import Any

from packages.common.models import NormalizedTemporal
from packages.nlp.interfaces import BaseTemporalExtractor


class RuleBasedTemporalExtractor(BaseTemporalExtractor):
    """Extracts and normalizes relative and absolute temporal expressions in transcripts."""

    WEEKDAYS = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    async def normalize_time(
        self,
        text: str,
        reference_date: datetime,
        segment_id: str | None = None,
        **kwargs: Any,
    ) -> list[NormalizedTemporal]:
        _ = kwargs
        ref = (
            reference_date
            if reference_date.tzinfo is not None
            else reference_date.replace(tzinfo=UTC)
        )
        temporals: list[NormalizedTemporal] = []
        lowered = text.lower()

        # 1. "today"
        if re.search(r"\btoday\b", lowered):
            temporals.append(
                NormalizedTemporal(
                    text="today",
                    normalized_date=ref,
                    segment_id=segment_id,
                )
            )

        # 2. "tomorrow"
        if re.search(r"\btomorrow\b", lowered):
            norm_dt = ref + timedelta(days=1)
            temporals.append(
                NormalizedTemporal(
                    text="tomorrow",
                    normalized_date=norm_dt,
                    segment_id=segment_id,
                )
            )

        # 3. "yesterday"
        if re.search(r"\byesterday\b", lowered):
            norm_dt = ref - timedelta(days=1)
            temporals.append(
                NormalizedTemporal(
                    text="yesterday",
                    normalized_date=norm_dt,
                    segment_id=segment_id,
                )
            )

        # 4. "by Friday" / "next Friday" / specific weekday
        weekday_pattern = re.compile(
            r"\b(?:by\s+|next\s+|on\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            re.IGNORECASE,
        )
        for m in weekday_pattern.finditer(lowered):
            raw_match = m.group(0)
            day_name = m.group(1)
            target_idx = self.WEEKDAYS[day_name]
            current_idx = ref.weekday()

            days_ahead = target_idx - current_idx
            if "next" in raw_match:
                days_ahead += 7
            elif days_ahead <= 0:
                days_ahead += 7

            norm_dt = ref + timedelta(days=days_ahead)
            temporals.append(
                NormalizedTemporal(
                    text=raw_match,
                    normalized_date=norm_dt,
                    segment_id=segment_id,
                )
            )

        # 5. "in N days" or "in N weeks"
        relative_offset_pattern = re.compile(
            r"\bin\s+(\d+)\s+(day|days|week|weeks)\b", re.IGNORECASE
        )
        for m in relative_offset_pattern.finditer(lowered):
            count = int(m.group(1))
            unit = m.group(2)
            days = count * 7 if "week" in unit else count
            norm_dt = ref + timedelta(days=days)
            temporals.append(
                NormalizedTemporal(
                    text=m.group(0),
                    normalized_date=norm_dt,
                    segment_id=segment_id,
                )
            )

        # 6. "end of the week" / "by the end of the week"
        if re.search(r"\b(end of the week|by the end of the week)\b", lowered):
            days_to_friday = (4 - ref.weekday()) % 7
            if days_to_friday == 0:
                days_to_friday = 7
            norm_dt = ref + timedelta(days=days_to_friday)
            temporals.append(
                NormalizedTemporal(
                    text="end of the week",
                    normalized_date=norm_dt,
                    segment_id=segment_id,
                )
            )

        return temporals
