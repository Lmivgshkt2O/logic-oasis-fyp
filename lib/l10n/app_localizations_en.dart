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
  String get forum => 'Q&A Forum';

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
  String get energy => 'Energy';

  @override
  String get dayStreak => 'Day Streak';

  @override
  String get tapMarkersToRestoreOasis => 'Tap markers to restore your oasis';

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
  String get guidedStepsTitle => 'Let\'s review the steps';

  @override
  String get hintTitle => 'Hint';

  @override
  String examplePrefix(Object example) {
    return 'Example: $example';
  }

  @override
  String get secureAnswerChecked => 'Your choice has been securely checked.';

  @override
  String get reviewTheseFirst => 'Review these first';

  @override
  String get perfectScore => 'Perfect score! Nothing to review.';

  @override
  String get nextPractice => 'Next practice';

  @override
  String nextPracticeLevel(Object difficulty) {
    return 'Next: $difficulty practice';
  }

  @override
  String get practiseAgain => 'Practise Again';

  @override
  String get moveOn => 'Move On';

  @override
  String get basedOnQuizProgress => 'Based on your quiz progress';

  @override
  String get preparingNextPractice => 'Preparing your next practice…';

  @override
  String get allTopicsComplete => 'You completed all available topics!';

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

  @override
  String get discussInForum => 'Discuss in forum';

  @override
  String get openingDiscussion => 'Opening discussion...';

  @override
  String get discussionUnavailable =>
      'This question is not available for discussion.';

  @override
  String parentDashboardCaption(String name) {
    return 'Safe learning updates for $name.';
  }

  @override
  String parentDashboardUpdated(String updated) {
    return 'Updated: $updated';
  }

  @override
  String get glanceFull => 'A steady week with a clear focus.';

  @override
  String glanceFullSupport(String focus) {
    return '$focus is the focus, with practice and Mutual Aid activity this week.';
  }

  @override
  String get glanceFocusPractice =>
      'A steady practice week with a clear focus.';

  @override
  String glanceFocusPracticeSupport(String focus) {
    return '$focus is the focus, with practice recorded this week.';
  }

  @override
  String get glanceFocusPracticeNoMutualAidYet =>
      'A steady practice week with a clear focus.';

  @override
  String glanceFocusPracticeNoMutualAidYetSupport(String focus) {
    return '$focus is the focus, with practice recorded and no Mutual Aid moments yet.';
  }

  @override
  String get glanceFocusNoPracticeYetMutualAid =>
      'Forum activity with a clear focus.';

  @override
  String glanceFocusNoPracticeYetMutualAidSupport(String focus) {
    return '$focus is the focus, with Mutual Aid moments and no practice recorded yet.';
  }

  @override
  String get glanceFocusNoPracticeYet => 'A clear focus is ready.';

  @override
  String glanceFocusNoPracticeYetSupport(String focus) {
    return '$focus is the focus. Practice evidence is still being collected.';
  }

  @override
  String get glanceFocusNoPracticeYetNoMutualAidYet =>
      'A clear focus is ready.';

  @override
  String glanceFocusNoPracticeYetNoMutualAidYetSupport(String focus) {
    return '$focus is the focus. Practice and Mutual Aid activity are still being collected.';
  }

  @override
  String get glanceFocusMutualAid => 'Forum activity with a clear focus.';

  @override
  String glanceFocusMutualAidSupport(String focus) {
    return '$focus is the focus, with Mutual Aid moments recorded this week.';
  }

  @override
  String get glanceFocusNoMutualAidYet => 'A clear focus is ready.';

  @override
  String glanceFocusNoMutualAidYetSupport(String focus) {
    return '$focus is the focus, with no Mutual Aid moments yet.';
  }

  @override
  String get glanceFocusOnly => 'A clear focus is ready.';

  @override
  String glanceFocusOnlySupport(String focus) {
    return '$focus is the current learning focus.';
  }

  @override
  String get glancePracticeRecorded => 'Practice is being recorded this week.';

  @override
  String get glancePracticeRecordedSupport =>
      'Practice continues while more Understanding evidence is collected.';

  @override
  String get glanceNoPracticeYet => 'No practice completed yet this week.';

  @override
  String get glanceNoPracticeYetSupport =>
      'A short practice can start the weekly routine.';

  @override
  String get glanceMutualAidRecorded =>
      'Mutual Aid activity is recorded this week.';

  @override
  String get glanceMutualAidRecordedSupport =>
      'More Understanding and Practice evidence is still being collected.';

  @override
  String get glanceNoMutualAidYet => 'No Mutual Aid moments yet this week.';

  @override
  String get glanceNoMutualAidYetSupport =>
      'More Understanding and Practice evidence is still being collected.';

  @override
  String get glanceNoDataYet => 'Learning evidence is still being collected.';

  @override
  String get glanceNoDataYetSupport =>
      'Safe updates will appear after the next completed practice.';

  @override
  String get understandingCardTitle => 'Understanding';

  @override
  String get learningSnapshotLabel => 'Learning snapshot';

  @override
  String get practiceCardTitle => 'Practice Effort';

  @override
  String get mutualAidCardTitle => 'Mutual Aid';

  @override
  String get conversationStarterTitle => 'A gentle question to ask';

  @override
  String get focusStatusNeedsGuidedPractice => 'Needs guided practice';

  @override
  String get focusStatusGrowing => 'Growing';

  @override
  String get focusStatusCurrentStrength => 'Current strength';

  @override
  String focusTopic(String topic) {
    return 'Topic: $topic';
  }

  @override
  String focusSubtopic(String subtopic) {
    return 'Focus: $subtopic';
  }

  @override
  String focusObservationSentence(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'Based on $count trusted learning observations.',
      one: 'Based on 1 trusted learning observation.',
    );
    return '$_temp0';
  }

  @override
  String focusStrength(String subtopic) {
    return 'Strength: $subtopic';
  }

  @override
  String get understandingInsufficient =>
      'More recent learning evidence is needed before a focus can be named.';

  @override
  String get understandingUnavailable =>
      'Understanding is temporarily unavailable.';

  @override
  String get parentNextStep => 'Parent next step';

  @override
  String actionUnderstandingFocus(String subtopic) {
    return 'Practise $subtopic together this week.';
  }

  @override
  String actionMaintainStrength(String subtopic) {
    return 'Keep $subtopic fresh with a short practice.';
  }

  @override
  String get actionPracticeRoutine =>
      'One short practice this week keeps the routine going.';

  @override
  String get actionMutualAidInvitation =>
      'Ask whether classmates answered a maths question this week.';

  @override
  String get actionNeedsMoreActivity =>
      'More activity is needed before a recommendation can be made.';

  @override
  String practiceWeekly(int total) {
    String _temp0 = intl.Intl.pluralLogic(
      total,
      locale: localeName,
      other: '$total practices completed this week',
      one: '1 practice completed this week',
      zero: 'No practice completed yet this week',
    );
    return '$_temp0';
  }

  @override
  String practiceActiveDays(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count active days',
      one: '1 active day',
    );
    return 'across $_temp0';
  }

  @override
  String get practiceUnavailable => 'Practice effort is unavailable this week.';

  @override
  String practiceComparison(int previous) {
    String _temp0 = intl.Intl.pluralLogic(
      previous,
      locale: localeName,
      other: '$previous practices',
      one: '1 practice',
    );
    return 'Compared with $_temp0 last week.';
  }

  @override
  String practiceImproved(int difference) {
    return 'Practice improved by $difference this week.';
  }

  @override
  String get dayMonday => 'Mon';

  @override
  String get dayTuesday => 'Tue';

  @override
  String get dayWednesday => 'Wed';

  @override
  String get dayThursday => 'Thu';

  @override
  String get dayFriday => 'Fri';

  @override
  String get daySaturday => 'Sat';

  @override
  String get daySunday => 'Sun';

  @override
  String mutualAidQuestions(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count questions asked',
      one: '1 question asked',
    );
    return '$_temp0';
  }

  @override
  String mutualAidReplies(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count replies',
      one: '1 reply',
    );
    return '$_temp0';
  }

  @override
  String mutualAidAccepted(int count) {
    return ' · $count accepted';
  }

  @override
  String mutualAidHelpfulMarks(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count helpful marks',
      one: '1 helpful mark',
    );
    return '$_temp0';
  }

  @override
  String get mutualAidZero => 'No Mutual Aid moments yet this week.';

  @override
  String get mutualAidUnavailable =>
      'Participation summary is unavailable this week.';

  @override
  String conversationUnderstandingFocus(String subtopic) {
    return 'What part of $subtopic should we look at together?';
  }

  @override
  String conversationMaintainStrength(String subtopic) {
    return 'Would you like to show me how you solve $subtopic?';
  }

  @override
  String get conversationPracticeRoutine =>
      'Shall we do one short practice together this week?';

  @override
  String get conversationMutualAidInvitation =>
      'Did anyone in class help with a maths question this week?';

  @override
  String get conversationNeedsMoreActivity =>
      'What did you enjoy practising this week?';
}
