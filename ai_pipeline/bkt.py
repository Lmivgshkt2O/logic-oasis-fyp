"""Legacy wrapper around the shared U4 BKT observation equation."""

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
    ordered_attempts = sorted(attempts, key=lambda item: item.get("createdAtSort", ""))

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
