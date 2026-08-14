from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

DOMAIN_ID_PATTERN = r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$"

DomainID = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=100, pattern=DOMAIN_ID_PATTERN
    ),
]

CaseID = DomainID
CharacterID = DomainID
EvidenceID = DomainID
LocationID = DomainID
FactID = DomainID
EventID = DomainID
HintID = DomainID
BehaviorRuleID = DomainID
RubricCriterionID = DomainID


class StrictFrozenModel(BaseModel):
    """
    Base class for immutable published-case models.

    extra="forbid":
        Rejects misspelled or unrecognized authored properties.

    frozen=True:
        Prevents case data from being mutated after validation.

    validate_assignment=True:
        Provides an additional guard if frozen is changed in the future.

    str_strip_whitespace=True:
        Normalizes accidental surrounding whitespace in authored strings.
    """

    model_config = ConfigDict(
        extra="forbid", frozen=True, validate_assignment=True, str_strip_whitespace=True
    )


class Visibility(StrEnum):
    PUBLIC = "public"
    DISCOVERABLE = "discoverable"
    HIDDEN = "hidden"


class CharacterRole(StrEnum):
    SUSPECT = "suspect"
    WITNESS = "witness"
    VICTIM = "victim"
    OTHER = "other"


class EvidenceKind(StrEnum):
    PHYSICAL = "physical"
    DOCUMENT = "document"
    DIGITAL = "digital"
    TESTIMONY = "testimony"


class BehaviorStrategy(StrEnum):
    COOPERATE = "cooperate"
    EVADE = "evade"
    DEFLECT = "deflect"
    DENY = "deny"
    REVEAL = "reveal"
    CONFESS = "confess"


class BehaviorCondition(StrEnum):
    ALWAYS = "always"
    FACT_KNOWN = "fact_known"
    EVIDENCE_PRESENTED = "evidence_presented"
    CONTRADICTION_FOUND = "contradiction_found"


class HintTier(StrEnum):
    NUDGE = "nudge"
    DIRECT = "direct"
    EXPLICIT = "explicit"


class SupportCategory(StrEnum):
    MOTIVE = "motive"
    MEANS = "means"
    OPPORTUNITY = "opportunity"
    CONTRADICTION = "contradiction"
    IDENTITY = "identity"
