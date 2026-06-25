import 'package:flutter/material.dart';
import 'package:logic_oasis/features/formula_forge/widgets/topic_card.dart';
import 'package:logic_oasis/features/quiz/quiz_page.dart';
import 'package:logic_oasis/features/quiz/result_page.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

class FormulaForgePage extends StatelessWidget {
  const FormulaForgePage({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 18),
      children: [
        Row(
          children: [
            Container(
              width: 68,
              height: 68,
              decoration: BoxDecoration(
                color: theme.colorScheme.primary.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(18),
              ),
              child: Icon(
                Icons.calculate_outlined,
                color: theme.colorScheme.primary,
                size: 34,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    state.t('Formula Forge', 'Latihan Formula'),
                    style: theme.textTheme.headlineLarge,
                  ),
                  const SizedBox(height: 5),
                  Text(
                    state.t(
                      'Choose a topic and practise calmly.',
                      'Pilih topik dan berlatih dengan tenang.',
                    ),
                    style: theme.textTheme.bodyLarge,
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),
        for (final topic in state.topics) ...[
          TopicCard(
            topic: topic,
            isBahasaMelayu: state.isBahasaMelayu,
            onStart: topic.questions.isEmpty
                ? null
                : () async {
                    final result = await Navigator.of(context).push<int>(
                      MaterialPageRoute(builder: (_) => QuizPage(topic: topic)),
                    );
                    if (result != null && context.mounted) {
                      final reward = state.saveQuizResult(
                        topicId: topic.id,
                        correctCount: result,
                        totalQuestions: topic.questions.length,
                      );
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => ResultPage(
                            correctCount: result,
                            totalQuestions: topic.questions.length,
                            topicArea: topic.area,
                            reward: reward,
                            onBackToForge: () {
                              Navigator.of(context).pop();
                              state.changeTab(1);
                            },
                          ),
                        ),
                      );
                    }
                  },
          ),
          const SizedBox(height: 13),
        ],
      ],
    );
  }
}
