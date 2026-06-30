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
