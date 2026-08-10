import 'package:logic_oasis/shared/models/forum_answer.dart';

/// Presentation-only language for the safe feedback state stored on an answer.
class ForumAiStatusService {
  const ForumAiStatusService();

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
  ) => switch (feedback.label) {
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
