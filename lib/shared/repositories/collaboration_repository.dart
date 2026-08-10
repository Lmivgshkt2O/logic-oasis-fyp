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

  Stream<List<ForumQuestion>> watchQuestions() => _firestore
      .collection('forumQuestions')
      .orderBy('updatedAt', descending: true)
      .limit(40)
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
