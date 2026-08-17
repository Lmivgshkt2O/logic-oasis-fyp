---
artifact_contract: firestore-schema-and-security-contract/v1
status: u10-fyp1-controlled-demo-closure-verified
created: 2026-07-15
updated: 2026-08-09
canonical_plan: docs/plans/2026-08-01-001-feat-u10-forum-production-closure-plan.md
---

# Logic Oasis Firestore Database Schema and Security Contract

**Purpose:** This is the developer-facing Firestore schema for Logic Oasis. It records the implemented trusted-content, secure-quiz, parent-link, adaptive-AI, and U10 forum boundaries plus future migration expectations.

**Authority:** The canonical FYP1 executable plan
(`docs/plans/2026-07-05-001-feat-fyp1-prototype-development-plan(2)(1).md`) and
the approved U14 parent Progress Map plan remain the product and sequencing
authority. This schema document reconciles to them; where wording differs, the
canonical plan and enforced code/rules win.

The U10 closure addendum below is authoritative for forum records. Older
`Target FYP1` forum sketches remain historical design context only where they
conflict with that addendum.

It is a contract, not a claim that every collection already exists. `Current prototype` records are the temporary repository behaviour observed on 2026-07-15. `Target FYP1` records are the design to implement through U2-U11. Stage 3 onboarding records remain reserved only and must not be created as active FYP1 scope unless Stage 3 is formally admitted.

## 1. Core Rules

1. Firebase Authentication `uid` is the identity key. Do not use display name, email, or a client-generated ID as an ownership key.
2. The Flutter client may submit untrusted choices and text, but it never creates trusted correctness, score, reward, AI, wallet, ledger, progression, or committed-world evidence.
3. Callable Functions or controlled administration create server-owned records using the Admin SDK. Firestore rules deny direct client writes to those records.
4. Timestamps are server timestamps. Monetary/reward-like values use integers, never floating-point values.
5. Keep immutable evidence as append-only documents. Materialized summaries such as mastery, wallet balance, and dashboard projections are derived and may be regenerated.
6. Store stable technical IDs and version fields. Do not store translated labels, Flutter widget names, or manifest frame names as durable identity.
7. Do not place passwords, Firebase Auth tokens, answer keys, raw child feedback, or model artifacts in client-readable documents.

## 2. Status Legend

| Status | Meaning |
|---|---|
| Current prototype | Exists in the repository/seed data today and may have weaker prototype behaviour. |
| Target FYP1 | Required planned schema for the final FYP1 architecture. |
| Derived target | Target FYP1 document regenerated from trusted source records. |
| Reserved | Architecture is approved but not active work or an FYP1 completion requirement. |
| Seed-only / retired | May exist in demo data but must not become trusted production evidence. |

## 3. Identity, Roles, and Relationships

```mermaid
erDiagram
    USER ||--o{ QUIZ_SESSION : starts
    USER ||--o{ QUIZ_ATTEMPT : owns
    USER ||--o{ QUESTION_RESPONSE : owns
    USER ||--o{ ADAPTIVE_ASSIGNMENT : receives
    USER ||--|| STUDENT_WALLET : has
    USER ||--|| OASIS_WORLD : owns
    USER ||--o{ FORUM_QUESTION : posts
    USER ||--o{ FORUM_ANSWER : posts
    USER ||--o{ PARENT_LINK : linked_to
    QUIZ_SESSION ||--o{ QUESTION_RESPONSE : seals
    QUIZ_SESSION ||--|| QUIZ_ATTEMPT : finalizes
    QUIZ_ATTEMPT ||--o{ AI_JOB : triggers
    QUIZ_ATTEMPT ||--o{ MASTERY_SNAPSHOT : updates
    QUIZ_ATTEMPT ||--o{ ADAPTIVE_ASSIGNMENT : informs
    OASIS_WORLD ||--o{ OASIS_ENTITY : contains
    STUDENT_WALLET ||--o{ WALLET_LEDGER : derives_from
```

### 3.1 Firebase Auth and profile documents

| Path | Status | Document ID | Required fields | Client access | Server/admin responsibility |
|---|---|---|---|---|---|
| Firebase Authentication user | Current prototype / Target FYP1 | Firebase `uid` | Auth provider identity, verified email where applicable | Auth SDK only | Authentication lifecycle. Do not mirror passwords into Firestore. |
| `users/{uid}` | Current prototype / Target FYP1 | Auth `uid` | `role` (`student` or `parent`), `displayName`, `yearLevel` for students, `preferredLanguage`, `createdAt`, `updatedAt`, `profileVersion` | Owner reads own profile. Owner may update safe presentation fields only. | Sets immutable role/ownership fields and validates profile shape. |
| `parentLinks/{parentId}_{studentId}` | Target FYP1 relationship contract | Stable pair ID | `parentId`, `studentId`, `status`, `createdAt`, `linkedBy`, `linkVersion` | Linked student and linked authenticated parent may read. Neither party may self-grant a link. | Creates/revokes approved links and verifies both identities. |
| `parentAccounts/{parentId}` | Current prototype transitional record | Existing parent ID | Prototype parent metadata only; never store plaintext password | Treat as transitional. Do not extend it as a production authentication design. | Replace unsafe prototype credential handling with authenticated UID plus `parentLinks` checks when U9 is secured. |
| `rememberedProfiles/{uid}` | Current prototype convenience record | Auth `uid` | Minimal display preference only, such as `displayName`, `yearLevel`, `updatedAt` | Owner only | Never store passwords, tokens, parent access secrets, trusted learning fields, or role grants. |

