import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:logic_oasis/shared/models/adaptive_assignment.dart';

/// Safe, display-only composition of U8 projections.
///
/// This model intentionally has no raw feature values, SHAP arrays, artifact
/// metadata, job errors, or model-registry values. A supportive reason is
/// supplied only by the compatible, server-written adaptive assignment.
class AiDiagnosis {
  const AiDiagnosis({
    required this.attemptId,
    required this.studentId,
    required this.sourceAttemptSequence,
    required this.analysisState,
    required this.displayCode,
    String? topicId,
    this.yearLevel,
    this.masteryProbability,
    this.weakTopicPriorityScore,
    this.evidenceLevel,
    this.observationCount,
    this.rankingVersion,
    this.assignment,
    this.updatedAt,
  }) : _topicId = topicId;

  final String attemptId;
  final String studentId;
  final int sourceAttemptSequence;
  final String analysisState;
  final String displayCode;
  final String? _topicId;
  String get topicId => _topicId ?? '';
  final int? yearLevel;
  final double? masteryProbability;
  final double? weakTopicPriorityScore;
  final String? evidenceLevel;
  final int? observationCount;
  final String? rankingVersion;
  final AdaptiveAssignment? assignment;
  final DateTime? updatedAt;

  double get priorityScore => weakTopicPriorityScore ?? 0;
  double get bktMasteryProbability => masteryProbability ?? 0;
  double get weaknessProbability => weakTopicPriorityScore ?? 0;
  double get confidence => evidenceLevel == 'established' ? 1 : 0.5;
  String get finalMasteryLabel {
    final mastery = masteryProbability;
    if (mastery == null) return 'Updating';
    if (mastery >= 0.8) return 'Strong';
    if (mastery >= 0.5) return 'Building';
    return 'Needs practice';
  }
  String get modelName => isCompleted ? 'Approved server analysis' : 'BKT guidance';
  int get attemptsCount => observationCount ?? 0;
  DateTime get createdAt => updatedAt ?? DateTime.fromMillisecondsSinceEpoch(0);
  List<String> get explanationReasons =>
      supportingReason == null ? const [] : <String>[supportingReason!];
  String get recommendedAction => supportingReason ?? childFacingStatus;

  bool isNewerThan(AiDiagnosis other) {
    if (sourceAttemptSequence != other.sourceAttemptSequence) {
      return sourceAttemptSequence > other.sourceAttemptSequence;
    }
    return createdAt.isAfter(other.createdAt);
  }

  bool get isProcessing => analysisState == 'queued' || analysisState == 'processing';
  bool get isCompleted => analysisState == 'completed';
  bool get isFallback => analysisState == 'fallback';
  bool get isFailed => analysisState == 'failed';
  bool get hasCompatibleRanking =>
      rankingVersion != null && rankingVersion!.isNotEmpty && masteryProbability != null;

  /// Only server-projected child-friendly text may be shown as an explanation.
  String? get supportingReason => assignment?.reasonText;

  String get childFacingStatus => switch (analysisState) {
    'completed' => 'Your next practice is ready.',
    'fallback' => 'Your next practice is ready using your quiz progress.',
    'failed' => 'Your quiz score is saved. Practice advice will be available later.',
    _ => 'Your quiz score is saved. Preparing your next practice…',
  };

  static AiDiagnosis? fromSafeProjection(
    String attemptId,
    Map<String, dynamic> status, {
    Map<String, dynamic>? mastery,
    AdaptiveAssignment? assignment,
  }) {
    final studentId = status['studentId'];
    final sourceAttemptSequence = _int(status['sourceAttemptSequence']);
    final analysisState = status['analysisState'];
    final displayCode = status['displayCode'];
    if (studentId is! String ||
        studentId.isEmpty ||
        sourceAttemptSequence == null ||
        sourceAttemptSequence < 1 ||
        analysisState is! String ||
        displayCode is! String) {
      return null;
    }
    return AiDiagnosis(
      attemptId: attemptId,
      studentId: studentId,
      sourceAttemptSequence: sourceAttemptSequence,
      analysisState: analysisState,
      displayCode: displayCode,
      topicId: _string(mastery?['topicId']),
      yearLevel: _int(mastery?['yearLevel']),
      masteryProbability: _probability(mastery?['masteryProbability']),
      weakTopicPriorityScore: _probability(mastery?['weakTopicPriorityScore']),
      evidenceLevel: _string(mastery?['evidenceLevel']),
      observationCount: _int(mastery?['observationCount']),
      rankingVersion: _string(mastery?['rankingVersion']),
      assignment: assignment,
      updatedAt: status['updatedAt'] is Timestamp
          ? (status['updatedAt'] as Timestamp).toDate()
          : null,
    );
  }

  static int? _int(Object? value) {
    if (value is int) return value;
    if (value is num && value == value.roundToDouble()) return value.toInt();
    return null;
  }

  static double? _probability(Object? value) {
    if (value is! num) return null;
    final normalized = value.toDouble();
    return normalized >= 0 && normalized <= 1 ? normalized : null;
  }

  static String? _string(Object? value) =>
      value is String && value.isNotEmpty ? value : null;
}
