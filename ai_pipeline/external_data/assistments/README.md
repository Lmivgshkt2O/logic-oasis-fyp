# ASSISTments EDM Cup 2023 external-real-data path (J0)

This directory implements the J0 physical-source and U7-feasibility validation
for the approved **external real-data** evaluation route described in
`docs/plans/2026-08-07-001-feat-u7-assistments-edm-cup-2023-external-real-data-evaluation-plan.md`.

Status: **J0 GO for base U7** and **J1 adapter + manifest complete** (see
`docs/evidence/u7-assistments-source-validation.md`). J2 has not been started.

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
- `tests/test_assistments_schema_contract.py` - J0 schema-contract tests.
- `tests/test_assistments_adapter.py` - J1 adapter/manifest tests.

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
