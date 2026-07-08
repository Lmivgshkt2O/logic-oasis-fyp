import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:logic_oasis/shared/models/quiz_question.dart';
import 'package:logic_oasis/shared/models/subtopic.dart';
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

    final questionSnapshot = await _firestore.collection('questions').get();

    final questionsByTopic = <String, List<QuizQuestion>>{};
    final questionsBySubtopic = <String, List<QuizQuestion>>{};
    for (final doc in questionSnapshot.docs) {
      final data = doc.data();
      final topicId = data['topicId'] as String?;
      if (topicId == null || topicId.isEmpty) continue;

      final question = _questionFromData(data);
      if (question == null) continue;

      questionsByTopic.putIfAbsent(topicId, () => []).add(question);
      final subtopicId = question.subtopicId;
      if (subtopicId != null && subtopicId.isNotEmpty) {
        questionsBySubtopic
            .putIfAbsent(
              _subtopicQuestionKey(topicId: topicId, subtopicId: subtopicId),
              () => [],
            )
            .add(question);
      }
    }
    for (final questions in questionsByTopic.values) {
      questions.sort(_compareQuestions);
    }
    for (final questions in questionsBySubtopic.values) {
      questions.sort(_compareQuestions);
    }

    final subtopicsByTopic = await _fetchSubtopicsByTopic(
      normalizedYearLevel: yearLevel.clamp(4, 6),
      questionsBySubtopic: questionsBySubtopic,
    );

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
      final questions = questionsByTopic[doc.id] ?? const <QuizQuestion>[];
      return Topic(
        id: doc.id,
        title: _stringValue(data['title'], fallback: doc.id),
        titleBm: _stringValue(data['titleBm'], fallback: data['title']),
        area: _stringValue(data['description'], fallback: 'KSSR practice'),
        areaBm: _stringValue(data['descriptionBm']),
        yearLevel: _yearLevelFromData(data, doc.id) ?? normalizedYearLevel,
        progress: 0,
        mastery: 'New',
        questions: questions,
        subtopics: subtopicsByTopic[doc.id] ??
            _inferSubtopicsFromQuestions(
              topicId: doc.id,
              questions: questions,
            ),
      );
    }).toList();
  }

  Future<Map<String, List<Subtopic>>> _fetchSubtopicsByTopic({
    required int normalizedYearLevel,
    required Map<String, List<QuizQuestion>> questionsBySubtopic,
  }) async {
    final QuerySnapshot<Map<String, dynamic>> snapshot;
    try {
      snapshot = await _firestore.collection('subtopics').get();
    } on FirebaseException {
      return const <String, List<Subtopic>>{};
    }
    if (snapshot.docs.isEmpty) return const <String, List<Subtopic>>{};

    final grouped = <String, List<Subtopic>>{};
    for (final doc in snapshot.docs) {
      final data = doc.data();
      final topicId = data['topicId'];
      if (topicId is! String || topicId.isEmpty) continue;
      final yearLevel = _yearLevelFromData(data, topicId);
      if (yearLevel != null && yearLevel != normalizedYearLevel) continue;
      if (data['isActive'] == false) continue;
      final rawSubtopicId = data['subtopicId'];
      final subtopicId =
          rawSubtopicId is String && rawSubtopicId.trim().isNotEmpty
          ? rawSubtopicId
          : _logicalSubtopicId(documentId: doc.id, topicId: topicId);

      grouped.putIfAbsent(topicId, () => []).add(
        Subtopic(
          id: subtopicId,
          title: _stringValue(data['title'], fallback: doc.id),
          titleBm: _stringValue(data['titleBm'], fallback: data['title']),
          order: _numberValue(data['order']).round(),
          description: _stringValue(data['description']),
          descriptionBm: _stringValue(data['descriptionBm']),
          standardCode: _stringValue(data['standardCode']),
          sourcePages: _stringValue(data['sourcePages']),
          questions:
              questionsBySubtopic[_subtopicQuestionKey(
                topicId: topicId,
                subtopicId: subtopicId,
              )] ??
              const <QuizQuestion>[],
        ),
      );
    }

    for (final subtopics in grouped.values) {
      subtopics.sort((a, b) => a.order.compareTo(b.order));
    }
    return grouped;
  }

  List<Subtopic> _inferSubtopicsFromQuestions({
    required String topicId,
    required List<QuizQuestion> questions,
  }) {
    final grouped = <String, List<QuizQuestion>>{};
    for (final question in questions) {
      final subtopicId = question.subtopicId;
      if (subtopicId == null || subtopicId.isEmpty) continue;
      grouped.putIfAbsent(subtopicId, () => []).add(question);
    }
    var order = 0;
    return grouped.entries.map((entry) {
      order += 1;
      final title = _titleFromId(entry.key);
      return Subtopic(
        id: entry.key,
        title: title,
        titleBm: title,
        order: order,
        description: 'Practice from $topicId',
        questions: entry.value,
      );
    }).toList(growable: false);
  }

  String _subtopicQuestionKey({
    required String topicId,
    required String subtopicId,
  }) {
    return '$topicId::$subtopicId';
  }

  String _logicalSubtopicId({
    required String documentId,
    required String topicId,
  }) {
    final prefix = '${topicId}_';
    if (documentId.startsWith(prefix) && documentId.length > prefix.length) {
      return documentId.substring(prefix.length);
    }
    return documentId;
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
      subtopicId: data['subtopicId'] is String
          ? data['subtopicId'] as String
          : null,
      order: _intValue(data['order']),
      bloomLevel: data['bloomLevel'] is String
          ? data['bloomLevel'] as String
          : null,
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

  int _compareQuestions(QuizQuestion a, QuizQuestion b) {
    final orderComparison = (a.order ?? 999).compareTo(b.order ?? 999);
    if (orderComparison != 0) return orderComparison;
    return a.question.compareTo(b.question);
  }

  String _titleFromId(String value) {
    return value
        .split('_')
        .where((part) => part.isNotEmpty)
        .map((part) => '${part[0].toUpperCase()}${part.substring(1)}')
        .join(' ');
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
