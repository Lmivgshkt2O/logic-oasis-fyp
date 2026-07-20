# Logic Oasis Feature Implementation Explanation

This document explains how the current Logic Oasis prototype is implemented from a developer point of view. It is not a planning document. It describes the actual frontend structure, backend/Firebase structure, shared state logic, and feature workflows so a developer can understand how the app works before editing it.

**U1 audit status (2026-07-13):** Sections 1-19 are a living explanation of the current implementation and should be updated as later units change the app. Section 20 is the dated pre-U2 baseline snapshot and must remain an audit record rather than being silently rewritten as gaps close. Both were checked against the live repository on this date. The canonical target is `docs/plans/2026-07-05-001-feat-fyp1-prototype-development-plan(2)(1).md`; its confirmed decisions replace the older supervisor-question assumptions that previously appeared in this document.

## 1. High-Level App Structure

Logic Oasis is a Flutter app with Firebase as the main backend and local fallback state for demo resilience.

The entry point is `lib/main.dart`. It initializes Flutter bindings, starts Firebase with `firebase_options.dart`, then runs `LogicOasisApp`.

`lib/app/logic_oasis_app.dart` owns the app-level lifecycle:

- Creates the shared `AppState` with `persistQuizResults: true`.
- Loads Firebase topics during startup.
- Loads saved app preferences after the opening animation.
- Checks whether Firebase Auth already has a current student.
- Switches between opening animation, login, plot intro, and the main shell.
- Wraps the app in `AppStateScope`, localization delegates, theme, and accessibility text scaling.

`lib/app/logic_oasis_shell.dart` is the main child-facing shell. It keeps the active prototype to three tabs:

- Home
- Formula Forge
- Settings

The shell reads `state.selectedTab`, builds the matching page, and uses `BottomNavBar` from `lib/shared/widgets/logic_oasis_figma_components.dart`. `AppState.changeTab()` clamps tab indexes to `0..2`, which protects the app from old or invalid tab jumps.

## 2. Core Architecture Pattern

The app follows a simple Flutter architecture:

```text
UI page/widget
  reads AppState
  calls AppState method
    updates local state
    optionally calls repository
      reads/writes Firebase
    saves SharedPreferences when needed
  notifies UI through ChangeNotifier
```

The central state object is `lib/shared/state/app_state.dart`.

`AppState` extends `ChangeNotifier` and stores:

- Current tab and app preferences.
- Current student identity and year level.
- Topic, subtopic, and question data.
- Quiz attempts and mastery progress.
- Crystals and mutual aid energy.
- Oasis restoration areas.
- AI diagnosis records.
- Parent dashboard loading status.
- Firebase sync messages.

The provider mechanism is `lib/shared/state/app_state_scope.dart`. It uses `InheritedNotifier<AppState>` instead of a third-party state package. Pages call:

- `AppStateScope.watch(context)` when the UI must rebuild after state changes.
- `AppStateScope.read(context)` when only a one-time state access is needed.

## 3. Backend and Persistence Structure

The backend layer is in `lib/shared/repositories/`.

| Repository | Main responsibility |
|---|---|
| `auth_repository.dart` | Student login/register, Google sign-in, remembered profile, parent account setup, parent password check, parent password reset, student profile update. |
| `topic_repository.dart` | Loads topics, questions, and subtopics from Firestore, then converts them into `Topic`, `Subtopic`, and `QuizQuestion` models. |
| `learning_repository.dart` | Saves quiz attempts, topic mastery, subtopic mastery, oasis progress, and fetches parent dashboard snapshots with AI diagnosis records. |

The app uses Firebase Auth for student authentication and Firestore for app data. SharedPreferences is used for local session preferences such as selected tab, language, reminders, accessibility mode, screen time limit, unlocked progression, claimed mission rewards, and locally saved attempts.

## 4. Important Data Models

Core models live in `lib/shared/models/`.

