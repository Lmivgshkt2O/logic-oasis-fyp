from pathlib import Path


FEATURE_NAMES = [
    "score",
    "averageScore",
    "correctRate",
    "wrongCount",
    "averageWrongCount",
    "timeTakenSeconds",
    "averageTimeTakenSeconds",
    "retryCount",
    "difficultyLevel",
    "attemptsCount",
    "scoreChange",
    "scoreConsistency",
    "recentTrend",
    "bktMasteryProbability",
]

LABELS = ["Weak", "Moderate", "Strong"]
MODEL_BUNDLE_PATH = Path(__file__).with_name("xgboost_logic_oasis_model.pkl")


def predict_with_xgboost_or_fallback(records):
    try:
        if MODEL_BUNDLE_PATH.exists():
            return _predict_with_saved_xgboost(records)
        return _predict_with_xgboost(records)
    except Exception:
        return [_fallback_prediction(record) for record in records]


def _predict_with_saved_xgboost(records):
    import joblib
    import shap

    bundle = joblib.load(MODEL_BUNDLE_PATH)
    model = bundle["model"] if isinstance(bundle, dict) and "model" in bundle else bundle
    feature_names = bundle.get("features", FEATURE_NAMES) if isinstance(bundle, dict) else FEATURE_NAMES
    label_map = bundle.get("label_map", {label: index for index, label in enumerate(LABELS)}) if isinstance(bundle, dict) else {label: index for index, label in enumerate(LABELS)}
    label_by_index = {index: label for label, index in label_map.items()}

    missing_features = [name for name in feature_names if name not in records[0]]
    if missing_features:
        raise ValueError(f"Saved model needs missing features: {missing_features}")

    features = [[record[name] for name in feature_names] for record in records]
    probabilities = model.predict_proba(features)
    predictions = model.predict(features)
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(features)

    outputs = []
    for index, record in enumerate(records):
        label = label_by_index.get(int(predictions[index]), "Moderate")
        weakness_index = label_map.get("Weak", 0)
        weakness_probability = float(probabilities[index][weakness_index])
        confidence = max(float(value) for value in probabilities[index])
        explanation = _shap_explanation(
            shap_values,
            index,
            record,
            label,
            LABELS,
            feature_names,
        )
        outputs.append(
            {
                "xgboostPrediction": label,
                "weaknessProbability": round(weakness_probability, 4),
                "confidence": round(confidence, 4),
                "shapReasons": explanation["shapReasons"],
                "shapDetails": explanation["shapDetails"],
            }
        )
    return outputs


def _predict_with_xgboost(records):
    import shap
    from sklearn.preprocessing import LabelEncoder
    from xgboost import XGBClassifier

    if len(records) < 6:
        raise ValueError("Not enough records for useful XGBoost training.")

    labels = [_training_label(record) for record in records]
    if len(set(labels)) < 2:
        raise ValueError("At least two mastery classes are required.")

    encoder = LabelEncoder()
    encoded_labels = encoder.fit_transform(labels)
    features = [[record[name] for name in FEATURE_NAMES] for record in records]
    model = XGBClassifier(
        n_estimators=40,
        max_depth=3,
        learning_rate=0.12,
        objective="multi:softprob",
        eval_metric="mlogloss",
        random_state=42,
    )
    model.fit(features, encoded_labels)

    probabilities = model.predict_proba(features)
    predictions = model.predict(features)
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(features)

    outputs = []
    for index, record in enumerate(records):
        label = encoder.inverse_transform([predictions[index]])[0]
        class_names = list(encoder.classes_)
        weakness_probability = _class_probability(
            probabilities[index],
            class_names,
            "Weak",
        )
        confidence = max(float(value) for value in probabilities[index])
        explanation = _shap_explanation(
            shap_values,
            index,
            record,
            label,
            class_names,
            FEATURE_NAMES,
        )
        outputs.append(
            {
                "xgboostPrediction": label,
                "weaknessProbability": round(weakness_probability, 4),
                "confidence": round(confidence, 4),
                "shapReasons": explanation["shapReasons"],
                "shapDetails": explanation["shapDetails"],
            }
        )
    return outputs


def _fallback_prediction(record):
    weakness_probability = _fallback_weakness_probability(record)
    if weakness_probability >= 0.7:
        label = "Weak"
    elif weakness_probability <= 0.35 and record["bktMasteryProbability"] >= 0.75:
        label = "Strong"
    else:
        label = "Moderate"

    explanation = _fallback_explanation(record, label)
    return {
        "xgboostPrediction": label,
        "weaknessProbability": round(weakness_probability, 4),
        "confidence": 0.68,
        "shapReasons": explanation["shapReasons"],
        "shapDetails": explanation["shapDetails"],
    }