**Parent boundary:** Parent access uses Firebase Auth in an isolated parent
   session plus a server-owned, approved `parentLinks/{parentId}_{studentId}`
   record; prototype parent-password/OTP records are retired. A linked parent
   reads only the selected child's safe projections: `subtopicMastery`,
   `parentPracticeSummaries/{studentId}` (U14 current-week rhythm), and
   `forumParticipationSummaries/{studentId}` (U10 count-only). Raw attempts,
   responses, answer keys, AI jobs/runs, SHAP, forum content, model registry,
   and parent-link documents remain denied.

## 4. Curriculum and Trusted Content

These are controlled reference records. They are versioned, client-readable only where the answer is safe, and never directly client-writable.

| Path | Status | Document ID | Required target fields | Read/write boundary |
|---|---|---|---|---|
| `topics/{topicId}` | Current prototype / Target FYP1 | Stable curriculum topic ID | `yearLevel`, `titleEn`, `titleMs`, `order`, `isActive`, `contentVersion` | Authenticated read; controlled seed/admin write only. |
| `subtopics/{subtopicId}` | Current prototype / Target FYP1 | Stable curriculum subtopic ID | `topicId`, `yearLevel`, `titleEn`, `titleMs`, `order`, `skillIds`, `activeBankCounts`, `contentVersion`, `isActive` | Authenticated read; controlled seed/admin write only. |
| `questionBanks/{bankId}` | Current prototype / Target FYP1 | Stable bank/version ID | `topicId`, `subtopicId`, `difficultyLevel` (`easy`, `moderate`, `hard`), `questionIds`, `version`, `isActive`, `createdAt` | Authenticated read; controlled seed/admin write only. |
| `questions/{questionId}` | Current prototype / Target FYP1 | Stable question/version ID | `topicId`, `subtopicId`, `skillId`, `bankId`, `difficultyLevel`, `questionText`, `questionTextBm`, `options`, `optionsBm`, `questionType`, `questionTypeBm`, `estimatedDifficulty`, `contentVersion`, `sourceMaterialId`, `sourceMaterialIdBm`, `sourceLocator`, `sourceLocatorBm`, `sourceSectionClass`, `isActive` | Authenticated read; controlled seed/admin write only. Must not contain `answerIndex`, `feedbackByOption`, or any explanation/hint content. |
| `questionAnswerKeys/{questionId}` | Target FYP1 | Same stable question ID | `answerIndex`, `feedbackByOption` (per wrong option: `misconceptionCode`, `hint`, `hintBm`, optional `example`/`exampleBm`, `reviewFocus`, `reviewFocusBm`), `difficultyReview` (`cognitiveDemand`, `reasoningStepCount`, `transferRequired`), `contentVersion`, `isActive`, author/reviewer identity | Client read/write denied. Callable Functions only. |
| `contentSourceManifest/{materialId}` | Target FYP1 (U15) | Stable material ID (e.g. `en_y4`, `bm_y4`) | `materialId`, `filename`, `sha256`, `syllabus`, `yearLevel`, `language`, `contentVersion`, `authorId`, `reviewerId`, `approvedAt`, `sourceSectionClass`, `questions` (per question: `sourceLocator`, `sourceLocatorBm`, `contentDigest`, `questionType`, `questionTypeBm`, `sourceSectionClass`) | Client read/write denied. Seed writes the approved manifest only; any content change invalidates the digest and blocks activation. |

**Content invariant:** `questions/{questionId}` and `questionAnswerKeys/{questionId}` share a content version. A session records that version and rejects stale or mismatched content during U3 validation.

## 5. Quiz Session and Response Evidence (U3 Critical Path)

U3 replaces client-created quiz result records with this server-owned lifecycle:

```text
startQuizSession
  -> quizSessions/{sessionId} = active
  -> submitQuizResponse x expectedQuestionCount
  -> questionResponses/{responseId} = sealed immutable evidence
  -> finalizeQuizSession
  -> quizAttempts/{attemptId} = immutable final attempt
  -> later automatic BKT/AI processing
```

