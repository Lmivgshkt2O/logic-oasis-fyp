// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Logic Oasis';

  @override
  String get home => 'Home';

  @override
  String get forge => 'Forge';

  @override
  String get settings => 'Settings';

  @override
  String get studentProfile => 'Student Profile';

  @override
  String get manageProfilePreferences => 'Manage your profile and preferences.';

  @override
  String get viewEditProfile => 'View and edit your profile';

  @override
  String get language => 'Language';

  @override
  String get missionReminders => 'Mission Reminders';

  @override
  String get on => 'On';

  @override
  String get off => 'Off';

  @override
  String get eyeComfort => 'Eye Comfort';

  @override
  String get logout => 'Log out';

  @override
  String get returnLogin => 'Return to the login page';

  @override
  String get confirmLogout => 'Confirm to log out?';

  @override
  String get logoutConfirmBody => 'You will return to the login page.';

  @override
  String get cancel => 'Cancel';

  @override
  String get studentProfileUpdated => 'Student profile updated';

  @override
  String languageSet(Object language) {
    return 'Language set to $language';
  }

  @override
  String get enterStudentName => 'Enter the student name.';

  @override
  String get updateStudentProfileFailed =>
      'Unable to update student profile. Please try again.';

  @override
  String get editStudentProfile => 'Edit student profile';

  @override
  String get studentName => 'Student name';

  @override
  String get year4 => 'Year 4';

  @override
  String get year5 => 'Year 5';

  @override
  String get year6 => 'Year 6';

  @override
  String get saving => 'Saving...';

  @override
  String get saveProfile => 'Save Profile';

  @override
  String get parentDashboard => 'Parent Dashboard';

  @override
  String get locked => 'Locked';

  @override
  String get unlockAccess => 'Unlock Access';

  @override
  String get unlockProgressWeakTopics =>
      'Unlock to view progress and weak topics';

  @override
  String get parentAccessRequired => 'Parent access required';

  @override
  String get enterLinkedParentPassword => 'Enter the linked parent password.';

  @override
  String get parentAccountUnavailable =>
      'Parent account is unavailable. Please try again.';

  @override
  String get parentAccountNotLinked => 'Parent account not linked';

  @override
  String get parentAccountNotLinkedBody =>
      'Create a parent demo account before opening the protected dashboard.';

  @override
  String get createParentAccount => 'Create account';

  @override
  String get parentAuthentication => 'Parent Authentication';

  @override
  String get parentAuthInstruction =>
      'Enter the linked parent password to unlock learning insights.';

  @override
  String get parentPassword => 'Parent password';

  @override
  String get showPassword => 'Show password';

  @override
  String get hidePassword => 'Hide password';

  @override
  String get forgotPassword => 'Forgot password?';

  @override
  String get checkingPassword => 'Checking password...';

  @override
  String get unlockDashboard => 'Unlock Dashboard';

  @override
  String get linkedParentEmail => 'Linked parent email';

  @override
  String get formulaForge => 'Formula Forge';

  @override
  String get forgeSubtitle => 'Choose a topic and practise calmly.';

  @override
  String get loadingFirebaseQuestionBank => 'Loading Firebase question bank...';

  @override
  String get topicLockedQuestionBank =>
      'Question bank not ready for this topic yet.';

  @override
  String get missionRemindersOn => 'Mission reminders turned on';

  @override
  String get missionRemindersOff => 'Mission reminders turned off';

  @override
  String missionRewardClaimed(Object crystals) {
    return 'Mission reward claimed: +$crystals crystals';
  }

  @override
  String get missionRewardAlreadyClaimed => 'Mission reward already claimed';

  @override
  String get recommendedMission => 'Recommended mission';

  @override
  String get done => 'Done';

  @override
  String rewardClaimedKeepPractising(Object topic) {
    return 'Reward claimed. Keep practising $topic.';
  }

  @override
  String get missionCompleteClaimReward =>
      'Mission complete. Tap to claim reward.';

  @override
  String completeTopicDrills(Object count, Object topic) {
    return 'Complete $count $topic drills';
  }

  @override
  String get available => 'Available';

  @override
  String get repairCost => 'Repair cost';

  @override
  String get fullyRestored => 'Fully Restored';

  @override
  String repairWithResource(Object resource) {
    return 'Repair with $resource';
  }

  @override
  String needMoreResource(Object resource) {
    return 'Need more $resource';
  }

  @override
  String restoredPercent(Object percent) {
    return '$percent% restored';
  }

  @override
  String areaRepaired(Object area) {
    return '$area repaired +25%';
  }

  @override
  String notEnoughResource(Object resource) {
    return 'Not enough $resource';
  }

  @override
  String areaFullyRestored(Object area) {
    return '$area is fully restored';
  }

  @override
  String get mathCrystals => 'Math Crystals';

  @override
  String get mutualAid => 'Mutual Aid';

  @override
  String get quizResult => 'Quiz Result';

  @override
  String topicRestored(Object topic) {
    return '$topic restored';
  }

  @override
  String quizCorrectSummary(Object correct, Object total) {
    return 'You answered $correct of $total correctly.';
  }

  @override
  String get score => 'Score';

  @override
  String get crystals => 'Crystals';

  @override
  String get repairReady => 'Repair Ready';

  @override
  String masteryResultMessage(
    Object encouragement,
    Object next,
    Object previous,
  ) {
    return '$encouragement Mastery: $previous -> $next. Spend crystals on Home to choose what to repair.';
  }

  @override
  String get backToForge => 'Back to Forge';

  @override
  String questionProgress(Object current, Object total) {
    return 'Question $current of $total';
  }

  @override
  String get finishQuiz => 'Finish Quiz';

  @override
  String get nextQuestion => 'Next Question';

  @override
  String parentDashboardSummary(Object name) {
    return 'A calm summary of $name\'s learning progress.';
  }

  @override
  String get overallRestoration => 'Overall restoration';

  @override
  String oasisRestoredSummary(Object percent) {
    return '$percent% of the oasis is restored.';
  }

  @override
  String get averageScore => 'Average Score';

  @override
  String get latestQuiz => 'Latest Quiz';

  @override
  String get recentActivity => 'Recent activity';

  @override
  String get predictionSummary => 'Prediction summary';

  @override
  String weakTopic(Object topic) {
    return 'Weak topic: $topic';
  }

  @override
  String suggestedAction(Object action) {
    return 'Suggested action: $action';
  }

  @override
  String get collaborationNote => 'Collaboration note';

  @override
  String get collaborationNoteBody =>
      'Mutual Aid features are prepared as a later phase. For FYP1, the dashboard can show the placeholder contribution score first.';

  @override
  String get greyBoxAiResult => 'Grey Box AI result';

  @override
  String aiResultSummary(
    Object confidence,
    Object label,
    Object mastery,
    Object weakness,
  ) {
    return 'Final mastery: $label - BKT mastery: $mastery% - Weakness risk: $weakness% - Confidence: $confidence%';
  }

  @override
  String shapReasons(Object reasons) {
    return 'SHAP reasons: $reasons';
  }

  @override
  String get prototypeOtpNotice =>
      'Prototype reset flow: use OTP 246810 for testing only. Replace this with email OTP delivery before real user testing.';

  @override
  String get loadingParentDashboard =>
      'Loading parent dashboard from Firebase...';

  @override
  String attemptSummary(
    Object correct,
    Object crystals,
    Object score,
    Object total,
  ) {
    return '$score% score - $correct/$total correct - +$crystals crystals';
  }

  @override
  String get justNow => 'Just now';

  @override
  String minutesAgo(Object minutes) {
    return '$minutes min ago';
  }

  @override
  String hoursAgo(Object hours) {
    return '$hours hr ago';
  }

  @override
  String daysAgo(Object days) {
    return '$days day ago';
  }
}