| Model | Purpose |
|---|---|
| `topic.dart` | Represents a KSSR topic, including title, bilingual title, year level, questions, subtopics, progress, and mastery. |
| `subtopic.dart` | Represents a smaller learning step inside a topic, including order, bilingual text, progress, mastery, and questions. |
| `quiz_question.dart` | Represents a multiple-choice question with bilingual question/options/explanation support. |
| `quiz_completion.dart` | Returned from `QuizPage` to tell the caller how many answers were correct and how long the quiz took. |
| `quiz_attempt.dart` | Stores one completed quiz attempt for local state, Firestore persistence, dashboard metrics, and the legacy manual-pipeline input. The canonical AI contract requires server-finalized ordered responses. |
| `quiz_reward.dart` | Stores the reward output after a quiz: score, earned crystals, previous/new mastery, and encouragement text. |
| `oasis_area.dart` | Represents each repairable oasis area, including cost, resource type, progress, marker position, and restoration image paths. |
| `recommended_mission.dart` | Represents the Home mission card, progress toward mission completion, and reward claim status. |
| `weak_topic_insight.dart` | Represents a rule-based weak-topic summary for parent dashboard fallback. |
| `ai_diagnosis.dart` | Parses AI model run data from Firestore, including BKT probability, XGBoost prediction, SHAP reasons, confidence, and recommendation. |
| `parent_dashboard_snapshot.dart` | Groups parent dashboard data fetched from Firestore. |

## 5. Authentication and Entry Flow

### Frontend

The opening flow starts in `OpeningAnimationPage`. When it finishes, `LogicOasisApp.completeOpening()` loads saved preferences and checks `AuthRepository.loadCurrentStudentProfile()`.

If no Firebase Auth user exists, the app shows `LoginPage`. If a valid profile exists in Firestore, the app updates `AppState` with the signed-in student and opens `LogicOasisShell`.

`LoginPage` supports:

- Email/password login.
- Remember profile option.
- Google sign-in path.
- Navigation to `RegisterPage`.

`RegisterPage` creates a Firebase Auth user and a Firestore `users/{uid}` profile.

### Backend

`AuthRepository.signInStudent()` calls Firebase Auth, then validates that `users/{uid}` exists. If the Firestore profile is missing, the user is signed out and the login is rejected.

`AuthRepository.registerStudent()` creates the Firebase Auth user, updates the display name, writes the `users/{uid}` document, and optionally stores a remembered profile in SharedPreferences and `rememberedProfiles/{uid}`.

### State Logic

After login/register, `LogicOasisApp` calls `AppState.updateSignedInStudent()`. This sets:

- `currentStudentId`
- `currentStudentEmail`
- `studentName`
- `yearLevel`

Then it saves the session and starts Firebase loads for oasis progress and parent dashboard data.

## 6. Home Feature

### Frontend

Home is implemented in `lib/features/home/home_page.dart`.

It shows:

- Sprout avatar.
- Student greeting.
- Crystals, mutual aid energy, and streak stat cards.
- Mission reminder toggle.
- Settings shortcut.
- Oasis restoration hero.
- Recommended mission card.

The visual system comes mostly from `lib/shared/widgets/logic_oasis_figma_components.dart`, including `LogicOasisScaffold`, `SproutAvatar`, `StatCard`, `OasisHeroCard`, and `MissionCard`.

### Restoration UI

Home passes these values into `OasisHeroCard`:

- `state.restorationProgress`
- `state.oasisAreas`
- `state.crystals`
- `state.mutualAidEnergy`
- `state.canRepair`
- `state.repairOasisArea`

There is also a separate `lib/features/home/widgets/oasis_map.dart` implementation that contains a custom-painter oasis map and repair detail sheet. Current shared components also include restoration rendering in `logic_oasis_figma_components.dart`.

### State Logic

`AppState.restorationProgress` averages the progress of all `oasisAreas`.

Each `OasisArea` has:

- `resource`: either crystals or mutual aid.
- `repairCost`.
- `progress`.
- damaged, repairing, and restored image paths.

`OasisArea.currentImage` chooses the image:

- progress `< 0.5`: damaged image
- progress `>= 0.5` and `< 1.0`: repairing image
- progress `>= 1.0`: restored image

`AppState.canRepair(area)` checks whether the area is not complete and whether the student has enough of the required resource.

`AppState.repairOasisArea(areaId)` deducts the resource, increases progress, notifies the UI, saves local session state, and syncs oasis progress to Firestore when persistence is enabled.

### Backend

Oasis progress is saved through `LearningRepository.saveOasisProgress()` into `oasisProgress/{studentId}` with:

- `studentId`
- `yearLevel`
- `crystals`
- `mutualAidEnergy`
- `language`
- `missionReminders`
- `eyeComfortMode`
- `repairedAreas`
- `updatedAt`

### Current Caveat

The current `AppState._applyOasisProgress()` contains demo/testing behavior: it resets all area progress to `0.0`, grants `800` crystals and `800` mutual aid energy, then saves that reset back to Firebase. A future developer should remove or isolate this before treating Firebase progress as production-like behavior.

The state also references `home_overlay_*_50.png` and `home_overlay_*_100.png` paths, but the current `assets/illustrations/oasis_parts/` folder contains the standalone damaged/repairing/restored PNGs. Either add those overlay assets or remove the overlay references.

## 7. Formula Forge Feature

### Frontend

Formula Forge is implemented in `lib/features/formula_forge/formula_forge_page.dart`.

It shows:

- Header and village illustration.
- Firebase topic loading status.
- Quiz save status.
- Topic cards.

Each topic card is rendered by `lib/features/formula_forge/widgets/topic_card.dart`.

When a topic is openable, tapping it pushes `SubtopicPage`.

### Topic Unlock Logic

`FormulaForgePage` calls:

- `state.isTopicUnlocked(topic)`
- `state.lockedReasonForTopic(topic)`
- `state.subtopicsForTopic(topic)`

`AppState.isTopicUnlocked()` unlocks the first topic by default. Later topics unlock if the previous topic is complete or if the topic was previously recorded in `_unlockedTopicIds`.

Topic completion is calculated by `_isTopicComplete()`:

- If the topic has subtopics, all subtopics must be complete.
- If there are no subtopics, `Moderate` or `Strong` mastery is enough.
- Otherwise progress above `0.5` is enough.

### Backend

`AppState.loadTopicsFromFirebase()` calls `TopicRepository.fetchTopicsWithQuestions(yearLevel: yearLevel)`.

`TopicRepository` reads:

- `topics`
- `questions`
- `subtopics`

It groups questions by topic and subtopic, filters topics/subtopics by year level and `isActive`, sorts them by `order`, and returns `Topic` objects with attached `Subtopic` and `QuizQuestion` lists.

If Firebase topic loading fails or returns no useful data, `AppState` keeps local topic data as fallback.

## 8. Subtopic Workflow

### Frontend

Subtopic flow is implemented in `lib/features/formula_forge/subtopic_page.dart`.

It displays:

- Topic title.
- Topic progress summary.
- Ordered subtopic cards.
- Lock state and locked reason.
- Subtopic progress bar.
- Mastery/lock chip.

Tapping an unlocked subtopic with questions starts `QuizPage`.

### Subtopic Unlock Logic

`AppState.isSubtopicUnlocked(topic, subtopic)` unlocks the first subtopic by default. Later subtopics unlock if:

- the previous subtopic is complete, or
- the subtopic key was previously stored in `_unlockedSubtopicIds`.

`Subtopic.isComplete` is based on progress/mastery. After a quiz, `AppState.saveQuizResult()` updates the selected subtopic progress and mastery.

### Workflow

```text
FormulaForgePage
  topic card tapped
    SubtopicPage
      subtopic card tapped
        QuizPage
          returns QuizCompletion
      AppState.saveQuizResult()
      ResultPage
        back button returns to SubtopicPage
```

This is important because the student returns to the same topic context and can see which subtopic was completed or unlocked.

## 9. Quiz Feature

### Frontend

Quiz is implemented in `lib/features/quiz/quiz_page.dart`.

It receives:

- a `Topic` object containing only the selected subtopic questions
- the current language flag

It tracks local widget state:

- `questionIndex`
- `correctCount`
- `selectedIndex`
- `answered`
- `startedAt`

When the student selects an answer, the page marks it selected and increments `correctCount` if correct. After each answer, it shows the explanation using `RecommendationBox`.

When the last question is finished, `QuizPage` pops a `QuizCompletion` object back to `SubtopicPage`.

### State Logic

`SubtopicPage` receives `QuizCompletion` and calls `AppState.saveQuizResult()`.

`saveQuizResult()`:

