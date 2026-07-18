import 'package:logic_oasis/shared/models/adaptive_assignment.dart';

/// Presentation-safe helper for assignments written later by the U8 backend.
class AdaptiveAssignmentService {
  const AdaptiveAssignmentService();

  AdaptiveAssignment? parseLatest(
    String id,
    Map<Object?, Object?>? data,
  ) {
    if (data == null) return null;
    try {
      return AdaptiveAssignment.fromFirestoreData(id, data);
    } on FormatException {
      return null;
    }
  }

  String studentPracticeState(AdaptiveAssignment assignment) {
    switch (assignment.difficulty.name) {
      case 'easy':
        return 'Building';
      case 'moderate':
        return 'Practising';
      case 'hard':
        return 'Ready for a Challenge';
      default:
        return 'Practising';
    }
  }
}
