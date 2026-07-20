import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_page.dart';

void main() {
  test('formats AI diagnosis createdAt in Malaysia time with AM PM', () {
    final createdAt = DateTime.utc(2026, 7, 2, 9, 19);

    expect(formatAiUpdatedAt(createdAt), '2/7/2026 5:19 PM');
  });

  test('keeps afternoon and midnight readable', () {
    expect(
      formatAiUpdatedAt(DateTime.utc(2026, 7, 2, 4, 5)),
      '2/7/2026 12:05 PM',
    );
    expect(
      formatAiUpdatedAt(DateTime.utc(2026, 7, 1, 16, 5)),
      '2/7/2026 12:05 AM',
    );
  });
}
