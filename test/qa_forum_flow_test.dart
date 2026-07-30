import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/models/forum_answer.dart';
import 'package:logic_oasis/shared/services/forum_ai_status_service.dart';

void main() {
  test('forum feedback stays advisory and never labels probability confidence', () {
    const feedback = ForumAnswerFeedback(
      state: 'completed',
      label: 'needs_reasoning',
      message: 'Please add the steps behind your answer.',
      probability: 0.74,
      modelVersion: 'forum-explanation-nb-v1',
      calibrationState: 'not_calibrated',
    );

    expect(const ForumAiStatusService().statusText(feedback), contains('steps'));
    expect(feedback.calibrationState, 'not_calibrated');
  });

  test('fallback stays editable rather than asserting a model decision', () {
    const feedback = ForumAnswerFeedback(
      state: 'fallback',
      label: 'uncertain',
      message: '',
    );
    expect(const ForumAiStatusService().statusText(feedback), contains('saved'));
  });
}
