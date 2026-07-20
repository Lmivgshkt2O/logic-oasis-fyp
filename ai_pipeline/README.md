# Logic Oasis Legacy Manual AI Pipeline

> **U1 baseline status (2026-07-13):** This directory contains the current developer-run Firestore batch pipeline. It is useful for auditing the existing BKT/XGBoost/SHAP-shaped contract, but it is not the canonical final FYP1 runtime. Normal quiz completion does not invoke this code automatically, and the current `.pkl` is a legacy, non-final artifact until the canonical plan's real-data, comparison, versioning, and promotion gates are complete.

This batch pipeline prototypes the earlier Grey Box AI architecture:

- XGBoost predicts immediate weakness/risk from quiz attempt features.
- SHAP explains the XGBoost prediction.
- BKT updates long-term mastery probability over time.
- Firestore stores the manual pipeline's derived `aiModelRuns` and `topicMastery` records for Flutter to display.

The Flutter app keeps its current rule-based logic as fallback if no AI result exists. The canonical final target is defined by `../docs/plans/2026-07-05-001-feat-fyp1-prototype-development-plan(2)(1).md`: trusted per-question responses, automatic event-triggered inference, adaptive assignment, model comparison, and versioned data/model lineage.

## Current Boundary

- Entry point: a developer manually runs `run_ai_pipeline.py`.
- Input: existing `quizAttempts` summary records, not server-finalized ordered response evidence.
- Output: `aiModelRuns` and `topicMastery` records consumed by Flutter.
- Missing automatic path: there is currently no `functions/` runtime or Firestore trigger configured in this repository.
- Missing final evidence: approved real-attempt provenance, grouped comparison against Decision Tree and MLP, promoted-model metadata, and `attemptId -> jobId -> modelRunId` lineage.

The commands below document the legacy utility. They must not be used to claim that the final automatic FYP1 workflow is implemented.

## Setup

Place Firebase service account key at:

```text
firebase_seed/serviceAccountKey.json
```

Install Python dependencies:

```powershell
cd C:\Users\zyonn\Documents\FYP\logic_oasis\ai_pipeline
python -m pip install -r requirements.txt
```

## Dry Run

This reads Firestore and prints the AI results without saving:

```powershell
python run_ai_pipeline.py --dry-run
```

To process only one signed-in student account, pass the Firebase Auth UID from
that student's `quizAttempts.studentId` field:

```powershell
python run_ai_pipeline.py --student-id YOUR_FIREBASE_UID --dry-run
```

To skip legacy seeded IDs such as `student_aiman_y4` and
`student_demo_001` (IDs beginning with `student_`):

```powershell
python run_ai_pipeline.py --exclude-demo --dry-run
```

This flag is only an ID-prefix filter. It does not prove that the remaining
records are real, approved, anonymized, or suitable for final evaluation.

## Save To Firestore

```powershell
python run_ai_pipeline.py
```

For one student only:

```powershell
python run_ai_pipeline.py --student-id YOUR_FIREBASE_UID
```

The script writes:

- `aiModelRuns/{studentId_topicId_timestamp}`
- `topicMastery/{studentId_y{yearLevel}_{topicId}}`

The `yearLevel` field is included in both AI output collections so the Flutter
parent dashboard can filter insights to the child's selected year.

## Training and Validation Notebook

Use `xgboost_training_validation.ipynb` to train and validate the XGBoost model in Jupyter Notebook. The notebook saves:

```text
xgboost_logic_oasis_model.pkl
```

When this file exists, `run_ai_pipeline.py` uses the notebook-produced model for XGBoost prediction and SHAP explanation. If the file does not exist, the pipeline falls back to its built-in temporary training logic, then to deterministic fallback when the dataset is too small.

The presence of `xgboost_logic_oasis_model.pkl` does **not** make it the promoted FYP1 model. See canonical units U6-U7 for the provenance, comparison, versioning, and promotion requirements.

## Canonical FYP1 Requirement

The developer-run commands above do not satisfy the automatic normal-demo-path requirement. See canonical unit U8 and the plan's Verification Contract for the required Functions/Emulator entry point and fallback evidence rules.
