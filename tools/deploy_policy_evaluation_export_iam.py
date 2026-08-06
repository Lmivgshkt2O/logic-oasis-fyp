"""Declarative least-privilege IAM contract for AQC-6 policy-evaluation custody.

The dedicated export identity reads Firestore and the policy-evaluation export
HMAC secret only, writes only the protected release bucket, and can never read
model resources.  The retention identity owns deletion and key-version
destruction.  This module never prints secret values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


PROJECT_ID = "logic-oasis-fyp"
PROTECTED_BUCKET = "logic-oasis-fyp-protected-data"
HMAC_SECRET_PREFIX = "logic-oasis-policy-evaluation-export-key-v"
EXPORT_SERVICE_ACCOUNT = (
    "logic-oasis-policy-evaluation-export@logic-oasis-fyp.iam.gserviceaccount.com"
)
RETENTION_SERVICE_ACCOUNT = (
    "logic-oasis-policy-evaluation-retention@logic-oasis-fyp.iam.gserviceaccount.com"
)


@dataclass(frozen=True)
class IamBinding:
    principal: str
    role: str
    resource: str


def build_bindings(
    *, project_id: str = PROJECT_ID, hmac_secret_version: str = "v1"
) -> tuple[IamBinding, ...]:
    """Return the exact AQC-6 allow-list for one dedicated HMAC key series."""
    secret_name = f"{HMAC_SECRET_PREFIX}{hmac_secret_version.removeprefix('v')}"
    if not secret_name.startswith(HMAC_SECRET_PREFIX) or not hmac_secret_version:
        raise ValueError("hmac_secret_version must identify the policy-evaluation HMAC key")
    project = f"projects/{project_id}"
    bucket = f"gs://{PROTECTED_BUCKET}"
    secret = f"{project}/secrets/{secret_name}"
    return (
        IamBinding(EXPORT_SERVICE_ACCOUNT, "roles/datastore.viewer", project),
        IamBinding(EXPORT_SERVICE_ACCOUNT, "roles/storage.objectCreator", bucket),
        IamBinding(
            EXPORT_SERVICE_ACCOUNT, "roles/secretmanager.secretAccessor", secret
        ),
        IamBinding(RETENTION_SERVICE_ACCOUNT, "roles/storage.objectAdmin", bucket),
        IamBinding(
            RETENTION_SERVICE_ACCOUNT, "roles/secretmanager.secretVersionManager", secret
        ),
    )


def validate_bindings(
    bindings: Iterable[IamBinding],
    *,
    project_id: str = PROJECT_ID,
    hmac_secret_version: str = "v1",
) -> None:
    """Reject missing, broad, cross-resource, or role-escalating bindings."""
    actual = frozenset(bindings)
    expected = frozenset(
        build_bindings(project_id=project_id, hmac_secret_version=hmac_secret_version)
    )
    if actual != expected:
        raise ValueError(
            "policy-evaluation IAM bindings must exactly match the AQC-6 contract"
        )
    denied_role_fragments = ("owner", "editor", "signer", "serviceAccountTokenCreator")
    if any(
        fragment.lower() in binding.role.lower()
        for binding in actual
        for fragment in denied_role_fragments
    ):
        raise ValueError("broad or signing roles are forbidden for export identities")
    if any("model" in binding.resource for binding in actual):
        raise ValueError("policy-evaluation identities must not access model resources")


def deployment_commands(
    *, project_id: str = PROJECT_ID, hmac_secret_version: str = "v1"
) -> tuple[tuple[str, ...], ...]:
    """Render reviewable gcloud commands without carrying a secret value."""
    commands: list[tuple[str, ...]] = []
    for binding in build_bindings(
        project_id=project_id, hmac_secret_version=hmac_secret_version
    ):
        member = f"serviceAccount:{binding.principal}"
        if binding.resource.startswith("gs://"):
            commands.append(
                (
                    "gcloud",
                    "storage",
                    "buckets",
                    "add-iam-policy-binding",
                    binding.resource,
                    f"--member={member}",
                    f"--role={binding.role}",
                )
            )
        elif "/secrets/" in binding.resource:
            commands.append(
                (
                    "gcloud",
                    "secrets",
                    "add-iam-policy-binding",
                    binding.resource.rsplit("/", 1)[-1],
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
    return tuple(commands)


if __name__ == "__main__":
    for command in deployment_commands():
        print(" ".join(command))

