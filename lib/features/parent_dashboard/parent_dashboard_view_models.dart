import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_time.dart';
import 'package:logic_oasis/shared/models/forum_participation_summary.dart';
import 'package:logic_oasis/shared/models/parent_practice_summary.dart';
import 'package:logic_oasis/shared/models/subtopic.dart';
import 'package:logic_oasis/shared/models/topic.dart';
import 'package:logic_oasis/shared/models/trusted_subtopic_progress.dart';

const int parentUnderstandingFreshnessDays = 14;
const double parentNeedsGuidedPracticeThreshold = 0.40;
const double parentGrowingThreshold = 0.70;

enum ParentUnderstandingStatus { ready, insufficientEvidence }

enum ParentPracticeStatus { ready, unavailable }

enum ParentMutualAidStatus { ready, unavailable }

enum ParentMasteryBand { needsGuidedPractice, growing, currentStrength }

enum ParentActionKind {
  understandingFocus,
  maintainStrength,
  practiceRoutine,
  mutualAidInvitation,
  needsMoreActivity,
}

/// The approved qualitative band shared by the Understanding card, action,
/// and semantics. The 0.40/0.70 boundaries follow the existing BKT display
/// convention.
ParentMasteryBand parentMasteryBand(double masteryProbability) {
  if (masteryProbability < parentNeedsGuidedPracticeThreshold) {
    return ParentMasteryBand.needsGuidedPractice;
  }
  if (masteryProbability < parentGrowingThreshold) {
    return ParentMasteryBand.growing;
  }
  return ParentMasteryBand.currentStrength;
}

class ParentUnderstandingCard {
  const ParentUnderstandingCard.insufficientEvidence()
    : status = ParentUnderstandingStatus.insufficientEvidence,
      topicId = null,
      topicTitle = '',
      topicTitleBm = '',
      focusSubtopicId = null,
      focusSubtopicTitle = '',
      focusSubtopicTitleBm = '',
      focusMasteryProbability = null,
      focusObservationCount = null,
      focusUpdatedAt = null,
      masteryBand = null,
      positiveSubtopicId = null,
      positiveSubtopicTitle = '',
      positiveSubtopicTitleBm = '',
      positiveMasteryProbability = null,
      positiveUpdatedAt = null;

  const ParentUnderstandingCard.ready({
    required this.topicId,
    required this.topicTitle,
    required this.topicTitleBm,
    required this.focusSubtopicId,
    required this.focusSubtopicTitle,
    required this.focusSubtopicTitleBm,
    required this.focusMasteryProbability,
    required this.focusObservationCount,
    required this.focusUpdatedAt,
    required this.masteryBand,
    this.positiveSubtopicId,
    this.positiveSubtopicTitle = '',
    this.positiveSubtopicTitleBm = '',
    this.positiveMasteryProbability,
    this.positiveUpdatedAt,
  }) : status = ParentUnderstandingStatus.ready;

  final ParentUnderstandingStatus status;
  final String? topicId;
  final String topicTitle;
  final String topicTitleBm;
  final String? focusSubtopicId;
  final String focusSubtopicTitle;
  final String focusSubtopicTitleBm;
  final double? focusMasteryProbability;
  final int? focusObservationCount;
  final DateTime? focusUpdatedAt;
  final ParentMasteryBand? masteryBand;
  final String? positiveSubtopicId;
  final String positiveSubtopicTitle;
  final String positiveSubtopicTitleBm;
  final double? positiveMasteryProbability;
  final DateTime? positiveUpdatedAt;
}

class ParentPracticeCard {
  const ParentPracticeCard.unavailable()
    : status = ParentPracticeStatus.unavailable,
      weeklyTotal = 0,
      activeDayCount = 0,
      dailyCounts = const <int>[],
      previousWeekCompletedPracticeCount = null,
      improvedOverPreviousWeek = false,
      supportedDifference = null,
      latestPracticeAt = null,
      updatedAt = null;