| Path | Status | Document ID | Required target fields | Writer and reader rules |
|---|---|---|---|---|
| `quizSessions/{sessionId}` | Target FYP1 | Server-generated session ID | `studentId`, `assignmentId`, `bankId`, `questionIds`, `contentVersion`, `status`, `validatedResponseCount`, `expectedResponseCount`, `startedAt`, `expiresAt`, `finalizedAt`, `attemptId` | Callable Functions create/transition states. Client direct reads/writes denied; safe state is returned by callable responses. |
| `questionResponses/{responseId}` | Target FYP1 | Deterministic session/question or idempotency identity | `sessionId`, `attemptId` after finalization, `studentId`, `questionId`, `skillId`, `bankId`, `selectedIndex`, `serverIsCorrect`, `validationStatus`, `responseTimeMs`, `hintCount`, `sequenceIndex`, `idempotencyKey`, `createdAt` | Callable Functions write once. Client direct reads/writes denied. A second sealed answer is rejected. |
| `quizAttempts/{attemptId}` | Current prototype -> Target FYP1 | Server-generated finalized attempt ID | `studentId`, `sessionId`, `topicId`, `subtopicId`, `bankId`, `difficultyLevel`, `contentVersion`, `validationStatus`, `processingStatus`, `trustedScore`, `trustedCorrectCount`, `responseCount`, `responseIds`, `reviewItems` (per missed question: `questionId`, `sequenceIndex`, `questionText`, `questionTextBm`, `questionType`, `questionTypeBm`, `reviewFocus`, `reviewFocusBm`), `startedAt`, `finalizedAt`, `dataSource`, `deviceSessionId` | Backend creates once. Student reads own; linked parents never read raw attempts (U14 reads only safe projections). Client writes denied. `reviewItems` are answer-free and list only missed questions in quiz order. |
| `quizAttemptTelemetry/{telemetryId}` | Optional target only if needed | Generated ID | Untrusted UI timing/device telemetry, `studentId`, `sessionId`, `createdAt` | Client may submit only through a restricted validated path. Never use as correctness, score, reward, or model truth without server validation. |

### U3 invariants

- Valid session states are `active`, `finalizing`, `finalized`, and `expired`; only the backend may transition them.
- `idempotencyKey` maps retries to the original accepted response or result. It never creates another response, attempt, or reward.
- `selectedIndex` is client input; `serverIsCorrect`, trusted score, explanation, and finalization are server-derived.
- A final attempt exists only when every expected session question has one validated sealed response.
- Failed network submission remains pending on the client, but no local answer key is exposed while retrying.

## 6. Mastery, Adaptive Assignment, and AI Evidence

| Path | Status | Document ID | Required target fields | Writer and reader rules |
|---|---|---|---|---|
| `masterySnapshots/{studentId}_{skillId}` | Derived target | Student-skill pair | `studentId`, `skillId`, `pKnown`, `pLearn`, `pGuess`, `pSlip`, `observationCount`, `sourceAttemptId`, `modelVersion`, `updatedAt` | AI/BKT backend writes. Student reads own derived result; parents read authorized summaries. |
| `topicMastery/{studentId}_y{yearLevel}_{topicId}` | Current prototype -> Derived target | Student/year/topic pair | `studentId`, `yearLevel`, `topicId`, summary mastery fields, `sourceAttemptId`, `updatedAt` | Derived dashboard summary only; client writes denied. |
| `subtopicMastery/{studentId}_y{yearLevel}_{topicId}_{subtopicId}` | Current prototype -> Derived target | Student/year/topic/subtopic pair | `studentId`, `yearLevel`, `topicId`, `subtopicId`, `masteryProbability` (nullable), `observationCount`, `evidenceLevel`, `attempted`, `accessUnlocked`, `completed` (monotonic BKT outcome), `completionCriterionVersion`, `recommendedLearningAction` (`repeat_subtopic`/`advance`), `recommendationBasis` (`bkt_mastery`/`correct_rate_fallback`/`provisional_pending_ai`), `recommendationTargetTopicId`, `recommendationTargetSubtopicId`, `projectionStatus`, `bestCorrectRate`, `lastCorrectRate`, `masteryLevel`, `lastSourceAttemptId`, `sourceAttemptSequence`, `updatedAt` | Derived dashboard summary only; client writes denied. Access and completion are separate: any valid finalized attempt sets `attempted`/`accessUnlocked`, while `completed` only rises via `subtopic-completion-v1` (BKT `masteryProbability >= 0.72` with at least 5 observations) and is never reset by a weaker retry. |
| `adaptiveAssignments/{assignmentId}` | Target FYP1 | Deterministic student/subtopic assignment ID | `studentId`, `subtopicId`, `bankId`, `difficultyLevel`, `reasonCode`, `reasonText`, `policyVersion`, `sourceAttemptId`, `sourceAttemptSequence`, `status`, optional bounded `modelEvidenceState`, `createdAt` | Adaptive-policy backend writes. Student and linked parent may read the safe projection; clients cannot choose or edit the bank assignment. `modelEvidenceState` is present only for a compatible completed model-backed assignment. |
| `aiJobs/{attemptId}` | Target FYP1 | Attempt ID | `attemptId`, `studentId`, `status`, `attemptCount`, sanitized `errorCode`, timestamps, `sourceAttemptSequence` | Trigger/worker only. All client reads and writes are denied; visible state is copied to `studentAiStatuses`. |
| `aiModelRuns/{runId}` | Derived target | Deterministic attempt run ID | `studentId`, `attemptId`, `modelVersion`, `featureSchemaVersion`, prediction, raw feature values, Tree SHAP values/expected value, `releaseId`, evidence and source lineage, `status`, `createdAt` | AI runtime only. All client reads and writes are denied; no raw feature, SHAP, hash, path, or release data enters a client projection. |
| `studentAiStatuses/{attemptId}` | Safe derived projection | Attempt ID | `attemptId`, `studentId`, `analysisState`, `displayCode`, `sourceAttemptSequence`, optional bounded `modelEvidenceState`, `updatedAt` | AI runtime writes. Owning student and active linked parent may read; clients cannot write. The controlled value is exactly `controlled_demonstration` and only accompanies `completed`. |
| `modelRegistry/{artifactId}` | Target FYP1 | Immutable artifact ID | Model/version/type, artifact and manifest paths/hashes, package/schema/ranking/adaptive-policy hashes, target/label/mastery contract, dataset/report/catalogue/config hashes, provenance/evidence/release/deployment scopes, lifecycle/promotion state, complete `releaseId`/`releasedBy`/`releasedAt`/`releaseRationale` developer declaration, `isActive`, and timestamps | Privileged promotion/deployment only; all client reads and writes are denied. One transaction deactivates the current record and creates exactly one active immutable record. A controlled-demo record uses `releaseScope: fyp1_controlled_demo` and `deploymentScope: controlled_demo`. |

