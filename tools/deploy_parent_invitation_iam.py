"""Print/apply the narrow U12 parent-invitation runtime IAM contract."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess


PROJECT_ID = "logic-oasis-fyp"
FUNCTION_REGION = "asia-southeast1"
SERVICE_ACCOUNT = f"logic-oasis-parent-invitation@{PROJECT_ID}.iam.gserviceaccount.com"
RUNTIME_ROLES = (
    "roles/firebaseauth.admin",  # generates the server-owned email sign-in link
    "roles/datastore.user",
    "roles/logging.logWriter",
)
# Values must be created and populated separately. Keeping the bindings at the
# individual-secret scope avoids granting this runtime project-wide secret
# access. SMTP may be replaced by an approved provider without changing the
# invitation's Firestore contract.
REQUIRED_SECRETS = (
    "PARENT_INVITATION_EMAIL_HMAC_KEY",
    "PARENT_INVITATION_SMTP_PASSWORD",
)
CALLABLES = (
    "createparentlinkinvitation",
    "acceptparentlinkinvitation",
    "declineparentlinkinvitation",
    "unlinkownparentlink",
)


def commands(*, deployer_member: str) -> list[list[str]]:
    if not deployer_member.startswith(("user:", "serviceAccount:")):
        raise ValueError("deployer_member must be a user: or serviceAccount: principal")
    result = [[
        "gcloud", "iam", "service-accounts", "create", "logic-oasis-parent-invitation",
        "--project", PROJECT_ID, "--display-name", "Logic Oasis U12 parent invitation runtime",
    ]]
    result += [[
        "gcloud", "projects", "add-iam-policy-binding", PROJECT_ID,
        "--member", f"serviceAccount:{SERVICE_ACCOUNT}", "--role", role,
    ] for role in RUNTIME_ROLES]
    result += [[
        "gcloud", "secrets", "add-iam-policy-binding", secret,
        "--project", PROJECT_ID,
        "--member", f"serviceAccount:{SERVICE_ACCOUNT}",
        "--role", "roles/secretmanager.secretAccessor",
    ] for secret in REQUIRED_SECRETS]
    result.append([
        "gcloud", "iam", "service-accounts", "add-iam-policy-binding", SERVICE_ACCOUNT,
        "--member", deployer_member, "--role", "roles/iam.serviceAccountUser",
    ])
    result += [[
        "gcloud", "run", "services", "add-iam-policy-binding", service,
        "--region", FUNCTION_REGION, "--project", PROJECT_ID,
        "--member", "allUsers", "--role", "roles/run.invoker",
    ] for service in CALLABLES]
    return result


def _gcloud() -> str:
    return os.environ.get("GCLOUD_BIN") or shutil.which("gcloud") or shutil.which("gcloud.cmd") or "gcloud"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployer-member", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    for command in commands(deployer_member=args.deployer_member):
        print(" ".join(command))
        if args.apply:
            subprocess.run([_gcloud(), *command[1:]], check=True)


if __name__ == "__main__":
    main()
