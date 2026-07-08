import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/quiz_reward.dart';
import 'package:logic_oasis/shared/widgets/logic_oasis_figma_components.dart';
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
    this.backActionLabel,
  });

  final int correctCount;
  final int totalQuestions;
  final String topicArea;
  final bool isBahasaMelayu;
  final QuizReward reward;
  final VoidCallback onBackToForge;
  final String? backActionLabel;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final wrongCount = (totalQuestions - correctCount)
        .clamp(0, totalQuestions)
        .toInt();

    return Scaffold(
      appBar: AppBar(title: Text(l10n.quizResult)),
      body: LogicOasisScaffold(
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
          SectionCard(
            title: isBahasaMelayu ? 'Kesilapan' : 'Mistakes',
            icon: Icons.fact_check_outlined,
            child: Text(
              isBahasaMelayu
                  ? '$wrongCount perlu disemak'
                  : '$wrongCount to review',
              style: theme.textTheme.headlineMedium,
            ),
          ),
          const SizedBox(height: 14),
          RecommendationBox(
            text: l10n.masteryResultMessage(
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
          const SizedBox(height: 12),
          RecommendationBox(text: _nextAction(wrongCount)),
          const SizedBox(height: 22),
          FilledButton.icon(
            onPressed: onBackToForge,
            icon: const Icon(Icons.calculate_outlined),
            label: Text(backActionLabel ?? l10n.backToForge),
          ),
        ],
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

  String _nextAction(int wrongCount) {
    if (isBahasaMelayu) {
      if (reward.score >= 80 && wrongCount == 0) {
        return 'Tindakan seterusnya: Cuba topik lain atau bantu pulihkan kawasan di Laman.';
      }
      if (reward.score >= 80) {
        return 'Tindakan seterusnya: Semak $wrongCount kesilapan, kemudian cuba topik baharu.';
      }
      if (reward.score >= 50) {
        return 'Tindakan seterusnya: Semak kesilapan dan ulang satu latihan pendek untuk menguatkan topik ini.';
      }
      return 'Tindakan seterusnya: Ulang asas topik ini, kemudian cuba semula kuiz yang sama.';
    }

    if (reward.score >= 80 && wrongCount == 0) {
      return 'Next action: Try another topic or repair an area on Home.';
    }
    if (reward.score >= 80) {
      final mistakeLabel = wrongCount == 1 ? 'mistake' : 'mistakes';
      return 'Next action: Review $wrongCount $mistakeLabel, then try a new topic.';
    }
    if (reward.score >= 50) {
      return 'Next action: Review the mistakes and repeat one short practice to strengthen this topic.';
    }
    return 'Next action: Revisit the basics for this topic, then retry the same quiz.';
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

    return SoftCard(
      padding: const EdgeInsets.all(14),
      radius: 18,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 104),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color),
            const SizedBox(height: 20),
            FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text(value, style: theme.textTheme.headlineMedium),
            ),
            Text(
              label,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: theme.textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}
