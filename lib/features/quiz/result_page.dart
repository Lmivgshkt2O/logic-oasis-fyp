import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/quiz_reward.dart';
import 'package:logic_oasis/shared/widgets/recommendation_box.dart';
import 'package:logic_oasis/shared/widgets/section_card.dart';

class ResultPage extends StatelessWidget {
  const ResultPage({
    super.key,
    required this.correctCount,
    required this.totalQuestions,
    required this.topicArea,
    required this.isBahasaMelayu,
    required this.reward,
    required this.onBackToForge,
  });

  final int correctCount;
  final int totalQuestions;
  final String topicArea;
  final bool isBahasaMelayu;
  final QuizReward reward;
  final VoidCallback onBackToForge;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.quizResult)),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
          children: [
            Text(
              l10n.topicRestored(topicArea),
              style: theme.textTheme.headlineLarge,
            ),
            const SizedBox(height: 10),
            Text(
              l10n.quizCorrectSummary(correctCount, totalQuestions),
              style: theme.textTheme.bodyLarge,
            ),
            const SizedBox(height: 18),
            SectionCard(
              title: l10n.score,
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
                    label: l10n.crystals,
                    value: '+${reward.earnedCrystals}',
                    color: LogicOasisTheme.water,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _RewardTile(
                    icon: Icons.construction_outlined,
                    label: l10n.repairReady,
                    value: l10n.home,
                    color: LogicOasisTheme.clay,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            RecommendationBox(
              text:
                  l10n.masteryResultMessage(
                    isBahasaMelayu
                        ? _encouragementBm(reward.score)
                        : reward.encouragement,
                    isBahasaMelayu
                        ? _masteryBm(reward.previousMastery)
                        : reward.previousMastery,
                    isBahasaMelayu
                        ? _masteryBm(reward.newMastery)
                        : reward.newMastery,
                  ),
            ),
            const SizedBox(height: 22),
            FilledButton.icon(
              onPressed: onBackToForge,
              icon: const Icon(Icons.calculate_outlined),
              label: Text(l10n.backToForge),
            ),
          ],
        ),
      ),
    );
  }

  String _encouragementBm(int score) {
    if (score >= 80) {
      return 'Bagus. Topik ini semakin kukuh.';
    }
    if (score >= 50) {
      return 'Kemajuan yang baik. Sedikit lagi latihan boleh menguatkan topik ini.';
    }
    return 'Teruskan usaha. Oasis tetap berkembang apabila anda mencuba dan menyemak jawapan.';
  }

  String _masteryBm(String mastery) {
    return switch (mastery) {
      'Strong' => 'Kukuh',
      'Moderate' => 'Sederhana',
      'Weak' => 'Lemah',
      'New' => 'Baharu',
      'Locked' => 'Dikunci',
      _ => mastery,
    };
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
