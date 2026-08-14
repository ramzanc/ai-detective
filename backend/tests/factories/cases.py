from __future__ import annotations

from datetime import datetime, timezone

from app.domain.case_models import (
    AlwaysCondition,
    BehaviorRule,
    CaseManifest,
    CaseManifestMetadata,
    Character,
    Evidence,
    EvidenceKnowledgeGrant,
    Fact,
    FactKnowledgeGrant,
    Hint,
    Location,
    RubricCriterion,
    SolutionRubric,
    TimeRange,
    TimelineEvent,
    TravelConstraint,
)
from app.domain.types import (
    BehaviorStrategy,
    CharacterRole,
    EvidenceKind,
    HintTier,
    SupportCategory,
    Visibility,
)


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(
        2026,
        8,
        1,
        hour,
        minute,
        tzinfo=timezone.utc,
    )


def make_valid_case() -> CaseManifest:
    return CaseManifest(
        metadata=CaseManifestMetadata(
            case_id="ashcroft_manor",
            version="1.0.0",
            title="The Ashcroft Manor Mystery",
            summary="A silver watch disappears during a private gathering.",
            author="AI Detective Team",
            published_at=dt(12),
        ),
        locations=(
            Location(
                id="study",
                name="Study",
                description="Victor Ashcroft's private study.",
                visibility=Visibility.PUBLIC,
            ),
            Location(
                id="front_door",
                name="Front Door",
                description="The manor's monitored main entrance.",
                visibility=Visibility.DISCOVERABLE,
            ),
            Location(
                id="garage",
                name="Garage",
                description="A detached garage behind the manor.",
                visibility=Visibility.DISCOVERABLE,
            ),
        ),
        travel_constraints=(
            TravelConstraint(
                from_location_id="study",
                to_location_id="front_door",
                minimum_minutes=3,
            ),
            TravelConstraint(
                from_location_id="front_door",
                to_location_id="garage",
                minimum_minutes=5,
            ),
        ),
        characters=(
            Character(
                id="maya",
                name="Maya Rao",
                role=CharacterRole.SUSPECT,
                public_description="A guest at the private gathering.",
                private_motivation="She wants to conceal her early departure.",
                knowledge_grants=(
                    FactKnowledgeGrant(
                        fact_id="maya_left_early",
                    ),
                    EvidenceKnowledgeGrant(
                        evidence_id="door_log",
                    ),
                ),
            ),
            Character(
                id="victor",
                name="Victor Ashcroft",
                role=CharacterRole.VICTIM,
                public_description="The owner of the missing watch.",
                private_motivation="He wants the watch recovered quietly.",
            ),
        ),
        facts=(
            Fact(
                id="watch_missing",
                statement="Victor's silver watch is missing.",
                visibility=Visibility.PUBLIC,
            ),
            Fact(
                id="maya_left_early",
                statement="Maya left earlier than she claimed.",
                visibility=Visibility.HIDDEN,
            ),
            Fact(
                id="maya_had_access",
                statement="Maya had access to the study.",
                visibility=Visibility.HIDDEN,
            ),
        ),
        evidence=(
            Evidence(
                id="silver_watch",
                name="Silver Watch",
                description="Victor's engraved silver watch.",
                kind=EvidenceKind.PHYSICAL,
                visibility=Visibility.DISCOVERABLE,
                location_id="study",
                reveals_fact_ids=("watch_missing",),
            ),
            Evidence(
                id="door_log",
                name="Electronic Door Log",
                description="A timestamped record of manor exits.",
                kind=EvidenceKind.DIGITAL,
                visibility=Visibility.DISCOVERABLE,
                location_id="front_door",
                reveals_fact_ids=("maya_left_early",),
            ),
            Evidence(
                id="study_key_log",
                name="Study Key Log",
                description="A record showing who borrowed the study key.",
                kind=EvidenceKind.DOCUMENT,
                visibility=Visibility.DISCOVERABLE,
                location_id="study",
                reveals_fact_ids=("maya_had_access",),
            ),
        ),
        timeline=(
            TimelineEvent(
                id="maya_in_study",
                title="Maya enters the study",
                description="Maya enters the study shortly before dinner.",
                time_range=TimeRange(
                    start=dt(19),
                    end=dt(19, 10),
                ),
                actor_ids=("maya",),
                location_id="study",
                visibility=Visibility.HIDDEN,
            ),
            TimelineEvent(
                id="maya_departure",
                title="Maya leaves the manor",
                description="Maya exits through the front door.",
                time_range=TimeRange(
                    start=dt(19, 15),
                    end=dt(19, 20),
                ),
                actor_ids=("maya",),
                location_id="front_door",
                visibility=Visibility.HIDDEN,
            ),
        ),
        behavior_rules=(
            BehaviorRule(
                id="maya_default",
                character_id="maya",
                priority=100,
                condition=AlwaysCondition(),
                strategy=BehaviorStrategy.EVADE,
            ),
        ),
        hints=(
            Hint(
                id="check_departure",
                tier=HintTier.NUDGE,
                text="Check whether everyone left when they claimed.",
                requires_fact_ids=("watch_missing",),
                points_to_evidence_ids=("door_log",),
            ),
        ),
        solution=SolutionRubric(
            culprit_character_id="maya",
            explanation=(
                "Maya had access to the study, and the door log "
                "contradicts her claimed departure time."
            ),
            criteria=(
                RubricCriterion(
                    id="establish_item",
                    category=SupportCategory.IDENTITY,
                    description="Identify the missing watch.",
                    supporting_evidence_ids=("silver_watch",),
                    weight=1,
                ),
                RubricCriterion(
                    id="establish_opportunity",
                    category=SupportCategory.OPPORTUNITY,
                    description="Establish Maya's access to the study.",
                    supporting_evidence_ids=("study_key_log",),
                    weight=1,
                ),
                RubricCriterion(
                    id="establish_contradiction",
                    category=SupportCategory.CONTRADICTION,
                    description="Identify Maya's false departure claim.",
                    supporting_evidence_ids=("door_log",),
                    weight=2,
                ),
            ),
            minimum_score=3,
        ),
    )
