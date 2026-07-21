import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/quiz_reward.dart';
import 'package:logic_oasis/shared/services/ai_status_service.dart';
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
    this.reward,
    required this.onBackToForge,
    this.backActionLabel,
    this.aiDiagnosis,
    this.attemptId,
  });

  final int correctCount;
  final int totalQuestions;
  final String topicArea;
  final bool isBahasaMelayu;
  final QuizReward? reward;
  final VoidCallback onBackToForge;
  final String? backActionLabel;
  final AiDiagnosis? aiDiagnosis;
  final String? attemptId;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final score =
        reward?.score ?? ((correctCount / totalQuestions) * 100).round();
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
            child: Text('$score%', style: theme.textTheme.headlineLarge),
          ),
          if (reward != null) ...[
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: _RewardTile(
                    icon: Icons.diamond_outlined,
                    label: l10n.crystals,
                    value: '+${reward!.earnedCrystals}',
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
          ],
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
            text: reward == null
                ? (isBahasaMelayu
                      ? 'Markah ini telah disahkan oleh pelayan dan kemajuan anda sedang dikemas kini.'
                      : 'This score was confirmed by the server and your learning progress is being updated.')
                : l10n.masteryResultMessage(
                    isBahasaMelayu
                        ? _encouragementBm(reward!.score)
                        : reward!.encouragement,
                    isBahasaMelayu
                        ? _masteryBm(reward!.previousMastery)
                        : reward!.previousMastery,
                    isBahasaMelayu
                        ? _masteryBm(reward!.newMastery)
                        : reward!.newMastery,
                  ),
          ),
          const SizedBox(height: 12),
          RecommendationBox(text: _nextAction(wrongCount, score)),
          if (aiDiagnosis != null) ...[
            const SizedBox(height: 12),
            AiAnalysisStatusCard(
              diagnosis: aiDiagnosis!,
              isBahasaMelayu: isBahasaMelayu,
            ),
          ],
          if (attemptId != null && attemptId!.isNotEmpty) ...[
            const SizedBox(height: 12),
            _AttemptAnalysisStatus(
              attemptId: attemptId!,
              isBahasaMelayu: isBahasaMelayu,
            ),
          ],
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

  String _nextAction(int wrongCount, int score) {
    if (isBahasaMelayu) {
      if (score >= 80 && wrongCount == 0) {
        return 'Tindakan seterusnya: Cuba topik lain atau bantu pulihkan kawasan di Laman.';
      }
      if (score >= 80) {
        return 'Tindakan seterusnya: Semak $wrongCount kesilapan, kemudian cuba topik baharu.';
      }
      if (score >= 50) {
        return 'Tindakan seterusnya: Semak kesilapan dan ulang satu latihan pendek untuk menguatkan topik ini.';
      }
      return 'Tindakan seterusnya: Ulang asas topik ini, kemudian cuba semula kuiz yang sama.';
    }

    if (score >= 80 && wrongCount == 0) {
      return 'Next action: Try another topic or repair an area on Home.';
    }
    if (score >= 80) {
      final mistakeLabel = wrongCount == 1 ? 'mistake' : 'mistakes';
      return 'Next action: Review $wrongCount $mistakeLabel, then try a new topic.';
    }
    if (score >= 50) {
      return 'Next action: Review the mistakes and repeat one short practice to strengthen this topic.';
    }
    return 'Next action: Revisit the basics for this topic, then retry the same quiz.';
  }
}

class _AttemptAnalysisStatus extends StatefulWidget {
  const _AttemptAnalysisStatus({
    required this.attemptId,
    required this.isBahasaMelayu,
  });

  final String attemptId;
  final bool isBahasaMelayu;

  @override
  State<_AttemptAnalysisStatus> createState() => _AttemptAnalysisStatusState();
}

class _AttemptAnalysisStatusState extends State<_AttemptAnalysisStatus> {
  late final Stream<AiDiagnosis?> _diagnosisStream;

  @override
  void initState() {
    super.initState();
    _diagnosisStream = AiStatusService().watchAttempt(widget.attemptId);
  }

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<AiDiagnosis?>(
      stream: _diagnosisStream,
      builder: (context, snapshot) {
        final diagnosis = snapshot.data;
        if (diagnosis == null) {
          return RecommendationBox(
            text: widget.isBahasaMelayu
                ? 'Markah anda disimpan. Analisis pembelajaran sedang bermula…'
                : 'Your score is saved. Learning analysis is starting…',
          );
        }
        return AiAnalysisStatusCard(
          diagnosis: diagnosis,
          isBahasaMelayu: widget.isBahasaMelayu,
        );
      },
    );
  }
}

/// A small safe projection card shared by immediate quiz results and future
/// result screens. It must receive only [AiDiagnosis.fromSafeProjection].
class AiAnalysisStatusCard extends StatelessWidget {
  const AiAnalysisStatusCard({
    super.key,
    required this.diagnosis,
    required this.isBahasaMelayu,
  });

  final AiDiagnosis diagnosis;
  final bool isBahasaMelayu;

  @override
  Widget build(BuildContext context) {
    final isReady = diagnosis.isCompleted || diagnosis.isFallback;
    final title = isBahasaMelayu
        ? (isReady ? 'Langkah latihan seterusnya' : 'Analisis pembelajaran')
        : (isReady ? 'Next practice step' : 'Learning analysis');
    final status = isBahasaMelayu
        ? switch (diagnosis.analysisState) {
            'completed' => 'Latihan seterusnya sudah sedia.',
            'fallback' => 'Cadangan latihan sedia menggunakan kemajuan kuiz.',
            'failed' =>
              'Markah anda disimpan. Cadangan akan tersedia kemudian.',
            _ => 'Markah anda disimpan. Sedang menyediakan latihan seterusnya…',
          }
        : diagnosis.childFacingStatus;
    final evidence = diagnosis.evidenceLevel == 'preliminary'
        ? (isBahasaMelayu
              ? 'Bukti awal — teruskan latihan ringkas.'
              : 'Preliminary evidence — keep practising in short steps.')
        : null;
    return SectionCard(
      title: title,
      icon: isReady ? Icons.route_outlined : Icons.hourglass_top_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(status),
          if (diagnosis.supportingReason != null) ...[
            const SizedBox(height: 8),
            Text(
              diagnosis.supportingReason!,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w700),
            ),
          ],
          if (evidence != null) ...[
            const SizedBox(height: 8),
            Text(evidence, style: Theme.of(context).textTheme.bodySmall),
          ],
        ],
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
