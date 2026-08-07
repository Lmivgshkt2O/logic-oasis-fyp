"""J1 normalized external contract for ASSISTments EDM Cup 2023.

Implements the plan's ``ExternalActionRow`` (section 9.1) exactly.  Rows are
pseudonymized (project-local stable keys) and never carry raw learner
identifiers.  Native Logic Oasis runtime fields are never fabricated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import hmac
from typing import Mapping

from .assistments_contract import PROVENANCE, SOURCE_DATASET, parse_epoch_seconds


EXTERNAL_ACTION_ROWS_SCHEMA_VERSION = "assistments-external-action-rows-v1"
SOURCE_WINDOW = "2022-01-01/2023-12-31"
SOURCE_SUBJECT_MATHEMATICS = "Mathematics"

EXTERNAL_ACTION_ROW_FIELDS = (
    "datasetReleaseId",
    "externalStudentKey",
    "externalAssignmentKey",
    "externalSequenceKey",
    "externalProblemKey",
    "externalContentKey",
    "sourceTimestamp",
    "sourceActionType",
    "sourceGrade",
    "sourceSubject",
    "sourceSkillCode",
    "provenance",
    "sourceDataset",
    "sourceWindow",
)


def external_pseudonym(namespace: str, raw_identifier: object, key: bytes | str) -> str:
    """Stable project-local key for one source identity, without the raw value.

    Mirrors the project's HMAC pseudonym convention.  The digest is
    reproducible for the same ``(namespace, raw value, key)`` so later units
    can group by it, and it never contains the raw identifier.
    """
    raw = str(raw_identifier)
    if not namespace or not raw:
        raise ValueError("namespace and raw identifier are required")
    key_bytes = key.encode("utf-8") if isinstance(key, str) else key
    if not key_bytes:
        raise ValueError("a non-empty pseudonym key is required")
    digest = hmac.new(key_bytes, f"{namespace}:{raw}".encode("utf-8"), sha256).hexdigest()
    return f"assistments_{namespace}_{digest}"


def _parse_source_timestamp_or_raise(value: object) -> None:
    """Accept the normalized ISO form or the raw epoch-seconds form."""
    if parse_epoch_seconds(value) is not None:
        return
    if isinstance(value, str):
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return
        except ValueError:
            pass
    raise ValueError("sourceTimestamp must be a parseable timestamp")


@dataclass(frozen=True)
class ExternalActionRow:
    """One normalized, in-window ASSISTments source action (plan 9.1)."""

    datasetReleaseId: str
    externalStudentKey: str
    externalAssignmentKey: str
    externalSequenceKey: str | None
    externalProblemKey: str | None
    externalContentKey: str | None
    sourceTimestamp: str
    sourceActionType: str
    sourceGrade: str | None
    sourceSubject: str | None
    sourceSkillCode: str | None
    provenance: str = PROVENANCE
    sourceDataset: str = SOURCE_DATASET
    sourceWindow: str = SOURCE_WINDOW

    def __post_init__(self) -> None:
        for field in ("datasetReleaseId", "externalStudentKey", "externalAssignmentKey", "sourceActionType"):
            if not getattr(self, field):
                raise ValueError(f"{field} is required")
        if self.provenance != PROVENANCE:
            raise ValueError("ASSISTments normalized rows must use provenance external_real")
        if self.sourceDataset != SOURCE_DATASET:
            raise ValueError("sourceDataset must be assistments_edm_cup_2023")
        if self.sourceWindow != SOURCE_WINDOW:
            raise ValueError("sourceWindow must be 2022-01-01/2023-12-31")
        _parse_source_timestamp_or_raise(self.sourceTimestamp)

    def to_csv_row(self) -> dict[str, str]:
        return {
            "datasetReleaseId": self.datasetReleaseId,
            "externalStudentKey": self.externalStudentKey,
            "externalAssignmentKey": self.externalAssignmentKey,
            "externalSequenceKey": self.externalSequenceKey or "",
            "externalProblemKey": self.externalProblemKey or "",
            "externalContentKey": self.externalContentKey or "",
            "sourceTimestamp": self.sourceTimestamp,
            "sourceActionType": self.sourceActionType,
            "sourceGrade": self.sourceGrade or "",
            "sourceSubject": self.sourceSubject or "",
            "sourceSkillCode": self.sourceSkillCode or "",
            "provenance": self.provenance,
            "sourceDataset": self.sourceDataset,
            "sourceWindow": self.sourceWindow,
        }

    @classmethod
    def field_names(cls) -> tuple[str, ...]:
        return EXTERNAL_ACTION_ROW_FIELDS


def validate_no_raw_learner_identifiers(row: Mapping[str, object], raw_student_id: object) -> None:
    """Fail closed if a normalized row exposes the raw learner identifier."""
    raw = str(raw_student_id) if raw_student_id is not None else ""
    if raw and raw in str(row.get("externalStudentKey", "")):
        raise ValueError("normalized rows must not expose the raw learner identifier")
