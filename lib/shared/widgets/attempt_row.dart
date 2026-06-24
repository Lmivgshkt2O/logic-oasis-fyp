import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/shared/models/quiz_attempt.dart';
import 'package:logic_oasis/shared/widgets/mastery_chip.dart';

class AttemptRow extends StatelessWidget {
  const AttemptRow({super.key, required this.attempt});

  final QuizAttempt attempt;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

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
                '${attempt.score}% score - ${attempt.correctCount}/${attempt.totalQuestions} correct - +${attempt.earnedCrystals} crystals',
                style: theme.textTheme.bodyMedium,
              ),
              const SizedBox(height: 2),
              Text(
                _formatTime(attempt.createdAt),
                style: theme.textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      ],
    );
  }

  String _formatTime(DateTime value) {
    final difference = DateTime.now().difference(value);
    if (difference.inMinutes < 1) return 'Just now';
    if (difference.inHours < 1) return '${difference.inMinutes} min ago';
    if (difference.inDays < 1) return '${difference.inHours} hr ago';
    return '${difference.inDays} day ago';
  }
}
