import 'package:logic_oasis/shared/models/question_bank.dart';

/// Read-only server assignment for the next trusted quiz bank.
class AdaptiveAssignment {
  const AdaptiveAssignment({
    required this.id,
    required this.subtopicId,
    required this.bankId,
    required this.difficulty,
    required this.policyVersion,
    required this.reasonCode,
    required this.reasonText,
    required this.evidenceCount,
    required this.usedBktFallback,
    this.masteryProbability,
    this.supportRisk,
  });

  final String id;
  final String subtopicId;
  final String bankId;
  final QuestionDifficulty difficulty;
  final String policyVersion;
  final String reasonCode;
  final String reasonText;
  final int evidenceCount;
  final bool usedBktFallback;
  final double? masteryProbability;
  final double? supportRisk;

  factory AdaptiveAssignment.fromFirestoreData(
    String id,
    Map<Object?, Object?> data,
  ) {
    final difficulty = QuestionDifficulty.fromLabel(
      _requiredString(data, 'difficultyLevel'),
    );
    if (difficulty == null) {
      throw FormatException('Unknown assignment difficulty.');
    }
    final evidenceCount = _requiredInt(data, 'evidenceCount');
    if (evidenceCount < 0) {
      throw FormatException('Adaptive assignment evidence count is invalid.');
    }
    final usedBktFallback = data['usedBktFallback'];
    if (usedBktFallback is! bool) {
      throw FormatException('Adaptive assignment fallback state is missing.');
    }
    return AdaptiveAssignment(
      id: id,
      subtopicId: _requiredString(data, 'subtopicId'),
      bankId: _requiredString(data, 'bankId'),
      difficulty: difficulty,
      policyVersion: _requiredString(data, 'policyVersion'),
      reasonCode: _requiredString(data, 'reasonCode'),
      reasonText: _requiredString(data, 'reasonText'),
      evidenceCount: evidenceCount,
      usedBktFallback: usedBktFallback,
      masteryProbability: _optionalDouble(data['masteryProbability']),
      supportRisk: _optionalDouble(data['supportRisk']),
    );
  }

  static String _requiredString(Map<Object?, Object?> data, String field) {
    final value = data[field];
    if (value is String && value.isNotEmpty) return value;
    throw FormatException('Missing adaptive assignment field: $field');
  }

  static int _requiredInt(Map<Object?, Object?> data, String field) {
    final value = data[field];
    if (value is int) return value;
    if (value is num && value == value.roundToDouble()) return value.toInt();
    throw FormatException('Missing adaptive assignment field: $field');
  }

  static double? _optionalDouble(Object? value) =>
      value is num ? value.toDouble() : null;
}