- Finds the topic.
- Validates `totalQuestions`.
- Calculates score.
- Calculates earned crystals.
- Calculates new mastery.
- Updates selected subtopic progress and mastery.
- Recalculates topic progress from completed subtopics.
- Inserts a new local `QuizAttempt`.
- Returns a `QuizReward`.
- Saves local session state.
- Saves quiz attempt/mastery and oasis progress to Firebase when enabled.

The current score thresholds are:

- `Strong`: score `>= 80`
- `Moderate`: score `>= 50`
- `Weak`: below `50`

Crystal reward is calculated inside `_calculateCrystals()`.

### Backend

`LearningRepository.saveQuizAttemptAndMastery()` writes a Firestore batch:

- `quizAttempts/{attemptId}`
- `topicMastery/{studentId}_y{yearLevel}_{topicId}`
- `subtopicMastery/{studentId}_y{yearLevel}_{topicId}_{subtopicId}` when a subtopic exists

`buildQuizAttemptData()` stores raw attempt data such as score, correct count, wrong count, correct rate, time taken, retry count, difficulty, mastery level, and earned crystals.

`buildTopicMasteryData()` aggregates topic progress from attempts and completed subtopics.

`buildSubtopicMasteryData()` calculates best correct rate and whether the subtopic is completed.

## 10. Result Feature

### Frontend

Result is implemented in `lib/features/quiz/result_page.dart`.

It receives:

- correct count
- total questions
- topic/subtopic display name
- language flag
- `QuizReward`
- back action callback

It displays:

- score percentage
- crystals earned
- repair-ready message
- mistake count
- mastery change explanation
- next recommended action

The back button label can be customized. In the subtopic flow it is `Back to Subtopics`.

### State Relationship

`ResultPage` does not save data by itself. It only displays the `QuizReward` already produced by `AppState.saveQuizResult()`.

This separation matters: the quiz result is saved before the Result page is shown, so closing the Result page does not lose the attempt.

## 11. Recommended Mission Feature

### Frontend

The Home mission card is rendered by `_HomeMissionCard` in `home_page.dart`, using `MissionCard` from shared widgets.

It shows:

- mission topic
- short duration/difficulty label
- required completions
- reward label
- progress count
- claim state

### State Logic

`AppState.recommendedMission` is derived from the current recommended topic. The state prefers AI diagnosis when available, then falls back to weak-topic or unclaimed topic logic.

When the mission is not ready, tapping the card moves the student to Forge with `state.changeTab(1)`.

When ready, `AppState.claimRecommendedMissionReward()`:

- Adds reward crystals.
- Marks the topic as claimed in `claimedRecommendedMissionTopicIds`.
- Saves local session state.
- Syncs oasis progress to Firebase when enabled.

## 12. Settings Feature

### Frontend

Settings is implemented in `lib/features/settings/settings_page.dart`.

It shows:

- Student profile card.
- Sound toggle.
- Language selector.
- Accessibility toggle.
- Mission reminder toggle.
- Eye protecting mode toggle.
- Screen time control.
- Parent dashboard access card.
- Privacy and safety information.
- Logout button.

Most rows use `SettingsRow` from shared Figma components.

### State Logic

Settings calls these `AppState` methods:

- `updateLanguage()`
- `updateMissionReminders()`
- `updateEyeComfortMode()`
- `updateSoundEnabled()`
- `updateAccessibilityMode()`
- `updateScreenTimeLimit()`
- `updateStudentProfile()`

These methods update local state, notify the UI, save SharedPreferences, and in some cases sync oasis preferences to Firebase.

### Student Profile Update

The profile sheet calls `AuthRepository.updateStudentProfile()`, which updates Firebase Auth display name when the current user matches, then writes the changed display name/year level to `users/{uid}` and `rememberedProfiles/{uid}`.

If year level changes, `AppState` resets topics for the new year and reloads topics from Firebase.

## 13. Parent Access and Parent Dashboard

### Parent Access

Parent access starts from Settings.

The related pages are:

- `lib/features/settings/parent_link_page.dart`
- `lib/features/settings/parent_auth_page.dart`
- `lib/features/settings/parent_password_reset_page.dart`

`AuthRepository.fetchLinkedParentAccount()` checks whether the student profile has a linked parent account.

If no parent is linked, `ParentLinkPage` can register one. `AuthRepository.registerLinkedParentAccount()` creates or merges a `parentAccounts/{parentId}` document, stores a prototype `passwordKey`, adds the student ID, and updates the student `users/{uid}` document with parent link fields.