**AI evidence invariant:** `aiModelRuns` must identify its finalized `attemptId`,
model version, feature schema, release identity, and data-source lineage. A
controlled-demo run uses `trainingDataProvenance:
expert_authored_controlled_demo` in its protected registry evidence and exposes
only `modelEvidenceState: controlled_demonstration` through completed safe
status/assignment projections. Seed/demo rows remain excluded from real-data
performance claims. A later `real_evaluated` registry record requires separate
data governance, evaluation, and a separately governed release declaration;
existing controlled projections are never relabelled in place.

## 7. Q&A and Naive Bayes Data

| Path | Status | Document ID | Required target fields | Writer and reader rules |
|---|---|---|---|---|
| `forumQuestions/{questionId}` | Target FYP1 | Generated ID | `authorId`, `topicId`, `subtopicId`, `body`, `attemptedExplanation`, `status`, `acceptedAnswerId`, `createdAt`, `updatedAt` | Author creates/edits allowed draft fields only; moderation/status fields are controlled. Do not expose unnecessary profile data. |
| `forumAnswers/{answerId}` | Target FYP1 | Generated ID | `questionId`, `authorId`, `body`, `reasoningText`, `qualityStatus`, `predictedProbability`, `evidenceState`, `forumModelVersion`, `helpfulCount`, `isAccepted`, `createdAt` | Author writes safe answer fields; backend/moderation owns prediction, acceptance, reward eligibility, and moderation fields. |
| `forumAiJobs/{answerId}` | Target FYP1 | Answer ID | `answerId`, `status`, `retryCount`, `modelVersion`, `errorCode`, `startedAt`, `completedAt` | Backend only. |
| `forumAiRuns/{runId}` | Target FYP1 | Generated ID | `answerId`, `predictedLabel`, `predictedProbabilities`, `evidenceState`, `isCalibrated`, `feedbackCode`, `modelVersion`, `preprocessorVersion`, `createdAt` | Backend only; client reads only safe feedback for the relevant answer. |
| `moderationLogs/{logId}` | Current prototype -> Target FYP1 | Generated ID | `targetType`, `targetId`, `action`, `actorId`, `reasonCode`, `createdAt` | Moderator/backend only. Do not make moderation notes public. |

Current seed names such as `forumPosts`, `forumReplies`, and `helperReputation` are prototype/seed-only names. Migrate only reviewed content into the target Q&A contract; do not treat seed text as training evidence.

## 7A. Policy Evaluation Study Collections (AQC-4)

All collections below are server-owned and require explicit terminal-deny Rules
even though the default deny rule would also protect them. The callable
control plane (`policyEvaluationAdmin` claim) and the Canonical U8 runtime use
the Admin SDK and are not constrained by these rules. On export these records
are HMAC-pseudonymized, not anonymous.

