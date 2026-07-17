"""Print/apply the narrow U8 runtime identity bindings for a deployment run."""

from __future__ import annotations

import argparse
import subprocess


PROJECT_ID = "logic-oasis-fyp"
SERVICE_ACCOUNT = f"logic-oasis-ai-runtime@{PROJECT_ID}.iam.gserviceaccount.com"
ALLOWED_PROJECT_ROLES = ("roles/datastore.user", "roles/logging.logWriter")
MODEL_BUCKET_ROLE = "roles/storage.objectViewer"


def commands(*, model_bucket: str) -> list[list[str]]:
    base = ["gcloud", "iam", "service-accounts", "create", "logic-oasis-ai-runtime", "--project", PROJECT_ID,
            "--display-name", "Logic Oasis U8 AI runtime"]
    bindings = [["gcloud", "projects", "add-iam-policy-binding", PROJECT_ID, "--member", f"serviceAccount:{SERVICE_ACCOUNT}",
                 "--role", role] for role in ALLOWED_PROJECT_ROLES]
    bindings.append(["gcloud", "storage", "buckets", "add-iam-policy-binding", model_bucket,
                     "--member", f"serviceAccount:{SERVICE_ACCOUNT}", "--role", MODEL_BUCKET_ROLE])
    return [base, *bindings]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-bucket", required=True, help="gs:// bucket containing approved model artifacts")
    parser.add_argument("--apply", action="store_true", help="execute commands; default only prints them")
    args = parser.parse_args()
    for command in commands(model_bucket=args.model_bucket):
        print(" ".join(command))
        if args.apply:
            subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
