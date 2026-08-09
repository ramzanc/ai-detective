from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, TypeAdapter, field_validator, model_validator

from app.domain.types import (
    BehaviorCondition,
    BehaviorRuleID,
    BehaviorStrategy,
    CaseID,
    CharacterID,
    CharacterRole,
    EventID,
    EvidenceID,
    EvidenceKind,
    FactID,
    HintID,
    HintTier,
    LocationID,
    RubricCriterionID,
    StrictFrozenModel,
    SupportCategory,
    Visibility,
)


class TimeRange(StrictFrozenModel):
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("time range start and end must include timezones")

        if self.end <= self.start:
            raise ValueError("time range end must be later than start")

        return self


class CaseManifestMetadata(StrictFrozenModel):
    case_id: CaseID
    version: str = Field(
        min_length=1,
        max_length=50,
        pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$",
    )
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=1_000)
    author: str = Field(min_length=1, max_length=200)
    published_at: datetime

    @field_validator("published_at")
    @classmethod
    def published_at_must_have_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("published_at must include a timezone")
        return value


class Location(StrictFrozenModel):
    id: LocationID
    name: str = Field(min_length=1, max_length=150)
    description: str = Field(min_length=1, max_length=2_000)
    visibility: Visibility = Visibility.DISCOVERABLE

class TravelConstraint(StrictFrozenModel):
    from_location_id: LocationID
    to_location_id: LocationID
    minimum_minutes: int = Field(ge=0, le=1_440)


class Fact(StrictFrozenModel):
    id: FactID
    statement: str = Field(min_length=1, max_length=2_000)
    visibility: Visibility = Visibility.HIDDEN


class FactKnowledgeGrant(StrictFrozenModel):
    kind: Literal["fact"] = "fact"
    fact_id: FactID


class EvidenceKnowledgeGrant(StrictFrozenModel):
    kind: Literal["evidence"] = "evidence"
    evidence_id: EvidenceID


class EventKnowledgeGrant(StrictFrozenModel):
    kind: Literal["timeline_event"] = "timeline_event"
    event_id: EventID


KnowledgeGrant = Annotated[
    FactKnowledgeGrant | EvidenceKnowledgeGrant | EventKnowledgeGrant,
    Field(discriminator="kind"),
]


class Character(StrictFrozenModel):
    id: CharacterID
    name: str = Field(min_length=1, max_length=150)
    role: CharacterRole
    public_description: str = Field(min_length=1, max_length=2_000)
    private_motivation: str = Field(min_length=1, max_length=2_000)
    knowledge_grants: tuple[KnowledgeGrant, ...] = ()


class TimelineEvent(StrictFrozenModel):
    id: EventID
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2_000)
    time_range: TimeRange
    actor_ids: tuple[CharacterID, ...] = ()
    location_id: LocationID
    visibility: Visibility = Visibility.HIDDEN


class Evidence(StrictFrozenModel):
    id: EvidenceID
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2_000)
    kind: EvidenceKind
    visibility: Visibility = Visibility.DISCOVERABLE
    location_id: LocationID
    available_during: TimeRange | None = None
    reveals_fact_ids: tuple[FactID, ...] = ()
    unlocks_evidence_ids: tuple[EvidenceID, ...] = ()


class AlwaysCondition(StrictFrozenModel):
    kind: Literal[BehaviorCondition.ALWAYS] = BehaviorCondition.ALWAYS


class FactKnownCondition(StrictFrozenModel):
    kind: Literal[BehaviorCondition.FACT_KNOWN] = BehaviorCondition.FACT_KNOWN
    fact_id: FactID


class EvidencePresentedCondition(StrictFrozenModel):
    kind: Literal[
        BehaviorCondition.EVIDENCE_PRESENTED
    ] = BehaviorCondition.EVIDENCE_PRESENTED
    evidence_id: EvidenceID


class ContradictionFoundCondition(StrictFrozenModel):
    kind: Literal[
        BehaviorCondition.CONTRADICTION_FOUND
    ] = BehaviorCondition.CONTRADICTION_FOUND
    fact_id: FactID


RuleCondition = Annotated[
    AlwaysCondition
    | FactKnownCondition
    | EvidencePresentedCondition
    | ContradictionFoundCondition,
    Field(discriminator="kind"),
]


class BehaviorRule(StrictFrozenModel):
    id: BehaviorRuleID
    character_id: CharacterID
    priority: int = Field(ge=0, le=10_000)
    condition: RuleCondition
    strategy: BehaviorStrategy
    reveal_fact_ids: tuple[FactID, ...] = ()


class Hint(StrictFrozenModel):
    id: HintID
    tier: HintTier
    text: str = Field(min_length=1, max_length=1_000)
    requires_fact_ids: tuple[FactID, ...] = ()
    points_to_evidence_ids: tuple[EvidenceID, ...] = ()


class RubricCriterion(StrictFrozenModel):
    id: RubricCriterionID
    category: SupportCategory
    description: str = Field(min_length=1, max_length=1_000)
    supporting_evidence_ids: tuple[EvidenceID, ...] = Field(min_length=1)
    weight: int = Field(default=1, ge=1, le=100)


class SolutionRubric(StrictFrozenModel):
    culprit_character_id: CharacterID
    explanation: str = Field(min_length=1, max_length=4_000)
    criteria: tuple[RubricCriterion, ...] = Field(min_length=1)
    minimum_score: int = Field(ge=1)

    @model_validator(mode="after")
    def minimum_score_must_be_reachable(self) -> Self:
        maximum_score = sum(criterion.weight for criterion in self.criteria)

        if self.minimum_score > maximum_score:
            raise ValueError(
                "solution rubric minimum_score cannot exceed total criterion weight"
            )

        return self


class CaseManifest(StrictFrozenModel):
    metadata: CaseManifestMetadata
    locations: tuple[Location, ...] = Field(min_length=1)
    travel_constraints: tuple[TravelConstraint, ...] = ()
    characters: tuple[Character, ...] = Field(min_length=1)
    facts: tuple[Fact, ...] = Field(min_length=1)
    evidence: tuple[Evidence, ...] = Field(min_length=1)
    timeline: tuple[TimelineEvent, ...] = Field(min_length=1)
    behavior_rules: tuple[BehaviorRule, ...] = ()
    hints: tuple[Hint, ...] = ()
    solution: SolutionRubric


def case_to_json(case: CaseManifest) -> str:
    """
    Serialize a validated case using deterministic key ordering.

    Compact separators ensure that the same case produces the same textual
    representation, making hashing and version comparison possible later.
    """

    return json.dumps(
        case.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def case_from_json(payload: str | bytes | bytearray) -> CaseManifest:
    """Validate and deserialize a JSON case package."""

    return CaseManifest.model_validate_json(payload)


def case_json_schema() -> dict[str, object]:
    """Return JSON Schema for case-authoring tools and documentation."""

    return TypeAdapter(CaseManifest).json_schema()


def case_json_schema_text() -> str:
    """Return the JSON Schema using deterministic formatting."""

    return json.dumps(
        case_json_schema(),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )


def export_case_json_schema(destination: str | Path) -> None:
    """
    Write the authoring schema to disk.

    This helper is optional for Day 2, but prepares for a future authoring UI.
    """

    Path(destination).write_text(
        case_json_schema_text() + "\n",
        encoding="utf-8",
    )