  const ParentPracticeCard.ready({
    required this.weeklyTotal,
    required this.activeDayCount,
    required this.dailyCounts,
    this.previousWeekCompletedPracticeCount,
    required this.improvedOverPreviousWeek,
    this.supportedDifference,
    this.latestPracticeAt,
    required this.updatedAt,
  }) : status = ParentPracticeStatus.ready;

  final ParentPracticeStatus status;
  final int weeklyTotal;
  final int activeDayCount;
  final List<int> dailyCounts;
  final int? previousWeekCompletedPracticeCount;
  final bool improvedOverPreviousWeek;
  final int? supportedDifference;
  final DateTime? latestPracticeAt;
  final DateTime? updatedAt;
}

class ParentMutualAidCard {
  const ParentMutualAidCard.unavailable()
    : status = ParentMutualAidStatus.unavailable,
      questionsPostedCount = 0,
      answersSubmittedCount = 0,
      acceptedAnswersCount = 0,
      helpfulReceivedCount = 0,
      totalActivity = 0,
      hasActivity = false;

  const ParentMutualAidCard.ready({
    required this.questionsPostedCount,
    required this.answersSubmittedCount,
    required this.acceptedAnswersCount,
    required this.helpfulReceivedCount,
  }) : status = ParentMutualAidStatus.ready,
       totalActivity =
           questionsPostedCount +
           answersSubmittedCount +
           acceptedAnswersCount +
           helpfulReceivedCount,
       hasActivity =
           questionsPostedCount +
               answersSubmittedCount +
               acceptedAnswersCount +
               helpfulReceivedCount >
           0;

  final ParentMutualAidStatus status;
  final int questionsPostedCount;
  final int answersSubmittedCount;
  final int acceptedAnswersCount;
  final int helpfulReceivedCount;
  final int totalActivity;
  final bool hasActivity;
}

class ParentAction {
  const ParentAction({
    required this.kind,
    this.masteryBand,
    this.focusSubtopicId,
    this.focusMasteryProbability,
  });

  final ParentActionKind kind;
  final ParentMasteryBand? masteryBand;
  final String? focusSubtopicId;
  final double? focusMasteryProbability;
}

class ParentConversationStarter {
  const ParentConversationStarter({
    required this.actionKind,
    required this.templateKey,
  });

  final ParentActionKind actionKind;
  final String templateKey;
}

String parentConversationStarterTemplateKey(ParentActionKind kind) {
  return switch (kind) {
    ParentActionKind.understandingFocus =>
      'conversation_starter_understanding_focus',
    ParentActionKind.maintainStrength =>
      'conversation_starter_maintain_strength',
    ParentActionKind.practiceRoutine => 'conversation_starter_practice_routine',
    ParentActionKind.mutualAidInvitation =>
      'conversation_starter_mutual_aid_invitation',
    ParentActionKind.needsMoreActivity =>
      'conversation_starter_needs_more_activity',
  };
}

class ParentWeeklyGlance {
  const ParentWeeklyGlance({
    required this.hasFocus,
    required this.hasPracticeActivity,
    required this.practiceUnavailable,
    required this.hasMutualAidActivity,
    required this.mutualAidUnavailable,
    required this.improvedOverPreviousWeek,
    this.supportedDifference,
    required this.key,
  });

  final bool hasFocus;
  final bool hasPracticeActivity;
  final bool practiceUnavailable;
  final bool hasMutualAidActivity;
  final bool mutualAidUnavailable;
  final bool improvedOverPreviousWeek;
  final int? supportedDifference;
  final String key;
}

/// Deterministic, conservative glance key derived only from facts supported
/// by available cards. Copy resolution happens in the UI layer.
String parentGlanceKey({
  required bool hasFocus,
  required bool practiceAvailable,
  required bool hasPracticeActivity,
  required bool mutualAidAvailable,
  required bool hasMutualAidActivity,
}) {
  if (hasFocus) {
    final practicePart = practiceAvailable
        ? (hasPracticeActivity ? 'practice' : 'no_practice_yet')
        : null;
    final mutualAidPart = mutualAidAvailable
        ? (hasMutualAidActivity ? 'mutual_aid' : 'no_mutual_aid_yet')
        : null;
    if (practicePart != null && mutualAidPart != null) {
      return 'glance_focus_${practicePart}_$mutualAidPart';
    }
    if (practicePart != null) return 'glance_focus_$practicePart';
    if (mutualAidPart != null) return 'glance_focus_$mutualAidPart';
    return 'glance_focus_only';
  }
  if (practiceAvailable) {
    return hasPracticeActivity
        ? 'glance_practice_recorded'
        : 'glance_no_practice_yet';
  }
  if (mutualAidAvailable) {
    return hasMutualAidActivity
        ? 'glance_mutual_aid_recorded'
        : 'glance_no_mutual_aid_yet';
  }
  return 'glance_no_data_yet';
}

