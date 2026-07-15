import 'package:cloud_functions/cloud_functions.dart';
import 'package:logic_oasis/shared/models/question_response.dart';
import 'package:logic_oasis/shared/models/quiz_completion.dart';
import 'package:logic_oasis/shared/models/quiz_session.dart';

class QuizSessionException implements Exception {
  const QuizSessionException(this.message, {this.code});

  final String message;
  final String? code;

  @override
  String toString() => message;
}

/// The only Flutter boundary for U3 callable session functions.
class QuizSessionService {
  QuizSessionService({FirebaseFunctions? functions})
    : _functions =
          functions ?? FirebaseFunctions.instanceFor(region: 'asia-southeast1');

  final FirebaseFunctions _functions;

  Future<QuizSession> startSession({
    required String topicId,
    required String subtopicId,
    required int yearLevel,
  }) async {
    try {
      final result = await _functions
          .httpsCallable('startQuizSession')
          .call<Map<Object?, Object?>>(<String, Object>{
            'topicId': topicId,
            'subtopicId': subtopicId,
            // Send this as digits to avoid Android numeric-bridge decoding
            // differences; the callable normalizes only whole-number text.
            'yearLevel': yearLevel.toString(),
          });
      return QuizSession.fromCallableData(result.data);
    } on FirebaseFunctionsException catch (error) {
      throw QuizSessionException(
        error.message ?? 'Unable to start this quiz.',
        code: error.code,
      );
    }
  }

  Future<QuestionResponse> submitResponse({
    required QuestionResponse pendingResponse,
    required int responseTimeMs,
    int hintCount = 0,
  }) async {
    try {
      final result = await _functions
          .httpsCallable('submitQuizResponse')
          .call<Map<Object?, Object?>>(
            pendingResponse.toSubmissionData(
              responseTimeMs: responseTimeMs,
              hintCount: hintCount,
            ),
          );
      return QuestionResponse.fromCallableData(
        result.data,
        idempotencyKey: pendingResponse.idempotencyKey,
      );
    } on FirebaseFunctionsException catch (error) {
      throw QuizSessionException(
        error.message ?? 'Your answer is waiting for a secure retry.',
        code: error.code,
      );
    }
  }

  Future<QuizCompletion> finalizeSession(String sessionId) async {
    try {
      final result = await _functions
          .httpsCallable('finalizeQuizSession')
          .call<Map<Object?, Object?>>(<String, Object>{
            'sessionId': sessionId,
          });
      return QuizCompletion.fromCallableData(result.data);
    } on FirebaseFunctionsException catch (error) {
      throw QuizSessionException(
        error.message ?? 'Unable to finalize this quiz.',
        code: error.code,
      );
    }
  }
}
