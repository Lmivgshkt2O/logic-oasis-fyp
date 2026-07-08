import 'package:cloud_firestore/cloud_firestore.dart';

class AiDiagnosis {
  const AiDiagnosis({
    required this.id,
    required this.studentId,
    required this.topicId,
    this.yearLevel,
    required this.modelName,
    required this.xgboostPrediction,
    required this.weaknessProbability,
    required this.confidence,
    required this.shapReasons,
    required this.shapDetails,
    required this.bktPriorKnowledge,
    required this.bktLearnRate,
    required this.bktGuessRate,
    required this.bktSlipRate,
    required this.bktMasteryProbability,
    required this.finalMasteryLabel,
    required this.recommendedAction,
    required this.attemptsCount,
    required this.createdAt,
  });

  final String id;
  final String studentId;
  final String topicId;
  final int? yearLevel;
  final String modelName;
  final String xgboostPrediction;
  final double weaknessProbability;
  final double confidence;
  final List<String> shapReasons;
  final List<ShapDetail> shapDetails;
  final double bktPriorKnowledge;
  final double bktLearnRate;
  final double bktGuessRate;
  final double bktSlipRate;
  final double bktMasteryProbability;
  final String finalMasteryLabel;
  final String recommendedAction;
  final int attemptsCount;
  final DateTime createdAt;

  double get priorityScore {
    final masteryGap = 1 - bktMasteryProbability;
    return (weaknessProbability * 0.65) + (masteryGap * 0.35);
  }

  List<String> get explanationReasons {
    if (shapReasons.isNotEmpty) return shapReasons;
    return shapDetails
        .map((detail) => detail.reason)
        .where((reason) => reason.trim().isNotEmpty)
        .toList(growable: false);
  }

  bool isNewerThan(AiDiagnosis other) {
    final createdAtComparison = createdAt.compareTo(other.createdAt);
    if (createdAtComparison != 0) return createdAtComparison > 0;
    if (attemptsCount != other.attemptsCount) {
      return attemptsCount > other.attemptsCount;
    }
    return id.compareTo(other.id) > 0;
  }

  static AiDiagnosis? fromFirestore(String id, Map<String, dynamic> data) {
    final studentId = data['studentId'];
    final topicId = data['topicId'];
    if (studentId is! String || topicId is! String) return null;

    return AiDiagnosis(
      id: id,
      studentId: studentId,
      topicId: topicId,
      yearLevel: _intValue(data['yearLevel']) ?? _yearFromTopicId(topicId),
      modelName: _stringValue(data['modelName'], 'xgboost_shap_bkt_v1'),
      xgboostPrediction: _stringValue(data['xgboostPrediction'], 'Moderate'),
      weaknessProbability: _probabilityValue(data['weaknessProbability']),
      confidence: _probabilityValue(data['confidence']),
      shapReasons: _stringList(data['shapReasons']),
      shapDetails: _shapDetails(data['shapDetails']),
      bktPriorKnowledge: _probabilityValue(data['bktPriorKnowledge']),
      bktLearnRate: _probabilityValue(data['bktLearnRate']),
      bktGuessRate: _probabilityValue(data['bktGuessRate']),
      bktSlipRate: _probabilityValue(data['bktSlipRate']),
      bktMasteryProbability: _probabilityValue(data['bktMasteryProbability']),
      finalMasteryLabel: _stringValue(data['finalMasteryLabel'], 'Moderate'),
      recommendedAction: _stringValue(
        data['recommendedAction'],
        'Complete one guided practice mission.',
      ),
      attemptsCount: _intValue(data['attemptsCount']) ?? 0,
      createdAt: data['createdAt'] is Timestamp
          ? (data['createdAt'] as Timestamp).toDate()
          : DateTime.fromMillisecondsSinceEpoch(0),
    );
  }

  static String _stringValue(dynamic value, String fallback) {
    return value is String && value.isNotEmpty ? value : fallback;
  }

  static double _doubleValue(dynamic value) {
    return value is num ? value.toDouble() : 0;
  }

  static double _probabilityValue(dynamic value) {
    final parsed = _doubleValue(value);
    final normalized = parsed > 1 && parsed <= 100 ? parsed / 100 : parsed;
    return normalized.clamp(0.0, 1.0).toDouble();
  }

  static int? _intValue(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.round();
    if (value is String) return int.tryParse(value);
    return null;
  }

  static int? _yearFromTopicId(String topicId) {
    final match = RegExp(r'(?:^|_)y([456])(?:_|$)').firstMatch(topicId);
    return match == null ? null : int.tryParse(match.group(1)!);
  }

  static List<String> _stringList(dynamic value) {
    if (value is! List) return const [];
    return value.whereType<String>().toList(growable: false);
  }

  static List<ShapDetail> _shapDetails(dynamic value) {
    if (value is! List) return const [];
    return value
        .whereType<Map>()
        .map(ShapDetail.fromMap)
        .whereType<ShapDetail>()
        .toList(growable: false);
  }
}

class ShapDetail {
  const ShapDetail({
    required this.feature,
    required this.value,
    required this.shapValue,
    required this.direction,
    required this.reason,
    required this.source,
  });

  final String feature;
  final Object? value;
  final double? shapValue;
  final String direction;
  final String reason;
  final String source;

  static ShapDetail? fromMap(Map<dynamic, dynamic> data) {
    final feature = data['feature'];
    final reason = data['reason'];
    if (feature is! String || reason is! String) return null;

    return ShapDetail(
      feature: feature,
      value: data['value'],
      shapValue: _nullableDoubleValue(data['shapValue']),
      direction: _stringValue(data['direction'], 'unknown'),
      reason: reason,
      source: _stringValue(data['source'], 'unknown'),
    );
  }

  static String _stringValue(dynamic value, String fallback) {
    return value is String && value.isNotEmpty ? value : fallback;
  }

  static double? _nullableDoubleValue(dynamic value) {
    return value is num ? value.toDouble() : null;
  }
}
