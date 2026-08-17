/// Malaysia does not observe daylight saving time; the offset is a fixed
/// UTC+8, so every instant maps to the same wall-clock shift.
const Duration malaysiaUtcOffset = Duration(hours: 8);

/// The Malaysia wall-clock reading of [value] as a shifted DateTime.
///
/// Callers read the wall-clock fields (year, month, day, hour, ...); the
/// returned value carries the UTC flag from the source instant but represents
/// Malaysia time.
DateTime malaysiaTimeOf(DateTime value) {
  final utc = value.isUtc ? value : value.toUtc();
  return utc.add(malaysiaUtcOffset);
}

/// The UTC instant of Monday 00:00 in Asia/Kuala_Lumpur for the week that
/// contains [value]. The week starts on Monday in Malaysia time.
DateTime malaysiaWeekStartUtc(DateTime value) {
  final wall = malaysiaTimeOf(value);
  final mondayWallMidnight = DateTime.utc(
    wall.year,
    wall.month,
    wall.day - (wall.weekday - DateTime.monday),
  );
  return mondayWallMidnight.subtract(malaysiaUtcOffset);
}

/// Whether [a] and [b] fall in the same Monday-start Malaysia week.
bool isSameMalaysiaWeek(DateTime a, DateTime b) =>
    malaysiaWeekStartUtc(a) == malaysiaWeekStartUtc(b);

/// Whether [updatedAt] is no older than [maxDays] and not in the future.
bool isFreshWithinDays(DateTime updatedAt, DateTime now, {int maxDays = 14}) {
  if (updatedAt.isAfter(now)) return false;
  return now.difference(updatedAt) <= Duration(days: maxDays);
}

String formatAiUpdatedAt(DateTime value) {
  final malaysiaTime = malaysiaTimeOf(value);
  final hour = malaysiaTime.hour;
  final displayHour = hour == 0
      ? 12
      : hour > 12
      ? hour - 12
      : hour;
  final minute = malaysiaTime.minute.toString().padLeft(2, '0');
  final period = hour >= 12 ? 'PM' : 'AM';
  return '${malaysiaTime.day}/${malaysiaTime.month}/${malaysiaTime.year} '
      '$displayHour:$minute $period';
}
