import 'package:logic_oasis/shared/models/forum_participation_summary.dart';
import 'package:logic_oasis/shared/models/parent_practice_summary.dart';
import 'package:logic_oasis/shared/models/trusted_subtopic_progress.dart';

/// A whole-snapshot authorization failure: permission denied, revoked parent
/// link, or a selected-child identity mismatch. It must clear the entire
/// child view and is classified for parent-safe retry messaging.
class ParentDashboardAuthException implements Exception {
  const ParentDashboardAuthException(this.message);

  final String message;

  @override
  String toString() => 'ParentDashboardAuthException: $message';
}

/// The independently available, typed safe card inputs for one linked child.
///
/// There are no raw maps, attempts, AI diagnoses, forum texts, or technical
/// explanations. Each non-auth projection resolves independently: a missing or
/// failed Practice/Mutual Aid document is `null` while valid Understanding
/// records remain.
class ParentDashboardSnapshot {
  const ParentDashboardSnapshot({
    required this.mastery,
    this.practiceSummary,
    this.forumParticipationSummary,
  });

  /// Strictly parsed safe mastery projections for the selected child; `null`
  /// when the mastery read itself failed so the card can be unavailable
  /// without discarding valid Practice or Mutual Aid evidence.
  final List<TrustedSubtopicProgress>? mastery;

  /// Server-owned current-week practice summary; `null` when unavailable.
  final ParentPracticeSummary? practiceSummary;

  /// U10 count-only current-week Mutual Aid summary; `null` when unavailable.
  final ForumParticipationSummary? forumParticipationSummary;
}
