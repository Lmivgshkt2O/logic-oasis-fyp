import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/progress/widgets/topic_progress_row.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/attempt_row.dart';
import 'package:logic_oasis/shared/widgets/metric_card.dart';
import 'package:logic_oasis/shared/widgets/section_card.dart';

class ProgressPage extends StatelessWidget {
  const ProgressPage({super.key, required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    final insight = state.weakTopicInsight;

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      children: [
        Text(
          state.t('Student Progress', 'Kemajuan Murid'),
          style: theme.textTheme.headlineLarge,
        ),
        const SizedBox(height: 8),
        Text(
          state.t(
            'Track topic mastery before sending insights to parents.',
            'Pantau penguasaan topik sebelum menghantar pandangan kepada ibu bapa.',
          ),
          style: theme.textTheme.bodyLarge,
        ),
        const SizedBox(height: 18),
        Row(
          children: [
            Expanded(
              child: MetricCard(
                icon: Icons.assignment_turned_in_outlined,
                label: state.t('Quizzes', 'Kuiz'),
                value: '${state.completedQuizzes}',
                color: oasis.leaf,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: MetricCard(
                icon: Icons.scoreboard_outlined,
                label: state.t('Average', 'Purata'),
                value: '${state.averageScore}%',
                color: oasis.water,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: state.t('Topic mastery', 'Penguasaan topik'),
          icon: Icons.route_outlined,
          child: Column(
            children: [
              for (final topic in state.topics)
                Padding(
                  padding: const EdgeInsets.only(bottom: 14),
                  child: TopicProgressRow(
                    topic: topic,
                    isBahasaMelayu: state.isBahasaMelayu,
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: state.t('Recent attempts', 'Cubaan terkini'),
          icon: Icons.history_outlined,
          child: Column(
            children: [
              for (final attempt in state.recentAttempts) ...[
                AttemptRow(
                  attempt: attempt,
                  isBahasaMelayu: state.isBahasaMelayu,
                ),
                if (attempt != state.recentAttempts.last)
                  const Divider(height: 24),
              ],
            ],
          ),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: state.t('Weak-topic signal', 'Isyarat topik lemah'),
          icon: Icons.psychology_alt_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                state.t(
                  '${insight.topicTitle} needs focus',
                  '${insight.topicTitle} perlu fokus',
                ),
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 6),
              Text(insight.reason),
              const SizedBox(height: 8),
              Text(
                state.t(
                  'Mastery: ${insight.mastery} • Average: ${insight.averageScore}%',
                  'Penguasaan: ${insight.mastery} • Purata: ${insight.averageScore}%',
                ),
                style: theme.textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      ],
    );
  }
}
