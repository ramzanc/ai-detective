from __future__ import annotations

from collections import defaultdict, deque
from datetime import timedelta
from enum import StrEnum
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from app.domain.case_models import (
    AlwaysCondition,
    CaseManifest,
    ContradictionFoundCondition,
    EvidencePresentedCondition,
    FactKnownCondition
)

from app.domain.types import Visibility

class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"

class ValidationCode(StrEnum):
    DUPLICATE_ID = "duplicate_id"
    UNKNOWN_REFERENCE = "unknown_reference"

    TIMELINE_NOT_ORDERED = "timeline_not_ordered"
    ACTOR_EVENT_OVERLAP = "actor_event_overlap"
    TRAVEL_TIME_VIOLATION = "travel_time_violation"

    EVIDENCE_UNLOCKS_ITSELF = "evidence_unlocks_itself"
    UNLOCK_CYCLE = "unlock_cycle"
    REQUIRED_EVIDENCE_UNREACHABLE = "required_evidence_unreachable"

    RUBRIC_INSUFFICIENT_CATEGORIES = "rubric_insufficient_categories"
    RUBRIC_EVIDENCE_NOT_DISCOVERABLE = "rubric_evidence_not_discoverable"

class ValidationIssue(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    code: ValidationCode
    severity: ValidationSeverity
    path: str = Field(min_length=1)
    message: str = Field(min_length=1)

class ValidationReport(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    issues: tuple[ValidationIssue, ...]

    @property
    def is_publishable(self) -> bool:
        return not any(
            issue.severity == ValidationSeverity.ERROR
            for issue in self.issues
        )

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.severity == ValidationSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(
            issue
            for issue in self.issues
            if issue.severity == ValidationSeverity.WARNING
        )

    def has_code(self, code: ValidationCode) -> bool:
        return any(issue.code == code for issue in self.issues)


class CaseValidator:
    """
    Performs deterministic, cross-object validation of a case package.

    Validation methods never mutate the CaseManifest. Every validation pass
    produces issues in a stable order.
    """

    def validate(self, case: CaseManifest) -> ValidationReport:
        issues: list[ValidationIssue] = []

        self._validate_unique_ids(case, issues)
        self._validate_references(case, issues)
        self._validate_timeline_order(case, issues)
        self._validate_actor_timelines(case, issues)
        self._validate_unlock_graph(case, issues)
        self._validate_solution_rubric(case, issues)

        return ValidationReport(
            issues=tuple(self._sort_issues(issues)),
        )

    @staticmethod
    def _add_issue(
        issues: list[ValidationIssue],
        *,
        code: ValidationCode,
        path: str,
        message: str,
        severity: ValidationSeverity = ValidationSeverity.ERROR
    ) -> None:
        issues.append(
            ValidationIssue(
                code=code,
                severity=severity,
                path=path,
                message=message
            )
        )

    def _validate_unique_ids(
        self,
        case: CaseManifest,
        issues: list[ValidationIssue]
    ) -> None:
        collections: tuple[tuple[str, tuple[object, ...]], ...] = (
            ("locations", case.locations),
            ("characters", case.characters),
            ("facts", case.facts),
            ("evidence", case.evidence),
            ("timeline", case.timeline),
            ("behavior_rules", case.behavior_rules),
            ("hints", case.hints),
            ("solution.criteria", case.solution.criteria)
        )

        for collection_path, items in collections:
            seen: dict[str, int] = {}

            for index, item in enumerate(items):
                item_id = str(getattr(item, "id"))

                if item_id in seen:
                    first_index = seen[item_id]

                    self._add_issue(
                        issues,
                        code=ValidationCode.DUPLICATE_ID,
                        path=f"$.{collection_path}[{index}].id",
                        message=(
                            f"ID '{item_id} duplicates "
                            f"$.{collection_path}[{first_index}].id"
                        )
                    )
                else:
                    seen[item_id] = index

    def _validate_references(
        self,
        case: CaseManifest,
        issues: list[ValidationIssue]
    ) -> None:
        location_ids = {location.id for location in case.locations}
        character_ids = {character.id for character in case.characters}
        fact_ids = {fact.id for fact in case.facts}
        evidence_ids = {evidence.id for evidence in case.evidence}
        event_ids = {event.id for event in case.timeline}

        # Validate travel constraints
        for index, constraint in enumerate(case.travel_constraints):
            self._require_reference(
                issues,
                value=constraint.from_location_id,
                valid_ids=location_ids,
                path=f"$.travel_constraints[{index}].from_location_id",
                target_type="location",
            )
            self._require_reference(
                issues,
                value=constraint.to_location_id,
                valid_ids=location_ids,
                path=f"$.travel_constraints[{index}].to_location_id",
                target_type="location",
            )

        # Validate character knowledge grants
        for character_index, character in enumerate(case.characters):
            for grant_index, grant in enumerate(character.knowledge_grants):
                grant_path = (
                    f"$.characters[{character_index}]"
                    f".knowledge_grants[{grant_index}]"
                )

                if grant.kind == "fact":
                    self._require_reference(
                        issues,
                        value=grant.fact_id,
                        valid_ids=fact_ids,
                        path=f"{grant_path}.fact_id",
                        target_type="fact",
                    )
                elif grant.kind == "evidence":
                    self._require_reference(
                        issues,
                        value=grant.evidence_id,
                        valid_ids=evidence_ids,
                        path=f"{grant_path}.evidence_id",
                        target_type="evidence",
                    )
                else:
                    self._require_reference(
                        issues,
                        value=grant.event_id,
                        valid_ids=event_ids,
                        path=f"{grant_path}.event_id",
                        target_type="timeline event",
                    )

        # Validate Timeline References
        for event_index, event in enumerate(case.timeline):
            self._require_reference(
                issues,
                value=event.location_id,
                valid_ids=location_ids,
                path=f"$.timeline[{event_index}].location_id",
                target_type="location",
            )

            for actor_index, actor_id in enumerate(event.actor_ids):
                self._require_reference(
                    issues,
                    value=actor_id,
                    valid_ids=character_ids,
                    path=f"$.timeline[{event_index}].actor_ids[{actor_index}]",
                    target_type="character",
                )

        # Validate Evidence References
        for evidence_index, evidence in enumerate(case.evidence):
            self._require_reference(
                issues,
                value=evidence.location_id,
                valid_ids=location_ids,
                path=f"$.evidence[{evidence_index}].location_id",
                target_type="location",
            )

            for fact_index, fact_id in enumerate(evidence.reveals_fact_ids):
                self._require_reference(
                    issues,
                    value=fact_id,
                    valid_ids=fact_ids,
                    path=f"$.evidence[{evidence_index}].reveals_fact_ids[{fact_index}]",
                    target_type="fact",
                )

            for unlocked_index, unlocked_id in enumerate(evidence.unlocks_evidence_ids):
                self._require_reference(
                    issues,
                    value=unlocked_id,
                    valid_ids=evidence_ids,
                    path=f"$.evidence[{evidence_index}].unlocks_evidence_ids[{unlocked_index}]",
                    target_type="evidence",
                )

        # Validate Behavior Rules & Conditions
        for rule_index, rule in enumerate(case.behavior_rules):
            self._require_reference(
                issues,
                value=rule.character_id,
                valid_ids=character_ids,
                path=f"$.behavior_rules[{rule_index}].character_id",
                target_type="character",
            )

            for fact_index, fact_id in enumerate(rule.reveal_fact_ids):
                self._require_reference(
                    issues,
                    value=fact_id,
                    valid_ids=fact_ids,
                    path=f"$.behavior_rules[{rule_index}].reveal_fact_ids[{fact_index}]",
                    target_type="fact",
                )

            condition = rule.condition
            condition_path = f"$.behavior_rules[{rule_index}].condition"

            if isinstance(condition, (FactKnownCondition, ContradictionFoundCondition)):
                self._require_reference(
                    issues,
                    value=condition.fact_id,
                    valid_ids=fact_ids,
                    path=f"{condition_path}.fact_id",
                    target_type="fact",
                )
            elif isinstance(condition, EvidencePresentedCondition):
                self._require_reference(
                    issues,
                    value=condition.evidence_id,
                    valid_ids=evidence_ids,
                    path=f"{condition_path}.evidence_id",
                    target_type="evidence",
                )

        # Validate Hints & Solution References
        for hint_index, hint in enumerate(case.hints):
            for fact_index, fact_id in enumerate(hint.requires_fact_ids):
                self._require_reference(
                    issues,
                    value=fact_id,
                    valid_ids=fact_ids,
                    path=f"$.hints[{hint_index}].requires_fact_ids[{fact_index}]",
                    target_type="fact",
                )

            for evidence_index, evidence_id in enumerate(hint.points_to_evidence_ids):
                self._require_reference(
                    issues,
                    value=evidence_id,
                    valid_ids=evidence_ids,
                    path=f"$.hints[{hint_index}].points_to_evidence_ids[{evidence_index}]",
                    target_type="evidence",
                )

        self._require_reference(
            issues,
            value=case.solution.culprit_character_id,
            valid_ids=character_ids,
            path="$.solution.culprit_character_id",
            target_type="character",
        )

        for criterion_index, criterion in enumerate(case.solution.criteria):
            for evidence_index, evidence_id in enumerate(criterion.supporting_evidence_ids):
                self._require_reference(
                    issues,
                    value=evidence_id,
                    valid_ids=evidence_ids,
                    path=f"$.solution.criteria[{criterion_index}].supporting_evidence_ids[{evidence_index}]",
                    target_type="evidence",
                )

    def _validate_timeline_order(
        self,
        case: CaseManifest,
        issues: list[ValidationIssue]
    ) -> None:
        for index in range(1, len(case.timeline)):
            previous = case.timeline[index - 1]
            current = case.timeline[index]

            if current.time_range.start < previous.time_range.start:
                self._add_issue(
                    issues,
                    code=ValidationCode.TIMELINE_NOT_ORDERED,
                    path=f"$.timeline[{index}].time_range.start",
                    message=(
                        f"Timeline event '{current.id}' starts before "
                        f"the preceding event '{previous.id}'"
                    ),
                )

    def _validate_actor_timelines(
        self,
        case: CaseManifest,
        issues: list[ValidationIssue],
    ) -> None:
        events_by_actor: dict[
            str,
            list[tuple[int, object]],
        ] = defaultdict(list)

        for event_index, event in enumerate(case.timeline):
            for actor_id in event.actor_ids:
                events_by_actor[actor_id].append(
                    (event_index, event)
                )

        travel_minutes = self._travel_lookup(case)

        for actor_id in sorted(events_by_actor):
            actor_events = sorted(
                events_by_actor[actor_id],
                key=lambda item: (
                    item[1].time_range.start,
                    item[1].time_range.end,
                    item[1].id
                )
            ) 

            for pair_index in range(1, len(actor_events)):
                previous_index, previous = actor_events[pair_index - 1]
                current_index, current = actor_events[pair_index]

                # Check 1: Physical Overlap
                if current.time_range.start < previous.time_range.end:
                    self._add_issue(
                        issues,
                        code=ValidationCode.ACTOR_EVENT_OVERLAP,
                        path=f"$.timeline[{current_index}].time_range.start",
                        message=(
                            f"Character '{actor_id}' appears in overlapping "
                            f"events '{previous.id}' and '{current.id}'"
                        ),
                    )
                    continue

                if previous.location_id == current.location_id:
                    continue

                # Check 2: Travel Constraints
                required_minutes = travel_minutes.get(
                    (previous.location_id, current.location_id)
                )

                if required_minutes is None:
                    continue

                earliest_arrival = (
                    previous.time_range.end
                    + timedelta(minutes=required_minutes)
                )

                if current.time_range.start < earliest_arrival:
                    actual_gap = (
                        current.time_range.start - previous.time_range.end
                    ).total_seconds() / 60

                    self._add_issue(
                        issues,
                        code=ValidationCode.TRAVEL_TIME_VIOLATION,
                        path=f"$.timeline[{current_index}].time_range.start",
                        message=(
                            f"Character '{actor_id}' has only "
                            f"{actual_gap:g} minutes to travel from "
                            f"'{previous.location_id}' to "
                            f"'{current.location_id}', but "
                            f"{required_minutes} minutes are required"
                        ),
                    )

    def _validate_unlock_graph(
        self,
        case: CaseManifest,
        issues: list[ValidationIssue]
    ) -> None:
        evidence_by_id = {evidence.id: evidence for evidence in case.evidence}
        evidence_index = {evidence.id: index for index, evidence in enumerate(case.evidence)}

        graph: dict[str, tuple[str, ...]] = {}

        for index, evidence in enumerate(case.evidence):
            valid_targets = tuple(
                target
                for target in evidence.unlocks_evidence_ids
                if target in evidence_by_id
            )

            graph[evidence.id] = valid_targets

            # Self-unlock check
            if evidence.id in evidence.unlocks_evidence_ids:
                self._add_issue(
                    issues,
                    code=ValidationCode.EVIDENCE_UNLOCKS_ITSELF,
                    path=f"$.evidence[{index}].unlocks_evidence_ids",
                    message=f"Evidence '{evidence.id}' cannot unlock itself",
                )

        # Detect Dependency Cycles
        cycle_nodes = self._find_cycle_nodes(graph)
        for evidence_id in sorted(cycle_nodes, key=lambda item: evidence_index[item]):
            index = evidence_index[evidence_id]
            self._add_issue(
                issues,
                code=ValidationCode.UNLOCK_CYCLE,
                path=f"$.evidence[{index}].unlocks_evidence_ids",
                message=f"Evidence '{evidence_id}' participates in an unlock dependency cycle",
            )

        # Reachability Check via BFS
        initially_reachable = sorted(
            evidence.id
            for evidence in case.evidence
            if evidence.visibility != Visibility.HIDDEN
        )
        reachable = self._reachable_nodes(graph, initially_reachable)

        required_evidence = {
            evidence_id
            for criterion in case.solution.criteria
            for evidence_id in criterion.supporting_evidence_ids
            if evidence_id in evidence_by_id
        }

        for evidence_id in sorted(required_evidence, key=lambda item: evidence_index[item]):
            if evidence_id not in reachable:
                index = evidence_index[evidence_id]
                self._add_issue(
                    issues,
                    code=ValidationCode.REQUIRED_EVIDENCE_UNREACHABLE,
                    path=f"$.evidence[{index}]",
                    message=(
                        f"Solution-required evidence '{evidence_id}' "
                        "cannot be reached from initially visible or "
                        "discoverable evidence"
                    ),
                )

    def _validate_solution_rubric(
        self,
        case: CaseManifest,
        issues: list[ValidationIssue],
    ) -> None:
        categories = {
            criterion.category
            for criterion in case.solution.criteria
        }

        if len(categories) < 3:
            self._add_issue(
                issues,
                code=ValidationCode.RUBRIC_INSUFFICIENT_CATEGORIES,
                path="$.solution.criteria",
                message=(
                    "The solution rubric must contain evidence from "
                    "at least three distinct support categories"
                ),
            )

        evidence_by_id = {evidence.id: evidence for evidence in case.evidence}

        reachable = self._reachable_nodes(
            {
                evidence.id: tuple(
                    target
                    for target in evidence.unlocks_evidence_ids
                    if target in evidence_by_id
                )
                for evidence in case.evidence
            },
            [
                evidence.id
                for evidence in case.evidence
                if evidence.visibility != Visibility.HIDDEN
            ],
        )

        for criterion_index, criterion in enumerate(case.solution.criteria):
            for evidence_index, evidence_id in enumerate(criterion.supporting_evidence_ids):
                if evidence_id not in evidence_by_id:
                    continue

                if evidence_id not in reachable:
                    self._add_issue(
                        issues,
                        code=ValidationCode.RUBRIC_EVIDENCE_NOT_DISCOVERABLE,
                        path=(
                            f"$.solution.criteria[{criterion_index}]"
                            f".supporting_evidence_ids[{evidence_index}]"
                        ),
                        message=(
                            f"Rubric evidence '{evidence_id}' cannot "
                            "be discovered by the player"
                        ),
                    )

    @staticmethod
    def _require_reference(
        issues: list[ValidationIssue],
        *,
        value: str,
        valid_ids: set[str],
        path: str,
        target_type: str,
    ) -> None:
        if value not in valid_ids:
            issues.append(
                ValidationIssue(
                    code=ValidationCode.UNKNOWN_REFERENCE,
                    severity=ValidationSeverity.ERROR,
                    path=path,
                    message=f"Unknown {target_type} reference '{value}'",
                )
            )

    @staticmethod
    def _travel_lookup(
        case: CaseManifest,
    ) -> dict[tuple[str, str], int]:
        lookup: dict[tuple[str, str], int] = {}

        for constraint in case.travel_constraints:
            key = (
                constraint.from_location_id,
                constraint.to_location_id,
            )

            current = lookup.get(key)

            if current is None or constraint.minimum_minutes > current:
                lookup[key] = constraint.minimum_minutes

        return lookup

    @staticmethod
    def _reachable_nodes(
        graph: dict[str, tuple[str, ...]],
        starting_nodes: Iterable[str],
    ) -> set[str]:
        reachable: set[str] = set()
        queue: deque[str] = deque(sorted(starting_nodes))

        while queue:
            current = queue.popleft()

            if current in reachable:
                continue

            reachable.add(current)

            for neighbour in sorted(graph.get(current, ())):
                if neighbour not in reachable:
                    queue.append(neighbour)

        return reachable

    @staticmethod
    def _find_cycle_nodes(
        graph: dict[str, tuple[str, ...]]
    ) -> set[str]:
        """
        Return every node that participates in at least one directed cycle.

        A recursion-stack DFS is sufficient for the small authored case
        packages expected by the MVP.
        """

        visited: set[str] = set()
        active: set[str] = set()
        stack: list[str] = []
        cycle_nodes: set[str] = set()

        def visit(node: str) -> None:
            visited.add(node)
            active.add(node)
            stack.append(node)

            for neighbor in sorted(graph.get(node, ())):
                if neighbor not in graph:
                    continue
                if neighbor not in visited:
                    visit(neighbor)
                elif neighbor in active:
                    cycle_start = stack.index(neighbor)
                    cycle_nodes.update(stack[cycle_start:])

            stack.pop()
            active.remove(node)

        for node in sorted(graph):
            if node not in visited:
                visit(node)

        return cycle_nodes

    @staticmethod
    def _sort_issues(
        issues: list[ValidationIssue],
    ) -> list[ValidationIssue]:
        return sorted(
            issues,
            key=lambda issue: (
                issue.path,
                issue.code.value,
                issue.message,
            ),
        )

def validate_case(case: CaseManifest) -> ValidationReport:
    """Convenience entry point for callers that do not need a validator object."""

    return CaseValidator().validate(case)
