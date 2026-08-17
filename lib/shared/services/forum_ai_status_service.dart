import 'package:logic_oasis/shared/models/forum_answer.dart';

/// Presentation-only language for the safe feedback state stored on an answer.
class ForumAiStatusService {
  const ForumAiStatusService();

  /// Allow-listed public advisory badge text. Returns null when the answer
  /// carries no public AI decision (the neutral state).
  String? publicBadgeLabel(
    String publicState, {
    bool isBahasaMelayu = false,
  }) => switch (publicState) {
    'verified' => isBahasaMelayu ? 'AI-disahkan' : 'AI-verified',
    'may_be_irrelevant' =>
      isBahasaMelayu ? 'Mungkin tidak berkaitan' : 'May be irrelevant',
    _ => null,
  };

  /// Accessible explanatory copy for the public advisory badge.
  String? publicBadgeExplanation(
    String publicState, {
    bool isBahasaMelayu = false,
  }) => switch (publicState) {
    'verified' => isBahasaMelayu
        ? 'Jawapan ini lulus semakan automatik sistem (nasihat sahaja).'
        : "This answer passed the system's automated checks (advisory only).",
    'may_be_irrelevant' => isBahasaMelayu
        ? 'Jawapan ini mungkin tidak menjawab soalan secara langsung.'
        : 'This answer may not directly address the question.',
    _ => null,
  };

  String statusText(
    ForumAnswerFeedback feedback, {
    bool isBahasaMelayu = false,
  }) => switch (feedback.state) {
    'pending' || 'queued' || 'processing' =>
      isBahasaMelayu
          ? 'Sedang menyemak penerangan…'
          : 'Checking the explanation…',
    'completed' => _completedText(feedback, isBahasaMelayu),
    'fallback' =>
      isBahasaMelayu
          ? 'Jawapan anda telah disimpan. Anda masih boleh menambah penerangan.'
          : 'Your answer is saved. You can still add your reasoning.',
    _ =>
      isBahasaMelayu
          ? 'Maklum balas tidak tersedia buat sementara waktu. Anda masih boleh mengedit jawapan.'
          : 'Feedback is temporarily unavailable. You can still edit your answer.',
  };

  String _completedText(
    ForumAnswerFeedback feedback,
    bool isBahasaMelayu,
  ) {
    if (feedback.correctness == 'incorrect') {
      return isBahasaMelayu
          ? 'Jawapan akhir anda tidak sepadan dengan kunci jawapan. Semak langkah anda dan edit jawapan jika perlu.'
          : 'Your selected final answer does not match the worked answer key. Check the steps again and edit your answer if you wish.';
    }
    if (feedback.relevance == 'irrelevant') {
      return isBahasaMelayu
          ? 'Penerangan ini mungkin tidak menjawab soalan secara langsung. Cuba terangkan cara anda menyelesaikan soalan ini.'
          : 'This explanation may not address the question directly. Try explaining how you worked out this question.';
    }
    if (feedback.reasoning == 'needs_reasoning') {
      return isBahasaMelayu
          ? 'Sila tambah langkah atau sebab matematik supaya rakan dapat belajar daripada jawapan anda.'
          : 'Please add the steps or mathematical reason behind your answer so a peer can learn from it.';
    }
    if (feedback.label == 'verified') {
      return isBahasaMelayu
          ? 'Jawapan akhir dan penerangan anda lulus semakan automatik sistem (nasihat sahaja).'
          : "Your final answer and explanation passed the system's automated checks (advisory only).";
    }
    return switch (feedback.label) {
    'sufficient_reasoning' =>
      isBahasaMelayu
          ? 'Terima kasih kerana menerangkan kaedah anda. Rakan anda kini boleh mengikuti penaakulan tersebut.'
          : 'Thanks for explaining your method. Your peer can now follow the reasoning.',
    'needs_reasoning' =>
      isBahasaMelayu
          ? 'Sila tambah langkah atau sebab matematik supaya rakan dapat belajar daripada jawapan anda.'
          : 'Please add the steps or mathematical reason behind your answer so a peer can learn from it.',
    _ =>
      isBahasaMelayu
          ? 'Jawapan anda telah disimpan. Anda boleh menambah cara anda mendapat jawapan tersebut.'
          : feedback.message,
    };
  }
}
