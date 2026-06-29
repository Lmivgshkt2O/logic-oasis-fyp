import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/quiz_attempt.dart';
import 'package:logic_oasis/shared/widgets/mastery_chip.dart';

class AttemptRow extends StatelessWidget {
  const AttemptRow({
    super.key,
    required this.attempt,
    this.isBahasaMelayu = false,
  });

  final QuizAttempt attempt;
  final bool isBahasaMelayu;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 42,
          height: 42,
          decoration: BoxDecoration(
            color: LogicOasisTheme.mint,
            borderRadius: BorderRadius.circular(8),
          ),
          child: const Icon(
            Icons.assignment_turned_in_outlined,
            color: LogicOasisTheme.leaf,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      attempt.topicTitle,
                      style: theme.textTheme.titleMedium,
                    ),
                  ),
                  MasteryChip(label: attempt.mastery),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                isBahasaMelayu
                    ? l10n.attemptSummary(
                        attempt.score,
                        attempt.correctCount,
                        attempt.totalQuestions,
                        attempt.earnedCrystals,
                      )
                    : l10n.attemptSummary(
                        attempt.score,
                        attempt.correctCount,
                        attempt.totalQuestions,
                        attempt.earnedCrystals,
                      ),
                style: theme.textTheme.bodyMedium,
              ),
              const SizedBox(height: 2),
              Text(
                _formatTime(attempt.createdAt, l10n),
                style: theme.textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      ],
    );
  }

  String _formatTime(DateTime value, AppLocalizations l10n) {
    final difference = DateTime.now().difference(value);
    if (difference.inMinutes < 1) {
      return l10n.justNow;
    }
    if (difference.inHours < 1) {
      return l10n.minutesAgo(difference.inMinutes);
    }
    if (difference.inDays < 1) {
      return l10n.hoursAgo(difference.inHours);
    }
    return l10n.daysAgo(difference.inDays);
  }
}
