import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:logic_oasis/shared/models/adaptive_assignment.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';

/// Reads only U8's approved safe projections. Raw AI jobs/runs are never read
/// by the client, even for processing or fallback states.
class AiStatusService {
  AiStatusService({FirebaseFirestore? firestore})
      : _firestore = firestore ?? FirebaseFirestore.instance;

  final FirebaseFirestore _firestore;

  Stream<AiDiagnosis?> watchAttempt(String attemptId) {
    if (attemptId.trim().isEmpty) return Stream<AiDiagnosis?>.value(null);
    return _firestore
        .collection('studentAiStatuses')
        .doc(attemptId)
        .snapshots()
        .asyncMap((status) async {
      final data = status.data();
      if (!status.exists || data == null) {
        return const AiDiagnosis(
          attemptId: '',
          studentId: '',
          sourceAttemptSequence: 0,
          analysisState: 'processing',
          displayCode: 'analysis_pending',
        );
      }
      AdaptiveAssignment? assignment;
      final studentId = data['studentId'];
      if (studentId is String && studentId.isNotEmpty) {
        final assignments = await _firestore
            .collection('adaptiveAssignments')
            .where('studentId', isEqualTo: studentId)
            .where('sourceAttemptId', isEqualTo: attemptId)
            .limit(1)
            .get();
        if (assignments.docs.isNotEmpty) {
          try {
            assignment = AdaptiveAssignment.fromFirestoreData(
              assignments.docs.first.id,
              assignments.docs.first.data(),
            );
          } on FormatException {
            assignment = null;
          }
        }
      }
      return AiDiagnosis.fromSafeProjection(
        status.id,
        data,
        assignment: assignment,
      );
    });
  }
}
