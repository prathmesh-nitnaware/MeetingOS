from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from apps.api.auth import UserIdentity, require_member
from apps.api.config import settings
from fastapi import APIRouter, Depends
from packages.common.enums import ProcessingStatus, SourceType
from packages.common.models import Meeting, MeetingMetadata, Participant
from packages.memory.database import get_db_session
from packages.memory.repository import MeetingRepository
from packages.nlp.text_analyzer import analyze_text_intelligence, parse_text_to_segments

router = APIRouter(prefix="/demo", tags=["Demo"])

SAMPLE_MEETINGS = [
    {
        "title": "Product Launch Kickoff",
        "date_offset_days": -14,
        "content_type": "transcript",
        "content": """Alex: Welcome everyone. We need to finalize the product launch strategy and release plan for our Q4 release.
Sarah: The product is in great shape from the design side. We still need to finish the onboarding flow and user guide.
David: Engineering can complete the onboarding implementation by Thursday. We also need to run automated load tests before release.
Maya: I'll prepare the marketing announcements and press release draft by Wednesday. Let's target Friday for the internal staging release.
Alex: Agreed. We will use Friday as our internal release target. Let's make sure all critical bug fixes are merged before Thursday 5 PM.
David: I will coordinate the deployment pipeline and make sure the staging environment is provisioned.""",
        "participants": ["Alex Rivera", "Sarah Chen", "David Kim", "Maya Patel"],
    },
    {
        "title": "Engineering Architecture Planning",
        "date_offset_days": -10,
        "content_type": "transcript",
        "content": """David: Today's focus is finalizing our authentication architecture and API rate limiting before release.
Bob: I can handle the authentication module refactoring and JWT token rotation. It will be ready for code review by Tuesday.
Alice: We need to ensure the database connection pooling handles up to 500 concurrent connections.
David: Agreed. Alice, please verify the PostgreSQL connection pooling configuration and write migration verification scripts.
Alice: I will run stress tests on database migration scripts and document fallback rollback steps by Wednesday.
David: Decision: We will enforce API rate limiting of 100 requests per minute per user on public endpoints.""",
        "participants": ["David Kim", "Bob Vance", "Alice Smith"],
    },
    {
        "title": "Design & UX Review",
        "date_offset_days": -7,
        "content_type": "notes",
        "content": """- Reviewed design prototypes for the new text-first meeting workspace and dashboard.
- Sarah Chen presented the high-density information architecture with executive summaries and action items.
- Agreed to use clean typography with high-contrast text and subtle badges rather than heavy decorative graphics.
- Sarah Chen will deliver finalized icon assets and empty state illustrations by Thursday.
- Maya Patel will review user onboarding copy for clarity.
- Decision: Adopt the streamlined 3-step meeting creation workflow (Details -> Content -> AI Analysis).""",
        "participants": ["Sarah Chen", "Maya Patel", "Alex Rivera"],
    },
    {
        "title": "Launch Readiness Review",
        "date_offset_days": -3,
        "content_type": "transcript",
        "content": """Alex: Let's review the go/no-go checklist for our upcoming production release.
David: Engineering load tests passed with zero errors at 1,000 req/sec. Onboarding flows are fully verified in staging.
Sarah: Design QA signed off on all responsive viewports across desktop, tablet, and mobile.
Maya: Documentation and release blog post are scheduled for publication.
Alex: All criteria met. Decision: Proceed with production launch on Friday at 9 AM UTC.
David: I will monitor the deployment health and latency dashboards during the launch window.
Alex: I will notify stakeholders once the deployment is verified in production.""",
        "participants": ["Alex Rivera", "David Kim", "Sarah Chen", "Maya Patel"],
    },
    {
        "title": "Post-Launch Performance Review",
        "date_offset_days": -1,
        "content_type": "transcript",
        "content": """Alex: The launch went smoothly with 99.99% uptime over the first 48 hours.
David: API response times averaged 42ms with zero 500 error spikes reported.
Maya: User feedback has been positive, especially around instant meeting summaries and action item tracking.
Sarah: We received requests for a global keyboard search shortcut.
Alex: Decision: Schedule keyboard search shortcut (Cmd+K) and cross-meeting knowledge discovery for the next sprint.
David: I will start work on the global search indexing pipeline.""",
        "participants": ["Alex Rivera", "David Kim", "Sarah Chen", "Maya Patel"],
    }
]


@router.post("/seed", response_model=dict[str, Any])
async def seed_demo_meetings(
    user: UserIdentity = Depends(require_member),
) -> dict[str, Any]:
    """Seed realistic business demo meetings with structured intelligence into the current organization."""
    now = datetime.now(UTC)
    created_meetings: list[str] = []

    async with get_db_session(settings.database_url) as session:
        repo = MeetingRepository(session)

        # 1. Create or ensure Product Launch project
        existing_projects = await repo.list_projects(org_id=user.org_id)
        prod_launch_proj = next((p for p in existing_projects if "Product Launch" in p["name"]), None)
        if not prod_launch_proj:
            new_proj = await repo.create_project(
                name="Product Launch",
                description="Coordinate cross-functional preparation, beta testing, engineering readiness, and release for Q4.",
                color="#4f46e5",
                status="active",
                org_id=user.org_id,
            )
            project_id = new_proj.id
        else:
            project_id = prod_launch_proj["id"]

        for m_data in SAMPLE_MEETINGS:
            m_id = f"meet-{uuid4()}"
            m_date = now + timedelta(days=m_data["date_offset_days"])
            participants = [Participant(canonical_name=p) for p in m_data["participants"]]

            # Analyze intelligence with zero-hallucination validation and evidence spans
            analysis = analyze_text_intelligence(
                title=m_data["title"],
                content=m_data["content"],
                meeting_date=m_date,
                existing_participants=participants,
                meeting_id=m_id,
            )

            segments, speakers = parse_text_to_segments(m_data["content"], content_type=m_data["content_type"])

            meeting = Meeting(
                meeting_id=m_id,
                title=m_data["title"],
                meeting_date=m_date,
                source_type=SourceType.TEXT_TRANSCRIPT,
                processing_status=ProcessingStatus.SUCCEEDED,
                content_type=m_data["content_type"],
                content=m_data["content"],
                summary=analysis.summary,
                key_points=analysis.key_points,
                project_id=project_id,
                participants=analysis.participants,
                speakers=speakers,
                segments=segments,
                metadata=MeetingMetadata(
                    content_type=m_data["content_type"],
                    project_id=project_id,
                ),
            )

            await repo.create_meeting(meeting, org_id=user.org_id)

            # Persist facts with source spans and review statuses
            from packages.nlp.pipeline import NLPExtractionResult
            nlp_res = NLPExtractionResult(
                meeting_id=m_id,
                topics=analysis.topics,
                decisions=analysis.decisions,
                commitments=analysis.action_items,
                actions=analysis.action_items,
            )
            await repo.save_nlp_extraction_results(m_id, nlp_res)
            created_meetings.append(m_id)

        await session.commit()

    return {
        "status": "succeeded",
        "message": f"Successfully seeded {len(created_meetings)} realistic demo meetings linked to Product Launch organizational memory.",
        "project_id": project_id,
        "meeting_ids": created_meetings,
    }
