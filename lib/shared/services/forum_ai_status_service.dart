import 'package:logic_oasis/shared/models/forum_answer.dart';

/// Presentation-only language for the safe feedback state stored on an answer.
class ForumAiStatusService {
  const ForumAiStatusService();

  String statusText(ForumAnswerFeedback feedback) => switch (feedback.state) {
    'queued' || 'processing' => 'Checking the explanation…',
    'completed' => feedback.message,
    'fallback' => 'Your answer is saved. You can still add your reasoning.',
    _ => 'Feedback is temporarily unavailable. You can still edit your answer.',
  };
}
