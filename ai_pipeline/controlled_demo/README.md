# Controlled-demonstration dataset

This directory contains fictional, developer-authored multi-attempt learning journeys for the developer-released FYP1 controlled demonstration. It contains no real learner records and must not be used to claim real-student accuracy, learning improvement, or model superiority.

`scenario_catalog_v1.yaml` is the immutable source catalogue. Each family is one coherent fictional journey. `build_dataset.py` validates the catalogue, constructs only the two `quiz-attempt-features-v2` inputs, and derives `next_attempt_support_needed` exclusively from the following compatible attempt using the frozen `0.60` criterion. Last attempts and incompatible or immediately repeated-question transitions are retained in the pair audit but censored from training.

The dedicated provenance is `expert_authored_controlled_demo`. Callers must opt in with `allow_controlled_demo=True`; the normal real-data path and the unrelated `allow_synthetic_test` test-fixture path reject it. Runtime inference never reads this catalogue.

The generated manifest binds the catalogue and feature-schema hashes, target and label versions, counts, scenario-family grouping, developer declaration reference, and mechanics-only claim level. After evaluation and artifact checks pass, activation requires the exact immutable developer release declaration; no model-specific supervisor approval metadata is used.
