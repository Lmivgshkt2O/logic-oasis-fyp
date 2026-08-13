import 'dart:convert';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:cloud_functions/cloud_functions.dart';
import 'package:logic_oasis/shared/models/forum_answer.dart';
import 'package:logic_oasis/shared/models/forum_question.dart';

/// Student-only collaboration access. Parents deliberately use neither this
/// repository nor these collections; they receive the count-only projection.
class CollaborationRepository {
  CollaborationRepository({
    FirebaseFirestore? firestore,
    FirebaseFunctions? functions,
  }) : _firestore = firestore ?? FirebaseFirestore.instance,
       _functions =
           functions ??
           FirebaseFunctions.instanceFor(region: 'asia-southeast1');

  final FirebaseFirestore _firestore;
  final FirebaseFunctions _functions;

  /// Load one deterministic page ordered by `updatedAt` descending and then
  /// document ID descending. The cursor is opaque and carries both values so
  /// equal timestamps cannot duplicate or skip items.
  Future<ForumQuestionPage> loadForumQuestions({
    required int limit,
    String? cursor,
  }) async {
    var query = _firestore
        .collection('forumQuestions')
        .orderBy('updatedAt', descending: true)
        .orderBy(FieldPath.documentId, descending: true)
        .limit(limit);
    if (cursor != null && cursor.isNotEmpty) {
      final decoded = decodeForumQuestionCursor(cursor);
      query = query.startAfter([decoded.updatedAt, decoded.id]);
    }
    final snapshot = await query.get();
    final questions = snapshot.docs
        .map((doc) => ForumQuestion.fromFirestore(doc.id, doc.data()))
        .toList(growable: false);
    final hasMore = snapshot.docs.length == limit;
    return ForumQuestionPage(
      questions: questions,
      nextCursor: snapshot.docs.isEmpty
          ? null
          : encodeForumQuestionCursor(
              id: snapshot.docs.last.id,
              data: snapshot.docs.last.data(),
            ),
      hasMore: hasMore,
    );
  }

  /// Realtime first page used to invalidate accumulated paging state when an
  /// ordering-affecting change (new question, updated timestamp) arrives.
  Stream<List<ForumQuestion>> watchLatestForumQuestions({
    required int limit,
  }) => _firestore
      .collection('forumQuestions')
      .orderBy('updatedAt', descending: true)
      .orderBy(FieldPath.documentId, descending: true)
      .limit(limit)
      .snapshots()
      .map(
        (snapshot) => snapshot.docs
            .map((doc) => ForumQuestion.fromFirestore(doc.id, doc.data()))
            .toList(growable: false),
      );

  Stream<Set<String>> watchBlockedStudentIds(String studentId) => _firestore
      .collection('forumBlocks')
      .where('studentId', isEqualTo: studentId)
      .snapshots()
      .map(
        (snapshot) => snapshot.docs
            .map((doc) => doc.data()['blockedStudentId'] as String? ?? '')
            .where((id) => id.isNotEmpty)
            .toSet(),
      );

  Stream<List<ForumAnswer>> watchAnswers(String questionId) => _firestore
      .collection('forumAnswers')
      .where('questionId', isEqualTo: questionId)
      .orderBy('createdAt')
      .snapshots()
      .map(
        (snapshot) => snapshot.docs
            .map((doc) => ForumAnswer.fromFirestore(doc.id, doc.data()))
            .toList(growable: false),
      );

  /// Author-only AI guidance for one answer. The server writes this projection
  /// and Rules allow only the answer author to read it; peers and parents are
  /// denied by [firestore.rules].
  Stream<ForumAnswerFeedback> watchOwnFeedback(String answerId) => _firestore
      .collection('forumAiFeedback')
      .doc(answerId)
      .snapshots()
      .map((snapshot) => ForumAnswerFeedback.fromFirestore(snapshot.data()));

  Future<void> createQuestion({
    required String studentId,
    required String title,
    required String text,
  }) => _firestore.collection('forumQuestions').add({
    'authorId': studentId,
    'title': title.trim(),
    'text': text.trim(),
    'createdAt': FieldValue.serverTimestamp(),
    'updatedAt': FieldValue.serverTimestamp(),
  });

  Future<void> editAnswer({
    required String studentId,
    required String answerId,
    required String text,
  }) async {
    final reference = _firestore.collection('forumAnswers').doc(answerId);
    await _firestore.runTransaction((transaction) async {
      final snapshot = await transaction.get(reference);
      final data = snapshot.data();
      if (data == null) throw StateError('Answer not found.');
      if (data['authorId'] != studentId) {
        throw StateError('Only the answer author may edit this answer.');
      }
      if (data['acceptedAt'] != null) {
        throw StateError('An accepted answer cannot be edited.');
      }
      final revision = (data['revision'] as int? ?? 1) + 1;
      transaction.update(reference, {
        'text': text.trim(),
        'revision': revision,
        'aiFeedback': {
          'state': 'pending',
          'label': 'uncertain',
          'message': 'Your revised answer is being reviewed.',
          'revision': revision,
        },
        'updatedAt': FieldValue.serverTimestamp(),
      });
    });
  }

