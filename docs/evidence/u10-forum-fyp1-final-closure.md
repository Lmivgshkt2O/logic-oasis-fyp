# U10 Forum FYP1 Final Closure Evidence

Closure date: 2026-08-09

Branch: `codex/qa-forum-naive-bayes`

U5 source commit: `8e93e4d3937a00d50b0680f7d6f555936bb242df`

Integrated U5 commit: `b0e3bfd2df462ad8e8d8ef78cb93dac637950f57`

U6 source implementation commit: `53964c15cd4271275abb854e6a4fe156d300aed5`

Integrated U6 implementation commit: `54fe28a8abd0b2de498269fbd9523225f9dcc0c4`

Scope: controlled-demonstration FYP1 closure only

## Conclusion

U1-U6 close the FYP1 Q&A Forum as a four-tab, authenticated,
privacy-bounded controlled demonstration. Automated gates and the local
Firebase rehearsal are green. This closure does not claim real-learner model
accuracy, educational effectiveness, generalisability, calibration, production
traffic readiness, or cloud deployment. Cloud activation remains
`pending_cloud_deployment`; U10-R is the required route to a future
`real_evaluated` release.

## Environment

| Component | Verified value |
|---|---|
| Operating system | Windows, Asia/Kuala_Lumpur |
| Flutter / Dart | 3.35.6 / 3.9.2 |
| CPython | 3.12.13 |
| Node / Firebase CLI | 24.18.0 / 15.22.2 |
| Java | Temurin 21.0.11 LTS |
| Firebase project namespace | fake/local `logic-oasis-fyp` |
| Cloud credentials used | none for the rehearsal |

Dependency caches were linked locally into the isolated worktree. Emulator-only
parent-email parameter values were supplied through ignored local environment
state; they are not deployable configuration or evidence of email delivery.

## Automated gates

| Gate | Command | Outcome |
|---|---|---|
| Flutter analysis | `flutter analyze --no-pub` | passed, no issues |
| Flutter tests | `flutter test --no-pub --reporter compact` | 94 passed |
| AI full suite | `python -m unittest discover -s ai_pipeline/tests` | 119 passed |
| Functions full suite | `python -m unittest discover -s functions/tests` | 106 passed |
| Tools/release suite | `python -m unittest discover -s tools/tests` | 40 passed |
| Firestore Rules | `firebase emulators:exec --only firestore ...question_answer_keys_rules.test.js` | passed |
| Auth + Firestore + Functions | `node tools/run_forum_emulator_flow.js` against local emulators | passed twice |

The repository now fixes LF checkout semantics for hash-bound text, treats
joblib reproducibility semantically across compatible executions while binding
the exact released bytes in each manifest, and keeps the historical July U8
release evidence immutable instead of relabelling its old deployed hashes.

## Student and linked-parent matrix

| Actor / surface | Verified result |
|---|---|
| Student A | question create, helpful idempotency, report convergence, block, accept idempotency |
| Student B | answer create and revision 2 through normal authenticated writes |
| Automatic AI | answer -> job -> immutable run -> revision-bound feedback completed with genuine released NB |
| Linked parent | count-only forum participation summary readable |
| Linked parent raw data | seven question/answer/moderation/job/run/registry reads denied |
| Unlinked/parent mutation | callable parent action denied; Rules suite denies protected mutation/read surfaces |
| Flutter presentation | Home, Formula Forge, Q&A Forum, Settings order plus forum loading/empty/filter/error/block flows covered |

No submitted question, answer, revision, or report text is retained in this
evidence. The observed state chain was `completed`; after registry revocation,
the next answer used `fallback`. Two immutable runs existed for the two answer
revisions, and the earlier completed run remained present after revocation.
U5 release 1 is preserved at commit
`8e93e4d3937a00d50b0680f7d6f555936bb242df`; the Emulator-verified release 2
is preserved at U6 commit `150b7d19524012df27f2f175bdf3af6005804312`.
Neither was promoted to the cloud. Main-branch integration changed the shared
Functions bundle, so the unchanged candidate artifact was republished as
release 3 instead of mutating release 2.

## Controlled release bindings

| Binding | SHA-256 / value |
|---|---|
| Release ID | `forum-controlled-demo-nb-v1-release-3` |
| Model | `forum-controlled-demo-nb-v1` / `MultinomialNB` |
| Code revision | `01e74fe579a81a3b3f39c675297b6f4791f5fb2f2c9b7bb62d028da9e3225d1f` |
| Artifact | `8307a480b5d5e61612b878653b2182d609ae594024ecae192e3677ace99a0049` |
| Catalogue | `614aefeffe4929f9b096452a4bb5e473cf671c809231a42edf2e8358b1f01c3a` |
| Dataset | `5d096d6ab1c6ce59428c9d89b8d972d743d6d613ae249b619c1c51579b3a8399` |
| Dataset manifest | `ce31bd081ea5e3f72d09171bfe7829d110a8fc5045fd202d3fe88255941c8d03` |
| Split manifest | `6c994001f0d1791030664310ba4bc3b807421b74364141ec7f82572d2945ba6d` |
| Evaluation report | `9bb9b4d1387ce943b88be042c6aade23594eb2aa9ea7413099ea44cf3f9ebb1a` |
| Candidate manifest | `45364c713b72351801afc00c37b5692085cf43d2c1225ca1eaf962c3cf2bfea5` |
| Rubric | `678505add7d4901d49ce1636baf8289877480383e3515b38e847b114da7ba05b` |
| Bundle manifest | `82bc19d8a82607355c14d7f4c1d6aad616bcfe3d400d7eef7ba94f940d250c78` |
| Claim level | `controlled_demonstration_only` |

The aggregate controlled-evidence corpus hash for the retained release-2
Emulator rehearsal was
`0d83a44bbca58b57d3545c69ba277f227317a6fdf6baf0270b8a96f786a2a44a`
both before and after inference. The retained, sanitized
[Emulator result](u10-forum-emulator-result.json) has SHA-256
`ea5fd2b7288a94161ede14326f0befac5390a8c138b904599a11e804f3c03152`;
its safe-log field records zero submitted-text matches.

## Evaluation boundary

The fictional catalogue contains 24 balanced rows, 12 scenario/question
families, and 8 English, 8 Malay, and 8 mixed-language rows. The grouped split
uses 8 training, 2 validation, and 2 untouched-test scenario families.
MultinomialNB final-test accuracy is `0.75`, macro F1 is `0.73333333`, and
publication/fallback coverage is `0.5`. The deterministic final-test baseline
scored `1.0`; the recorded Naive Bayes advantage applies only to selection-stage
validation. No general or final-test superiority claim is supported.

## Deactivation and remaining work

The Emulator registry record was changed from active/released to
inactive/revoked. The next event failed closed to deterministic fallback, while
prior immutable run evidence was preserved. A future activation requires a new
immutable compatible release and transactional supersession.

No cloud Functions deployment, cloud IAM binding, cloud registry promotion, or
production identity observation occurred in U6. The declared dedicated runtime
identity remains contract-tested only. U10-R must supply approved real/external
provenance, de-identification and retention controls, reviewer evidence,
author-grouped evaluation where feasible, full class metrics and calibration,
and a separately authorized cloud rollout before any `real_evaluated` claim.
