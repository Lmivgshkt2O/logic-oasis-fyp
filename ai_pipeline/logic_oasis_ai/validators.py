"""Reject records that did not originate from a sealed U3 session."""

from .schemas import FinalizedQuizAttemptRecord, ValidatedResponseRecord
from typing import Sequence


FINALIZED_STATUS = "finalized"
VALIDATED_STATUS = "validated"
RUNTIME_CALLABLE_DATA_SOURCE = "runtime_callable"


def validate_response_lineage(
    attempt: FinalizedQuizAttemptRecord,
    responses: Sequence[ValidatedResponseRecord],
) -> None:
    if (
        attempt.finalization_status != FINALIZED_STATUS
        or attempt.validation_status != FINALIZED_STATUS
        or attempt.data_source != RUNTIME_CALLABLE_DATA_SOURCE
    ):
        raise ValueError("attempt is not a trusted finalized runtime attempt")
    if len(responses) != attempt.total_questions:
        raise ValueError("attempt response count does not match")
    ordered = sorted(responses, key=lambda response: response.sequence_index)
    if tuple(response.response_id for response in ordered) != attempt.response_ids:
        raise ValueError("attempt response lineage is not ordered")
    for expected_index, response in enumerate(ordered):
        if response.session_id != attempt.session_id or response.attempt_id != attempt.attempt_id:
            raise ValueError("response belongs to another session or attempt")
        if response.student_id != attempt.student_id:
            raise ValueError("response belongs to another student")
        if (
            response.sequence_index != expected_index
            or response.validation_status != VALIDATED_STATUS
        ):
            raise ValueError("response was not securely validated in order")
    if sum(response.is_correct for response in ordered) != attempt.correct_count:
        raise ValueError("attempt correct count does not match validated responses")
