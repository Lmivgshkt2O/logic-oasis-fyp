"""Print/apply the exact U9 parent-link administration IAM bindings."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess


PROJECT_ID = "logic-oasis-fyp"
PARENT_LINK_ADMIN_SERVICE_ACCOUNT = (
    f"logic-oasis-parent-link-admin@{PROJECT_ID}.iam.gserviceaccount.com"
)
IDENTITY_ADMIN_SERVICE_ACCOUNT = (
    f"logic-oasis-identity-admin@{PROJECT_ID}.iam.gserviceaccount.com"
)
PARENT_LINK_ADMIN_ROLES = ("roles/datastore.user", "roles/logging.logWriter")
IDENTITY_ADMIN_ROLES = (
    "roles/firebaseauth.admin",
    "roles/datastore.user",
    "roles/logging.logWriter",
)


def commands(*, deployer_member: str) -> list[list[str]]:
    if not deployer_member.startswith(("user:", "serviceAccount:")):
        raise ValueError("deployer_member must be a user: or serviceAccount: principal")
    create = [
        ["gcloud", "iam", "service-accounts", "create", "logic-oasis-parent-link-admin", "--project", PROJECT_ID,
         "--display-name", "Logic Oasis U9 parent-link runtime"],
        ["gcloud", "iam", "service-accounts", "create", "logic-oasis-identity-admin", "--project", PROJECT_ID,
         "--display-name", "Logic Oasis U9 identity administration"],
    ]
    bindings = [
        ["gcloud", "projects", "add-iam-policy-binding", PROJECT_ID,
         "--member", f"serviceAccount:{PARENT_LINK_ADMIN_SERVICE_ACCOUNT}", "--role", role]
        for role in PARENT_LINK_ADMIN_ROLES
    ]
    bindings += [
        ["gcloud", "projects", "add-iam-policy-binding", PROJECT_ID,
         "--member", f"serviceAccount:{IDENTITY_ADMIN_SERVICE_ACCOUNT}", "--role", role]
        for role in IDENTITY_ADMIN_ROLES
    ]
    bindings += [
        ["gcloud", "iam", "service-accounts", "add-iam-policy-binding", PARENT_LINK_ADMIN_SERVICE_ACCOUNT,
         "--member", deployer_member, "--role", "roles/iam.serviceAccountUser"],
        ["gcloud", "iam", "service-accounts", "add-iam-policy-binding", IDENTITY_ADMIN_SERVICE_ACCOUNT,
         "--member", deployer_member, "--role", "roles/iam.serviceAccountUser"],
    ]
    return [*create, *bindings]


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
