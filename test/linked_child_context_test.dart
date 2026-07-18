import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/models/linked_child_context.dart';

void main() {
  test('accepts the bounded callable child context', () {
    final child = LinkedChildContext.fromCallableData(const {
      'studentId': 'student_a',
      'displayName': 'Aiman',
      'yearLevel': 4,
    });

    expect(child.studentId, 'student_a');
    expect(child.displayName, 'Aiman');
    expect(child.yearLevel, 4);
  });

  test('rejects malformed linked-child context', () {
    expect(
      () => LinkedChildContext.fromCallableData(const {
        'studentId': '',
        'yearLevel': 4,
      }),
      throwsFormatException,
    );
  });
}
