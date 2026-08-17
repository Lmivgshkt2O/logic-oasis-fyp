# Logic Oasis

AI-driven mathematics mobile app for Malaysian primary students.

## Project Scope

Logic Oasis is an FYP prototype for a bilingual KSSR mathematics learning app.
The first milestone focuses on one complete learning loop:

```text
student home -> topic selection -> quiz -> result -> setting -> locked parent dashboard
```

The app uses a minimalist "restore the oasis" theme with Math Crystals,
Mutual Aid Energy, topic mastery, and parent-friendly recommendations.

## Technology Stack

- Flutter
- Firebase Authentication
- Cloud Firestore
- Python ML model exploration

## FYP1 Prototype Features

- Logic Oasis home screen
- Formula Forge topic selection
- Fractions quiz with five sample questions
- Quiz result screen
- Setting tab with protected Parent Dashboard module
- Parent dashboard with progress summary
- Rule-based weak-topic recommendation
- Local sample data while Firebase is being connected

## Run Locally

From this folder:

```powershell
flutter pub get
flutter run
```

If using an Android emulator, open the emulator first from Android Studio.

## Firebase Emulators (development only)

Start the local emulators (`firebase emulators:start --only auth,firestore,functions`)
and run the app with:

```powershell
flutter run --dart-define=USE_FIREBASE_EMULATORS=true
```

The composite forum runtime requires the operator-supplied, gitignored
project env (see `functions/.env.logic-oasis-fyp.example`). For an emulator run,
set these in the shell first (values generated from the selected release
manifest):

```powershell
$env:FORUM_MODEL_EVIDENCE_MODE='controlled_demo'
$env:FORUM_RUNTIME_CODE_REVISION='<sha256-of-the-selected-release-code-revision>'
```

The emulator host is resolved once and shared by Auth, Firestore, and Functions:

- Android Virtual Device (default): `10.0.2.2` (the host loopback alias).
- Desktop and web (default): `localhost`.
- Physical Android device on the same LAN: pass your computer's LAN address, e.g.
  `--dart-define=FIREBASE_EMULATOR_HOST=192.168.1.50`.
- Physical Android device with `adb reverse` (no LAN needed):
  `--dart-define=FIREBASE_EMULATOR_HOST=localhost`, then tunnel the three ports:

  ```powershell
  adb reverse tcp:9099 tcp:9099   # Auth
  adb reverse tcp:8080 tcp:8080   # Firestore
  adb reverse tcp:5001 tcp:5001   # Functions
  ```

The override must be a bare host: no scheme, port, or path. `localhost` is
allowed as the `adb reverse` tunnel alias; numeric loopback addresses
(`127.0.0.1`, `::1`) are rejected because they point at the device itself.
Release builds never enable emulators unless the developer explicitly passes
`--dart-define=USE_FIREBASE_EMULATORS=true`.

## Next Build Steps

1. Add Firebase project configuration with FlutterFire.
2. Replace sample quiz data with Firestore topics and questions.
3. Save quiz attempts to Firestore.
4. Add Firebase login for the student session.
5. Convert the rule-based weak-topic signal into a report document for parents.