| Path | Document ID | Required target fields | Writer and reader boundary |
|---|---|---|---|
| `policyEvaluationStudies/{studyVersion}` | `studyVersion` | `studyVersion`, `status` (`draft`, `enrolling`, `active`, `closed`, `archived`), immutable `manifestHash`, policy versions, outcome/probe protocol versions, `deltaFD`, `randomizationVersion`, `releaseRef`, lifecycle timestamps | Dedicated evaluation admin only; no client read/write. Frozen manifest and `deltaFD` are immutable once the study is active. |
| `policyEvaluationConsents/{studentId}_{studyVersion}` | Student/study pair | `studentId`, `studyVersion`, `status` (`active`, `revoked`, `expired`), `consentRecordRef`, `expiresAt`, `recordedBy` | Dedicated evaluation admin only; no client read/write. Documented consent is separate from enrollment. |
| `policyEvaluationEnrollments/{studentId}_y{yearLevel}_{topicId}_{subtopicId}_{studyVersion}` | Learner/context/study key | `studentId`, `yearLevel`, `topicId`, `subtopicId`, `startingDifficulty`, `contextVersion`, `studyVersion`, `assignedArm`, `allocationBlockId`, `allocationVersion`, `consentRef`, `status`, `assignedAt`, `revokedAt` | Dedicated evaluation admin only; no client read/write. Stable blocked-randomized arm; revocation is historical, not a rewrite. |
| `policyEvaluationAllocationBlocks/{studyVersion}_{yearLevel}_{topicId}_{subtopicId}_{startingDifficulty}` | Stratum key | Immutable stratum fields, per-arm counts, `updatedAt` | Server-only enrollment transaction. Keeps allocation balanced without trusting a client random choice. |
| `policyEvaluationDecisionAudits/{decisionId}` | Deterministic decision ID | `decisionId`, `studyVersion`, `enrollmentId`, `attemptId`, `studentId`, `sourceAttemptSequence`, `assignedArm`, `deliveredArm`, `protocolDeviation`, selector/config versions, redacted input snapshot, reason code, selected difficulty/bank, `createdAt` | Canonical U8 runtime only; no client read/write (created in AQC-5). |
| `policyEvaluationProbes/{decisionId}` and `policyEvaluationOutcomes/{decisionId}` | Decision ID | Probe form/blueprint/target/calibration and outcome eligibility, censoring, later probe attempt, result, `computedAt`, outcome version | Canonical U8 runtime only; no client read/write (created in AQC-5). |
| `policyEvaluationAdminAudits/{auditId}` | Deterministic action ID | `actorUid`, `action`, `subjectRef`, `releaseRef`, `rationale`, `createdAt` | Admin callable only; no client read/write. Audits study creation, consent, enrollment, revocation, and closure. |

**Retention owner:** the policy-evaluation evaluation admin service account.
Arm and audit IDs are never added to `adaptiveAssignments`, `subtopicMastery`,
`studentAiStatuses`, `quizAttempts`, or any client-readable document, because
Firestore Rules cannot redact fields from an otherwise readable document.

## 8. Oasis Game Economy and World State

| Path | Status | Document ID | Required target fields | Writer and reader rules |
|---|---|---|---|---|
| `studentWallets/{studentId}` | Target FYP1 | Student Auth UID | `studentId`, `crystals`, `mutualAidEnergy`, `todayRestorationDate`, `todayRestorationCount`, `totalRestorations`, `level`, `nextLevelThreshold`, `economyPolicyVersion`, `progressionPolicyVersion`, `updatedAt` | Backend computes/writes. Student reads own projection; client cannot edit balances or level. |
| `walletLedger/{entryId}` | Target FYP1 | Generated or deterministic source ID | `studentId`, `entryType`, `resourceType`, integer `amount`, `sourceId`, `idempotencyKey`, `economyPolicyVersion`, `createdAt` | Backend append-only. Used to reconcile wallet balance. |
| `oasisActionCatalog/{catalogVersion}_{actionId}` | Target FYP1 materialization | Catalog/action pair | `catalogVersion`, `actionId`, `technicalSceneId`, `fromStage`, `toStage`, `resourceType`, `cost`, `allowedSlotIds`, `restorationUniquenessKey`, `styleVariantKey` | Controlled configuration deployment only; client read-only. Version-controlled YAML remains the authoring source. |
| `oasisWorlds/{studentId}` | Target FYP1 | Student Auth UID | `studentId`, `mapId`, `sceneSchemaVersion`, `contentCatalogVersion`, `economyPolicyVersion`, `progressionPolicyVersion`, `worldRevision`, `updatedAt` | Backend world commands write. Student reads own world. |
| `oasisWorlds/{studentId}/entities/{entityId}` | Target FYP1 | Stable entity/slot ID | `entityType`, `technicalSceneId`, `slotId`, `restorationStage`, `styleVariantKey`, `createdAt`, `updatedAt` | Backend world commands write. Never store a manifest atlas-frame filename. |
| `oasisRestorationEvents/{eventId}` | Target FYP1 | Deterministic qualifying action ID | `studentId`, `worldActionId`, `eventType`, `targetType`, `targetId`, `uniquenessKey`, `localDate`, `totalRestorationsAfter`, `levelAfter`, `progressionPolicyVersion`, `createdAt` | Backend append-only. Used to reconcile restoration totals/level. |
| `oasisProgress/{studentId}` | Current prototype -> Retired after migration | Student ID | Prototype Crystals, Energy, repaired-area map, and UI preferences | Do not extend. U3+ game work must migrate approved display state into separate wallet/world records through backend-owned commands. |

**World identity invariant:** `fraction_bridge`, `decimal_waterway`, `percentage_garden`, and `market_corner` are immutable `technicalSceneId` values. Display labels, art, and palettes come from a versioned presentation manifest and do not change saved-world identity.

