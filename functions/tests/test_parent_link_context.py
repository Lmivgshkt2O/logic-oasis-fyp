from __future__ import annotations

from types import SimpleNamespace
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import parent_link_context as context


class _Snapshot:
    def __init__(self, data: dict | None) -> None:
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return self._data


class _Ref:
    def __init__(self, data: dict | None) -> None:
        self._data = data

    def get(self):
        return _Snapshot(self._data)


class _Query:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self.parent_id: str | None = None

    def where(self, field: str, operator: str, value: str):
        self.parent_id = value if field == "parentId" and operator == "==" else None
        return self

    def stream(self):
        return [_Snapshot(row) for row in self._rows if row["parentId"] == self.parent_id]


class _Links:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def where(self, field: str, operator: str, value: str):
        return _Query(self._rows).where(field, operator, value)


class _Users:
    def __init__(self, rows: dict[str, dict]) -> None:
        self._rows = rows

    def document(self, identifier: str) -> _Ref:
        return _Ref(self._rows.get(identifier))


class _Db:
    def __init__(self) -> None:
        self.links = _Links(
            [
                {"parentId": "parent_a", "studentId": "student_z", "status": "active"},
                {"parentId": "parent_a", "studentId": "student_revoked", "status": "revoked"},
                {"parentId": "parent_b", "studentId": "student_other", "status": "active"},
            ]
        )
        self.users = _Users(
            {
                "student_z": {"displayName": "Zara", "yearLevel": 5},
                "student_revoked": {"displayName": "Revoked", "yearLevel": 4},
                "student_other": {"displayName": "Other", "yearLevel": 4},
            }
        )

    def collection(self, name: str):
        return self.links if name == "parentLinks" else self.users


class ParentLinkContextTests(unittest.TestCase):
    def test_context_returns_only_active_children_for_authenticated_parent(self) -> None:
        response = context.list_active_linked_children(
            {}, context.VerifiedParent(uid="parent_a"), _Db()
        )

        self.assertEqual(
            response,
            {
                "children": [
                    {"studentId": "student_z", "displayName": "Zara", "yearLevel": 5},
                ],
            },
        )

    def test_context_rejects_mismatched_or_revoked_token(self) -> None:
        request = SimpleNamespace(
            auth=SimpleNamespace(uid="parent_a"),
            raw_request=SimpleNamespace(headers={"Authorization": "Bearer token"}),
        )
        with self.assertRaisesRegex(context.ParentLinkContextError, "credentials"):
            context.verify_authenticated_parent(
                request,
                verify_token=lambda *_args, **_kwargs: {"uid": "parent_b"},
            )
        with self.assertRaisesRegex(context.ParentLinkContextError, "no longer active"):
            context.verify_authenticated_parent(
                request,
                verify_token=lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("revoked")),
            )


if __name__ == "__main__":
    unittest.main()
