"""Print/apply the narrow U8 runtime identity bindings for a deployment run."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AI_ROOT = REPOSITORY_ROOT / "ai_pipeline"
FUNCTIONS_ROOT = REPOSITORY_ROOT / "functions"
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from logic_oasis_ai.model_registry import validate_model_bucket_uri as validate_model_bucket


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
EVIDENCE_MODES = ("real_evaluated_only", "controlled_demo")


def _gcloud_executable() -> str:
    """Resolve the Cloud CLI on Windows as well as POSIX deployment hosts."""
    return (
        os.environ.get("GCLOUD_BIN")
        or shutil.which("gcloud")
        or shutil.which("gcloud.cmd")
        or "gcloud"
    )


def commands(*, model_bucket: str) -> list[list[str]]:
    bucket_name = validate_model_bucket(model_bucket)
    bucket_uri = f"gs://{bucket_name}"
    base = ["gcloud", "iam", "service-accounts", "create", "logic-oasis-ai-runtime", "--project", PROJECT_ID,
            "--display-name", "Logic Oasis U8 AI runtime"]
    bindings = [["gcloud", "projects", "add-iam-policy-binding", PROJECT_ID, "--member", f"serviceAccount:{SERVICE_ACCOUNT}",
                 "--role", role] for role in ALLOWED_PROJECT_ROLES]
    bindings.append(["gcloud", "storage", "buckets", "add-iam-policy-binding", bucket_uri,
                     "--member", f"serviceAccount:{SERVICE_ACCOUNT}", "--role", MODEL_BUCKET_ROLE])
    return [base, *bindings]


def runtime_deploy_command(*, model_bucket: str, evidence_mode: str) -> list[str]:
    bucket_name = validate_model_bucket(model_bucket)
    if evidence_mode not in EVIDENCE_MODES:
        raise ValueError("AI model evidence mode is not recognized")
    return [
        "gcloud", "functions", "deploy", "processFinalizedQuizAttempt",
        "--gen2", "--region", FUNCTION_REGION, "--project", PROJECT_ID,
        "--source", str(FUNCTIONS_ROOT),
        "--runtime", "python311", "--entry-point", "processFinalizedQuizAttempt",
        "--trigger-location", FUNCTION_REGION,
        "--trigger-event-filters", "type=google.cloud.firestore.document.v1.written,database=(default)",
        "--trigger-event-filters-path-pattern", "document=quizAttempts/{attemptId}",
        "--service-account", SERVICE_ACCOUNT,
        "--set-env-vars", f"AI_MODEL_EVIDENCE_MODE={evidence_mode},AI_MODEL_BUCKET={bucket_name}",
    ]


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
    parser.add_argument("--deploy-runtime", action="store_true",
                        help="also deploy the runtime with explicit evidence-mode configuration")
    parser.add_argument("--evidence-mode", choices=EVIDENCE_MODES, default="real_evaluated_only")
    args = parser.parse_args()
    requested = commands(model_bucket=args.model_bucket)
    if args.grant_run_invoker:
        requested.append(run_invoker_command())
    if args.deploy_runtime:
        requested.append(runtime_deploy_command(
            model_bucket=args.model_bucket, evidence_mode=args.evidence_mode
        ))
    for command in requested:
        print(" ".join(command))
        if args.apply:
            subprocess.run([_gcloud_executable(), *command[1:]], check=True)


if __name__ == "__main__":
    main()
