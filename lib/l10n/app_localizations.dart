import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_ms.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('ms'),
  ];

  /// No description provided for @appTitle.
  ///
  /// In en, this message translates to:
  /// **'Logic Oasis'**
  String get appTitle;

  /// No description provided for @home.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get home;

  /// No description provided for @forge.
  ///
  /// In en, this message translates to:
  /// **'Forge'**
  String get forge;

  /// No description provided for @forum.
  ///
  /// In en, this message translates to:
  /// **'Q&A Forum'**
  String get forum;

  /// No description provided for @settings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settings;

  /// No description provided for @studentProfile.
  ///
  /// In en, this message translates to:
  /// **'Student Profile'**
  String get studentProfile;

  /// No description provided for @manageProfilePreferences.
  ///
  /// In en, this message translates to:
  /// **'Manage your profile and preferences.'**
  String get manageProfilePreferences;

  /// No description provided for @viewEditProfile.
  ///
  /// In en, this message translates to:
  /// **'View and edit your profile'**
  String get viewEditProfile;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// No description provided for @missionReminders.
  ///
  /// In en, this message translates to:
  /// **'Mission Reminders'**
  String get missionReminders;

  /// No description provided for @on.
  ///
  /// In en, this message translates to:
  /// **'On'**
  String get on;

  /// No description provided for @off.
  ///
  /// In en, this message translates to:
  /// **'Off'**
  String get off;

  /// No description provided for @eyeComfort.
  ///
  /// In en, this message translates to:
  /// **'Eye Comfort'**
  String get eyeComfort;

  /// No description provided for @logout.
  ///
  /// In en, this message translates to:
  /// **'Log out'**
  String get logout;

  /// No description provided for @returnLogin.
  ///
  /// In en, this message translates to:
  /// **'Return to the login page'**
  String get returnLogin;

  /// No description provided for @confirmLogout.
  ///
  /// In en, this message translates to:
  /// **'Confirm to log out?'**
  String get confirmLogout;

  /// No description provided for @logoutConfirmBody.
  ///
  /// In en, this message translates to:
  /// **'You will return to the login page.'**
  String get logoutConfirmBody;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @studentProfileUpdated.
  ///
  /// In en, this message translates to:
  /// **'Student profile updated'**
  String get studentProfileUpdated;

  /// No description provided for @languageSet.
  ///
  /// In en, this message translates to:
  /// **'Language set to {language}'**
  String languageSet(Object language);

  /// No description provided for @enterStudentName.
  ///
  /// In en, this message translates to:
  /// **'Enter the student name.'**
  String get enterStudentName;

  /// No description provided for @updateStudentProfileFailed.
  ///
  /// In en, this message translates to:
  /// **'Unable to update student profile. Please try again.'**
  String get updateStudentProfileFailed;

  /// No description provided for @editStudentProfile.
  ///
  /// In en, this message translates to:
  /// **'Edit student profile'**
  String get editStudentProfile;

  /// No description provided for @studentName.
  ///
  /// In en, this message translates to:
  /// **'Student name'**
  String get studentName;

  /// No description provided for @year4.
  ///
  /// In en, this message translates to:
  /// **'Year 4'**
  String get year4;

  /// No description provided for @year5.
  ///
  /// In en, this message translates to:
  /// **'Year 5'**
  String get year5;

  /// No description provided for @year6.
  ///
  /// In en, this message translates to:
  /// **'Year 6'**
  String get year6;

  /// No description provided for @saving.
  ///
  /// In en, this message translates to:
  /// **'Saving...'**
  String get saving;

  /// No description provided for @saveProfile.
  ///
  /// In en, this message translates to:
  /// **'Save Profile'**
  String get saveProfile;

  /// No description provided for @parentDashboard.
  ///
  /// In en, this message translates to:
  /// **'Parent Dashboard'**
  String get parentDashboard;

  /// No description provided for @locked.
  ///
  /// In en, this message translates to:
  /// **'Locked'**
  String get locked;

  /// No description provided for @unlockAccess.
  ///
  /// In en, this message translates to:
  /// **'Unlock Access'**
  String get unlockAccess;

  /// No description provided for @unlockProgressWeakTopics.
  ///
  /// In en, this message translates to:
  /// **'Unlock to view progress and weak topics'**
  String get unlockProgressWeakTopics;

  /// No description provided for @parentAccessRequired.
  ///
  /// In en, this message translates to:
  /// **'Parent access required'**
  String get parentAccessRequired;

  /// No description provided for @enterLinkedParentPassword.
  ///
  /// In en, this message translates to:
  /// **'Enter the linked parent password.'**
  String get enterLinkedParentPassword;

  /// No description provided for @parentAccountUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Parent account is unavailable. Please try again.'**
  String get parentAccountUnavailable;

  /// No description provided for @parentAccountNotLinked.
  ///
  /// In en, this message translates to:
  /// **'Parent account not linked'**
  String get parentAccountNotLinked;

  /// No description provided for @parentAccountNotLinkedBody.
  ///
  /// In en, this message translates to:
  /// **'Create a parent demo account before opening the protected dashboard.'**
  String get parentAccountNotLinkedBody;

  /// No description provided for @createParentAccount.
  ///
  /// In en, this message translates to:
  /// **'Create account'**
  String get createParentAccount;

  /// No description provided for @parentAuthentication.
  ///
  /// In en, this message translates to:
  /// **'Parent Authentication'**
  String get parentAuthentication;

  /// No description provided for @parentAuthInstruction.
  ///
  /// In en, this message translates to:
  /// **'Enter the linked parent password to unlock learning insights.'**
  String get parentAuthInstruction;

  /// No description provided for @parentPassword.
  ///
  /// In en, this message translates to:
  /// **'Parent password'**
  String get parentPassword;

  /// No description provided for @showPassword.
  ///
  /// In en, this message translates to:
  /// **'Show password'**
  String get showPassword;

  /// No description provided for @hidePassword.
  ///
  /// In en, this message translates to:
  /// **'Hide password'**
  String get hidePassword;

  /// No description provided for @forgotPassword.
  ///
  /// In en, this message translates to:
  /// **'Forgot password?'**
  String get forgotPassword;

  /// No description provided for @checkingPassword.
  ///
  /// In en, this message translates to:
  /// **'Checking password...'**
  String get checkingPassword;

  /// No description provided for @unlockDashboard.
  ///
  /// In en, this message translates to:
  /// **'Unlock Dashboard'**
  String get unlockDashboard;

  /// No description provided for @linkedParentEmail.
  ///
  /// In en, this message translates to:
  /// **'Linked parent email'**
  String get linkedParentEmail;

  /// No description provided for @formulaForge.
  ///
  /// In en, this message translates to:
  /// **'Formula Forge'**
  String get formulaForge;

  /// No description provided for @forgeSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Choose a topic and practise calmly.'**
  String get forgeSubtitle;

  /// No description provided for @loadingFirebaseQuestionBank.
  ///
  /// In en, this message translates to:
  /// **'Loading Firebase question bank...'**
  String get loadingFirebaseQuestionBank;

  /// No description provided for @topicLockedQuestionBank.
  ///
  /// In en, this message translates to:
  /// **'Question bank not ready for this topic yet.'**
  String get topicLockedQuestionBank;

  /// No description provided for @missionRemindersOn.
  ///
  /// In en, this message translates to:
  /// **'Mission reminders turned on'**
  String get missionRemindersOn;

  /// No description provided for @missionRemindersOff.
  ///
  /// In en, this message translates to:
  /// **'Mission reminders turned off'**
  String get missionRemindersOff;

  /// No description provided for @missionRewardClaimed.
  ///
  /// In en, this message translates to:
  /// **'Mission reward claimed: +{crystals} crystals'**
  String missionRewardClaimed(Object crystals);

  /// No description provided for @missionRewardAlreadyClaimed.
  ///
  /// In en, this message translates to:
  /// **'Mission reward already claimed'**
  String get missionRewardAlreadyClaimed;

  /// No description provided for @recommendedMission.
  ///
  /// In en, this message translates to:
  /// **'Recommended mission'**
  String get recommendedMission;

  /// No description provided for @done.
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get done;

  /// No description provided for @rewardClaimedKeepPractising.
  ///
  /// In en, this message translates to:
  /// **'Reward claimed. Keep practising {topic}.'**
  String rewardClaimedKeepPractising(Object topic);

  /// No description provided for @missionCompleteClaimReward.
  ///
  /// In en, this message translates to:
  /// **'Mission complete. Tap to claim reward.'**
  String get missionCompleteClaimReward;

  /// No description provided for @completeTopicDrills.
  ///
  /// In en, this message translates to:
  /// **'Complete {count} {topic} drills'**
  String completeTopicDrills(Object count, Object topic);

  /// No description provided for @available.
  ///
  /// In en, this message translates to:
  /// **'Available'**
  String get available;

  /// No description provided for @repairCost.
  ///
  /// In en, this message translates to:
  /// **'Repair cost'**
  String get repairCost;

  /// No description provided for @fullyRestored.
  ///
  /// In en, this message translates to:
  /// **'Fully Restored'**
  String get fullyRestored;

  /// No description provided for @repairWithResource.
  ///
  /// In en, this message translates to:
  /// **'Repair with {resource}'**
  String repairWithResource(Object resource);

  /// No description provided for @needMoreResource.
  ///
  /// In en, this message translates to:
  /// **'Need more {resource}'**
  String needMoreResource(Object resource);

  /// No description provided for @restoredPercent.
  ///
  /// In en, this message translates to:
  /// **'{percent}% restored'**
  String restoredPercent(Object percent);

  /// No description provided for @areaRepaired.
  ///
  /// In en, this message translates to:
  /// **'{area} repaired +25%'**
  String areaRepaired(Object area);

  /// No description provided for @notEnoughResource.
  ///
  /// In en, this message translates to:
  /// **'Not enough {resource}'**
  String notEnoughResource(Object resource);

  /// No description provided for @areaFullyRestored.
  ///
  /// In en, this message translates to:
  /// **'{area} is fully restored'**
  String areaFullyRestored(Object area);

  /// No description provided for @mathCrystals.
  ///
  /// In en, this message translates to:
  /// **'Math Crystals'**
  String get mathCrystals;

  /// No description provided for @mutualAid.
  ///
  /// In en, this message translates to:
  /// **'Mutual Aid'**
  String get mutualAid;

  /// No description provided for @quizResult.
  ///
  /// In en, this message translates to:
  /// **'Quiz Result'**
  String get quizResult;

  /// No description provided for @topicRestored.
  ///
  /// In en, this message translates to:
  /// **'{topic} restored'**
  String topicRestored(Object topic);

  /// No description provided for @quizCorrectSummary.
  ///
  /// In en, this message translates to:
  /// **'You answered {correct} of {total} correctly.'**
  String quizCorrectSummary(Object correct, Object total);

  /// No description provided for @score.
  ///
  /// In en, this message translates to:
  /// **'Score'**
  String get score;

  /// No description provided for @crystals.
  ///
  /// In en, this message translates to:
  /// **'Crystals'**
  String get crystals;

  /// No description provided for @repairReady.
  ///
  /// In en, this message translates to:
  /// **'Repair Ready'**
  String get repairReady;

  /// No description provided for @masteryResultMessage.
  ///
  /// In en, this message translates to:
  /// **'{encouragement} Mastery: {previous} -> {next}. Spend crystals on Home to choose what to repair.'**
  String masteryResultMessage(
    Object encouragement,
    Object next,
    Object previous,
  );

  /// No description provided for @backToForge.
  ///
  /// In en, this message translates to:
  /// **'Back to Forge'**
  String get backToForge;

  /// No description provided for @questionProgress.
  ///
  /// In en, this message translates to:
  /// **'Question {current} of {total}'**
  String questionProgress(Object current, Object total);

  /// No description provided for @finishQuiz.
  ///
  /// In en, this message translates to:
  /// **'Finish Quiz'**
  String get finishQuiz;

  /// No description provided for @nextQuestion.
  ///
  /// In en, this message translates to:
  /// **'Next Question'**
  String get nextQuestion;

  /// No description provided for @guidedStepsTitle.
  ///
  /// In en, this message translates to:
  /// **'Let\'s review the steps'**
  String get guidedStepsTitle;

  /// No description provided for @hintTitle.
  ///
  /// In en, this message translates to:
  /// **'Hint'**
  String get hintTitle;

  /// No description provided for @examplePrefix.
  ///
  /// In en, this message translates to:
  /// **'Example: {example}'**
  String examplePrefix(Object example);

  /// No description provided for @secureAnswerChecked.
  ///
  /// In en, this message translates to:
  /// **'Your choice has been securely checked.'**
  String get secureAnswerChecked;

  /// No description provided for @reviewTheseFirst.
  ///
  /// In en, this message translates to:
  /// **'Review these first'**
  String get reviewTheseFirst;

  /// No description provided for @perfectScore.
  ///
  /// In en, this message translates to:
  /// **'Perfect score! Nothing to review.'**
  String get perfectScore;

  /// No description provided for @nextPractice.
  ///
  /// In en, this message translates to:
  /// **'Next practice'**
  String get nextPractice;

  /// No description provided for @nextPracticeLevel.
  ///
  /// In en, this message translates to:
  /// **'Next: {difficulty} practice'**
  String nextPracticeLevel(Object difficulty);

  /// No description provided for @practiseAgain.
  ///
  /// In en, this message translates to:
  /// **'Practise Again'**
  String get practiseAgain;

  /// No description provided for @moveOn.
  ///
  /// In en, this message translates to:
  /// **'Move On'**
  String get moveOn;

  /// No description provided for @basedOnQuizProgress.
  ///
  /// In en, this message translates to:
  /// **'Based on your quiz progress'**
  String get basedOnQuizProgress;

  /// No description provided for @preparingNextPractice.
  ///
  /// In en, this message translates to:
  /// **'Preparing your next practice…'**
  String get preparingNextPractice;

  /// No description provided for @allTopicsComplete.
  ///
  /// In en, this message translates to:
  /// **'You completed all available topics!'**
  String get allTopicsComplete;

  /// No description provided for @parentDashboardSummary.
  ///
  /// In en, this message translates to:
  /// **'A calm summary of {name}\'s learning progress.'**
  String parentDashboardSummary(Object name);

  /// No description provided for @overallRestoration.
  ///
  /// In en, this message translates to:
  /// **'Overall restoration'**
  String get overallRestoration;

  /// No description provided for @oasisRestoredSummary.
  ///
  /// In en, this message translates to:
  /// **'{percent}% of the oasis is restored.'**
  String oasisRestoredSummary(Object percent);

  /// No description provided for @averageScore.
  ///
  /// In en, this message translates to:
  /// **'Average Score'**
  String get averageScore;

  /// No description provided for @latestQuiz.
  ///
  /// In en, this message translates to:
  /// **'Latest Quiz'**
  String get latestQuiz;

  /// No description provided for @recentActivity.
  ///
  /// In en, this message translates to:
  /// **'Recent activity'**
  String get recentActivity;

  /// No description provided for @predictionSummary.
  ///
  /// In en, this message translates to:
  /// **'Prediction summary'**
  String get predictionSummary;

  /// No description provided for @weakTopic.
  ///
  /// In en, this message translates to:
  /// **'Weak topic: {topic}'**
  String weakTopic(Object topic);

  /// No description provided for @suggestedAction.
  ///
  /// In en, this message translates to:
  /// **'Suggested action: {action}'**
  String suggestedAction(Object action);

  /// No description provided for @collaborationNote.
  ///
  /// In en, this message translates to:
  /// **'Collaboration note'**
  String get collaborationNote;

  /// No description provided for @collaborationNoteBody.
  ///
  /// In en, this message translates to:
  /// **'Mutual Aid features are prepared as a later phase. For FYP1, the dashboard can show the placeholder contribution score first.'**
  String get collaborationNoteBody;

  /// No description provided for @greyBoxAiResult.
  ///
  /// In en, this message translates to:
  /// **'Grey Box AI result'**
  String get greyBoxAiResult;

  /// No description provided for @aiResultSummary.
  ///
  /// In en, this message translates to:
  /// **'Final mastery: {label} - BKT mastery: {mastery}% - Weakness risk: {weakness}% - Confidence: {confidence}%'**
  String aiResultSummary(
    Object confidence,
    Object label,
    Object mastery,
    Object weakness,
  );

  /// No description provided for @shapReasons.
  ///
  /// In en, this message translates to:
  /// **'SHAP reasons: {reasons}'**
  String shapReasons(Object reasons);

  /// No description provided for @prototypeOtpNotice.
  ///
  /// In en, this message translates to:
  /// **'Prototype reset flow: use OTP 246810 for testing only. Replace this with email OTP delivery before real user testing.'**
  String get prototypeOtpNotice;

  /// No description provided for @loadingParentDashboard.
  ///
  /// In en, this message translates to:
  /// **'Loading parent dashboard from Firebase...'**
  String get loadingParentDashboard;

  /// No description provided for @attemptSummary.
  ///
  /// In en, this message translates to:
  /// **'{score}% score - {correct}/{total} correct - +{crystals} crystals'**
  String attemptSummary(
    Object correct,
    Object crystals,
    Object score,
    Object total,
  );

  /// No description provided for @justNow.
  ///
  /// In en, this message translates to:
  /// **'Just now'**
  String get justNow;

  /// No description provided for @minutesAgo.
  ///
  /// In en, this message translates to:
  /// **'{minutes} min ago'**
  String minutesAgo(Object minutes);

  /// No description provided for @hoursAgo.
  ///
  /// In en, this message translates to:
  /// **'{hours} hr ago'**
  String hoursAgo(Object hours);

  /// No description provided for @daysAgo.
  ///
  /// In en, this message translates to:
  /// **'{days} day ago'**
  String daysAgo(Object days);

  /// No description provided for @discussInForum.
  ///
  /// In en, this message translates to:
  /// **'Discuss in forum'**
  String get discussInForum;

  /// No description provided for @openingDiscussion.
  ///
  /// In en, this message translates to:
  /// **'Opening discussion...'**
  String get openingDiscussion;

  /// No description provided for @discussionUnavailable.
  ///
  /// In en, this message translates to:
  /// **'This question is not available for discussion.'**
  String get discussionUnavailable;

  /// No description provided for @parentDashboardCaption.
  ///
  /// In en, this message translates to:
  /// **'Safe learning updates for {name}.'**
  String parentDashboardCaption(String name);

  /// No description provided for @parentDashboardUpdated.
  ///
  /// In en, this message translates to:
  /// **'Updated: {updated}'**
  String parentDashboardUpdated(String updated);

  /// No description provided for @glanceFull.
  ///
  /// In en, this message translates to:
  /// **'A steady week with a clear focus.'**
  String get glanceFull;

  /// No description provided for @glanceFullSupport.
  ///
  /// In en, this message translates to:
  /// **'{focus} is the focus, with practice and Mutual Aid activity this week.'**
  String glanceFullSupport(String focus);

  /// No description provided for @glanceFocusPractice.
  ///
  /// In en, this message translates to:
  /// **'A steady practice week with a clear focus.'**
  String get glanceFocusPractice;

  /// No description provided for @glanceFocusPracticeSupport.
  ///
  /// In en, this message translates to:
  /// **'{focus} is the focus, with practice recorded this week.'**
  String glanceFocusPracticeSupport(String focus);

  /// No description provided for @glanceFocusPracticeNoMutualAidYet.
  ///
  /// In en, this message translates to:
  /// **'A steady practice week with a clear focus.'**
  String get glanceFocusPracticeNoMutualAidYet;

  /// No description provided for @glanceFocusPracticeNoMutualAidYetSupport.
  ///
  /// In en, this message translates to:
  /// **'{focus} is the focus, with practice recorded and no Mutual Aid moments yet.'**
  String glanceFocusPracticeNoMutualAidYetSupport(String focus);

  /// No description provided for @glanceFocusNoPracticeYetMutualAid.
  ///
  /// In en, this message translates to:
  /// **'Forum activity with a clear focus.'**
  String get glanceFocusNoPracticeYetMutualAid;

  /// No description provided for @glanceFocusNoPracticeYetMutualAidSupport.
  ///
  /// In en, this message translates to:
  /// **'{focus} is the focus, with Mutual Aid moments and no practice recorded yet.'**
  String glanceFocusNoPracticeYetMutualAidSupport(String focus);

  /// No description provided for @glanceFocusNoPracticeYet.
  ///
  /// In en, this message translates to:
  /// **'A clear focus is ready.'**
  String get glanceFocusNoPracticeYet;

  /// No description provided for @glanceFocusNoPracticeYetSupport.
  ///
  /// In en, this message translates to:
  /// **'{focus} is the focus. Practice evidence is still being collected.'**
  String glanceFocusNoPracticeYetSupport(String focus);

  /// No description provided for @glanceFocusNoPracticeYetNoMutualAidYet.
  ///
  /// In en, this message translates to:
  /// **'A clear focus is ready.'**
  String get glanceFocusNoPracticeYetNoMutualAidYet;

  /// No description provided for @glanceFocusNoPracticeYetNoMutualAidYetSupport.
  ///
  /// In en, this message translates to:
  /// **'{focus} is the focus. Practice and Mutual Aid activity are still being collected.'**
  String glanceFocusNoPracticeYetNoMutualAidYetSupport(String focus);

  /// No description provided for @glanceFocusMutualAid.
  ///
  /// In en, this message translates to:
  /// **'Forum activity with a clear focus.'**
  String get glanceFocusMutualAid;

  /// No description provided for @glanceFocusMutualAidSupport.
  ///
  /// In en, this message translates to:
  /// **'{focus} is the focus, with Mutual Aid moments recorded this week.'**
  String glanceFocusMutualAidSupport(String focus);

  /// No description provided for @glanceFocusNoMutualAidYet.
  ///
  /// In en, this message translates to:
  /// **'A clear focus is ready.'**
  String get glanceFocusNoMutualAidYet;

  /// No description provided for @glanceFocusNoMutualAidYetSupport.
  ///
  /// In en, this message translates to:
  /// **'{focus} is the focus, with no Mutual Aid moments yet.'**
  String glanceFocusNoMutualAidYetSupport(String focus);

  /// No description provided for @glanceFocusOnly.
  ///
  /// In en, this message translates to:
  /// **'A clear focus is ready.'**
  String get glanceFocusOnly;

  /// No description provided for @glanceFocusOnlySupport.
  ///
  /// In en, this message translates to:
  /// **'{focus} is the current learning focus.'**
  String glanceFocusOnlySupport(String focus);

  /// No description provided for @glancePracticeRecorded.
  ///
  /// In en, this message translates to:
  /// **'Practice is being recorded this week.'**
  String get glancePracticeRecorded;

  /// No description provided for @glancePracticeRecordedSupport.
  ///
  /// In en, this message translates to:
  /// **'Practice continues while more Understanding evidence is collected.'**
  String get glancePracticeRecordedSupport;

  /// No description provided for @glanceNoPracticeYet.
  ///
  /// In en, this message translates to:
  /// **'No practice completed yet this week.'**
  String get glanceNoPracticeYet;

  /// No description provided for @glanceNoPracticeYetSupport.
  ///
  /// In en, this message translates to:
  /// **'A short practice can start the weekly routine.'**
  String get glanceNoPracticeYetSupport;

  /// No description provided for @glanceMutualAidRecorded.
  ///
  /// In en, this message translates to:
  /// **'Mutual Aid activity is recorded this week.'**
  String get glanceMutualAidRecorded;

  /// No description provided for @glanceMutualAidRecordedSupport.
  ///
  /// In en, this message translates to:
  /// **'More Understanding and Practice evidence is still being collected.'**
  String get glanceMutualAidRecordedSupport;

  /// No description provided for @glanceNoMutualAidYet.
  ///
  /// In en, this message translates to:
  /// **'No Mutual Aid moments yet this week.'**
  String get glanceNoMutualAidYet;

  /// No description provided for @glanceNoMutualAidYetSupport.
  ///
  /// In en, this message translates to:
  /// **'More Understanding and Practice evidence is still being collected.'**
  String get glanceNoMutualAidYetSupport;

  /// No description provided for @glanceNoDataYet.
  ///
  /// In en, this message translates to:
  /// **'Learning evidence is still being collected.'**
  String get glanceNoDataYet;

  /// No description provided for @glanceNoDataYetSupport.
  ///
  /// In en, this message translates to:
  /// **'Safe updates will appear after the next completed practice.'**
  String get glanceNoDataYetSupport;

  /// No description provided for @understandingCardTitle.
  ///
  /// In en, this message translates to:
  /// **'Understanding'**
  String get understandingCardTitle;

  /// No description provided for @learningSnapshotLabel.
  ///
  /// In en, this message translates to:
  /// **'Learning snapshot'**
  String get learningSnapshotLabel;

  /// No description provided for @practiceCardTitle.
  ///
  /// In en, this message translates to:
  /// **'Practice Effort'**
  String get practiceCardTitle;

  /// No description provided for @mutualAidCardTitle.
  ///
  /// In en, this message translates to:
  /// **'Mutual Aid'**
  String get mutualAidCardTitle;

  /// No description provided for @conversationStarterTitle.
  ///
  /// In en, this message translates to:
  /// **'A gentle question to ask'**
  String get conversationStarterTitle;

  /// No description provided for @focusStatusNeedsGuidedPractice.
  ///
  /// In en, this message translates to:
  /// **'Needs guided practice'**
  String get focusStatusNeedsGuidedPractice;

  /// No description provided for @focusStatusGrowing.
  ///
  /// In en, this message translates to:
  /// **'Growing'**
  String get focusStatusGrowing;

  /// No description provided for @focusStatusCurrentStrength.
  ///
  /// In en, this message translates to:
  /// **'Current strength'**
  String get focusStatusCurrentStrength;

  /// No description provided for @focusTopic.
  ///
  /// In en, this message translates to:
  /// **'Topic: {topic}'**
  String focusTopic(String topic);

  /// No description provided for @focusSubtopic.
  ///
  /// In en, this message translates to:
  /// **'Focus: {subtopic}'**
  String focusSubtopic(String subtopic);

  /// No description provided for @focusObservationSentence.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{Based on 1 trusted learning observation.} other{Based on {count} trusted learning observations.}}'**
  String focusObservationSentence(int count);

  /// No description provided for @focusStrength.
  ///
  /// In en, this message translates to:
  /// **'Strength: {subtopic}'**
  String focusStrength(String subtopic);

  /// No description provided for @understandingInsufficient.
  ///
  /// In en, this message translates to:
  /// **'More recent learning evidence is needed before a focus can be named.'**
  String get understandingInsufficient;

  /// No description provided for @understandingUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Understanding is temporarily unavailable.'**
  String get understandingUnavailable;

  /// No description provided for @parentNextStep.
  ///
  /// In en, this message translates to:
  /// **'Parent next step'**
  String get parentNextStep;

  /// No description provided for @actionUnderstandingFocus.
  ///
  /// In en, this message translates to:
  /// **'Practise {subtopic} together this week.'**
  String actionUnderstandingFocus(String subtopic);

  /// No description provided for @actionMaintainStrength.
  ///
  /// In en, this message translates to:
  /// **'Keep {subtopic} fresh with a short practice.'**
  String actionMaintainStrength(String subtopic);

  /// No description provided for @actionPracticeRoutine.
  ///
  /// In en, this message translates to:
  /// **'One short practice this week keeps the routine going.'**
  String get actionPracticeRoutine;

  /// No description provided for @actionMutualAidInvitation.
  ///
  /// In en, this message translates to:
  /// **'Ask whether classmates answered a maths question this week.'**
  String get actionMutualAidInvitation;

  /// No description provided for @actionNeedsMoreActivity.
  ///
  /// In en, this message translates to:
  /// **'More activity is needed before a recommendation can be made.'**
  String get actionNeedsMoreActivity;

  /// No description provided for @practiceWeekly.
  ///
  /// In en, this message translates to:
  /// **'{total, plural, =0{No practice completed yet this week} =1{1 practice completed this week} other{{total} practices completed this week}}'**
  String practiceWeekly(int total);

  /// No description provided for @practiceActiveDays.
  ///
  /// In en, this message translates to:
  /// **'across {count, plural, =1{1 active day} other{{count} active days}}'**
  String practiceActiveDays(int count);

  /// No description provided for @practiceUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Practice effort is unavailable this week.'**
  String get practiceUnavailable;

  /// No description provided for @practiceComparison.
  ///
  /// In en, this message translates to:
  /// **'Compared with {previous, plural, =1{1 practice} other{{previous} practices}} last week.'**
  String practiceComparison(int previous);

  /// No description provided for @practiceImproved.
  ///
  /// In en, this message translates to:
  /// **'Practice improved by {difference} this week.'**
  String practiceImproved(int difference);

  /// No description provided for @dayMonday.
  ///
  /// In en, this message translates to:
  /// **'Mon'**
  String get dayMonday;

  /// No description provided for @dayTuesday.
  ///
  /// In en, this message translates to:
  /// **'Tue'**
  String get dayTuesday;

  /// No description provided for @dayWednesday.
  ///
  /// In en, this message translates to:
  /// **'Wed'**
  String get dayWednesday;

  /// No description provided for @dayThursday.
  ///
  /// In en, this message translates to:
  /// **'Thu'**
  String get dayThursday;

  /// No description provided for @dayFriday.
  ///
  /// In en, this message translates to:
  /// **'Fri'**
  String get dayFriday;

  /// No description provided for @daySaturday.
  ///
  /// In en, this message translates to:
  /// **'Sat'**
  String get daySaturday;

  /// No description provided for @daySunday.
  ///
  /// In en, this message translates to:
  /// **'Sun'**
  String get daySunday;

  /// No description provided for @mutualAidQuestions.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 question asked} other{{count} questions asked}}'**
  String mutualAidQuestions(int count);

  /// No description provided for @mutualAidReplies.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 reply} other{{count} replies}}'**
  String mutualAidReplies(int count);

  /// No description provided for @mutualAidAccepted.
  ///
  /// In en, this message translates to:
  /// **' · {count} accepted'**
  String mutualAidAccepted(int count);

  /// No description provided for @mutualAidHelpfulMarks.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 helpful mark} other{{count} helpful marks}}'**
  String mutualAidHelpfulMarks(int count);

  /// No description provided for @mutualAidZero.
  ///
  /// In en, this message translates to:
  /// **'No Mutual Aid moments yet this week.'**
  String get mutualAidZero;

  /// No description provided for @mutualAidUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Participation summary is unavailable this week.'**
  String get mutualAidUnavailable;

  /// No description provided for @conversationUnderstandingFocus.
  ///
  /// In en, this message translates to:
  /// **'What part of {subtopic} should we look at together?'**
  String conversationUnderstandingFocus(String subtopic);

  /// No description provided for @conversationMaintainStrength.
  ///
  /// In en, this message translates to:
  /// **'Would you like to show me how you solve {subtopic}?'**
  String conversationMaintainStrength(String subtopic);

  /// No description provided for @conversationPracticeRoutine.
  ///
  /// In en, this message translates to:
  /// **'Shall we do one short practice together this week?'**
  String get conversationPracticeRoutine;

  /// No description provided for @conversationMutualAidInvitation.
  ///
  /// In en, this message translates to:
  /// **'Did anyone in class help with a maths question this week?'**
  String get conversationMutualAidInvitation;

  /// No description provided for @conversationNeedsMoreActivity.
  ///
  /// In en, this message translates to:
  /// **'What did you enjoy practising this week?'**
  String get conversationNeedsMoreActivity;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'ms'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'ms':
      return AppLocalizationsMs();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
