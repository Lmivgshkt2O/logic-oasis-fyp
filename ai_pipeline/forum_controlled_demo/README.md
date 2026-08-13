# Forum controlled-demonstration corpus

`forum_verification_catalog_v1.yaml` is the authoritative source for this
fictional, developer-authored corpus. Every example carries truth labels for
correctness (linked contexts only), relevance, reasoning, and the composite
public decision across English, Bahasa Melayu, and mixed text. It contains no
learner identity, copied forum text, answer keys, or real-learner distribution
claims. Generated JSONL and evidence files must be rebuilt by
`training/evaluate_forum_classifier.py`; editing a generated row manually
invalidates its hash.

The evaluation trains and freezes two separately governed TF-IDF + Naive Bayes
components (reasoning and relevance) on grouped training/validation families,
runs the untouched grouped test exactly once, and applies the frozen composite
policy: deterministic correctness, relevance positive/negative thresholds, and
the reasoning abstention threshold. Precision is reported only over emitted
public decisions (`AI-verified` and `May be irrelevant`); abstentions reduce
coverage. Any false public decision, insufficient support, missing coverage,
leakage, provenance, or non-degeneracy gate publishes no candidate.

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