class ParentProgressMapViewModel {
  const ParentProgressMapViewModel({
    required this.understanding,
    required this.practice,
    required this.mutualAid,
    required this.glance,
    this.action,
    this.conversationStarter,
  });

  final ParentUnderstandingCard understanding;
  final ParentPracticeCard practice;
  final ParentMutualAidCard mutualAid;
  final ParentAction? action;
  final ParentConversationStarter? conversationStarter;
  final ParentWeeklyGlance glance;
}

/// Derives every parent-facing card, action, conversation starter, and glance
/// from typed safe inputs. This is the trust boundary between safe records
/// and parent advice; it contains no Firestore or widget dependencies.
ParentProgressMapViewModel deriveParentProgressMap({
  required DateTime now,
  required String studentId,
  required int yearLevel,
  required List<TrustedSubtopicProgress> mastery,
  required ParentPracticeSummary? practice,
  required ForumParticipationSummary? mutualAid,
  required List<Topic> curriculum,
}) {
  final understanding = _deriveUnderstanding(
    mastery: mastery,
    curriculum: curriculum,
    studentId: studentId,
    yearLevel: yearLevel,
    now: now,
  );
  final practiceCard = _derivePractice(practice, now);
  final mutualAidCard = _deriveMutualAid(mutualAid, studentId, now);
  final action = _deriveAction(understanding, practiceCard, mutualAidCard);
  final conversationStarter = action == null
      ? null
      : ParentConversationStarter(
          actionKind: action.kind,
          templateKey: parentConversationStarterTemplateKey(action.kind),
        );
  return ParentProgressMapViewModel(
    understanding: understanding,
    practice: practiceCard,
    mutualAid: mutualAidCard,
    action: action,
    conversationStarter: conversationStarter,
    glance: _deriveGlance(understanding, practiceCard, mutualAidCard),
  );
}

class _EligibleCandidate {
  const _EligibleCandidate({
    required this.record,
    required this.topicTitle,
    required this.topicTitleBm,
    required this.subtopicTitle,
    required this.subtopicTitleBm,
  });

  final TrustedSubtopicProgress record;
  final String topicTitle;
  final String topicTitleBm;
  final String subtopicTitle;
  final String subtopicTitleBm;
}

ParentUnderstandingCard _deriveUnderstanding({
  required List<TrustedSubtopicProgress> mastery,
  required List<Topic> curriculum,
  required String studentId,
  required int yearLevel,
  required DateTime now,
}) {
  final candidates = _eligibleCandidates(
    mastery: mastery,
    curriculum: curriculum,
    studentId: studentId,
    yearLevel: yearLevel,
    now: now,
  );
  if (candidates.isEmpty) {
    return const ParentUnderstandingCard.insufficientEvidence();
  }
  final focus = _selectFocus(candidates);
  final comparator = _selectComparator(candidates, focus);
  return ParentUnderstandingCard.ready(
    topicId: focus.record.topicId,
    topicTitle: focus.topicTitle,
    topicTitleBm: focus.topicTitleBm,
    focusSubtopicId: focus.record.subtopicId,
    focusSubtopicTitle: focus.subtopicTitle,
    focusSubtopicTitleBm: focus.subtopicTitleBm,
    focusMasteryProbability: focus.record.masteryProbability,
    focusObservationCount: focus.record.observationCount,
    focusUpdatedAt: focus.record.updatedAt,
    masteryBand: parentMasteryBand(focus.record.masteryProbability!),
    positiveSubtopicId: comparator?.record.subtopicId,
    positiveSubtopicTitle: comparator?.subtopicTitle ?? '',
    positiveSubtopicTitleBm: comparator?.subtopicTitleBm ?? '',
    positiveMasteryProbability: comparator?.record.masteryProbability,
    positiveUpdatedAt: comparator?.record.updatedAt,
  );
}