def final_mastery_label(xgboost_prediction, weakness_probability, bkt_mastery):
    if bkt_mastery < 0.45 and weakness_probability >= 0.70:
        return "Weak"
    if 0.45 <= bkt_mastery <= 0.75:
        return "Moderate"
    if bkt_mastery > 0.75 and weakness_probability < 0.40:
        return "Strong"
    return xgboost_prediction


def recommended_action(topic_title, final_label):
    if final_label == "Weak":
        return f"Review {topic_title} basics, then complete one guided mission."
    if final_label == "Moderate":
        return f"Practise one mixed {topic_title} mission and review mistakes."
    return f"Maintain progress with one short {topic_title} challenge."


def _training_label(record):
    average = record["averageScore"]
    if average >= 80:
        return "Strong"
    if average >= 50:
        return "Moderate"
    return "Weak"


def _class_probability(probabilities, class_names, target):
    if target not in class_names:
        return 0.0
    return float(probabilities[class_names.index(target)])


def _fallback_weakness_probability(record):
    score_risk = 1 - min(max(record["averageScore"] / 100, 0), 1)
    wrong_risk = min(record["wrongCount"] / 5, 1)
    average_wrong_risk = min(record["averageWrongCount"] / 5, 1)
    time_risk = min(record["timeTakenSeconds"] / 300, 1)
    average_time_risk = min(record["averageTimeTakenSeconds"] / 300, 1)
    retry_risk = min(record["retryCount"] / 3, 1)
    decline_risk = min(max(-record["scoreChange"] / 30, 0), 1)
    bkt_risk = 1 - min(max(record["bktMasteryProbability"], 0), 1)
    return (
        score_risk * 0.28
        + wrong_risk * 0.14
        + average_wrong_risk * 0.1
        + time_risk * 0.08
        + average_time_risk * 0.08
        + retry_risk * 0.1
        + decline_risk * 0.08
        + bkt_risk * 0.14
    )


def _fallback_explanation(record, label):
    candidates = [
        (
            "score",
            record["score"],
            _score_reason(record["score"], label),
            100 - record["score"],
        ),
        (
            "averageScore",
            record["averageScore"],
            _average_score_reason(record["averageScore"], label),
            100 - record["averageScore"],
        ),
        (
            "wrongCount",
            record["wrongCount"],
            "High wrong count",
            record["wrongCount"] * 20,
        ),
        (
            "averageWrongCount",
            record["averageWrongCount"],
            _average_wrong_count_reason(record["averageWrongCount"], label),
            record["averageWrongCount"] * 20,
        ),
        (
            "timeTakenSeconds",
            record["timeTakenSeconds"],
            "Long completion time",
            record["timeTakenSeconds"] / 3,
        ),
        (
            "averageTimeTakenSeconds",
            record["averageTimeTakenSeconds"],
            _average_time_reason(record["averageTimeTakenSeconds"], label),
            record["averageTimeTakenSeconds"] / 3,
        ),
        (
            "retryCount",
            record["retryCount"],
            _retry_count_reason(record["retryCount"], label),
            record["retryCount"] * 25,
        ),
        (
            "bktMasteryProbability",
            record["bktMasteryProbability"],
            _bkt_reason(record["bktMasteryProbability"], label),
            (1 - record["bktMasteryProbability"]) * 100,
        ),
        (
            "scoreChange",
            record["scoreChange"],
            _score_change_reason(record["scoreChange"], label),
            max(-record["scoreChange"], 0) * 2,
        ),
    ]
    candidates.sort(key=lambda item: item[3], reverse=True)
    details = [
        {
            "feature": feature,
            "value": value,
            "shapValue": None,
            "direction": "heuristic",
            "reason": reason,
            "source": "heuristicFallback",
        }
        for feature, value, reason, importance in candidates[:3]
        if importance > 0
    ]
    return {
        "shapReasons": [detail["reason"] for detail in details],
        "shapDetails": details,
    }


