import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/shared/models/quiz_reward.dart';
import 'package:logic_oasis/shared/widgets/recommendation_box.dart';
import 'package:logic_oasis/shared/widgets/section_card.dart';

class ResultPage extends StatelessWidget {
  const ResultPage({
    super.key,
    required this.correctCount,
    required this.totalQuestions,
    required this.topicArea,
    required this.reward,
    required this.onBackToForge,
  });

  final int correctCount;
  final int totalQuestions;
  final String topicArea;
  final QuizReward reward;
  final VoidCallback onBackToForge;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Quiz Result')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
          children: [
            Text('$topicArea restored', style: theme.textTheme.headlineLarge),
            const SizedBox(height: 10),
            Text(
              'You answered $correctCount of $totalQuestions correctly.',
              style: theme.textTheme.bodyLarge,
            ),
            const SizedBox(height: 18),
            SectionCard(
              title: 'Score',
              icon: Icons.emoji_events_outlined,
              child: Text(
                '${reward.score}%',
                style: theme.textTheme.headlineLarge,
              ),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: _RewardTile(
                    icon: Icons.diamond_outlined,
                    label: 'Crystals',
                    value: '+${reward.earnedCrystals}',
                    color: LogicOasisTheme.water,
                  ),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: _RewardTile(
                    icon: Icons.construction_outlined,
                    label: 'Repair Ready',
                    value: 'Home',
                    color: LogicOasisTheme.clay,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            RecommendationBox(
              text:
                  '${reward.encouragement} Mastery: ${reward.previousMastery} -> ${reward.newMastery}. Spend crystals on Home to choose what to repair.',
            ),
            const SizedBox(height: 22),
            FilledButton.icon(
              onPressed: onBackToForge,
              icon: const Icon(Icons.calculate_outlined),
              label: const Text('Back to Forge'),
            ),
          ],
        ),
      ),
    );
  }
}

class _RewardTile extends StatelessWidget {
  const _RewardTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color),
            const SizedBox(height: 10),
            Text(value, style: theme.textTheme.headlineMedium),
            Text(label, style: theme.textTheme.bodyMedium),
          ],
        ),
      ),
    );
  }
}
