"""Validated, de-identified input contract for the U10 label dataset."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .classifier import REVISION, SUFFICIENT

ALLOWED_PROVENANCE = frozenset({"real", "approved_external", "synthetic_test"})
ALLOWED_FIELDS = frozenset({"text", "label", "provenance", "reviewer", "authorGroup"})


@dataclass(frozen=True)
class LabelledForumExample:
    text: str
    label: str
    provenance: str
    reviewer: str
    author_group: str


def load_labelled_examples(path: str | Path) -> list[LabelledForumExample]:
    examples: list[LabelledForumExample] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON at line {line_number}") from error
        if not isinstance(value, dict):
            raise ValueError(f"label row {line_number} must be an object")
        unknown = set(value) - ALLOWED_FIELDS
        if unknown:
            raise ValueError(f"label row {line_number} contains unsupported field(s): {sorted(unknown)}")
        text = value.get("text")
        label = value.get("label")
        provenance = value.get("provenance")
        reviewer = value.get("reviewer")
        author_group = value.get("authorGroup")
        if not isinstance(text, str) or len(text.strip()) < 8:
            raise ValueError(f"label row {line_number} needs de-identified answer text")
        if label not in {SUFFICIENT, REVISION}:
            raise ValueError(f"label row {line_number} has an unknown rubric label")
        if provenance not in ALLOWED_PROVENANCE:
            raise ValueError(f"label row {line_number} has unapproved provenance")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ValueError(f"label row {line_number} needs a reviewer reference")
        if not isinstance(author_group, str) or not author_group.strip():
            raise ValueError(f"label row {line_number} needs a de-identified author group")
        examples.append(LabelledForumExample(text.strip(), label, provenance, reviewer.strip(), author_group.strip()))
    if len(examples) < 4 or {example.label for example in examples} != {SUFFICIENT, REVISION}:
        raise ValueError("dataset needs at least four reviewed examples across both rubric labels")
    return examples


def grouped_rows(examples: Iterable[LabelledForumExample]) -> list[tuple[str, str]]:
    return [(example.text, example.label) for example in examples]