## 9. Configuration, Preferences, and Reserved Stage 3 Records

| Path | Status | Document ID | Fields and boundary |
|---|---|---|---|
| Version-controlled `config/oasis/` YAML | Target FYP1 authoring source | Versioned files | Source of truth for Oasis catalogues, economy, progression, and presentation. Validated and deployed; no manual Firestore console authoring. |
| `onboardingPolicy/stage3` | Reserved | Fixed `stage3` | Read-only policy with `enabled`, active story/tour versions, rollout timestamp, minimum app version, fallback route, compatibility, and update timestamp. Create only if Stage 3 is formally admitted. |
| `studentPreferences/{studentId}/onboarding/current` | Reserved | Fixed `current` under student UID | Owner-scoped onboarding outcome/accessibility preferences. It must never contain global policy fields, wallet data, quiz evidence, AI output, or world mutation. |

The approved Stage 3 reservation does not change FYP1 database implementation. These documents are included for architectural completeness only and stay inactive unless a supervisor-approved `formally_admitted` decision occurs before U11 closure.

## 10. Firestore Security Matrix

| Data class | Client read | Client write | Backend/admin write | Rule/test expectation |
|---|---|---|---|---|
| Safe curriculum (`topics`, `subtopics`, `questions`, `questionBanks`) | Authenticated read | Denied | Controlled seed/deployment | Questions never include answer keys. |
| Answer keys, sessions, responses | Denied | Denied | Callable Functions only | Emulator denies direct access even to the owning student. |
| Content approval manifest (`contentSourceManifest`) | Denied | Denied | Controlled seed/deployment only | Material checksums, locators, digests, and reviewer identities never cross the client boundary. |
| Safe mastery, practice, and Mutual Aid projections (`subtopicMastery`, `parentPracticeSummaries`, `forumParticipationSummaries`) | Owner or exact linked parent | Denied | Backend only | Student cannot forge correctness, score, evidence state, mastery, practice rhythm, or participation counts. |
| Raw AI jobs/runs and model registry | Denied | Denied | Runtime or privileged promotion only | Raw features, SHAP values, errors, hashes, paths, release metadata, and registry state never cross the client boundary. |
| User profile and preferences | Owner only | Restricted safe fields only | Server validates identity/role fields | Foreign UID access denied; role/link escalation denied. |
| Parent links | Linked parties may read | Denied | Approved server/admin flow | No self-linking or cross-student access. |
| Policy evaluation studies, consents, enrollments, allocation blocks, decision audits, probes, outcomes, admin audits | Denied | Denied | Dedicated `policyEvaluationAdmin` callables and U8 runtime only | Emulator denies direct client reads/writes; non-enrolled learners keep the unchanged production adaptive path. |
| Q&A source text | Role/visibility-based read | Author restricted fields or validated callable | Backend/moderation derived fields | Acceptance, AI quality, rewards, and moderation are not client-controlled. |
| Wallet, ledger, world, restoration | Owner read of projection | Denied | Backend commands only | Reconcile balances, events, level, and revision; reject duplicate source IDs. |
| Configuration and model registry | Read only where needed | Denied | Controlled deployment/promotion only | Client cannot activate policy/model/configuration. |

`firestore.rules` is the enforcement layer. Firebase Emulator tests must prove
owner isolation, exact linked-parent projection reads, answer-key denial,
direct trusted-write denial, collection/list enumeration denial, and no access
to another student's records. The U14 authenticated emulator flow
(`tools/run_parent_dashboard_emulator_flow.js`) exercises the exact-child read
matrix and every denied path.

## 11. Required Query Indexes

Create indexes only after the matching query is implemented and recorded in `firestore.indexes.json`. Expected target queries include:

| Collection | Query pattern | Expected composite index |
|---|---|---|
| `quizAttempts` | `studentId ==` plus latest finalized attempt | `studentId ASC, finalizedAt DESC` |
| `aiModelRuns` | `studentId ==` plus latest completed run | `studentId ASC, createdAt DESC` |
| `adaptiveAssignments` | active assignment for a student/subtopic | `studentId ASC, subtopicId ASC, status ASC, createdAt DESC` |
| `forumQuestions` | topic/subtopic/status feed | `topicId ASC, subtopicId ASC, status ASC, createdAt DESC` |
| `forumAnswers` | answers for a question in display order | `questionId ASC, createdAt ASC` |
| `walletLedger` | reconciliation by student/resource/time | `studentId ASC, resourceType ASC, createdAt DESC` |
| `oasisRestorationEvents` | daily or lifetime progress by student | `studentId ASC, localDate DESC, createdAt DESC` |

## 12. Current-Prototype Migration Boundaries

