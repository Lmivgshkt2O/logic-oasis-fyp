import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/quiz_attempt.dart';

class ParentDashboardSnapshot {
  const ParentDashboardSnapshot({
    required this.attempts,
    required this.masteryRecordCount,
    required this.aiDiagnoses,
  });

  final List<QuizAttempt> attempts;
  final int masteryRecordCount;
  final List<AiDiagnosis> aiDiagnoses;
}
