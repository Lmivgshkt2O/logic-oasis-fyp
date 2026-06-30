import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:logic_oasis/shared/models/quiz_question.dart';
import 'package:logic_oasis/shared/models/topic.dart';

class TopicRepository {
  TopicRepository({FirebaseFirestore? firestore})
    : _firestore = firestore ?? FirebaseFirestore.instance;

  final FirebaseFirestore _firestore;

  Future<List<Topic>> fetchTopicsWithQuestions({required int yearLevel}) async {
    final topicSnapshot = await _firestore.collection('topics').get();

    if (topicSnapshot.docs.isEmpty) {
      return [];
    }

    final questionSnapshot = await _firestore
        .collection('questions')
        .orderBy('difficultyLevel')
        .get();

    final questionsByTopic = <String, List<QuizQuestion>>{};
    for (final doc in questionSnapshot.docs) {
      final data = doc.data();
      final topicId = data['topicId'] as String?;
      if (topicId == null || topicId.isEmpty) continue;

      final question = _questionFromData(data);
      if (question == null) continue;

      questionsByTopic.putIfAbsent(topicId, () => []).add(question);
    }

    final normalizedYearLevel = yearLevel.clamp(4, 6);
    final topicDocs =
        topicSnapshot.docs
            .where((doc) {
              final data = doc.data();
              final topicYearLevel = _yearLevelFromData(data, doc.id);
              return data['isActive'] != false &&
                  (topicYearLevel == null ||
                      topicYearLevel == normalizedYearLevel);
            })
            .toList()
          ..sort(
            (a, b) => _numberValue(
              a.data()['order'],
            ).compareTo(_numberValue(b.data()['order'])),
          );

    return topicDocs.map((doc) {
      final data = doc.data();
      return Topic(
        id: doc.id,
        title: _stringValue(data['title'], fallback: doc.id),
        titleBm: _stringValue(data['titleBm'], fallback: data['title']),
        area: _stringValue(data['description'], fallback: 'KSSR practice'),
        areaBm: _stringValue(data['descriptionBm']),
        yearLevel: _yearLevelFromData(data, doc.id) ?? normalizedYearLevel,
        progress: 0,
        mastery: 'New',
        questions: questionsByTopic[doc.id] ?? const [],
      );
    }).toList();
  }

  QuizQuestion? _questionFromData(Map<String, dynamic> data) {
    final questionText = data['questionText'];
    final questionTextBm = data['questionTextBm'];
    final options = data['options'];
    final optionsBm = data['optionsBm'];
    final answerIndex = data['answerIndex'];
    final explanation = data['explanation'];
    final explanationBm = data['explanationBm'];

    if (questionText is! String ||
        options is! List ||
        answerIndex is! int ||
        explanation is! String) {
      return null;
    }

    return QuizQuestion(
      question: questionText,
      questionBm: questionTextBm is String && questionTextBm.trim().isNotEmpty
          ? questionTextBm
          : null,
      options: options.map((option) => option.toString()).toList(),
      optionsBm: optionsBm is List
          ? optionsBm.map((option) => option.toString()).toList()
          : null,
      answerIndex: answerIndex,
      explanation: explanation,
      explanationBm: explanationBm is String && explanationBm.trim().isNotEmpty
          ? explanationBm
          : null,
    );
  }

  String _stringValue(Object? value, {Object? fallback}) {
    if (value is String && value.trim().isNotEmpty) {
      return value;
    }
    if (fallback is String && fallback.trim().isNotEmpty) {
      return fallback;
    }
    return '';
  }

  num _numberValue(Object? value) {
    if (value is num) return value;
    return 999;
  }

  int? _yearLevelFromData(Map<String, dynamic> data, String topicId) {
    final explicitYear =
        _intValue(data['yearLevel']) ??
        _intValue(data['year']) ??
        _intValue(data['grade']);
    if (explicitYear != null) return explicitYear.clamp(4, 6);

    final match = RegExp(r'(?:^|_)y([456])(?:_|$)').firstMatch(topicId);
    return match == null ? null : int.tryParse(match.group(1)!);
  }

  int? _intValue(Object? value) {
    if (value is int) return value;
    if (value is num) return value.round();
    if (value is String) return int.tryParse(value);
    return null;
  }
}