`ParentAuthPage` verifies the parent password through `AuthRepository.authenticateLinkedParent()`.

Password reset uses a prototype OTP flow. `sendParentResetOtp()` writes fixed OTP `246810`; `resetLinkedParentPassword()` checks the OTP and updates the password key.

### Parent Dashboard Frontend

Parent dashboard is implemented in `lib/features/parent_dashboard/parent_dashboard_page.dart`.

It loads Firebase data in `initState()` by calling `state.loadParentDashboardFromFirebase()`.

It displays:

- Parent summary.
- Learning story summary.
- Overall restoration.
- Average score.
- Latest quiz score.
- Recent activity.
- Weak-topic prediction.
- AI diagnosis details when available.
- Suggested action.
- Parent action steps.

### Parent Dashboard Backend

`AppState.loadParentDashboardFromFirebase()` calls `LearningRepository.fetchParentDashboardSnapshot()`.

That repository fetches:

- `quizAttempts` for the student.
- `topicMastery` for the student.
- `aiModelRuns` for the student.

It filters records by current year level and keeps only the latest AI diagnosis per topic.

`AppState` then merges the snapshot into local attempts and `aiDiagnoses`.

### Weak Topic and AI Logic

If AI diagnosis exists, `recommendedAiDiagnosis` prioritizes it using `AiDiagnosis.priorityScore`, which combines weakness probability and mastery gap.

If AI data is missing, the app uses rule-based weak-topic insight from quiz attempts. The fallback logic looks at average scores and attempt counts to build a parent-friendly weakness reason and recommendation.

AI diagnosis data is parsed by `AiDiagnosis.fromFirestore()`. It supports:

- `modelName`
- `xgboostPrediction`
- `weaknessProbability`
- `confidence`
- `shapReasons`
- `shapDetails`
- BKT parameters
- `bktMasteryProbability`
- `finalMasteryLabel`
- `recommendedAction`
- `attemptsCount`
- `createdAt`

The Flutter app currently only displays stored AI records. BKT updates, XGBoost inference/training, and SHAP explanation run outside the client through manual or seeded paths.

## 14. Localization and Accessibility

The app uses Flutter localization generated from `lib/l10n`.

`LogicOasisApp` sets:

- `AppLocalizations.supportedLocales`
- Flutter localization delegates
- `state.locale`

`AppState.locale` returns Malay when `language == 'Bahasa Melayu'`, otherwise English.

Some content uses generated localization strings. Other feature-specific strings use `AppState.t(english, bahasaMelayu)` for lightweight bilingual switching.

Accessibility mode increases text scaling through the `MaterialApp.builder`. Eye protecting mode changes the shell theme to a warmer palette.

## 15. Visual Assets and Design System

The app registers these assets in `pubspec.yaml`:

- `assets/illustrations/`
- `assets/icons/`
- `assets/illustrations/oasis_parts/`

`flutter_svg` is used by `AppSvgIcon` to render SVG icons from `assets/icons/`.

`AppIllustration` renders JPG/PNG illustrations from `assets/illustrations/`.

The main reusable UI file is `lib/shared/widgets/logic_oasis_figma_components.dart`. It contains:

- `LogicOasisScaffold`
- `LogicHeader`
- `SoftCard`
- `SoftIconButton`
- `SproutAvatar`
- `StatCard`
- `StatusChip`
- `MissionCard`
- `OasisHeroCard`
- `RepairMarker`
- `SettingsRow`
- `BottomNavBar`
- `ProgressBar`
- topic/oasis illustration helpers

Older shared widgets still exist, such as `MetricCard`, `SectionCard`, and `RecommendationBox`. These are still used by quiz/result/parent dashboard pages.

## 16. Local Fallback Data

`AppState` contains a local topic bank for demo fallback. This lets the app remain usable when Firebase data is unavailable.

The topic loading strategy is:

1. Start with local topics for the current year.
2. Try to load Firebase topics/questions/subtopics.
3. Merge Firebase content with existing local progress.
4. If Firebase fails, keep local topics and show a status message.

This fallback is intentional for FYP demo stability, but developers should avoid presenting fallback data as the final database design.

## 17. Firestore Collections Used by the Current Code

The current code directly uses these collections:

