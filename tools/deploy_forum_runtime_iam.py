"""Print the least-privilege IAM commands for U10's forum runtime."""
from __future__ import annotations

PROJECT_ID = "logic-oasis-fyp"
SERVICE_ACCOUNT = "logic-oasis-forum-runtime@logic-oasis-fyp.iam.gserviceaccount.com"
RUNTIME_ROLES = ("roles/datastore.user", "roles/logging.logWriter")


def commands(*, deployer_member: str) -> list[list[str]]:
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
