from pathlib import Path


def initialize_firestore(service_account_path):
    import firebase_admin
    from firebase_admin import credentials, firestore

    path = Path(service_account_path)
    if not path.exists():
        raise FileNotFoundError(f"Service account key not found: {path}")

    if not firebase_admin._apps:
        cred = credentials.Certificate(str(path))
        firebase_admin.initialize_app(cred)
    return firestore.client()


def load_quiz_attempts(db, student_id=None, exclude_demo=False):
    from google.cloud.firestore_v1 import FieldFilter

    attempts = []
    query = db.collection("quizAttempts")
    if student_id:
        query = query.where(filter=FieldFilter("studentId", "==", student_id))

    for doc in query.stream():
        data = doc.to_dict() or {}
        attempt_student_id = data.get("studentId")
        topic_id = data.get("topicId")
        if not attempt_student_id or not topic_id:
            continue
        if exclude_demo and _is_demo_student(attempt_student_id):
            continue

        correct_count = _number(data.get("correctCount"), 0)
        total_questions = _number(data.get("totalQuestions"), 0)
        correct_rate = data.get("correctRate")
        if correct_rate is None and total_questions:
            correct_rate = correct_count / total_questions

        created_at = data.get("createdAt")
        attempts.append(
            {
                "id": doc.id,
                "studentId": attempt_student_id,
                "topicId": topic_id,
                "topicTitle": data.get("topicTitle") or topic_id,
                "yearLevel": _number(
                    data.get("yearLevel"),
                    _year_from_topic_id(topic_id),
                ),
                "score": _number(data.get("score"), 0),
                "correctRate": float(correct_rate or 0),
                "correctCount": correct_count,
                "totalQuestions": total_questions,
                "wrongCount": _number(
                    data.get("wrongCount"),
                    max(total_questions - correct_count, 0),
                ),
                "timeTakenSeconds": _number(data.get("timeTakenSeconds"), 0),
                "retryCount": _number(data.get("retryCount"), 0),
                "difficultyLevel": data.get("difficultyLevel") or "Mixed",
                "createdAtSort": _timestamp_sort_value(created_at),
            }
        )
    return attempts


def load_topic_titles(db):
    titles = {}
    for doc in db.collection("topics").stream():
        data = doc.to_dict() or {}
        titles[doc.id] = data.get("title") or doc.id
    return titles


def load_quiz_attempt_student_summary(db):
    summary = {}
    for doc in db.collection("quizAttempts").stream():
        data = doc.to_dict() or {}
        student_id = data.get("studentId")
        topic_id = data.get("topicId")
        if not student_id:
            continue

        item = summary.setdefault(
            student_id,
            {
                "attempts": 0,
                "topics": set(),
            },
        )
        item["attempts"] += 1
        if topic_id:
            item["topics"].add(topic_id)

    return {
        student_id: {
            "attempts": item["attempts"],
            "topics": sorted(item["topics"]),
        }
        for student_id, item in sorted(summary.items())
    }


def save_ai_outputs(db, outputs):
    from firebase_admin import firestore

    batch = db.batch()
    for output in outputs:
        run_ref = db.collection("aiModelRuns").document(output["runId"])
        mastery_ref = db.collection("topicMastery").document(
            f"{output['studentId']}_y{output['yearLevel']}_{output['topicId']}"
        )
        run_data = dict(output)
        run_data.pop("runId", None)
        run_data["createdAt"] = firestore.SERVER_TIMESTAMP

        mastery_data = {
            "studentId": output["studentId"],
            "topicId": output["topicId"],
            "yearLevel": output["yearLevel"],
            "masteryLevel": output["finalMasteryLabel"],
            "bktMasteryProbability": output["bktMasteryProbability"],
            "weaknessProbability": output["weaknessProbability"],
            "recentTrend": output["recentTrend"],
            "attemptsCount": output["attemptsCount"],
            "shapReasons": output["shapReasons"],
            "shapDetails": output["shapDetails"],
            "aiUpdatedAt": firestore.SERVER_TIMESTAMP,
        }
        batch.set(run_ref, run_data, merge=True)
        batch.set(mastery_ref, mastery_data, merge=True)
    batch.commit()


def _number(value, fallback):
    if isinstance(value, (int, float)):
        return value
    return fallback


def _timestamp_sort_value(value):
    if hasattr(value, "timestamp"):
        return value.timestamp()
    return str(value or "")


def _year_from_topic_id(topic_id):
    if topic_id.endswith("_y4"):
        return 4
    if topic_id.endswith("_y5"):
        return 5
    if topic_id.endswith("_y6"):
        return 6
    return 4


def _is_demo_student(student_id):
    return student_id.startswith("student_")