| Current behaviour | Target change | Owning unit |
|---|---|---|
| `LearningRepository` writes `quizAttempts`, topic mastery, and subtopic mastery from Flutter. | Replace with backend-owned session/response/finalization flow. Flutter reads safe derived results only. | U3, then U4/U8. |
| `oasisProgress` is client writable and mixes resources, repaired areas, and UI preferences. | Replace with backend-owned `studentWallets`, `walletLedger`, `oasisWorlds`, and `oasisRestorationEvents`. | G3-G7. |
| `aiModelRuns` can show seeded/manual evidence. | Require lineage to a finalized attempt and automatic job/run status. | U6-U9. |
| Seed `forumPosts`/`forumReplies` use prototype names. | Use the FYP1 `forumQuestions`/`forumAnswers` model with moderation and Naive Bayes job/run records. | U10. |
| `parentAccounts` uses a prototype parent-access flow. | Keep FYP1 parent access limited and authenticated; do not store/extend prototype passwords. | U9/U11. |
| Reserved onboarding policy/preferences are not active. | Do nothing in current FYP1 scope; create only after Stage 3 formal admission. | UI3 after formal admission. |

## 13. U2 and U3 Delivery Checklist

### U2 - trusted content (implemented and verified 2026-07-16)

- [x] Client-readable `questions` contain no authoritative answer index or explanation; matching `questionAnswerKeys` are server-only.
- [x] `firestore.rules` denies all client read/write access to `questionAnswerKeys`; the authenticated Rules Playground denial and `firebase_seed/tests/question_answer_keys_rules.test.js` Emulator test were confirmed.
- [x] Direct client writes to trusted quiz, mastery, and attempt records remain denied. Do not reintroduce client writes for trusted fields.

### U3 - trusted attempt creation (implemented and production-verified 2026-07-16)

- [x] Authenticated `startQuizSession`, `submitQuizResponse`, and `finalizeQuizSession` callable Functions create one server-owned session, ordered sealed responses, and one immutable finalized attempt.
- [x] Idempotent response identity, sequential response checks, expiry handling, and backend-controlled state transitions are enforced. `LearningRepository.saveQuizAttemptAndMastery` remains legacy/prototype behaviour and is not the U3 runtime path.
- [x] `firestore.rules` denies direct client access to `quizSessions` and `questionResponses`, and denies direct writes to `quizAttempts`, `topicMastery`, and `subtopicMastery`.
- [x] Production deployment: `firebase deploy --only functions,firestore:rules --project logic-oasis-fyp` completed on 2026-07-16. The released Rules compiled successfully; `startQuizSession`, `submitQuizResponse`, and `finalizeQuizSession` were confirmed at the reviewed deployed revision in `asia-southeast1`.
- [x] Production authenticated verification created `quizSessions/session_fd6f125780624def9ee1112e66d3c16a`, five validated `questionResponses` (`06133091547229544ce623d90b7b1ec4`, `01a5921b38e13f49e538fbdf8e5164b6`, `d33f5db033d164b9063597117ea81187`, `ebaad6761b26d7dccff2d8a2ad17468a`, and `008815b6a3b30b9ff546b6c07a06882d`), and `quizAttempts/attempt_f86136271a1b4ec6949a1aeefcfe3f8f` with `finalizationStatus: finalized`.
- [x] Focused Python U3 workflow tests passed (10 tests, OK). The authenticated Flutter app flow was also completed to the server-confirmed final-score dialog.

## 14. Security Review Questions Before U3 Sign-off

1. Does every client-readable question document exclude answer keys and authoritative explanations?
2. Can a student access only their own safe profile, attempts, mastery, AI insight, wallet projection, and world?
3. Can a linked parent read only the assigned student's permitted dashboard projection?
4. Can any client write trusted correctness, score, attempt finalization, reward, ledger, AI result, mastery, assignment, or world revision? The required answer is no.
5. Do all server-created evidence records include a source ID, version, server timestamp, and idempotency/immutability strategy where needed?
6. Are seed/demo rows marked and excluded from model-evaluation claims?
7. Are migrations from `oasisProgress` and client-created quiz records explicit, reversible where necessary, and tested in the Firebase Emulator?

## 15. Source Documents and Ownership

- Canonical architecture and implementation order: `docs/plans/2026-07-05-001-feat-fyp1-prototype-development-plan(2)(1).md`.
- Current enforced rule baseline: `firestore.rules`.
- U2 content source/deployment: `firebase_seed/seed_data.json`, `firebase_seed/seed_firestore.js`, and later controlled configuration tooling.
- U3 secure session implementation: `lib/shared/services/quiz_session_service.dart`, `lib/shared/repositories/learning_repository.dart`, `functions/quiz_session.py`, `functions/main.py`, and their tests.
- Stage 3 reserved database records: `docs/plans/logic-oasis-stage3-onboarding-animation-plan(2).md` and `docs/plans/logic-oasis-stage3-canonical-integration-review-plan.md`.

Update this document whenever a collection, field, access rule, or ownership boundary changes. A code change that contradicts this contract must update the contract and its Firestore Emulator test in the same unit of work.
## U10 FYP1 Forum Closure Addendum (authoritative, 2026-08-09)

The implemented student forum uses these collections and identities:

| Collection | Identity and implemented contract |
|---|---|
| `forumQuestions/{questionId}` | student-authored `title`, `text`, timestamps, and server-owned acceptance fields |
| `forumAnswers/{answerId}` | `questionId`, author, `text`, monotonic `revision`, server-owned `aiFeedback`, and `acceptedAt` |
| `forumHelpfulMarks/{studentId_answerId}` | idempotent helpful action |
| `forumReports/{reporterId_targetType_targetId}` | convergent server-owned moderation report |
| `forumBlocks/{studentId_blockedStudentId}` | student-owned block relationship |
| `forumParticipationEvents/{eventId}` | immutable counter event |
| `forumParticipationAggregateClaims/{claimId}` | idempotent aggregation claim |
| `forumParticipationWeeklySummaries/{studentId_week}` | server-owned Malaysia-week materialization |
| `forumParticipationSummaries/{studentId}` | current count-only student/linked-parent projection |
| `parentPracticeSummaries/{studentId}` | U14 server-owned current-week rhythm; one current week plus one optional prior total, no raw identifiers |
| `forumAiJobs/{answerId}` | mutable lease/fencing job for the latest answer revision |
| `forumAiRuns/{logicalInferenceId}` | immutable revision/text/model/artifact/policy/claim-level result |
| `modelRegistry/{releaseId}` | forum-scoped immutable release bindings with controlled lifecycle pointer |

`logicalInferenceId` is deterministic over answer ID, revision, text hash,
model version, artifact identity, claim level, and advisory policy. Jobs record
`state`, `attemptCount`, lease expiry, fencing generation, revision, text hash,
artifact identity, and policy version. Runs preserve the same lineage plus
`resultState` and never use raw answer text as identity or evidence.

The observed job/result state contract is `processing -> completed|fallback`,
with `retryable` for bounded transient recovery, terminal `failed`, and
audit-only `superseded`. `queued` is not an implemented runtime write state.

Students may read forum questions/answers and create only bounded client-owned
fields. Callables/triggers own helpful, acceptance, moderation, counters, AI
jobs, AI runs, and feedback. A linked parent may read only
`forumParticipationSummaries/{studentId}`; raw forum text, identities,
moderation, AI records, model registry, and parent-link documents remain denied.

The evidence ladder is `synthetic_test`, current
`controlled_demonstration`, and future `real_evaluated`. Controlled activation
requires explicit `controlled_demo` mode, exactly one active compatible release,
matching bounded code revision, dependency and hash bindings, and source/vendor
parity before model deserialization. Revocation/supersession changes only
lifecycle pointer fields and preserves prior release/run evidence. The
dedicated cloud identity is declared and contract-tested; it is required only
when an authorized cloud deployment occurs, which remains pending.

## Supervisor Quiz Learning Loop Refinements Addendum (U15-U20, authoritative 2026-08-12)

The supervisor refinements separate learner access from mastery, ground every
active question in uploaded teaching material, and replace fixed guidance and
count-only review with authored, answer-free feedback and one server-backed
next action. This addendum is the authoritative field contract; earlier
descriptions of score-gated unlocking and `guidedSteps` guidance are
superseded.

### Content provenance and activation

- `questions/{questionId}` is the only client-readable content record. It
  carries the approved bilingual projection plus `questionType`/`questionTypeBm`
  and material locators, and never contains `answerIndex`, `feedbackByOption`,
  `difficultyReview`, or author/reviewer state.
- `questionAnswerKeys/{questionId}` is server-only. It carries `answerIndex`,
  per-wrong-option `feedbackByOption` entries (misconception code, bilingual
  hint, optional different-number worked example, bilingual review focus), and
  the reviewed difficulty metadata. `guidedSteps` is no longer authored.
- `contentSourceManifest/{materialId}` is the server-only approval record:
  material filename/SHA-256, source-section class, bilingual locator, exact
  bilingual content digest, content version, author/reviewer identity, and
  approval timestamp. Any prompt, option, hint, example, type, focus, or
  translation change alters the digest and blocks activation until re-approval.
- Active banks contain exactly five questions; the callable serves the complete
  five-question form and validates every wrong option's feedback before any
  response is sealed.

### Access, mastery, and next action

- `subtopicMastery` writes `attempted: true` and `accessUnlocked: true` for
  every valid finalized attempt, including 0%. `completed` is separate: it is
  promoted only by `subtopic-completion-v1` (BKT `masteryProbability >= 0.72`
  with at least five validated observations) and is monotonic.
- `recommendedLearningAction` is `repeat_subtopic` below the criterion and
  `advance` with target topic/subtopic IDs when it passes. `recommendationBasis`
  is `bkt_mastery` normally, `correct_rate_fallback` when BKT processing
  terminates in fallback/failed state, and `provisional_pending_ai` on the
  immediate finalization projection before analysis completes.
- `quizAttempts.reviewItems` is answer-free and lists only missed questions in
  quiz order with prompt, type, and review focus in both languages.
- `studentAiStatuses` remains the only client-readable analysis state; a repeat
  session start is refused with a retryable `analysis-pending` response until
  the assignment's source analysis reaches a terminal state.
