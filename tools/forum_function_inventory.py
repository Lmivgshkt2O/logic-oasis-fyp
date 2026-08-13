"""Authoritative, versioned nine-entry forum function inventory.

Deployment, post-deploy inspection, promotion attestation, and evidence all
share this single inventory. Every entry uses ``asia-southeast1`` and the
dedicated forum runtime identity; only the answer create/update triggers
enable Eventarc retry.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Iterable, Mapping


FORUM_PROJECT = "logic-oasis-fyp"
FORUM_REGION = "asia-southeast1"
FORUM_RUNTIME_SERVICE_ACCOUNT = (
    "logic-oasis-forum-runtime@logic-oasis-fyp.iam.gserviceaccount.com"
)
FORUM_RUNTIME = "python311"
FORUM_INVENTORY_VERSION = "forum-function-inventory-v1"
CALLABLES = (
    "openOrCreateForumDiscussion",
    "submitLinkedForumAnswer",
    "editLinkedForumAnswer",
    "markForumAnswerHelpful",
    "acceptForumAnswer",
    "reportForumContent",
)
TRIGGERS = (
    {
        "kind": "trigger", "name": "processForumQuestion",
        "region": FORUM_REGION,
        "serviceAccount": FORUM_RUNTIME_SERVICE_ACCOUNT,
        "runtime": FORUM_RUNTIME,
        "document": "forumQuestions/{questionId}",
        "eventType": "google.cloud.firestore.document.v1.created",
        "retry": False,
    },
    {
        "kind": "trigger", "name": "processForumAnswer",
        "region": FORUM_REGION,
        "serviceAccount": FORUM_RUNTIME_SERVICE_ACCOUNT,
        "runtime": FORUM_RUNTIME,
        "document": "forumAnswers/{answerId}",
        "eventType": "google.cloud.firestore.document.v1.created",
        "retry": True,
    },
    {
        "kind": "trigger", "name": "reprocessForumAnswer",
        "region": FORUM_REGION,
        "serviceAccount": FORUM_RUNTIME_SERVICE_ACCOUNT,
        "runtime": FORUM_RUNTIME,
        "document": "forumAnswers/{answerId}",
        "eventType": "google.cloud.firestore.document.v1.updated",
        "retry": True,
    },
)
FORUM_FUNCTION_INVENTORY = tuple(
    (
        {
            "kind": "callable", "name": name,
            "region": FORUM_REGION,
            "serviceAccount": FORUM_RUNTIME_SERVICE_ACCOUNT,
            "runtime": FORUM_RUNTIME,
            "retry": False,
        }
        for name in CALLABLES
    )
) + TRIGGERS


def validate_forum_function_inventory(
    inventory: Iterable[Mapping[str, Any]] | None = None,
) -> tuple[Mapping[str, Any], ...]:
    entries = tuple(inventory or FORUM_FUNCTION_INVENTORY)
    names = [str(entry["name"]) for entry in entries]
    if len(entries) != 9 or len(names) != len(set(names)):
        raise ValueError("forum inventory must contain exactly nine unique functions")
    if {str(entry["kind"]) for entry in entries} != {"callable", "trigger"}:
        raise ValueError("forum inventory must contain callables and triggers")
    for entry in entries:
        if entry.get("region") != FORUM_REGION:
            raise ValueError("every forum function must use asia-southeast1")
        if entry.get("serviceAccount") != FORUM_RUNTIME_SERVICE_ACCOUNT:
            raise ValueError("every forum function must use the dedicated runtime identity")
        if entry.get("runtime") != FORUM_RUNTIME:
            raise ValueError("every forum function must use the python311 runtime")
        if entry.get("kind") == "callable":
            if entry.get("retry") is not False:
                raise ValueError("callables must not enable Eventarc retry")
        else:
            if entry.get("document") not in {"forumQuestions/{questionId}", "forumAnswers/{answerId}"}:
                raise ValueError("forum trigger document path is not recognized")
            if entry.get("eventType") not in {
                "google.cloud.firestore.document.v1.created",
                "google.cloud.firestore.document.v1.updated",
            }:
                raise ValueError("forum trigger event type is not recognized")
            if entry.get("retry") not in {True, False}:
                raise ValueError("forum trigger retry must be a boolean")
    # Only the answer create/update triggers enable retry.
    retrying = {
        str(entry["name"]) for entry in entries if entry.get("retry") is True
    }
    if retrying != {"processForumAnswer", "reprocessForumAnswer"}:
        raise ValueError("only the answer create/update triggers may enable retry")
    return entries


def forum_inventory_digest(
    inventory: Iterable[Mapping[str, Any]] | None = None,
) -> str:
    entries = validate_forum_function_inventory(inventory)
    payload = {
        "inventoryVersion": FORUM_INVENTORY_VERSION,
        "entries": list(entries),
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
