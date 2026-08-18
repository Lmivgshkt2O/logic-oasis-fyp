"""Print the least-privilege IAM commands for U10's forum runtime."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from forum_function_inventory import (
    FORUM_FUNCTION_INVENTORY,
    FORUM_INVENTORY_VERSION,
    FORUM_PROJECT,
    FORUM_REGION,
    FORUM_RUNTIME,
    FORUM_RUNTIME_SERVICE_ACCOUNT,
    forum_inventory_digest,
    validate_forum_function_inventory,
)


PROJECT_ID = FORUM_PROJECT
SERVICE_ACCOUNT = FORUM_RUNTIME_SERVICE_ACCOUNT
FUNCTION_REGION = FORUM_REGION
FORUM_RUNTIME_NAME = FORUM_RUNTIME
INVENTORY_VERSION = FORUM_INVENTORY_VERSION
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
        "--memory=512MiB",
        "--trigger-location", FUNCTION_REGION,
        "--trigger-service-account", SERVICE_ACCOUNT,
        "--trigger-event-filters",
        f"type={MODEL_FUNCTION_EVENTS[function_name]},database=(default)",
        "--trigger-event-filters-path-pattern", "document=forumAnswers/{answerId}",
        "--retry", "--service-account", SERVICE_ACCOUNT,
        "--set-env-vars",
        f"FORUM_MODEL_EVIDENCE_MODE={evidence_mode},FORUM_RUNTIME_CODE_REVISION={code_revision},FUNCTION_SIGNATURE_TYPE=cloudevent",
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


def preflight_checks(
    *,
    project_id: str,
    operator_account: str,
    region: str,
    runtime: str,
    evidence_mode: str,
    code_revision: str,
    inventory: Iterable[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Read-only preflight: reject every wrong-or-unsafe deployment input."""
    validate_forum_function_inventory(inventory)
    checks: list[dict[str, Any]] = []
    if project_id != PROJECT_ID:
        raise ValueError("deployment targets the wrong Firebase project")
    checks.append({"check": "project", "project": project_id, "ok": True})
    if not operator_account or operator_account in {
        "serviceAccount:default",
        "serviceAccount:runtime",
        "default-compute",
        "compute",
    }:
        raise ValueError("the default or runtime compute identity cannot be the release operator")
    if operator_account == f"serviceAccount:{SERVICE_ACCOUNT}":
        raise ValueError("the forum runtime identity cannot be its own release operator")
    checks.append({"check": "operator", "operator": operator_account, "ok": True})
    if region != FUNCTION_REGION:
        raise ValueError("deployment region must be asia-southeast1")
    if runtime != FORUM_RUNTIME_NAME:
        raise ValueError("deployment runtime must be python311")
    checks.append({"check": "runtime", "region": region, "runtime": runtime, "ok": True})
    if evidence_mode not in {"controlled_demo", "real_evaluated_only"}:
        raise ValueError("forum model evidence mode is not recognized")
    if re.fullmatch(r"[0-9a-f]{64}", code_revision) is None:
        raise ValueError("forum runtime code revision is invalid")
    checks.append({"check": "evidence", "evidenceMode": evidence_mode, "ok": True})
    checks.append({
        "check": "inventory",
        "inventoryVersion": INVENTORY_VERSION,
        "entryCount": len(validate_forum_function_inventory(inventory)),
        "inventorySha256": forum_inventory_digest(inventory),
        "ok": True,
    })
    return checks


def deploy_command(
    entry: Mapping[str, Any],
    *,
    evidence_mode: str,
    code_revision: str,
    functions_root: Path | None = None,
) -> list[str]:
    source = functions_root or FUNCTIONS_ROOT
    environment = (
        f"FORUM_MODEL_EVIDENCE_MODE={evidence_mode},"
        f"FORUM_RUNTIME_CODE_REVISION={code_revision}"
    )
    command = [
        "gcloud", "functions", "deploy", str(entry["name"]),
        "--gen2", "--region", str(entry["region"]), "--project", PROJECT_ID,
        "--source", str(source),
        "--runtime", str(entry["runtime"]),
        "--entry-point", str(entry["name"]),
        "--service-account", str(entry["serviceAccount"]),
        "--set-env-vars",
        environment,
    ]
    if entry["kind"] == "trigger":
        # Firebase Python Gen2 handlers are CloudEvent functions: the
        # framework must receive the single event argument, and Eventarc
        # delivers through the dedicated runtime identity. The ML bundle needs
        # more than the 256 MiB default.
        command.extend([
            "--memory=512MiB",
            "--trigger-location", str(entry["region"]),
            "--trigger-service-account", str(entry["serviceAccount"]),
            "--trigger-event-filters",
            f"type={entry['eventType']},database=(default)",
            "--trigger-event-filters-path-pattern",
            f"document={entry['document']}",
        ])
        command[command.index("--set-env-vars") + 1] = (
            f"{environment},FUNCTION_SIGNATURE_TYPE=cloudevent"
        )
        if entry.get("retry") is True:
            command.append("--retry")
    else:
        command.extend(["--trigger-http", "--allow-unauthenticated"])
    return command


