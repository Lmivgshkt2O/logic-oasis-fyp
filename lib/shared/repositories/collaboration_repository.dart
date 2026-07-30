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
       _functions = functions ?? FirebaseFunctions.instance;

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

  Future<void> submitAnswer({
    required String studentId,
    required String questionId,
    required String text,
  }) => _firestore.collection('forumAnswers').add({
    'questionId': questionId,
    'authorId': studentId,
    'text': text.trim(),
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
    required String studentId,
    required String targetType,
    required String targetId,
    required String reason,
  }) => _firestore.collection('forumReports').add({
    'reporterId': studentId,
    'targetType': targetType,
    'targetId': targetId,
    'reason': reason.trim(),
    'createdAt': FieldValue.serverTimestamp(),
  });
}
