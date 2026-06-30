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
    required this.bktPriorKnowledge,
    required this.bktLearnRate,
    required this.bktGuessRate,
    required this.bktSlipRate,
    required this.bktMasteryProbability,
    required this.finalMasteryLabel,
    required this.recommendedAction,
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
  final double bktPriorKnowledge;
  final double bktLearnRate;
  final double bktGuessRate;
  final double bktSlipRate;
  final double bktMasteryProbability;
  final String finalMasteryLabel;
  final String recommendedAction;
  final DateTime createdAt;

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
      weaknessProbability: _doubleValue(data['weaknessProbability']),
      confidence: _doubleValue(data['confidence']),
      shapReasons: _stringList(data['shapReasons']),
      bktPriorKnowledge: _doubleValue(data['bktPriorKnowledge']),
      bktLearnRate: _doubleValue(data['bktLearnRate']),
      bktGuessRate: _doubleValue(data['bktGuessRate']),
      bktSlipRate: _doubleValue(data['bktSlipRate']),
      bktMasteryProbability: _doubleValue(data['bktMasteryProbability']),
      finalMasteryLabel: _stringValue(data['finalMasteryLabel'], 'Moderate'),
      recommendedAction: _stringValue(
        data['recommendedAction'],
        'Complete one guided practice mission.',
      ),
      createdAt: data['createdAt'] is Timestamp
          ? (data['createdAt'] as Timestamp).toDate()
          : DateTime.now(),
    );
  }

  static String _stringValue(dynamic value, String fallback) {
    return value is String && value.isNotEmpty ? value : fallback;
  }

  static double _doubleValue(dynamic value) {
    return value is num ? value.toDouble() : 0;
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
}