def deploy_commands(
    *,
    evidence_mode: str,
    code_revision: str,
    inventory: Iterable[Mapping[str, Any]] | None = None,
) -> list[list[str]]:
    entries = validate_forum_function_inventory(inventory)
    return [
        deploy_command(entry, evidence_mode=evidence_mode, code_revision=code_revision)
        for entry in entries
    ]


def inspection_commands(
    *,
    inventory: Iterable[Mapping[str, Any]] | None = None,
) -> list[list[str]]:
    entries = validate_forum_function_inventory(inventory)
    return [
        ["gcloud", "functions", "describe", str(entry["name"]),
         "--region", str(entry["region"]), "--project", PROJECT_ID,
         "--format=json"]
        for entry in entries
    ]


def deployment_attestation(
    *,
    release_manifest: Mapping[str, Any],
    observed_functions: Mapping[str, Mapping[str, Any]],
    attested_at: str,
) -> dict[str, Any]:
    """Build a live deployment attestation only when every entry matches."""
    entries = validate_forum_function_inventory()
    expected_names = {str(entry["name"]) for entry in entries}
    if set(observed_functions) != expected_names:
        raise ValueError("observed function inventory is incomplete or extra")
    for entry in entries:
        observed = observed_functions.get(str(entry["name"]))
        if observed is None:
            raise ValueError(f"missing observed function {entry['name']}")
        if observed.get("region") != FUNCTION_REGION:
            raise ValueError(f"observed function {entry['name']} region mismatch")
        if observed.get("serviceAccount") != SERVICE_ACCOUNT:
            raise ValueError(f"observed function {entry['name']} identity mismatch")
        if observed.get("runtime") != FORUM_RUNTIME_NAME:
            raise ValueError(f"observed function {entry['name']} runtime mismatch")
        if observed.get("codeRevision") != release_manifest.get("codeRevision"):
            raise ValueError(f"observed function {entry['name']} revision mismatch")
    attestation = {
        "attestationKind": "live_deployment_attestation_v1",
        "attestationSchemaVersion": "forum-deployment-attestation-v1",
        "project": PROJECT_ID,
        "region": FUNCTION_REGION,
        "releaseId": release_manifest.get("releaseId"),
        "codeRevision": release_manifest.get("codeRevision"),
        "inventoryVersion": INVENTORY_VERSION,
        "functionInventorySha256": forum_inventory_digest(),
        "observedFunctionCount": len(observed_functions),
        "deploymentState": "deployed",
        "attestedAt": attested_at,
    }
    attestation["attestationSha256"] = __import__("hashlib").sha256(
        json.dumps(attestation, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return attestation


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Forum deployment helper. Read-only preflight/dry-run by default; "
            "pass --apply to emit (not execute) apply commands for every entry."
        ),
    )
    parser.add_argument("--evidence-mode", required=True)
    parser.add_argument("--code-revision", required=True)
    parser.add_argument("--operator-account", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    checks = preflight_checks(
        project_id=PROJECT_ID,
        operator_account=args.operator_account,
        region=FUNCTION_REGION,
        runtime=FORUM_RUNTIME_NAME,
        evidence_mode=args.evidence_mode,
        code_revision=args.code_revision,
    )
    print(json.dumps({"preflight": checks}, sort_keys=True))
    if args.apply:
        for command in deploy_commands(
            evidence_mode=args.evidence_mode, code_revision=args.code_revision,
        ):
            print(" ".join(command))
    else:
        print("Dry-run: no deployment commands emitted. Re-run with --apply.")
