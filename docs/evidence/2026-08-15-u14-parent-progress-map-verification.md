# U14 Parent Evidence Progress Map - Verification Record

Date: 2026-08-15

Branch: `codex/feat-u14-parent-evidence-progress-map`

Environment: Windows with Flutter/Dart, the Firebase Emulator Suite (Auth on
9099, Firestore on 8080), and the project's Python 3.11 Functions runtime.
Only temporary, disposable identities and sanitized fixtures were used; no
real student, parent, supervisor, or production-learning data was touched.

Scope: canonical FYP1 unit U14 (parent Progress Map) - the approved screen
(weekly glance, Understanding, Practice Effort, Mutual Aid, one action and its
conversation starter), the projection-only privacy boundary, and every declared
availability/retry/revocation state.

## Automated gates

| Gate | Command | Result |
|---|---|---|
| Flutter full suite | `flutter test` | 229 passed |
| Flutter analyzer | `flutter analyze` | No issues |
| Functions suite | `python -m unittest discover -s functions/tests -t .` | 225 passed |
| Tools/release suite | `python -m unittest tools.tests.*` | 43 passed |

The focused model, repository, state, widget, localization, accessibility, and
golden gates are part of the Flutter suite; the parent-link Rules contract and
quiz-finalization regressions are part of the Functions suite.

## Authenticated emulator flow

The static Rules contract test is not sufficient on its own, so U14 adds an
authenticated Emulator flow that signs in a linked parent, an unrelated
parent, a revoked parent, and one student, seeds only the safe projections,
and proves the exact-child read matrix plus every denied path.

Command (from the repository root):

```powershell
$env:GCLOUD_PROJECT='logic-oasis-fyp'
firebase.cmd emulators:exec --only auth,firestore "node tools/run_parent_dashboard_emulator_flow.js"
```

Result (sanitized; all identities are random temporary emulator users):

```json
{
  "status": "passed",
  "step": "cleanup",
  "exactChildReads": {
    "subtopicMastery": true,
    "parentPracticeSummaries": true,
    "forumParticipationSummaries": true
  },
  "deniedReadsCount": 21,
  "deniedReads": [
    "cross-child subtopicMastery",
    "cross-child parentPracticeSummaries",
    "cross-child forumParticipationSummaries",
    "subtopicMastery collection enumeration",
    "parentPracticeSummaries collection enumeration",
    "forumParticipationSummaries collection enumeration",
    "raw quizAttempts read",
    "raw questionResponses read",
    "raw questionAnswerKeys read",
    "raw aiJobs read",
    "raw aiModelRuns read",
    "forum text question read",
    "forum text answer read",
    "parentLinks direct read",
    "client write to parentPracticeSummaries",
    "client write to forumParticipationSummaries",
    "client create of subtopicMastery",
    "unrelated parent exact-child subtopicMastery read",
    "unrelated parent exact-child practice read",
    "revoked parent exact-child practice read",
    "revoked parent exact-child mastery read"
  ],
  "callableContext": "covered-by-u9-live-verification",
  "fixtureCleanup": "deleted"
}
```

What this proves:

- A linked parent reads exactly the selected child's three safe projections
  (`subtopicMastery`, `parentPracticeSummaries/{studentId}`,
  `forumParticipationSummaries/{studentId}`) and nothing else.
- Collection/list enumeration is denied, so a parent cannot discover another
  child's records.
- Raw attempts, responses, answer keys, AI jobs/runs, forum text, parent-link
  documents, and all client writes to projections are denied.
- An unrelated parent and a revoked parent cannot read the child's
  projections.
- Controlled fixture cleanup is recorded (`fixtureCleanup: deleted`); every
  temporary user, profile, link, projection, and raw fixture was deleted.

The `getLinkedChildren` callable context (linked/unrelated/revoked parent
visibility) is covered by the U9 controlled live verification
(`docs/evidence/2026-07-19-u9-controlled-live-verification.md`), which ran the
same boundary against the deployed callable. When the Functions emulator is
included in a run, the operator provides the functions params through the
gitignored `functions/.env.logic-oasis-fyp` file (per
`functions/.env.logic-oasis-fyp.example`); the U14 emulator flow runs the
Auth + Firestore matrix so the Rules boundary is proven without requiring
production token-verification endpoints.

## UI state captures

Durable four-state captures are generated reproducibly by
`flutter test --update-goldens test/parent_dashboard_screenshot_test.dart`.
They render the approved hierarchy with the test font, so they evidence
layout, hierarchy, colour, and state differentiation; the live emulator
rehearsal captures (below) are the text-accurate screenshots for the
supervisor record.

![full](2026-08-15-u14-screenshots/full.png)

![partial](2026-08-15-u14-screenshots/partial.png)

![zero](2026-08-15-u14-screenshots/zero.png)

![insufficient](2026-08-15-u14-screenshots/insufficient.png)

Live capture commands (manual emulator rehearsal):

```powershell
firebase.cmd emulators:start --only auth,firestore
flutter run -d chrome --dart-define=USE_FIREBASE_EMULATORS=true
```

Sign in as the linked parent through Settings -> Parent Dashboard and capture
the four states as `screenshots/live-full.png`, `live-partial.png`,
`live-zero.png`, and `live-insufficient.png` (files, not the temporary
clipboard image).

## Accessibility checks

- Screen-reader order is title -> glance -> Understanding -> Practice Effort
  -> Mutual Aid -> conversation starter (semantics test).
- Daily counts (`Mon: 1` ...) and Mutual Aid counts are announced; status uses
  icon plus text, never colour alone.
- English and Bahasa Melayu render titles, plural counts, and day labels.
- 320 px width and 200% text scale are exercised in the widget gates and the
  manual rehearsal checklist (AE8); no clipping or horizontal overflow is
  expected because the map stacks vertically inside a scrollable scaffold.

## Limitations

- Widget-rendered captures use the test font; live screenshots from the
  emulator rehearsal are required for text-accurate evidence.
- The U14 emulator flow runs Auth + Firestore; the Functions callable context
  is cited from the U9 live verification because Python admin token
  verification against the Auth emulator is not part of this environment.
- No production or real learner data was used; fixtures were sanitized and
  deleted after the run.

## FYP1 exclusions (unchanged)

- Longitudinal trend charts, conversational coaching, AI Guard for parents,
  generative personalised advice, parent chat or forum-content previews, peer
  comparison/ranking, and client-side attempt aggregation remain outside
  FYP1 (deferred to FYP2 or excluded by the canonical plan).
- Quiz guided-step implementation (canonical U13), adaptive-bank comparison,
  Oasis stages, and onboarding are separate units, not part of U14.
