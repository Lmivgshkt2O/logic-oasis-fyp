DIFFICULTY_WEIGHTS = {
    "easy": 0,
    "medium": 1,
    "hard": 2,
    "mixed": 1,
}


def _average(values):
    return sum(values) / len(values) if values else 0


def group_attempts(attempts):
    grouped = {}
    for attempt in attempts:
        key = (attempt["studentId"], attempt["topicId"])
        grouped.setdefault(key, []).append(attempt)
    return grouped


def build_features(topic_attempts):
    ordered = sorted(topic_attempts, key=lambda item: item.get("createdAtSort", ""))
    latest = ordered[-1]
    scores = [float(item.get("score", 0)) for item in ordered]
    correct_rates = [float(item.get("correctRate", 0)) for item in ordered]
    wrong_counts = [float(item.get("wrongCount", 0)) for item in ordered]
    time_taken = [float(item.get("timeTakenSeconds", 0)) for item in ordered]
    retry_counts = [float(item.get("retryCount", index)) for index, item in enumerate(ordered)]
    latest_difficulty = str(latest.get("difficultyLevel", "mixed")).lower()
    score_change = scores[-1] - scores[-2] if len(scores) >= 2 else 0
    average_score = _average(scores)
    score_consistency = _average(
        [abs(score - average_score) for score in scores],
    )

    recent_trend = recent_trend_label(scores)
    features = {
        "score": scores[-1],
        "averageScore": average_score,
        "correctRate": correct_rates[-1],
        "wrongCount": wrong_counts[-1],
        "averageWrongCount": _average(wrong_counts),
        "timeTakenSeconds": time_taken[-1],
        "averageTimeTakenSeconds": _average(time_taken),
        "retryCount": retry_counts[-1],
        "difficultyLevel": DIFFICULTY_WEIGHTS.get(latest_difficulty, 1),
        "attemptsCount": len(ordered),
        "scoreChange": score_change,
        "scoreConsistency": score_consistency,
        "recentTrend": trend_to_number(recent_trend),
    }
    return features, recent_trend


def recent_trend_label(scores):
    if len(scores) < 2:
        return "stable"
    if scores[-1] >= scores[-2] + 5:
        return "improving"
    if scores[-1] <= scores[-2] - 5:
        return "declining"
    return "stable"


def trend_to_number(label):
    return {
        "declining": -1,
        "stable": 0,
        "improving": 1,
    }.get(label, 0)


def heuristic_mastery_label(features):
    score = features["averageScore"]
    if score >= 80:
        return "Strong"
    if score >= 50:
        return "Moderate"
    return "Weak"
