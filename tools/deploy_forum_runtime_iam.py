"""Print the least-privilege IAM commands for U10's forum runtime."""
from __future__ import annotations

from pathlib import Path
import re

PROJECT_ID = "logic-oasis-fyp"
SERVICE_ACCOUNT = "logic-oasis-forum-runtime@logic-oasis-fyp.iam.gserviceaccount.com"
RUNTIME_ROLES = ("roles/datastore.user", "roles/logging.logWriter")
EVIDENCE_MODES = ("real_evaluated_only", "controlled_demo")
FUNCTION_REGION = "asia-southeast1"
FUNCTIONS_ROOT = Path(__file__).resolve().parents[1] / "functions"
MODEL_FUNCTION_EVENTS = {
    "processForumAnswer": "google.cloud.firestore.document.v1.created",
    "reprocessForumAnswer": "google.cloud.firestore.document.v1.updated",
}


def commands(*, deployer_member: str = "serviceAccount:logic-oasis-deployer@logic-oasis-fyp.iam.gserviceaccount.com") -> list[list[str]]:
    runtime_member = f"serviceAccount:{SERVICE_ACCOUNT}"
    result = [
        ["gcloud", "projects", "add-iam-policy-binding", PROJECT_ID,
         f"--member={runtime_member}", f"--role={role}"]
        for role in RUNTIME_ROLES
    ]
    result.append([
        "gcloud", "iam", "service-accounts", "add-iam-policy-binding", SERVICE_ACCOUNT,
        f"--member={deployer_member}", "--role=roles/iam.serviceAccountUser",
    ])
    return result


def runtime_deploy_command(
    *, evidence_mode: str, code_revision: str,
    function_name: str = "processForumAnswer",
) -> list[str]:
    if evidence_mode not in EVIDENCE_MODES:
        raise ValueError("forum model evidence mode is not recognized")
    if re.fullmatch(r"[0-9a-f]{64}", code_revision) is None:
        raise ValueError("forum runtime code revision is invalid")
    if function_name not in MODEL_FUNCTION_EVENTS:
        raise ValueError("forum model function is not recognized")
    return [
        "gcloud", "functions", "deploy", function_name,
        "--gen2", "--region", FUNCTION_REGION, "--project", PROJECT_ID,
        "--source", str(FUNCTIONS_ROOT),
        "--runtime", "python311", "--entry-point", function_name,
        "--trigger-location", FUNCTION_REGION,
        "--trigger-event-filters",
        f"type={MODEL_FUNCTION_EVENTS[function_name]},database=(default)",
        "--trigger-event-filters-path-pattern", "document=forumAnswers/{answerId}",
        "--retry", "--service-account", SERVICE_ACCOUNT,
        "--set-env-vars",
        f"FORUM_MODEL_EVIDENCE_MODE={evidence_mode},FORUM_RUNTIME_CODE_REVISION={code_revision}",
    ]


def runtime_deploy_commands(*, evidence_mode: str, code_revision: str) -> list[list[str]]:
    return [
        runtime_deploy_command(
            evidence_mode=evidence_mode,
            code_revision=code_revision,
            function_name=function_name,
        )
        for function_name in MODEL_FUNCTION_EVENTS
    ]