| Collection | Used by | Purpose |
|---|---|---|
| `users` | `AuthRepository` | Student profiles, parent links, year level, display name. |
| `rememberedProfiles` | `AuthRepository` | Remembered login profile metadata. |
| `parentAccounts` | `AuthRepository` | Prototype parent access records and reset OTP. |
| `topics` | `TopicRepository` | Topic metadata. |
| `subtopics` | `TopicRepository` | Subtopic metadata. |
| `questions` | `TopicRepository` | Quiz question bank. |
| `quizAttempts` | `LearningRepository` | Raw completed quiz attempts. |
| `topicMastery` | `LearningRepository` | Aggregated topic progress/mastery. |
| `subtopicMastery` | `LearningRepository` | Aggregated subtopic progress/mastery. |
| `oasisProgress` | `LearningRepository` | Crystals, mutual aid energy, preferences, and repaired area progress. |
| `aiModelRuns` | `LearningRepository` | Seeded/offline AI diagnosis output for parent dashboard and recommendations. |

## 18. End-to-End Learning Loop

The core prototype loop is:

```text
Student logs in
  -> Formula Forge loads topics
  -> Student opens topic
  -> Student chooses unlocked subtopic
  -> Student answers quiz
  -> Quiz returns completion data
  -> AppState saves result
  -> Crystals increase
  -> Subtopic/topic mastery updates
  -> Attempt/mastery optionally save to Firebase
  -> Result page shows score and next action
  -> Home can repair oasis area
  -> Parent dashboard can explain progress and weak topic
```

This loop is the most important feature relationship in the app. Most future changes should protect this path before expanding secondary features.

## 19. Current Implementation Caveats

These are not blockers for understanding the app, but developers should know them:

- Parent authentication is prototype-level and uses a stored password key, not production Firebase parent auth.
- Mission reminders are a stored preference, not real scheduled notifications.
- The Flutter client only displays stored AI records; the current BKT/XGBoost/SHAP path is manual or seeded rather than client-run or automatically triggered.
- Restoration progress loading currently contains test/demo reset behavior that should be removed or isolated.
- Some Home restoration overlay paths are referenced but corresponding overlay assets are not present.
- Some pages still mix older shared widgets with the newer Figma-style design system.
- `ProgressPage` exists but is not part of the current Home/Forge/Settings shell.

## 20. U1 Baseline and Contract Gap Checklist

This checklist freezes the live baseline before U2 begins. It records blocking differences between the current app and the canonical FYP1 contract; it does not reopen completed visual work or the confirmed Home/Forge/Settings navigation decision.

