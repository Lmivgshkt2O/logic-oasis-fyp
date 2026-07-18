/// Bounded display context returned by the protected U9 callable.
///
/// It intentionally excludes parent-link audit fields, raw learning evidence,
/// model details, forum text, and protected projection contents.
class LinkedChildContext {
  const LinkedChildContext({
    required this.studentId,
    required this.displayName,
    required this.yearLevel,
  });

  final String studentId;
  final String displayName;
  final int yearLevel;

  factory LinkedChildContext.fromCallableData(Map<Object?, Object?> data) {
    final studentId = data['studentId'];
    final displayName = data['displayName'];
    final yearLevel = data['yearLevel'];
    if (studentId is! String || studentId.isEmpty || studentId.contains('/')) {
      throw const FormatException('Linked learner ID is invalid.');
    }
    if (displayName is! String || displayName.trim().isEmpty) {
      throw const FormatException('Linked learner display name is invalid.');
    }
    if (yearLevel is! int || yearLevel < 4 || yearLevel > 6) {
      throw const FormatException('Linked learner year level is invalid.');
    }
    return LinkedChildContext(
      studentId: studentId,
      displayName: displayName.trim(),
      yearLevel: yearLevel,
    );
  }
}
