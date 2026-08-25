from datetime import datetime

from pydantic import BaseModel, Field


class ConnectorParticipant(BaseModel):
    id: str
    name: str
    email: str | None = None


class ConnectorTranscriptSegment(BaseModel):
    speaker_id: str
    start_time: float
    end_time: float
    text: str


class ConnectorMeeting(BaseModel):
    external_id: str
    title: str
    meeting_date: datetime
    duration_seconds: float | None = None
    participants: list[ConnectorParticipant] = Field(default_factory=list)
    segments: list[ConnectorTranscriptSegment] = Field(default_factory=list)


class ConnectorConfig(BaseModel):
    provider: str
    enabled: bool = False
    client_id: str | None = None
    client_secret: str | None = None
    tenant_id: str | None = None
    account_id: str | None = None


class ConnectorSyncResult(BaseModel):
    provider: str
    sync_triggered_at: datetime
    discovered_count: int = 0
    ingested_count: int = 0
    skipped_count: int = 0
    errors: list[str] = Field(default_factory=list)
