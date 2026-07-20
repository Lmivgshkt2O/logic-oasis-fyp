import argparse
from datetime import datetime, timezone

from bkt import update_bkt_mastery
from feature_engineering import build_features, group_attempts
from firestore_io import (
    initialize_firestore,
    load_quiz_attempts,
    load_quiz_attempt_student_summary,
    load_topic_titles,
    save_ai_outputs,
)
from modeling import (
    final_mastery_label,
    predict_with_xgboost_or_fallback,
    recommended_action,
)

MODEL_NAME = "xgboost_shap_bkt_v1"


def build_ai_outputs(attempts, topic_titles):
    grouped = group_attempts(attempts)
    records = []

    for (student_id, topic_id), topic_attempts in grouped.items():
        features, recent_trend = build_features(topic_attempts)
        bkt = update_bkt_mastery(topic_attempts)
        record = {
            "studentId": student_id,
            "topicId": topic_id,
            "topicTitle": topic_titles.get(topic_id, topic_id),
            "yearLevel": topic_attempts[-1].get("yearLevel", 4),
            "recentTrend": recent_trend,
            **features,
            **bkt,
        }
        records.append(record)

    predictions = predict_with_xgboost_or_fallback(records)
    outputs = []
    now_key = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    for record, prediction in zip(records, predictions):
        final_label = final_mastery_label(
            prediction["xgboostPrediction"],
            prediction["weaknessProbability"],
            record["bktMasteryProbability"],
        )
        topic_title = record["topicTitle"]
        run_id = f"{record['studentId']}_{record['topicId']}_{now_key}"
        outputs.append(
            {
                "runId": run_id,
                "studentId": record["studentId"],
                "topicId": record["topicId"],
                "yearLevel": record["yearLevel"],
                "modelName": MODEL_NAME,
                "xgboostPrediction": prediction["xgboostPrediction"],
                "weaknessProbability": prediction["weaknessProbability"],
                "confidence": prediction["confidence"],
                "shapReasons": prediction["shapReasons"],
                "shapDetails": prediction["shapDetails"],
                "bktPriorKnowledge": record["bktPriorKnowledge"],
                "bktLearnRate": record["bktLearnRate"],
                "bktGuessRate": record["bktGuessRate"],
                "bktSlipRate": record["bktSlipRate"],
                "bktMasteryProbability": record["bktMasteryProbability"],
                "finalMasteryLabel": final_label,
                "recommendedAction": recommended_action(topic_title, final_label),
                "recentTrend": record["recentTrend"],
                "attemptsCount": record["attemptsCount"],
            }
        )

    return outputs


def main():
    parser = argparse.ArgumentParser(
        description="Run Logic Oasis Grey Box AI diagnosis pipeline."
    )
    parser.add_argument(
        "--service-account",
        default="../firebase_seed/serviceAccountKey.json",
        help="Path to Firebase serviceAccountKey.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print AI outputs without writing to Firestore.",
    )
    parser.add_argument(
        "--student-id",
        help="Only process quiz attempts for this Firebase Auth UID.",
    )
    parser.add_argument(
        "--exclude-demo",
        action="store_true",
        help="Skip seeded demo students whose IDs start with 'student_'.",
    )
    args = parser.parse_args()

    db = initialize_firestore(args.service_account)
    attempts = load_quiz_attempts(
        db,
        student_id=args.student_id,
        exclude_demo=args.exclude_demo,
    )
    if not attempts:
        print("No matching quizAttempts found. Complete quizzes first.")
        if args.student_id:
            print(f"Requested studentId: {args.student_id}")
            summary = load_quiz_attempt_student_summary(db)
            if summary:
                print("Available quizAttempts studentId values:")
                for student_id, details in summary.items():
                    topics = ", ".join(details["topics"]) or "-"
                    print(
                        f"- {student_id} "
                        f"({details['attempts']} attempt(s); topics: {topics})"
                    )
            else:
                print("No quizAttempts exist in this Firebase project.")
        return

    topic_titles = load_topic_titles(db)
    outputs = build_ai_outputs(attempts, topic_titles)

    for output in outputs:
        print(
            f"{output['studentId']} | {output['topicId']} | "
            f"{output['finalMasteryLabel']} | weakness={output['weaknessProbability']} | "
            f"bkt={output['bktMasteryProbability']}"
        )

    if args.dry_run:
        print("Dry run only. Firestore was not updated.")
        return

    save_ai_outputs(db, outputs)
    print(f"Saved {len(outputs)} AI diagnosis result(s) to Firestore.")


if __name__ == "__main__":
    main()
