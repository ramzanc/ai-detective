from __future__ import annotations

from app.domain.case_models import CaseManifest
from app.domain.case_validator import (
    CaseValidator,
    ValidationCode,
    ValidationSeverity,
    validate_case,
)
from tests.factories.cases import make_valid_case


def changed_case(**changes: object) -> CaseManifest:
    case = make_valid_case()
    data = case.model_dump(mode="python")
    data.update(changes)
    return CaseManifest.model_validate(data)


def test_valid_case_is_publishable() -> None:
    report = validate_case(make_valid_case())

    assert report.is_publishable is True
    assert report.errors == ()
    assert report.issues == ()


def test_duplicate_id_is_rejected() -> None:
    case = make_valid_case()
    evidence = list(case.evidence)

    duplicate = evidence[0].model_copy(
        update={"name": "Duplicate watch"}
    )
    evidence.append(duplicate)

    invalid_case = case.model_copy(
        update={"evidence": tuple(evidence)}
    )

    report = validate_case(invalid_case)

    assert report.is_publishable is False
    assert report.has_code(ValidationCode.DUPLICATE_ID)

    issue = next(
        issue
        for issue in report.issues
        if issue.code == ValidationCode.DUPLICATE_ID
    )

    assert issue.path == "$.evidence[3].id"
    assert issue.severity == ValidationSeverity.ERROR


def test_unknown_reference_is_rejected() -> None:
    case = make_valid_case()
    evidence = list(case.evidence)

    evidence[0] = evidence[0].model_copy(
        update={"location_id": "missing_location"}
    )

    invalid_case = case.model_copy(
        update={"evidence": tuple(evidence)}
    )

    report = validate_case(invalid_case)

    assert report.has_code(ValidationCode.UNKNOWN_REFERENCE)

    issue = next(
        issue
        for issue in report.issues
        if issue.code == ValidationCode.UNKNOWN_REFERENCE
    )

    assert issue.path == "$.evidence[0].location_id"
    assert "missing_location" in issue.message


def test_timeline_must_be_authored_in_chronological_order() -> None:
    case = make_valid_case()

    invalid_case = case.model_copy(
        update={"timeline": tuple(reversed(case.timeline))}
    )

    report = validate_case(invalid_case)

    assert report.has_code(ValidationCode.TIMELINE_NOT_ORDERED)


def test_actor_cannot_appear_in_overlapping_events() -> None:
    case = make_valid_case()
    timeline = list(case.timeline)

    timeline[1] = timeline[1].model_copy(
        update={
            "time_range": timeline[1].time_range.model_copy(
                update={
                    "start": timeline[0].time_range.start,
                }
            )
        }
    )

    invalid_case = case.model_copy(
        update={"timeline": tuple(timeline)}
    )

    report = validate_case(invalid_case)

    assert report.has_code(ValidationCode.ACTOR_EVENT_OVERLAP)


def test_actor_must_have_enough_travel_time() -> None:
    case = make_valid_case()
    timeline = list(case.timeline)

    timeline[1] = timeline[1].model_copy(
        update={
            "time_range": timeline[1].time_range.model_copy(
                update={
                    "start": timeline[0].time_range.end,
                }
            )
        }
    )

    invalid_case = case.model_copy(
        update={"timeline": tuple(timeline)}
    )

    report = validate_case(invalid_case)

    assert report.has_code(ValidationCode.TRAVEL_TIME_VIOLATION)


def test_evidence_cannot_unlock_itself() -> None:
    case = make_valid_case()
    evidence = list(case.evidence)

    evidence[0] = evidence[0].model_copy(
        update={
            "unlocks_evidence_ids": ("silver_watch",),
        }
    )

    invalid_case = case.model_copy(
        update={"evidence": tuple(evidence)}
    )

    report = validate_case(invalid_case)

    assert report.has_code(
        ValidationCode.EVIDENCE_UNLOCKS_ITSELF
    )


def test_unlock_cycle_is_rejected() -> None:
    case = make_valid_case()
    evidence = list(case.evidence)

    evidence[0] = evidence[0].model_copy(
        update={
            "unlocks_evidence_ids": ("door_log",),
        }
    )

    evidence[1] = evidence[1].model_copy(
        update={
            "unlocks_evidence_ids": ("study_key_log",),
        }
    )

    evidence[2] = evidence[2].model_copy(
        update={
            "unlocks_evidence_ids": ("silver_watch",),
        }
    )

    invalid_case = case.model_copy(
        update={"evidence": tuple(evidence)}
    )

    report = validate_case(invalid_case)

    cycle_issues = [
        issue
        for issue in report.issues
        if issue.code == ValidationCode.UNLOCK_CYCLE
    ]

    assert len(cycle_issues) == 3


def test_required_hidden_evidence_must_be_reachable() -> None:
    case = make_valid_case()
    evidence = list(case.evidence)

    evidence[1] = evidence[1].model_copy(
        update={
            "visibility": "hidden",
        }
    )

    invalid_case = case.model_copy(
        update={"evidence": tuple(evidence)}
    )

    report = validate_case(invalid_case)

    assert report.has_code(
        ValidationCode.REQUIRED_EVIDENCE_UNREACHABLE
    )

    assert report.has_code(
        ValidationCode.RUBRIC_EVIDENCE_NOT_DISCOVERABLE
    )


def test_hidden_evidence_can_be_unlocked() -> None:
    case = make_valid_case()
    evidence = list(case.evidence)

    evidence[0] = evidence[0].model_copy(
        update={
            "unlocks_evidence_ids": ("door_log",),
        }
    )

    evidence[1] = evidence[1].model_copy(
        update={
            "visibility": "hidden",
        }
    )

    invalid_case = case.model_copy(
        update={"evidence": tuple(evidence)}
    )

    report = validate_case(invalid_case)

    assert not report.has_code(
        ValidationCode.REQUIRED_EVIDENCE_UNREACHABLE
    )

    assert not report.has_code(
        ValidationCode.RUBRIC_EVIDENCE_NOT_DISCOVERABLE
    )


def test_solution_requires_three_support_categories() -> None:
    case = make_valid_case()

    criteria = tuple(
        criterion.model_copy(
            update={"category": "identity"}
        )
        for criterion in case.solution.criteria
    )

    solution = case.solution.model_copy(
        update={"criteria": criteria}
    )

    invalid_case = case.model_copy(
        update={"solution": solution}
    )

    report = validate_case(invalid_case)

    assert report.has_code(
        ValidationCode.RUBRIC_INSUFFICIENT_CATEGORIES
    )


def test_validation_order_is_deterministic() -> None:
    case = make_valid_case()
    evidence = list(case.evidence)

    evidence[0] = evidence[0].model_copy(
        update={
            "location_id": "missing_location",
            "reveals_fact_ids": ("missing_fact",),
        }
    )

    invalid_case = case.model_copy(
        update={"evidence": tuple(evidence)}
    )

    validator = CaseValidator()

    first = validator.validate(invalid_case)
    second = validator.validate(invalid_case)

    assert first == second

    sort_keys = [
        (
            issue.path,
            issue.code.value,
            issue.message,
        )
        for issue in first.issues
    ]

    assert sort_keys == sorted(sort_keys)


def test_report_can_be_serialized_to_json() -> None:
    report = validate_case(make_valid_case())

    payload = report.model_dump_json()

    assert '"issues":[]' in payload