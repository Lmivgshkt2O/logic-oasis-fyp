"""Declarative least-privilege IAM contract for the AQC-7 study boundary.

The dedicated policy-evaluation admin identity alone receives the allocation
secret accessor; the Canonical U8 runtime identity keeps its existing
finalization role and never receives it.  No identity may hold broad or
signing roles, and the export identity's own AQC-6 contract remains separate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


PROJECT_ID = "logic-oasis-fyp"
FUNCTION_REGION = "asia-southeast1"
POLICY_EVALUATION_ADMIN_SERVICE_ACCOUNT = (
    "logic-oasis-policy-evaluation-admin@logic-oasis-fyp.iam.gserviceaccount.com"
)
AI_RUNTIME_SERVICE_ACCOUNT = (
    "logic-oasis-ai-runtime@logic-oasis-fyp.iam.gserviceaccount.com"
)
ALLOCATION_SECRET = "POLICY_EVALUATION_ALLOCATION_KEY"
POLICY_EVALUATION_ADMIN_ROLES = (
    "roles/datastore.user",
    "roles/logging.logWriter",
)
POLICY_EVALUATION_ADMIN_SERVICES = (
    "managepolicyevaluationstudy",
    "recordpolicyevaluationconsent",
    "managepolicyevaluationenrollment",
)


@dataclass(frozen=True)
class IamBinding:
    principal: str
    role: str
    resource: str


def build_bindings(
    *,
    project_id: str = PROJECT_ID,
    allocation_secret_version: str = "v1",
) -> tuple[IamBinding, ...]:
    """Return the exact AQC-7 admin allow-list for the allocation secret."""
    if not allocation_secret_version:
        raise ValueError("allocation_secret_version is required")
    project = f"projects/{project_id}"
    secret = f"{project}/secrets/{ALLOCATION_SECRET}"
    return (
        IamBinding(
            POLICY_EVALUATION_ADMIN_SERVICE_ACCOUNT,
            "roles/datastore.user",
            project,
        ),
        IamBinding(
            POLICY_EVALUATION_ADMIN_SERVICE_ACCOUNT,
            "roles/logging.logWriter",
            project,
        ),
        IamBinding(
            POLICY_EVALUATION_ADMIN_SERVICE_ACCOUNT,
            "roles/secretmanager.secretAccessor",
            secret,
        ),
    )


def validate_bindings(
    bindings: Iterable[IamBinding],
    *,
    project_id: str = PROJECT_ID,
    allocation_secret_version: str = "v1",
) -> None:
    """Reject missing, broad, cross-identity, or model-scoped bindings."""
    actual = frozenset(bindings)
    denied_role_fragments = ("owner", "editor", "signer", "serviceAccountTokenCreator")
    if any(
        fragment.lower() in binding.role.lower()
        for binding in actual
        for fragment in denied_role_fragments
    ):
        raise ValueError("broad or signing roles are forbidden for the admin identity")
    for binding in actual:
        if (
            binding.role == "roles/secretmanager.secretAccessor"
            and ALLOCATION_SECRET in binding.resource
            and binding.principal != POLICY_EVALUATION_ADMIN_SERVICE_ACCOUNT
        ):
            raise ValueError(
                "the allocation secret must be bound only to the evaluation admin identity"
            )
        if "model" in binding.resource:
            raise ValueError("policy-evaluation identities must not access model resources")
    expected = frozenset(
        build_bindings(
            project_id=project_id,
            allocation_secret_version=allocation_secret_version,
        )
    )
    if actual != expected:
        raise ValueError(
            "policy-evaluation admin IAM bindings must exactly match the AQC-7 contract"
        )


def deployment_commands(
    *,
    project_id: str = PROJECT_ID,
    allocation_secret_version: str = "v1",
) -> tuple[tuple[str, ...], ...]:
    """Render reviewable gcloud commands without carrying a secret value."""
    commands: list[tuple[str, ...]] = []
    for binding in build_bindings(
        project_id=project_id,
        allocation_secret_version=allocation_secret_version,
    ):
        member = f"serviceAccount:{binding.principal}"
        if "/secrets/" in binding.resource:
            commands.append(
                (
                    "gcloud",
                    "secrets",
                    "add-iam-policy-binding",
                    ALLOCATION_SECRET,
                    f"--project={project_id}",
                    f"--member={member}",
                    f"--role={binding.role}",
                )
            )
        else:
            commands.append(
                (
                    "gcloud",
                    "projects",
                    "add-iam-policy-binding",
                    project_id,
                    f"--member={member}",
                    f"--role={binding.role}",
                )
            )
    for service in POLICY_EVALUATION_ADMIN_SERVICES:
        commands.append(
            (
                "gcloud",
                "run",
                "services",
                "add-iam-policy-binding",
                service,
                "--region",
                FUNCTION_REGION,
                "--project",
                project_id,
                "--member",
                "allUsers",
                "--role",
                "roles/run.invoker",
            )
        )
    return tuple(commands)


if __name__ == "__main__":
    for command in deployment_commands():
        print(" ".join(command))
