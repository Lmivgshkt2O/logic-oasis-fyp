# U10 Forum FYP1 Final Closure Evidence

Closure date: 2026-08-09

Branch: `codex/qa-forum-naive-bayes`

U5 source commit: `8e93e4d3937a00d50b0680f7d6f555936bb242df`

Integrated U5 commit: `b0e3bfd2df462ad8e8d8ef78cb93dac637950f57`

U6 source implementation commit: `53964c15cd4271275abb854e6a4fe156d300aed5`

Integrated U6 implementation commit: `54fe28a8abd0b2de498269fbd9523225f9dcc0c4`

Scope: controlled-demonstration FYP1 closure only

## 2026-08-13 superseding reconciliation (U1-U7, forum AI verification plan)

The forum AI verification closure plan
(`docs/plans/2026-08-11-001-feat-forum-ai-cloud-closure-plan.md`) extends the
U10 baseline through U7 on branch `codex/integrate-forum-cloud-supervisor-plans`.

- U1: canonical linked discussions, structured four-option answers, and
  separate public/private AI projections with author-only feedback.
- U2: quiz-review and forum entry flows, linked final-answer/explanation
  composer, public advisory badges, author-only guidance.
- U3: separate relevance Naive Bayes component, authoritative verification
  catalogue, and precision/coverage composite evaluation (zero false public
  decisions).
- U4: revision-bound composite runtime (deterministic correctness + both
  components), content-hash fencing, safe public/private presentation.
- U5: cursor-based pagination beyond 40 items and the validated emulator-host
  override (AVD default, LAN, `adb reverse`).
- U6: Python 3.11 dual-component release v2
  (`forum-controlled-demo-nb-v1-release-5`, `forum-model-release-manifest-v2`),
  digest-bound dependency lock, removed stale committed env, authoritative
  nine-entry function inventory, and hardened deploy/promote/revoke tooling
  with live-deployment attestation.
- U7: local evidence reconciled (see
  `docs/evidence/u10-forum-ai-verification-release.md`), the operator cloud
  runbook, and the governed offline-learning (U10-R) design.

Updated environment facts:

| Fact | Value |
|---|---|
| CPython | 3.11.9 for the released artifacts |
| Release | `forum-controlled-demo-nb-v1-release-5` |
| Manifest | `forum-model-release-manifest-v2` |
| Repository revision | `44772c4bf9e7071f43b2e9ce99a609220c9c579255c2e8ca7b3725bfe6e5414d` |

Automated gates: full Functions suite 194/194, Tools 64/64, forum AI suite
43/43 under Python 3.11, Rules emulator PASS, Flutter focused suites PASS
(paging, composite guidance, navigation, emulator-config). The full AI suite
under the local 3.12 dev venv shows exactly one expected runtime-parity
failure (the committed forum artifacts are the Python 3.11 release; the plan's
canonical AI gate is `py -3.11`, where parity passes).

Cloud deployment and production verification remain pending (U8) and require
explicit operator authorization; the registry is not mutated locally. All
evidence remains `controlled_demonstration_only` and
`not_established_on_real_learners`.

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
Functions bundle, so the unchanged candidate artifact was republished instead
of mutating release 2. Release 3 was withheld when the full gate found a stale
policy-manifest source hash; release 4 carries the corrected binding.

## Controlled release bindings

| Binding | SHA-256 / value |
|---|---|
| Release ID | `forum-controlled-demo-nb-v1-release-4` |
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
| Bundle manifest | `cd1c07d23dcb472776381c7d6af43e9357922fe882cfb879ef88267edb2ed14f` |
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

## U8 authorized cloud deployment — 2026-08-14

The authorized controlled cloud rollout was executed per the runbook: preflight
passed, the dedicated runtime identity and Eventarc delivery bindings were
established, Firestore Rules and all 11 forum functions were deployed and
inspected, the pre-promotion fallback was proven with fictional content, release
`forum-controlled-demo-nb-v1-release-8` (revision
`5cb68d79a5f235309d583140eb8ce2b5079fbd623f2f1846969be4645ca7b223`) was
promoted with a live deployment attestation
(`90f890c4c4ff431c5964373fbb01ec3e1bdad1bf8577b99b5032a80a94409d80`), and the
controlled smoke matrix produced the expected verified/incorrect/may-be-
irrelevant/needs-reasoning/free-form/edit-fencing outcomes under claim
`controlled_demonstration_only`. Full details are in
[u10-forum-cloud-deployment.md](u10-forum-cloud-deployment.md). The 24-hour
observation window runs from `2026-08-14T13:10Z`; closure is confirmed only
after that window reports zero integrity failures. The earlier paragraph above
reflects the U6 state and remains historical.
