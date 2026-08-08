# ASSISTments EDM Cup 2023 external-real-data path (J0)

This directory implements the J0 physical-source and U7-feasibility validation
for the approved **external real-data** evaluation route described in
`docs/plans/2026-08-07-001-feat-u7-assistments-edm-cup-2023-external-real-data-evaluation-plan.md`.

Status: **J0 GO**, **J1 complete**, **J2-v1 + J3-v1 complete (zero labels)**,
**J3A diagnostic complete**, and the **v2 amendment approved and implemented**
(J2-v2 + J3-v2; Grade 6 primary READY FOR J4). See
`docs/evidence/u7-assistments-source-validation.md`.

## Provenance boundary

ASSISTments rows are **external_real** evidence only. They must never be
relabelled as:

- `runtime_callable`
- Logic Oasis runtime real
- native `logic_oasis_quizAttempts`

Native Logic Oasis fields such as `finalizationStatus`, `validationStatus`,
`sourceAttemptSequence`, `contentVersionId`, runtime policy versions, or bank
assignment metadata are never fabricated onto ASSISTments rows. The schema
mapping records the exact detected physical columns instead of guessing them.

## Dataset and usage terms

- Source: ASSISTments EDM Cup 2023 (Kaggle competition data).
- Data terms: ASSISTments Data Terms of Use, effective 2020-10-30.
- Use is limited to non-commercial academic/research evaluation.
- Cite ASSISTments and the EDM Cup 2023 dataset in any resulting work.
- Do not attempt to de-anonymize users.
- Do not redistribute ASSISTments data.
- Code that processes the dataset may be committed; raw or derived
  learner-level source extracts must **not** be committed to Git.

The raw CSVs live under the protected external-data root, outside this Git
repository:

```text
logic-oasis-private-data/
  assistments_edm_cup_2023/
    raw/      <- source CSVs (never committed)
    j0/       <- J0 scan summaries (never committed)
    processed/<- future J1+ working extracts (never committed)
```

## Frozen U7 contract preserved for the external path

- Base feature schema: `quiz-attempt-features-v2`
- Base features: `correct_rate`, `mean_response_time_ms` only
- Prediction target: `next_attempt_support_needed`
- Prediction unit: one learner-specific in-unit assignment instance
- Source window: `2022-01-01T00:00:00Z` through `2023-12-31T23:59:59Z` inclusive
- Primary cohort: Grade 6 Mathematics (`sequence_folder_path_level_2 == "Grade 6"`)
- Correctness: first graded response (`correct_response`/`wrong_response`)
  after `problem_started`
- Response time: `(first graded response timestamp - problem_started timestamp)`
  in milliseconds; negative durations are rejected
- Excluded from base features: competition unit-test scores, hints, and
  explanations, and the ungraded `open_response` action

## Files

- `assistments_schema_mapping_v1.yaml` - detected physical -> semantic mapping.
- `assistments_contract.py` - pure fail-closed contract helpers shared by the
  inspector, tests, and the future J1 adapter.
- `inspect_assistments.py` - bounded/streaming inspector for the protected raw
  directory (never loads the large CSVs fully into memory).
- `schemas.py` - the normalized `ExternalActionRow` contract (plan 9.1) and
  HMAC pseudonymization.
- `adapter.py` - J1 streaming adapter: strict 2022-2023 filter, metadata joins,
  pseudonymization, staged atomic output, and manifest.
- `manifest.py` - auditable release manifest (source hashes, counts, terms,
  no-raw-identifier declaration).
- `assistments_j2_contract_v1.yaml` - frozen J2 attempt/label methodology.
- `j2_contract.py` - J2 constants and contract validation.
- `reconstruct_attempts.py` - J2 attempt reconstruction (completion,
  first-graded correctness, 30-minute timing rule, validity levels).
- `build_labels.py` - J2 current -> immediate-next labels, censoring, and the
  J2 manifest.
- `tests/test_assistments_schema_contract.py` - J0 schema-contract tests.
- `tests/test_assistments_adapter.py` - J1 adapter/manifest tests.
- `tests/test_assistments_attempt_reconstruction.py` - J2 reconstruction tests.
- `tests/test_assistments_next_attempt_labels.py` - J2 label/censor tests.
- `assistments_j2_contract_v2.yaml` - approved v2 contract (skill-episode
  compatibility delta; predecessor v1).
- `skill_episodes.py` - v2 production core: learner + exact-skill episodes and
  pairing.
- `reconstruct_skill_episodes.py` - v2 episode reconstruction CLI.
- `build_labels_v2.py` - v2 labels and `j2_v2_manifest.json`.
- `build_u7_dataset_v2.py` - J3-v2 model table, gates, and frozen split.
- `tests/test_assistments_j2_v2.py` - v2 focused tests.

The plan proposed these files; `assistments_contract.py` is a small addition so
the inspector and tests share one versioned contract instead of duplicating
rules.

## Running the J1 adapter

The adapter normalizes only in-window action rows into the protected processed
directory.  A project-local pseudonym key is required and is never written to
the manifest:

```powershell
cd C:\Users\zyonn\Documents\FYP\logic_oasis\ai_pipeline
$env:LOGIC_OASIS_ASSISTMENTS_PSEUDONYM_KEY = "<protected-key>"
python -m external_data.assistments.adapter `
  --raw-dir <protected>\assistments_edm_cup_2023\raw `
  --processed-dir <protected>\assistments_edm_cup_2023\processed `
  --release-id assistments-edm-cup-2023-release-v1 `
  --source-hashes <protected>\assistments_edm_cup_2023\j0\scan-summary.json
```

Outputs are written to a staging directory and atomically promoted, so a failed
run never leaves a partial release.  Reruns require `--force` (the release path
is immutable by default).

## Running the J2 build

```powershell
cd C:\Users\zyonn\Documents\FYP\logic_oasis\ai_pipeline
python -m external_data.assistments.reconstruct_attempts `
  --action-rows <protected>\processed\external_action_rows_v1.csv `
  --processed-dir <protected>\processed
python -m external_data.assistments.build_labels `
  --attempts <protected>\processed\external_attempts_v1.csv `
  --action-rows <protected>\processed\external_action_rows_v1.csv `
  --problem-outcomes <protected>\processed\external_problem_outcomes_v1.csv `
  --processed-dir <protected>\processed
```

J2 emits protected attempts, problem outcomes, labels, and `j2_manifest.json`.
The frozen rules are: Grade 6 Mathematics primary cohort; one in-unit
assignment per attempt; first-graded-response correctness; 30-minute
response-time rule; >= 3 graded problems and >= 3 timing pairs; immediate-next
pairing without skipping; `masteryCriterion = 0.60`; identical problem-set
repeats censored; BKT left to a later named ablation.

## Running the V2 build (approved skill-episode amendment)

The v2 contract maps the prediction unit to one learner + exact non-null
`sourceSkillCode` episode inside one completed assignment. It is a pre-model
methodology amendment (source semantic mismatch, not model performance); the
v1 contract and evidence remain preserved.

```powershell
python -m external_data.assistments.reconstruct_skill_episodes `
  --action-rows <protected>\processed\external_action_rows_v1.csv `
  --processed-dir <protected>\processed\v2 --cohort-grades 6
python -m external_data.assistments.build_labels_v2 `
  --episodes <protected>\processed\v2\external_skill_attempts_v2.csv `
  --action-rows <protected>\processed\external_action_rows_v1.csv `
  --problem-outcomes <protected>\processed\v2\external_skill_problem_outcomes_v2.csv `
  --processed-dir <protected>\processed\v2
python -m external_data.assistments.build_u7_dataset_v2 `
  --labels <protected>\processed\v2\external_labels_v2.csv `
  --episodes <protected>\processed\v2\external_skill_attempts_v2.csv `
  --processed-dir <protected>\processed\v2 --cohort-label "Grade 6"
```

Grade 6 primary reached the held-out gate with 4,401 labelled rows (655
learners); the frozen student-grouped split (seed 20260716) is in the
protected readiness manifest. Grades 4-6 remain the declared secondary
analysis.

## Running J4 (frozen external comparison)

```powershell
python -m external_data.assistments.run_j4 `
  --processed-dir <protected>\processed\v2 `
  --report ..\..\reports\u7_assistments_j4_model_comparison.md `
  --j4-manifest-out <protected>\processed\v2\j4_external_manifest.json
```

Trains Decision Tree / XGBoost / MLP on the frozen Grade 6 training partition,
evaluates once on the 2-learner held-out set, and adds 5-fold training-only
student-grouped stability evidence. Result: **MODEL COMPARISON COMPLETED** (no
stable advantage); artifacts remain `evidence_only_external` and are never
promoted.

## Running J5 (SHAP, operational, BKT ablation)

```powershell
python -m external_data.assistments.run_j5 `
  --processed-dir <protected>\processed\v2 `
  --action-rows <protected>\processed\external_action_rows_v1.csv `
  --report ..\..\reports\u7_assistments_j5_architecture_evidence.md `
  --j5-manifest-out <protected>\processed\v2\j5_architecture_manifest.json
```

Produces XGBoost global/local SHAP, operational evidence, model complexity,
the v2 BKT lineage gate, and the named base vs +BKT ablation. Result: SHAP and
operational evidence completed; BKT gate passed; BKT feature showed no stable
improvement. J4's conclusion is preserved.

### Detected source quirk handled by the adapter

819 action-log `problem_id` values are absent from `problem_details`
(342,998 rows overall; 12,283 rows in the 2022-2023 window, including graded
responses).  Because `externalContentKey` and `sourceSkillCode` are nullable in
the normalized contract, those rows are emitted with null content/skill
metadata and counted as `rowsWithUnresolvedProblemMetadata` in the manifest.
No metadata is fabricated and no learner behavior is silently dropped.

## Running the inspector

The raw directory is deliberately not hard-coded. Provide it explicitly:

```powershell
cd C:\Users\zyonn\Documents\FYP\logic_oasis\ai_pipeline
python -m external_data.assistments.inspect_assistments `
  --raw-dir <protected>\assistments_edm_cup_2023\raw `
  --json-out <protected>\assistments_edm_cup_2023\j0\scan-summary.json
```

Use `--skip-hashes` to avoid recomputing SHA-256 on reruns.

## Running the tests

```powershell
cd C:\Users\zyonn\Documents\FYP\logic_oasis\ai_pipeline
python -m unittest tests.test_assistments_schema_contract -v
```

The tests are pure and do not require the protected data.
