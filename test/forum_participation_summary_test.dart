import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/models/forum_participation_summary.dart';

void main() {
  test('forum participation summary tolerates absent and invalid count values', () {
    final summary = ForumParticipationSummary.fromFirestore('student_a', {
      'questionsPostedCount': 3,
      'answersSubmittedCount': -1,
      'acceptedAnswersCount': 2.0,
      // No text, author, peer, moderation, or model field belongs in this model.
    });

    expect(summary.questionsPostedCount, 3);
    expect(summary.answersSubmittedCount, 0);
    expect(summary.acceptedAnswersCount, 2);
    expect(summary.helpfulReceivedCount, 0);
  });
}
