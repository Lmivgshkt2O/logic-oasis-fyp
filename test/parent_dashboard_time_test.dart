import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_time.dart';

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

  test(
    'Malaysia time is a fixed UTC+8 offset independent of daylight saving',
    () {
      // Northern-summer and northern-winter instants map to the same +8 shift.
      final summer = malaysiaTimeOf(DateTime.utc(2026, 7, 2, 9, 19));
      final winter = malaysiaTimeOf(DateTime.utc(2026, 1, 2, 9, 19));
      expect([summer.hour, summer.minute], [17, 19]);
      expect([winter.hour, winter.minute], [17, 19]);
    },
  );

  test('Monday boundary splits the Malaysia week at Monday 00:00', () {
    // Monday 2026-08-10 00:00 MYT is 2026-08-09 16:00 UTC.
    final mondayMidnightUtc = DateTime.utc(2026, 8, 9, 16);

    expect(
      malaysiaWeekStartUtc(DateTime.utc(2026, 8, 9, 15, 59, 59)),
      DateTime.utc(2026, 8, 2, 16),
    );
    expect(malaysiaWeekStartUtc(mondayMidnightUtc), mondayMidnightUtc);
    expect(
      malaysiaWeekStartUtc(DateTime.utc(2026, 8, 10, 15)),
      mondayMidnightUtc,
    );
    expect(
      isSameMalaysiaWeek(mondayMidnightUtc, DateTime.utc(2026, 8, 12, 4)),
      isTrue,
    );
    expect(
      isSameMalaysiaWeek(
        mondayMidnightUtc,
        DateTime.utc(2026, 8, 16, 15, 59, 59),
      ),
      isTrue,
    );
    expect(
      isSameMalaysiaWeek(mondayMidnightUtc, DateTime.utc(2026, 8, 16, 16)),
      isFalse,
    );
  });

  test(
    '14-day freshness accepts the exact boundary and rejects older data',
    () {
      final now = DateTime.utc(2026, 8, 12, 4);
      final exactly14Days = DateTime.utc(2026, 7, 29, 4);
      final older = exactly14Days.subtract(const Duration(milliseconds: 1));
      final future = now.add(const Duration(hours: 1));

      expect(isFreshWithinDays(exactly14Days, now), isTrue);
      expect(isFreshWithinDays(older, now), isFalse);
      expect(isFreshWithinDays(future, now), isFalse);
    },
  );
}