  Future<void> submitAnswer({
    required String studentId,
    required String questionId,
    required String text,
  }) => _firestore.collection('forumAnswers').add({
    'questionId': questionId,
    'authorId': studentId,
    'text': text.trim(),
    'revision': 1,
    'createdAt': FieldValue.serverTimestamp(),
    'updatedAt': FieldValue.serverTimestamp(),
  });

  /// Create or open the canonical linked discussion for a question-bank item.
  /// Only the public question ID is sent; the server derives source identity,
  /// active-version eligibility, and the client-safe prompt/options snapshot.
  Future<LinkedDiscussion> openOrCreateLinkedDiscussion({
    required String questionId,
  }) async {
    final result = await _functions
        .httpsCallable('openOrCreateForumDiscussion')
        .call({'questionId': questionId});
    return LinkedDiscussion.fromCallableResult(
      Map<String, dynamic>.from(result.data as Map),
    );
  }

  Future<String> submitLinkedAnswer({
    required String discussionId,
    required int selectedOption,
    required String explanation,
  }) async {
    final result = await _functions
        .httpsCallable('submitLinkedForumAnswer')
        .call({
          'discussionId': discussionId,
          'selectedOption': selectedOption,
          'explanation': explanation.trim(),
        });
    final data = Map<String, dynamic>.from(result.data as Map);
    return data['answerId'] as String? ?? '';
  }

  Future<int> editLinkedAnswer({
    required String answerId,
    required int selectedOption,
    required String explanation,
  }) async {
    final result = await _functions
        .httpsCallable('editLinkedForumAnswer')
        .call({
          'answerId': answerId,
          'selectedOption': selectedOption,
          'explanation': explanation.trim(),
        });
    final data = Map<String, dynamic>.from(result.data as Map);
    return data['revision'] as int? ?? 1;
  }

  Future<void> acceptAnswer(String answerId) => _functions
      .httpsCallable('acceptForumAnswer')
      .call({'answerId': answerId});

  Future<void> markHelpful(String answerId) => _functions
      .httpsCallable('markForumAnswerHelpful')
      .call({'answerId': answerId});

  Future<void> report({
    required String targetType,
    required String targetId,
    required String reason,
  }) => _functions.httpsCallable('reportForumContent').call({
    'targetType': targetType,
    'targetId': targetId,
    'reason': reason.trim(),
  });

  Future<void> block({
    required String studentId,
    required String blockedStudentId,
  }) => _firestore
      .collection('forumBlocks')
      .doc('${studentId}_$blockedStudentId')
      .set({
        'studentId': studentId,
        'blockedStudentId': blockedStudentId,
        'createdAt': FieldValue.serverTimestamp(),
      });

  Future<void> unblock({
    required String studentId,
    required String blockedStudentId,
  }) => _firestore
      .collection('forumBlocks')
      .doc('${studentId}_$blockedStudentId')
      .delete();
}

/// Opaque, deterministic paging cursor for forum questions. It carries the
/// last document's `updatedAt` (ISO-8601, microsecond-preserving) and ID so a
/// `startAfter` page continues the exact frozen ordering.
String encodeForumQuestionCursor({
  required String id,
  required Map<String, dynamic>? data,
}) {
  final fields = data ?? const <String, dynamic>{};
  final updatedAt = fields['updatedAt'];
  final iso = updatedAt is Timestamp
      ? updatedAt.toDate().toUtc().toIso8601String()
      : '';
  return base64UrlEncode(
    utf8.encode(jsonEncode(<String, String>{'u': iso, 'i': id})),
  );
}

({DateTime? updatedAt, String id}) decodeForumQuestionCursor(
  String cursor,
) {
  try {
    final decoded = utf8.decode(base64Url.decode(cursor));
    final payload = jsonDecode(decoded);
    if (payload is! Map<String, dynamic>) {
      throw const FormatException();
    }
    final iso = payload['u'];
    final id = payload['i'];
    if (iso is! String || iso.isEmpty || id is! String || id.isEmpty) {
      throw const FormatException();
    }
    return (updatedAt: DateTime.parse(iso), id: id);
  } on FormatException {
    throw const FormatException('Malformed forum paging cursor.');
  } catch (_) {
    throw const FormatException('Malformed forum paging cursor.');
  }
}
