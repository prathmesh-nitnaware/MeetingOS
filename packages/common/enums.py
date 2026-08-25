from enum import StrEnum


class SourceType(StrEnum):
    AUDIO_WAV = "audio/wav"
    AUDIO_MP3 = "audio/mp3"
    AUDIO_M4A = "audio/m4a"
    VIDEO_MP4 = "video/mp4"
    TEXT_TRANSCRIPT = "text/plain"
    SRT_SUBTITLE = "application/x-subrip"
    SYNTHETIC = "synthetic/cmf"


class ProcessingStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class EntityType(StrEnum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    PROJECT = "PROJECT"
    TECHNOLOGY = "TECHNOLOGY"
    DATE = "DATE"
    LOCATION = "LOCATION"
    PRODUCT = "PRODUCT"


class UtteranceClass(StrEnum):
    DECISION = "Decision"
    ACTION = "Action"
    COMMITMENT = "Commitment"
    QUESTION = "Question"
    SUGGESTION = "Suggestion"
    PROBLEM = "Problem"
    INFORMATION = "Information"


class RelationType(StrEnum):
    ASSIGNED_TO = "ASSIGNED_TO"
    WORKS_ON = "WORKS_ON"
    OWNS = "OWNS"
    DECIDED_IN = "DECIDED_IN"
    RELATED_TO = "RELATED_TO"
    REPLACES = "REPLACES"
    HAS_DEADLINE = "HAS_DEADLINE"
    RESOLVES = "RESOLVES"


class EventType(StrEnum):
    DECISION_PROPOSED = "DECISION_PROPOSED"
    DECISION_APPROVED = "DECISION_APPROVED"
    DECISION_MODIFIED = "DECISION_MODIFIED"
    DECISION_REVERSED = "DECISION_REVERSED"
    DEADLINE_CHANGED = "DEADLINE_CHANGED"
    ISSUE_DETECTED = "ISSUE_DETECTED"
    ISSUE_RECURRING = "ISSUE_RECURRING"
    ISSUE_RESOLVED = "ISSUE_RESOLVED"
    COMMITMENT_ASSIGNED = "COMMITMENT_ASSIGNED"
    COMMITMENT_COMPLETED = "COMMITMENT_COMPLETED"
    COMMITMENT_OVERDUE = "COMMITMENT_OVERDUE"
    COMMITMENT_REASSIGNED = "COMMITMENT_REASSIGNED"
    TECHNOLOGY_REPLACED = "TECHNOLOGY_REPLACED"
    PROJECT_LAUNCHED = "PROJECT_LAUNCHED"


class DecisionStatus(StrEnum):
    PROPOSED = "Proposed"
    DISCUSSION = "Discussion"
    APPROVED = "Approved"
    IMPLEMENTED = "Implemented"
    MODIFIED = "Modified"
    REVERSED = "Reversed"


class CommitmentStatus(StrEnum):
    IDENTIFIED = "Identified"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    OVERDUE = "Overdue"
    REASSIGNED = "Reassigned"


class IssueStatus(StrEnum):
    DETECTED = "Detected"
    ASSIGNED = "Assigned"
    UNDER_INVESTIGATION = "Under Investigation"
    RESOLVED = "Resolved"
    RECURRING = "Recurring"
    UNRESOLVED = "Unresolved"