def _shap_explanation(shap_values, row_index, record, label, class_names, feature_names):
    label_index = class_names.index(label) if label in class_names else 0
    if hasattr(shap_values, "shape") and len(shap_values.shape) == 3:
        if shap_values.shape[1] == len(feature_names):
            values = shap_values[row_index, :, label_index]
        else:
            values = shap_values[label_index, row_index, :]
    else:
        values = shap_values[label_index][row_index]
    ranked = sorted(
        zip(feature_names, values),
        key=lambda item: abs(float(item[1])),
        reverse=True,
    )
    details = []
    for name, shap_value in ranked[:3]:
        value = record[name]
        details.append(
            {
                "feature": name,
                "value": value,
                "shapValue": round(float(shap_value), 6),
                "direction": "increased" if shap_value > 0 else "reduced",
                "reason": _friendly_feature_reason(
                    name,
                    value,
                    label,
                    float(shap_value),
                ),
                "source": "shap",
            }
        )
    return {
        "shapReasons": [detail["reason"] for detail in details],
        "shapDetails": details,
    }


def _friendly_feature_reason(name, value, label, shap_value):
    if shap_value < 0:
        return _reduced_support_reason(name, value, label)

    if name == "score":
        return _score_reason(value, label)
    if name == "averageScore":
        return _average_score_reason(value, label)
    if name == "correctRate":
        return _correct_rate_reason(value, label)
    if name == "attemptsCount":
        return _attempt_count_reason(value, label)
    if name == "bktMasteryProbability":
        return _bkt_reason(value, label)
    if name == "retryCount":
        return _retry_count_reason(value, label)
    if name == "scoreChange":
        return _score_change_reason(value, label)
    if name == "scoreConsistency":
        return _score_consistency_reason(value, label)
    if name == "averageWrongCount":
        return _average_wrong_count_reason(value, label)
    if name == "averageTimeTakenSeconds":
        return _average_time_reason(value, label)

    return {
        "wrongCount": "High wrong count",
        "timeTakenSeconds": "Long completion time",
        "difficultyLevel": "Harder question difficulty",
        "recentTrend": "Recent trend changed",
    }.get(name, f"{name}: {value}")


def _reduced_support_reason(name, value, label):
    if name == "attemptsCount" and value <= 1:
        return f"Only {int(value)} attempt is available, reducing support for {label}"
    return f"{_feature_label(name)} reduced support for {label}"


def _score_reason(value, label):
    if value < 50:
        return "Recent score is near the weak range"
    if value < 80:
        return "Recent score is in the moderate range"
    return "Recent score is in the strong range"


def _average_score_reason(value, label):
    if value < 50:
        return "Average score is near the weak range"
    if value < 80:
        return "Average score is in the moderate range"
    return "Average score is in the strong range"


def _correct_rate_reason(value, label):
    if value < 0.5:
        return "Correct rate shows many missed questions"
    if value < 0.8:
        return "Correct rate is around the moderate range"
    return "Correct rate is high"


def _attempt_count_reason(value, label):
    count = int(value)
    if count <= 1:
        return "Only one attempt is available"
    if label == "Weak":
        return "Repeated attempts still show weakness"
    if label == "Moderate":
        return "Several attempts show steady practice"
    return "Several attempts support consistent strength"


def _bkt_reason(value, label):
    if value < 0.45:
        return "BKT mastery probability is low"
    if value <= 0.75:
        return "BKT mastery probability is moderate"
    return "BKT mastery probability is high"


def _score_change_reason(value, label):
    if value > 0:
        return "Recent score is improving"
    if value < 0:
        return "Recent score has declined"
    return "Recent score is stable"


def _score_consistency_reason(value, label):
    if value <= 6:
        return "Scores are consistent"
    if label == "Weak":
        return "Scores vary and still show weakness"
    return "Scores vary across attempts"


def _average_wrong_count_reason(value, label):
    if value <= 1:
        return "Average wrong count is low"
    if label == "Weak":
        return "Average wrong count shows repeated mistakes"
    return "Average wrong count is moderate"


def _average_time_reason(value, label):
    if value <= 120:
        return "Average completion time is efficient"
    if label == "Weak":
        return "Average completion time is high"
    return "Average completion time is moderate"


def _retry_count_reason(value, label):
    if value <= 0:
        return "No retry was needed"
    if label == "Weak":
        return "Repeated retry suggests difficulty"
    return "Retry history influenced this prediction"


def _feature_label(name):
    return {
        "score": "Recent score",
        "averageScore": "Average score",
        "correctRate": "Correct rate",
        "wrongCount": "Wrong count",
        "averageWrongCount": "Average wrong count",
        "timeTakenSeconds": "Completion time",
        "averageTimeTakenSeconds": "Average completion time",
        "retryCount": "Retry count",
        "difficultyLevel": "Difficulty level",
        "attemptsCount": "Attempt count",
        "scoreChange": "Score change",
        "scoreConsistency": "Score consistency",
        "recentTrend": "Recent trend",
        "bktMasteryProbability": "BKT mastery probability",
    }.get(name, name)
