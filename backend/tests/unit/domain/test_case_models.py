from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

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
    case_from_json,
    case_json_schema,
    case_to_json,
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
            summary="A valuable watch disappears during a private gathering.",
            author="AI Detective Team",
            published_at=dt(12),
        ),
        locations=(
            Location(
                id="study",
                name="Study",
                description="Lord Ashcroft's private study.",
                visibility=Visibility.PUBLIC,
            ),
            Location(
                id="front_door",
                name="Front Door",
                description="The manor's monitored main entrance.",
                visibility=Visibility.DISCOVERABLE,
            ),
        ),
        characters=(
            Character(
                id="maya",
                name="Maya Rao",
                role=CharacterRole.SUSPECT,
                public_description="A guest attending the private gathering.",
                private_motivation="She wants to conceal why she left early.",
                knowledge_grants=(
                    FactKnowledgeGrant(fact_id="maya_left_early"),
                    EvidenceKnowledgeGrant(evidence_id="door_log"),
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
                statement="Maya left the manor before she claimed she did.",
                visibility=Visibility.HIDDEN,
            ),
        ),
        evidence=(
            Evidence(
                id="silver_watch",
                name="Silver Watch",
                description="Victor's valuable engraved watch.",
                kind=EvidenceKind.PHYSICAL,
                visibility=Visibility.DISCOVERABLE,
                location_id="study",
                reveals_fact_ids=("watch_missing",),
            ),
            Evidence(
                id="door_log",
                name="Electronic Door Log",
                description="A timestamped record of entries and exits.",
                kind=EvidenceKind.DIGITAL,
                visibility=Visibility.DISCOVERABLE,
                location_id="front_door",
                available_during=TimeRange(
                    start=dt(18),
                    end=dt(23),
                ),
                reveals_fact_ids=("maya_left_early",),
            ),
        ),
        timeline=(
            TimelineEvent(
                id="maya_departure",
                title="Maya leaves the manor",
                description="Maya exits through the monitored front door.",
                time_range=TimeRange(
                    start=dt(20, 10),
                    end=dt(20, 15),
                ),
                actor_ids=("maya",),
                location_id="front_door",
                visibility=Visibility.HIDDEN,
            ),
        ),
        behavior_rules=(
            BehaviorRule(
                id="maya_default_response",
                character_id="maya",
                priority=100,
                condition=AlwaysCondition(),
                strategy=BehaviorStrategy.EVADE,
                reveal_fact_ids=(),
            ),
        ),
        hints=(
            Hint(
                id="check_departure_time",
                tier=HintTier.NUDGE,
                text="Check whether everyone left when they claimed.",
                requires_fact_ids=("watch_missing",),
                points_to_evidence_ids=("door_log",),
            ),
        ),
        solution=SolutionRubric(
            culprit_character_id="maya",
            explanation=(
                "The door log contradicts Maya's stated departure time and "
                "connects her opportunity to the missing watch."
            ),
            criteria=(
                RubricCriterion(
                    id="departure_contradiction",
                    category=SupportCategory.CONTRADICTION,
                    description="Identify the contradiction in Maya's timeline.",
                    supporting_evidence_ids=("door_log",),
                    weight=2,
                ),
                RubricCriterion(
                    id="physical_item",
                    category=SupportCategory.IDENTITY,
                    description="Correctly identify the missing item.",
                    supporting_evidence_ids=("silver_watch",),
                    weight=1,
                ),
            ),
            minimum_score=2,
        ),
    )


def valid_case_data() -> dict:
    return make_valid_case().model_dump(mode="json")


def test_valid_case_round_trips_through_json() -> None:
    original = make_valid_case()

    serialized = case_to_json(original)
    restored = case_from_json(serialized)

    assert restored == original
    assert case_to_json(restored) == serialized


def test_serialization_is_deterministic() -> None:
    case = make_valid_case()

    first = case_to_json(case)
    second = case_to_json(case)

    assert first == second
    assert first == json.dumps(
        case.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def test_published_case_is_immutable() -> None:
    case = make_valid_case()

    with pytest.raises(ValidationError):
        case.metadata.title = "Changed title"


def test_unknown_fields_are_rejected() -> None:
    data = valid_case_data()
    data["characters"][0]["secret_debug_field"] = "must not be accepted"

    with pytest.raises(ValidationError) as error:
        CaseManifest.model_validate(data)

    assert "Extra inputs are not permitted" in str(error.value)
    assert "secret_debug_field" in str(error.value)


def test_unknown_enum_value_is_rejected() -> None:
    data = valid_case_data()
    data["evidence"][0]["kind"] = "magical"

    with pytest.raises(ValidationError) as error:
        CaseManifest.model_validate(data)

    assert "magical" in str(error.value)


def test_invalid_time_range_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        TimeRange(
            start=dt(21),
            end=dt(20),
        )

    assert "end must be later than start" in str(error.value)


def test_naive_time_range_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        TimeRange(
            start=datetime(2026, 8, 1, 20, 0),
            end=datetime(2026, 8, 1, 21, 0),
        )

    assert "must include timezones" in str(error.value)


def test_discriminated_union_rejects_wrong_knowledge_shape() -> None:
    data = valid_case_data()
    data["characters"][0]["knowledge_grants"][0] = {
        "kind": "fact",
        "event_id": "maya_departure",
    }

    with pytest.raises(ValidationError) as error:
        CaseManifest.model_validate(data)

    message = str(error.value)

    assert "fact_id" in message
    assert "event_id" in message


def test_solution_minimum_score_must_be_reachable() -> None:
    data = valid_case_data()
    data["solution"]["minimum_score"] = 100

    with pytest.raises(ValidationError) as error:
        CaseManifest.model_validate(data)

    assert "minimum_score cannot exceed total criterion weight" in str(error.value)


def test_json_schema_can_be_generated() -> None:
    schema = case_json_schema()

    assert schema["title"] == "CaseManifest"
    assert "metadata" in schema["properties"]
    assert "characters" in schema["properties"]
    assert "evidence" in schema["properties"]
    assert "solution" in schema["properties"]


def test_case_contains_no_player_session_state() -> None:
    schema_text = json.dumps(case_json_schema()).lower()

    forbidden_runtime_fields = (
        "session_id",
        "player_id",
        "discovered_evidence",
        "interview_history",
        "player_notes",
        "accusation_status",
    )

    for field in forbidden_runtime_fields:
        assert field not in schema_text
