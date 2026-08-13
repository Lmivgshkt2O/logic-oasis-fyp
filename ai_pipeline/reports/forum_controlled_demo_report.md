# Forum controlled-demonstration evaluation report

- Evaluation mode: `grouped_three_way`
- Candidate: `MultinomialNB`
- Candidate status: `eligible`
- Activation status: `pending_u5_activation`
- Claim level: `controlled_demonstration_only`

## Reasoning component

- Accuracy: `1.0`
- Macro F1: `1.0`
- Balanced accuracy: `1.0`
- Publication coverage: `1.0`
- Fallback coverage: `0.0`

## Relevance component

- Accuracy: `1.0`
- Macro F1: `1.0`
- Positive threshold: `0.65`
- Negative threshold: `0.8`

## Composite decisions

- Verified emitted: `9`
- May be irrelevant emitted: `9`
- False verified: `0`
- False may-be-irrelevant: `0`
- Verified precision: `1.0`
- May-be-irrelevant precision: `1.0`
- Verified coverage: `1.0`
- May-be-irrelevant coverage: `1.0`

## Selection and baseline

- Selection decision: `selected_MultinomialNB_using_training_and_validation_only`
- Relevance selection decision: `selected_MultinomialNB_using_training_and_validation_only`
- Baseline comparison: `naive_bayes_advantage_demonstrated`
- Relevance baseline comparison: `naive_bayes_advantage_demonstrated`
- The baselines are comparison-only and are never releasable candidates.

## Limitations

- The metrics demonstrate reproducible classifier behaviour, scenario-fit, artifact integrity, and prototype integration readiness. They do not establish predictive accuracy, generalisability, educational effectiveness, or performance for real primary-school learners.
- The deterministic baselines are comparison-only and cannot be released or activated.
- A baseline win permits no Naive Bayes superiority claim.
- Relevance and reasoning probabilities are never presented as learner-calibrated confidence.
