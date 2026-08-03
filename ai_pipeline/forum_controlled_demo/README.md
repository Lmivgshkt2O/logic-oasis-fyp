# Forum controlled-demonstration corpus

`forum_scenario_catalog_v1.yaml` is the authoritative source for this fictional,
developer-authored corpus. It contains no learner identity, copied forum text,
answer keys, or real-learner distribution claims. Generated JSONL and evidence
files must be rebuilt by `training/evaluate_forum_classifier.py`; editing a
generated row manually invalidates its hash.

The emulator fixture remains under `logic_oasis_ai/forum_ai/data/` and is never
an input to this evaluation. Evidence here is limited to
`controlled_demonstration_only` and cannot support real-learner accuracy,
generalisability, educational-effectiveness, or superiority claims.

From the repository root, rebuild with:

```powershell
$env:PYTHONPATH='ai_pipeline'
$env:FORUM_DEMO_OPERATOR_ROLE='developer'
.\functions\venv\Scripts\python.exe -m training.evaluate_forum_classifier
```

The command writes the canonical JSONL, dataset manifest, grouped split
manifest, eligible-candidate artifact and manifest under `generated/`, plus the
machine/human reports under `ai_pipeline/reports/`. The execution record is
deliberately volatile and excluded from every canonical content hash.