List<_EligibleCandidate> _eligibleCandidates({
  required List<TrustedSubtopicProgress> mastery,
  required List<Topic> curriculum,
  required String studentId,
  required int yearLevel,
  required DateTime now,
}) {
  final candidates = <_EligibleCandidate>[];
  for (final record in mastery) {
    if (record.studentId != studentId || record.yearLevel != yearLevel) {
      continue;
    }
    if (record.evidenceLevel != 'established') continue;
    final observations = record.observationCount;
    if (observations == null || observations <= 0) continue;
    final probability = record.masteryProbability;
    if (probability == null) continue;
    final updatedAt = record.updatedAt;
    if (updatedAt == null ||
        !isFreshWithinDays(
          updatedAt,
          now,
          maxDays: parentUnderstandingFreshnessDays,
        )) {
      continue;
    }
    final labels = _curriculumLabels(
      curriculum,
      record.topicId,
      record.subtopicId,
    );
    if (labels == null) continue;
    candidates.add(
      _EligibleCandidate(
        record: record,
        topicTitle: labels.$1.title,
        topicTitleBm: labels.$1.titleBm,
        subtopicTitle: labels.$2.title,
        subtopicTitleBm: labels.$2.titleBm,
      ),
    );
  }
  return candidates;
}

(Topic, Subtopic)? _curriculumLabels(
  List<Topic> curriculum,
  String topicId,
  String subtopicId,
) {
  for (final topic in curriculum) {
    if (topic.id != topicId) continue;
    for (final subtopic in topic.subtopics) {
      if (subtopic.id == subtopicId) return (topic, subtopic);
    }
    return null;
  }
  return null;
}

_EligibleCandidate _selectFocus(List<_EligibleCandidate> candidates) {
  var focus = candidates.first;
  for (final candidate in candidates.skip(1)) {
    if (_focusIsBetter(candidate, focus)) focus = candidate;
  }
  return focus;
}

bool _focusIsBetter(_EligibleCandidate a, _EligibleCandidate b) {
  final probability = a.record.masteryProbability!.compareTo(
    b.record.masteryProbability!,
  );
  if (probability != 0) return probability < 0;
  final freshness = b.record.updatedAt!.compareTo(a.record.updatedAt!);
  if (freshness != 0) return freshness < 0;
  return a.record.subtopicId.compareTo(b.record.subtopicId) < 0;
}

_EligibleCandidate? _selectComparator(
  List<_EligibleCandidate> candidates,
  _EligibleCandidate focus,
) {
  _EligibleCandidate? best;
  for (final candidate in candidates) {
    if (candidate.record.subtopicId == focus.record.subtopicId) continue;
    if (candidate.record.topicId != focus.record.topicId) continue;
    if (best == null || _comparatorIsStronger(candidate, best))
      best = candidate;
  }
  return best;
}

bool _comparatorIsStronger(_EligibleCandidate a, _EligibleCandidate b) {
  final probability = a.record.masteryProbability!.compareTo(
    b.record.masteryProbability!,
  );
  if (probability != 0) return probability > 0;
  final freshness = a.record.updatedAt!.compareTo(b.record.updatedAt!);
  if (freshness != 0) return freshness > 0;
  return a.record.subtopicId.compareTo(b.record.subtopicId) < 0;
}

