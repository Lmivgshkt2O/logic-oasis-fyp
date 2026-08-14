"""Redact disallowed legacy embedded AI feedback from shared forum answers.

The U1 privacy contract keeps shared answer documents to allow-listed public
advisory state and non-sensitive run/revision references. Historical free-form
answers embedded ``message``, ``probability``, and diagnostic fields inside
``aiFeedback``; this one-time, dry-run-first migration removes those fields and
reports counts without printing content. It never reconstructs private history
or writes derived fields to the author-only projection.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from typing import Any

import firebase_admin
from firebase_admin import firestore


FUNCTIONS_ROOT = Path(__file__).resolve().parents[1] / "functions"
if str(FUNCTIONS_ROOT) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_ROOT))

from forum_runtime import (  # noqa: E402  (path setup above)
    LEGACY_EMBEDDED_FEEDBACK_ALLOWED,
    LEGACY_EMBEDDED_FEEDBACK_DISALLOWED,
)


EMULATOR_HOSTS = {"127.0.0.1:8080", "localhost:8080"}


def redaction_plan(database: Any, *, limit: int | None = None) -> dict[str, Any]:
    """Scan answers and return counts plus affected document IDs.

    No answer content is returned or printed; only the field names to remove.
    """
    scanned = 0
    with_embedded = 0
    needs_redaction = 0
    affected: list[tuple[str, list[str]]] = []
    query = database.collection("forumAnswers")
    if limit is not None:
        query = query.limit(limit)
    for snapshot in query.stream():
        scanned += 1
        data = snapshot.to_dict() or {}
        feedback = data.get("aiFeedback")
        if not isinstance(feedback, dict):
            continue
        with_embedded += 1
        remove = [
            field
            for field in feedback
            if field in LEGACY_EMBEDDED_FEEDBACK_DISALLOWED
            or field not in LEGACY_EMBEDDED_FEEDBACK_ALLOWED
        ]
        if remove:
            needs_redaction += 1
            affected.append((snapshot.id, remove))
    return {
        "scanned": scanned,
        "with_embedded_feedback": with_embedded,
        "needs_redaction": needs_redaction,
        "affected": affected,
    }


def apply_redactions(database: Any, affected: list[tuple[str, list[str]]]) -> int:
    """Idempotently redact the planned fields; returns the number changed."""
    changed = 0
    for answer_id, fields in affected:
        reference = database.collection("forumAnswers").document(answer_id)
        snapshot = reference.get()
        if snapshot is None or not snapshot.exists:
            continue
        data = snapshot.to_dict() or {}
        feedback = data.get("aiFeedback")
        if not isinstance(feedback, dict):
            continue
        remaining = {
            key: value for key, value in feedback.items() if key not in fields
        }
        if set(remaining) == set(feedback):
            continue
        if remaining:
            reference.update({"aiFeedback": remaining})
        else:
            reference.update({"aiFeedback": firestore.DELETE_FIELD})
        changed += 1
    return changed


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run-first redaction of disallowed legacy embedded forum AI "
            "feedback. Defaults to read-only; pass --apply to write."
        ),
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Write redactions. Without this flag the tool is read-only.",
    )
    parser.add_argument(
        "--project",
        default=os.environ.get("GCLOUD_PROJECT", "logic-oasis-fyp"),
        help="Firebase project id (default: logic-oasis-fyp).",
    )
    parser.add_argument(
        "--emulator", action="store_true",
        help="Require and use the local Firestore Emulator host.",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Optional bounded scan limit for dry runs.",
    )
    args = parser.parse_args(argv)

    if args.emulator:
        host = os.environ.get("FIRESTORE_EMULATOR_HOST", "")
        if host not in EMULATOR_HOSTS:
            raise SystemExit(
                "Refusing emulator mode: set FIRESTORE_EMULATOR_HOST to "
                "127.0.0.1:8080 or localhost:8080."
            )
        os.environ["FIRESTORE_EMULATOR_HOST"] = host

    firebase_admin.initialize_app(options={"projectId": args.project})
    database = firestore.client()
    plan = redaction_plan(database, limit=args.limit)
    changed = 0
    if args.apply and plan["needs_redaction"]:
        changed = apply_redactions(database, plan["affected"])
    mode = "apply" if args.apply else "dry-run"
    print(
        "forum_feedback_migration "
        f"mode={mode} scanned={plan['scanned']} "
        f"with_embedded_feedback={plan['with_embedded_feedback']} "
        f"needs_redaction={plan['needs_redaction']} changed={changed}"
    )
    if plan["needs_redaction"] and not args.apply:
        print("Dry-run: no writes performed. Re-run with --apply to redact.")


if __name__ == "__main__":
    main()
