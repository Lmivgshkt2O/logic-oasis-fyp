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

## Next Build Steps

1. Add Firebase project configuration with FlutterFire.
2. Replace sample quiz data with Firestore topics and questions.
3. Save quiz attempts to Firestore.
4. Add Firebase login for the student session.
5. Convert the rule-based weak-topic signal into a report document for parents.
