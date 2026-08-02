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
    characters: tuple[Character, ...] = Field(min_length=1)
    facts: tuple[Fact, ...] = Field(min_length=1)
    evidence: tuple[Evidence, ...] = Field(min_length=1)
    timeline: tuple[TimelineEvent, ...] = Field(min_length=1)
    behavior_rules: tuple[BehaviorRule, ...] = ()
    hints: tuple[Hint, ...] = ()
    solution: SolutionRubric

    @model_validator(mode="after")
    def validate_ids_and_references(self) -> Self:
        location_ids = self._unique_ids("locations", self.locations)
        character_ids = self._unique_ids("characters", self.characters)
        fact_ids = self._unique_ids("facts", self.facts)
        evidence_ids = self._unique_ids("evidence", self.evidence)
        event_ids = self._unique_ids("timeline", self.timeline)
        self._unique_ids("behavior_rules", self.behavior_rules)
        self._unique_ids("hints", self.hints)
        self._unique_ids("solution.criteria", self.solution.criteria)

        for character in self.characters:
            for grant in character.knowledge_grants:
                if isinstance(grant, FactKnowledgeGrant):
                    self._require_reference(
                        source=f"character '{character.id}' knowledge grant",
                        field="fact_id",
                        value=grant.fact_id,
                        valid_ids=fact_ids,
                    )
                elif isinstance(grant, EvidenceKnowledgeGrant):
                    self._require_reference(
                        source=f"character '{character.id}' knowledge grant",
                        field="evidence_id",
                        value=grant.evidence_id,
                        valid_ids=evidence_ids,
                    )
                else:
                    self._require_reference(
                        source=f"character '{character.id}' knowledge grant",
                        field="event_id",
                        value=grant.event_id,
                        valid_ids=event_ids,
                    )

        for event in self.timeline:
            self._require_reference(
                source=f"timeline event '{event.id}'",
                field="location_id",
                value=event.location_id,
                valid_ids=location_ids,
            )

            for actor_id in event.actor_ids:
                self._require_reference(
                    source=f"timeline event '{event.id}'",
                    field="actor_ids",
                    value=actor_id,
                    valid_ids=character_ids,
                )

        for item in self.evidence:
            self._require_reference(
                source=f"evidence '{item.id}'",
                field="location_id",
                value=item.location_id,
                valid_ids=location_ids,
            )

            self._require_references(
                source=f"evidence '{item.id}'",
                field="reveals_fact_ids",
                values=item.reveals_fact_ids,
                valid_ids=fact_ids,
            )

            self._require_references(
                source=f"evidence '{item.id}'",
                field="unlocks_evidence_ids",
                values=item.unlocks_evidence_ids,
                valid_ids=evidence_ids,
            )

            if item.id in item.unlocks_evidence_ids:
                raise ValueError(f"evidence '{item.id}' cannot unlock itself")

        for rule in self.behavior_rules:
            self._require_reference(
                source=f"behavior rule '{rule.id}'",
                field="character_id",
                value=rule.character_id,
                valid_ids=character_ids,
            )

            self._require_references(
                source=f"behavior rule '{rule.id}'",
                field="reveal_fact_ids",
                values=rule.reveal_fact_ids,
                valid_ids=fact_ids,
            )

            if isinstance(rule.condition, FactKnownCondition):
                self._require_reference(
                    source=f"behavior rule '{rule.id}' condition",
                    field="fact_id",
                    value=rule.condition.fact_id,
                    valid_ids=fact_ids,
                )
            elif isinstance(rule.condition, EvidencePresentedCondition):
                self._require_reference(
                    source=f"behavior rule '{rule.id}' condition",
                    field="evidence_id",
                    value=rule.condition.evidence_id,
                    valid_ids=evidence_ids,
                )
            elif isinstance(rule.condition, ContradictionFoundCondition):
                self._require_reference(
                    source=f"behavior rule '{rule.id}' condition",
                    field="fact_id",
                    value=rule.condition.fact_id,
                    valid_ids=fact_ids,
                )

        for hint in self.hints:
            self._require_references(
                source=f"hint '{hint.id}'",
                field="requires_fact_ids",
                values=hint.requires_fact_ids,
                valid_ids=fact_ids,
            )

            self._require_references(
                source=f"hint '{hint.id}'",
                field="points_to_evidence_ids",
                values=hint.points_to_evidence_ids,
                valid_ids=evidence_ids,
            )

        self._require_reference(
            source="solution rubric",
            field="culprit_character_id",
            value=self.solution.culprit_character_id,
            valid_ids=character_ids,
        )

        for criterion in self.solution.criteria:
            self._require_references(
                source=f"solution criterion '{criterion.id}'",
                field="supporting_evidence_ids",
                values=criterion.supporting_evidence_ids,
                valid_ids=evidence_ids,
            )

        return self

    @staticmethod
    def _unique_ids(collection_name: str, items: tuple[object, ...]) -> set[str]:
        seen: set[str] = set()

        for item in items:
            item_id = getattr(item, "id")

            if item_id in seen:
                raise ValueError(
                    f"duplicate id '{item_id}' in collection '{collection_name}'"
                )

            seen.add(item_id)

        return seen

    @staticmethod
    def _require_reference(
        *,
        source: str,
        field: str,
        value: str,
        valid_ids: set[str],
    ) -> None:
        if value not in valid_ids:
            raise ValueError(
                f"{source} has unknown {field} reference '{value}'"
            )

    @classmethod
    def _require_references(
        cls,
        *,
        source: str,
        field: str,
        values: tuple[str, ...],
        valid_ids: set[str],
    ) -> None:
        for value in values:
            cls._require_reference(
                source=source,
                field=field,
                value=value,
                valid_ids=valid_ids,
            )


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