# AQC ASSISTments External-Real Descriptive Stage-B - Final Release Record

Date: 2026-08-09
Final status: **AQC ASSISTMENTS EXTERNAL-REAL DESCRIPTIVE STAGE-B COMPLETE**
Evidence level: **EXTERNAL_DESCRIPTIVE_REPLAY_WITH_LIMITED_MATCHED_OUTCOME_COVERAGE**
Claim level: `external_descriptive_replay`
Policy superiority: **NOT ESTABLISHED**; causal benefit: **NOT ESTABLISHED**
Production promotion: **NOT APPROVED**

## 1. Dataset / release hashes

- ASSISTments EDM Cup 2023, release `assistments-edm-cup-2023-release-v1`.
- Raw source hashes (J0): action_logs `DB6B0CD4875488D0847D9D9BA2896552F4AD1015F3E2388995222DD4A178443D`;
  assignment_details `D02D8B62DE088C896FCEB901BC986C25FA07F5D9AEEC0364BF9D351208BEC70E`;
  problem_details `4F45DAF2E010771C6B5E523DD4D583F3AC451F6CE8F2F35270FCB86B875CEE4E`;
  sequence_details `A1FA10E6DEBD4FD30C4B04E1554E18F2C426A981BCB10BED0B41DD083CCDB541`.
- J1 normalized rows `20d9514cabb4b23de0b2a0a4afdc36661ba30d5936aeb1a7950682d6af1ea378`.
- Provenance `external_real`; `containsRawIdentifiers: false`;
  `productionPromotionAllowed: false`; `p3bExecuted: false`.

## 2. Contract history

| Version | SHA-256 | Clarification |
|---|---|---|
| v1 | `46997eaf92d6c9aba0dc7d8d196080bc03bd59093ef5b2f04a1fd6fc4e424170` | initial external contract |
| v1.1 | `e54085ddfe1e00e1cd12d02639f02a70681c767a2ea51697548890e8211f63de` | discrete within-skill tertile boundaries |
| v1.2 | `d82b50432157f9321808dfced5ad7cb55960ce2dbc3501987ab17a23de725955` | attempt-purity denominator |
| v1.3 | `99897b2ac9486b3f725f549e3547f5905b0ba19980b9981f8c7bdffaa9815b77` | cluster-bootstrap / descriptive statistical reporting freeze |

All amendments were pre-result methodology clarifications (tertiles before any
proxy-policy result; purity before any real P1/P2/P3a result; bootstrap before
any matched-outcome value/rate), never policy-performance tuning.

## 3. Frozen artifact hashes

- E2 difficulty catalog `fe4cb2585bae9a8f15ee2802c23dea8270252384ab7e9c5a410d1ff934bd58e9`;
  E2 manifest `18502d7354c30a24849e659d7b8d656587eb3b48cefd495315f90b66436f3d17`.
- E3 attempts `b065d1d3cc70fc9086f92f24f998aed62a0d597ac74c1d2b9f385a1c4cd3b6a6`;
  E3 manifest `f5a966e98329c0936c12bce8728cf1601a57e8a649befd95c612b5cec468c2f1`.
- E4 readiness manifest `bf8a0b20c94aea98e5b0d66df9ce0efcac1985f039f7b86e8218d3ed2a6c1b9c`.
- E5 shared-state hash `66bfb15f4d59de29eee07774fcf6e6e93ecf7b2230e261cc01da62eac35fda76`;
  E5 decision audit (semantic) `75d9b9bdece8f410b787d68d7f7e99c3fb8405785bf142380683d704ff2907ab`;
  E5 audit file `067da4bc0dacf0510db52d5688bdecd5112a54ed19e1f2abf3dd485a0379b412`;
  E5 manifest `209750da34bc7fed5660ea6aa1ae3b0bbdd7cb9c75292ffe46204a9e06316c77`.
- E6 matched outcomes (semantic) `263b5554e2bb49927a0d89e1fedbfecfad9a91299f7997544da0d0c976ebf995`;
  E6 outcomes file `a8e4c195d345e634d2e0eda1f64e034547f987f0a2df91b4b6324f9f346aa8ca`;
  E6 manifest (reporting-label corrected) `8d4024b83daf5d63b239ce0acf0419d51c15f21b6cd854550f404a382e3862c4`.
- Policy bundle: adaptive policy `1b53aef77a8027b4256f915663ee894225c17efe4f876bff2e23a38ed17eef16`;
  policy evaluation `a12d251e5910a034c081950a8bede8dc7753329db0e9c540af108143e9a43a61`.
- BKT version `bkt-v1`; mastery criterion `0.60`;
  bootstrap seed `20260716`, resamples `2000`, confidence `0.95`, percentile
  learner-cluster method; sparse-CI guard `10` independent learners.

## 4. Policy replay population and decisions

- Shared policy-ready states 2,090 / learners 494 / exact skills 17.
- P1 UP 728 (34.83%), HOLD 1,362 (65.17%), DOWN 0.
- P2 UP 691 (33.06%), HOLD 1,319 (63.11%), DOWN 80 (3.83%).
- P3a UP 1,077 (51.53%), HOLD 888 (42.49%), DOWN 125 (5.98%).
- Agreement P1-P2 94.40%, P1-P3a 73.78%, P2-P3a 79.38%, three-way 73.78%.

## 5. Matched outcome counts (E6)

- P1 matched 41 (UP 10, HOLD 31, DOWN 0), mismatch 124; P2 matched 52 (2/31/19),
  mismatch 113; P3a matched 45 (5/21/19), mismatch 120.
- Censors (all policies): no-next 1,026; repeat 92; next-tier-missing 789;
  non-adjacent 18; invalid 0; chronology ambiguous 0.
- Matched-UP outcomes: P1 1 support / 9 success (n=10, supportNeededCi
  [0.0,0.3], successCi [0.7,1.0]); P2 0/2 (n=2, CIs suppressed); P3a 2/3
  (n=5, CIs suppressed).

## 6. BKT calibration

972 rows / 386 learners; Brier 0.13298; monotonic observed later success across
non-empty mastery bands (0.483, 0.571, 0.593, 0.885).

## 7. Final boundaries

- `policySuperiorityEstablished: false`; `causalEffectEstablished: false`;
  `P3b` not evaluated; production promotion not approved.
- Fresh-bank exact equivalence not reproduced; `freshProblemFraction` is an
  exposure audit only; no native Logic Oasis bankId exists for ASSISTments.
- External U.S.-curriculum evidence; not direct Malaysian KSSR validation; the
  proxy tiers are analytically derived, not native ASSISTments difficulty and
  not proven equivalent to Logic Oasis Easy/Moderate/Hard content.
- No local private-data paths appear in committed evidence; learner-level
  artifacts remain in the protected directory outside Git.

## 8. Tests

All affected suites (E1, E2/v1.1, E3/v1.2, E4, AQC-A, E5, E6/v1.3, U7
ASSISTments, native AQC regression) pass; the full ai_pipeline suite reports
481 tests with the single documented pre-existing line-ending-dependent
failure `test_report_records_hashes_parameters_and_safe_claim_boundary`
(reproduced identically on the clean predecessor AQC branch; not a Stage-B
regression).