| Contract area | Live repository evidence | U1 status | Plan trace |
|---|---|---|---|
| Existing learning loop | Login leads to the three-tab shell; Forge opens topic -> subtopic -> `QuizPage`; `SubtopicPage` calls `AppState.saveQuizResult()` before showing `ResultPage`; Home restoration and Parent Dashboard read the resulting state. | Baseline confirmed. Preserve this flow. | U2-U13 regression contract. |
| Three-tab shell | `LogicOasisShell` contains Home, Formula Forge, and Settings only; `AppState.changeTab()` clamps indexes to `0..2`. | Confirmed final navigation baseline. Do not add a fourth bottom tab. | U10. |
| Trusted question content | `QuizQuestion`, `TopicRepository`, local fallback content, and `QuizPage` expose `answerIndex` and explanations to the Flutter client. `QuizPage` calculates correctness locally. | Blocking gap: client-visible answers are not authoritative evidence. | U2-U3. |
| Question-bank contract | Questions are grouped by topic/subtopic, but there is no first-class `questionBanks`/`bankId` contract with Easy, Moderate, and Hard forms. | Blocking gap: adaptive bank assignment cannot be represented or audited. | U2, U5. |
| Attempt granularity | `LearningRepository.saveQuizAttemptAndMastery()` writes one attempt summary plus topic/subtopic aggregates. It does not persist an ordered response document for each question. | Blocking gap: summary-only persistence is insufficient for trusted BKT and detailed explanations. | U3. |
| Difficulty evidence | `_saveQuizResultToFirebase()` always passes `difficultyLevel: 'Mixed'`. Attempts do not preserve immutable `bankId`, question version, or skill-level evidence. | Blocking gap: current difficulty data cannot justify adaptive transitions. | U2-U3. |
| Rewards and mastery ownership | `AppState.saveQuizResult()` calculates score, mastery thresholds, crystals, and progression locally before the Firestore write. | Blocking gap: client-derived score/reward/mastery cannot be the trusted AI input. | U3. |
| AI runtime | `ai_pipeline/run_ai_pipeline.py` is a manually launched CLI. No `functions/` directory or Firebase function configuration exists. | Blocking gap: normal quiz completion does not invoke AI automatically. | U6, U8. |
| Legacy model artifact | `ai_pipeline/xgboost_logic_oasis_model.pkl` is loaded by the manual pipeline when present. The notebook produced it, but its current dataset provenance and promotion metadata do not satisfy the final contract. | Legacy/non-final evidence only. Do not claim it as the promoted FYP1 model. | U6-U7. |
| Real-data provenance | The manual runner can read `quizAttempts`, but the current attempt schema is summary-only and the notebook may use demo fallback rows when a real-attempt CSV is absent. | Blocking evidence gap: seeded/synthetic rows cannot support final performance claims. | U3, U6. |
| BKT/XGBoost/SHAP lineage | `aiModelRuns` can be displayed by Flutter, but current records are not automatically linked from one finalized trusted `attemptId` through a versioned job/model run. | Blocking gap: display support exists, end-to-end lineage does not. | U4, U7-U8. |
| Parent AI evidence | Parent Dashboard reads the latest `aiModelRuns` per topic and falls back to rule-based insight. It does not distinguish a seeded/manual record from a trusted automatic run. | Blocking integration gap. Fallback remains useful but cannot be presented as final AI evidence. | U9. |
| Collaboration/Objective 3 | No `lib/features/collaboration/` implementation exists and no Q&A Naive Bayes runtime is wired. | Blocking scope gap under confirmed S4. | U10-U12. |
| Restoration demo reset | `_applyOasisProgress()` currently resets all restored areas to `0.0`, grants `800` of each resource, and writes the reset back to Firestore. | Blocking normal-demo-path defect, but unrelated visual restoration work remains frozen. | U13 final gate. |
| Security boundary | Existing rules cover current collections, but there are no server-only `questionAnswerKeys`, trusted quiz-session/response restrictions, or function-owned AI/model records yet. | Blocking security gap for the revised architecture. | U2-U3, U13. |

### U1 Baseline Verification Result

| Gate | Result |
|---|---|
| Contract inspection | Complete. The checklist confirms `Mixed` difficulty, summary-only persistence, manual AI execution, absent collaboration/Functions runtime, and the legacy/non-final `.pkl` boundary. |
| Existing focused behavioral tests | Passed after resolving the managed-shell SDK-permission issue. `flutter test --no-pub --reporter expanded test\\app_state_test.dart test\\learning_repository_test.dart test\\result_page_test.dart` completed with 30 passing tests. `result_page_test.dart` now scrolls its intentionally scrollable result view before tapping the below-the-fold action. |
| Flutter static analysis | Completed with `flutter analyze --no-pub`: no errors and one unrelated pre-existing warning in `lib/features/formula_forge/widgets/topic_card.dart` for unused local variable `learningArea`. |

## 21. Recommended Reading Order for Developers

For a new developer, read files in this order:

1. `lib/main.dart`
2. `lib/app/logic_oasis_app.dart`
3. `lib/app/logic_oasis_shell.dart`
4. `lib/shared/state/app_state_scope.dart`
5. `lib/shared/state/app_state.dart`
6. `lib/shared/models/topic.dart`
7. `lib/shared/models/subtopic.dart`
8. `lib/shared/models/quiz_question.dart`
9. `lib/features/formula_forge/formula_forge_page.dart`
10. `lib/features/formula_forge/subtopic_page.dart`
11. `lib/features/quiz/quiz_page.dart`
12. `lib/features/quiz/result_page.dart`
13. `lib/features/home/home_page.dart`
14. `lib/shared/repositories/topic_repository.dart`
15. `lib/shared/repositories/learning_repository.dart`
16. `lib/shared/repositories/auth_repository.dart`
17. `lib/features/parent_dashboard/parent_dashboard_page.dart`

That reading path follows the real app flow from startup to learning loop to backend persistence.
