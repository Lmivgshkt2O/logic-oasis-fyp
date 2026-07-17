"""Legacy wrapper around the shared U4 BKT observation equation.

This summary-only helper is not valid U4 runtime evidence, but it must still
respect the U3-R server-owned sequence rather than using a wall-clock field.
"""

from logic_oasis_ai.bkt import BktParameters, update_probability


def update_bkt_mastery(
    attempts,
    prior_knowledge=0.35,
    learn_rate=0.18,
    guess_rate=0.2,
    slip_rate=0.1,
):
    parameters = BktParameters(
        prior_knowledge=prior_knowledge,
        learn_rate=learn_rate,
        guess_rate=guess_rate,
        slip_rate=slip_rate,
    )
    mastery = parameters.prior_knowledge
    materialized_attempts = tuple(attempts)
    for attempt in materialized_attempts:
        sequence = attempt.get("sourceAttemptSequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
            raise ValueError("sourceAttemptSequence is required for ordered BKT replay")
    ordered_attempts = sorted(
        materialized_attempts,
        key=lambda item: item["sourceAttemptSequence"],
    )

    for attempt in ordered_attempts:
        correct_rate = float(attempt.get("correctRate", 0))
        observed_correct = correct_rate >= 0.6

        mastery = update_probability(
            mastery,
            is_correct=observed_correct,
            parameters=parameters,
        )

    return {
        "bktPriorKnowledge": prior_knowledge,
        "bktLearnRate": learn_rate,
        "bktGuessRate": guess_rate,
        "bktSlipRate": slip_rate,
        "bktMasteryProbability": round(mastery, 4),
    }