ParentPracticeCard _derivePractice(
  ParentPracticeSummary? practice,
  DateTime now,
) {
  if (practice == null) return const ParentPracticeCard.unavailable();
  if (!isSameMalaysiaWeek(practice.weekStart, now)) {
    return const ParentPracticeCard.unavailable();
  }
  if (malaysiaWeekStartUtc(practice.weekStart) != practice.weekStart) {
    return const ParentPracticeCard.unavailable();
  }
  final previous = practice.previousWeekCompletedPracticeCount;
  return ParentPracticeCard.ready(
    weeklyTotal: practice.completedPracticeCount,
    activeDayCount: practice.activeDayCount,
    dailyCounts: List<int>.unmodifiable(practice.dailyCompletionCounts),
    previousWeekCompletedPracticeCount: previous,
    improvedOverPreviousWeek:
        previous != null && practice.completedPracticeCount > previous,
    supportedDifference: previous == null
        ? null
        : practice.completedPracticeCount - previous,
    latestPracticeAt: practice.lastPracticeAt,
    updatedAt: practice.updatedAt,
  );
}

ParentMutualAidCard _deriveMutualAid(
  ForumParticipationSummary? mutualAid,
  String studentId,
  DateTime now,
) {
  if (mutualAid == null) return const ParentMutualAidCard.unavailable();
  if (mutualAid.studentId != studentId) {
    return const ParentMutualAidCard.unavailable();
  }
  final weekStart = mutualAid.weekStart;
  if (weekStart == null ||
      !isSameMalaysiaWeek(weekStart, now) ||
      malaysiaWeekStartUtc(weekStart) != weekStart) {
    return const ParentMutualAidCard.unavailable();
  }
  return ParentMutualAidCard.ready(
    questionsPostedCount: mutualAid.questionsPostedCount,
    answersSubmittedCount: mutualAid.answersSubmittedCount,
    acceptedAnswersCount: mutualAid.acceptedAnswersCount,
    helpfulReceivedCount: mutualAid.helpfulReceivedCount,
  );
}

ParentAction? _deriveAction(
  ParentUnderstandingCard understanding,
  ParentPracticeCard practice,
  ParentMutualAidCard mutualAid,
) {
  if (understanding.status == ParentUnderstandingStatus.ready) {
    final band = understanding.masteryBand!;
    final kind = switch (band) {
      ParentMasteryBand.needsGuidedPractice ||
      ParentMasteryBand.growing => ParentActionKind.understandingFocus,
      ParentMasteryBand.currentStrength => ParentActionKind.maintainStrength,
    };
    return ParentAction(
      kind: kind,
      masteryBand: band,
      focusSubtopicId: understanding.focusSubtopicId,
      focusMasteryProbability: understanding.focusMasteryProbability,
    );
  }
  if (practice.status == ParentPracticeStatus.ready &&
      practice.weeklyTotal == 0) {
    return const ParentAction(kind: ParentActionKind.practiceRoutine);
  }
  if (mutualAid.status == ParentMutualAidStatus.ready) {
    return mutualAid.hasActivity
        ? const ParentAction(kind: ParentActionKind.needsMoreActivity)
        : const ParentAction(kind: ParentActionKind.mutualAidInvitation);
  }
  return null;
}

ParentWeeklyGlance _deriveGlance(
  ParentUnderstandingCard understanding,
  ParentPracticeCard practice,
  ParentMutualAidCard mutualAid,
) {
  final hasFocus = understanding.status == ParentUnderstandingStatus.ready;
  final practiceAvailable = practice.status == ParentPracticeStatus.ready;
  final hasPracticeActivity = practiceAvailable && practice.weeklyTotal > 0;
  final mutualAidAvailable = mutualAid.status == ParentMutualAidStatus.ready;
  final hasMutualAidActivity = mutualAidAvailable && mutualAid.hasActivity;
  final improved = hasPracticeActivity && practice.improvedOverPreviousWeek;
  return ParentWeeklyGlance(
    hasFocus: hasFocus,
    hasPracticeActivity: hasPracticeActivity,
    practiceUnavailable: !practiceAvailable,
    hasMutualAidActivity: hasMutualAidActivity,
    mutualAidUnavailable: !mutualAidAvailable,
    improvedOverPreviousWeek: improved,
    supportedDifference: improved ? practice.supportedDifference : null,
    key: parentGlanceKey(
      hasFocus: hasFocus,
      practiceAvailable: practiceAvailable,
      hasPracticeActivity: hasPracticeActivity,
      mutualAidAvailable: mutualAidAvailable,
      hasMutualAidActivity: hasMutualAidActivity,
    ),
  );
}
