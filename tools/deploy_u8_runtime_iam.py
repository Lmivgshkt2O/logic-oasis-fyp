"""Print/apply the narrow U8 runtime identity bindings for a deployment run."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess


PROJECT_ID = "logic-oasis-fyp"
SERVICE_ACCOUNT = f"logic-oasis-ai-runtime@{PROJECT_ID}.iam.gserviceaccount.com"
ALLOWED_PROJECT_ROLES = (
    "roles/datastore.user",
    "roles/logging.logWriter",
    "roles/eventarc.eventReceiver",
)
MODEL_BUCKET_ROLE = "roles/storage.objectViewer"
RUN_INVOKER_ROLE = "roles/run.invoker"
FUNCTION_SERVICE = "processfinalizedquizattempt"
FUNCTION_REGION = "asia-southeast1"


def _gcloud_executable() -> str:
    """Resolve the Cloud CLI on Windows as well as POSIX deployment hosts."""
    return (
        os.environ.get("GCLOUD_BIN")
        or shutil.which("gcloud")
        or shutil.which("gcloud.cmd")
        or "gcloud"
    )


def commands(*, model_bucket: str) -> list[list[str]]:
    base = ["gcloud", "iam", "service-accounts", "create", "logic-oasis-ai-runtime", "--project", PROJECT_ID,
            "--display-name", "Logic Oasis U8 AI runtime"]
    bindings = [["gcloud", "projects", "add-iam-policy-binding", PROJECT_ID, "--member", f"serviceAccount:{SERVICE_ACCOUNT}",
                 "--role", role] for role in ALLOWED_PROJECT_ROLES]
    bindings.append(["gcloud", "storage", "buckets", "add-iam-policy-binding", model_bucket,
                     "--member", f"serviceAccount:{SERVICE_ACCOUNT}", "--role", MODEL_BUCKET_ROLE])
    return [base, *bindings]


def run_invoker_command() -> list[str]:
    """Grant Eventarc delivery only to the one deployed U8 service.

    Run this after the function has been deployed; the Cloud Run service does
    not exist during the initial identity bootstrap.
    """
    return [
        "gcloud", "run", "services", "add-iam-policy-binding", FUNCTION_SERVICE,
        "--region", FUNCTION_REGION,
        "--project", PROJECT_ID,
        "--member", f"serviceAccount:{SERVICE_ACCOUNT}",
        "--role", RUN_INVOKER_ROLE,
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-bucket", required=True, help="gs:// bucket containing approved model artifacts")
    parser.add_argument("--apply", action="store_true", help="execute commands; default only prints them")
    parser.add_argument("--grant-run-invoker", action="store_true",
                        help="also bind Eventarc delivery after the U8 Cloud Run service exists")
    args = parser.parse_args()
    requested = commands(model_bucket=args.model_bucket)
    if args.grant_run_invoker:
        requested.append(run_invoker_command())
    for command in requested:
        print(" ".join(command))
        if args.apply:
            subprocess.run([_gcloud_executable(), *command[1:]], check=True)


if __name__ == "__main__":
    main()
