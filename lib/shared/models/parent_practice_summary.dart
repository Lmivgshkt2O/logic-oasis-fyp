import 'package:cloud_firestore/cloud_firestore.dart';

/// Fixed U14 schema version required by the strict parent Practice parser.
const String parentPracticeSummarySchemaVersion = 'u14-parent-practice-v1';

/// Fixed timezone of the server-owned weekly summary.
const String parentPracticeTimezone = 'Asia/Kuala_Lumpur';

/// Server-owned, parent-readable weekly practice projection.
///
/// The document holds only the current Malaysia week and one previous-week
/// total. It carries no attempt, session, question, response, score, answer,
/// bank, model, or forum identifiers. Malformed documents fail closed as
/// `FormatException` so a parent card can be unavailable instead of a false
/// zero.
class ParentPracticeSummary {
  const ParentPracticeSummary({
    required this.schemaVersion,
    required this.studentId,
    required this.timezone,
    required this.weekStart,
    required this.dailyCompletionCounts,
    required this.completedPracticeCount,
    required this.activeDayCount,
    this.previousWeekCompletedPracticeCount,
    this.lastPracticeAt,
    required this.updatedAt,
  }) : assert(dailyCompletionCounts.length == 7);

  final String schemaVersion;
  final String studentId;
  final String timezone;

  /// Server timestamp for Monday 00:00 in Asia/Kuala_Lumpur (UTC instant).
  final DateTime weekStart;

  /// Seven non-negative whole-number integers ordered Monday-Sunday.
  final List<int> dailyCompletionCounts;
  final int completedPracticeCount;
  final int activeDayCount;
  final int? previousWeekCompletedPracticeCount;
  final DateTime? lastPracticeAt;
  final DateTime updatedAt;

  factory ParentPracticeSummary.fromFirestore(
    String studentId,
    Map<String, dynamic> data,
  ) {
    final schemaVersion = data['schemaVersion'];
    if (schemaVersion != parentPracticeSummarySchemaVersion) {
      throw const FormatException(
        'Unsupported parent practice schema version.',
      );
    }
    final storedStudentId = data['studentId'];
    if (storedStudentId is! String ||
        storedStudentId.isEmpty ||
        storedStudentId != studentId) {
      throw const FormatException('Parent practice summary child mismatch.');
    }
    final timezone = data['timezone'];
    if (timezone != parentPracticeTimezone) {
      throw const FormatException('Parent practice summary timezone mismatch.');
    }
    final weekStart = _requiredTimestamp(data, 'weekStart');
    final dailyCounts = _dailyCounts(data['dailyCompletionCounts']);
    final completedTotal = _requiredWholeCount(data, 'completedPracticeCount');
    if (completedTotal != _sum(dailyCounts)) {
      throw const FormatException(
        'Parent practice summary total is inconsistent with day counts.',
      );
    }
    final activeDays = _requiredWholeCount(data, 'activeDayCount');
    if (activeDays != dailyCounts.where((value) => value > 0).length) {
      throw const FormatException(
        'Parent practice summary active days are inconsistent.',
      );
    }
    return ParentPracticeSummary(
      schemaVersion: schemaVersion as String,
      studentId: studentId,
      timezone: timezone as String,
      weekStart: weekStart,
      dailyCompletionCounts: dailyCounts,
      completedPracticeCount: completedTotal,
      activeDayCount: activeDays,
      previousWeekCompletedPracticeCount: _optionalWholeCount(
        data,
        'previousWeekCompletedPracticeCount',
      ),
      lastPracticeAt: _optionalTimestamp(data, 'lastPracticeAt'),
      updatedAt: _requiredTimestamp(data, 'updatedAt'),
    );
  }

  static List<int> _dailyCounts(Object? value) {
    if (value is! List || value.length != 7) {
      throw const FormatException('Parent practice summary must have 7 days.');
    }
    return List<int>.unmodifiable(
      value.map((item) => _wholeCount(item, 'daily completion count')),
    );
  }

  static int _requiredWholeCount(Map<String, dynamic> data, String field) {
    final value = data[field];
    if (value == null) {
      throw FormatException('Missing parent practice field: $field');
    }
    return _wholeCount(value, field);
  }

  static int? _optionalWholeCount(Map<String, dynamic> data, String field) {
    final value = data[field];
    if (value == null) return null;
    return _wholeCount(value, field);
  }

  static int _wholeCount(Object? value, String field) {
    if (value is num && value >= 0 && value == value.roundToDouble()) {
      return value.toInt();
    }
    throw FormatException('Invalid parent practice $field.');
  }

  static DateTime _requiredTimestamp(Map<String, dynamic> data, String field) {
    final value = data[field];
    if (value is Timestamp) return value.toDate().toUtc();
    throw FormatException('Missing or invalid parent practice $field.');
  }

  static DateTime? _optionalTimestamp(Map<String, dynamic> data, String field) {
    final value = data[field];
    if (value == null) return null;
    if (value is Timestamp) return value.toDate().toUtc();
    throw FormatException('Invalid parent practice $field.');
  }

  static int _sum(List<int> values) =>
      values.fold(0, (total, value) => total + value);
}
