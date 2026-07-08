import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/attempt_row.dart';
import 'package:logic_oasis/shared/widgets/logic_oasis_figma_components.dart';
import 'package:logic_oasis/shared/widgets/metric_card.dart';
import 'package:logic_oasis/shared/widgets/recommendation_box.dart';
import 'package:logic_oasis/shared/widgets/section_card.dart';

class ParentDashboardPage extends StatefulWidget {
  const ParentDashboardPage({super.key, required this.state});

  final AppState state;

  @override
  State<ParentDashboardPage> createState() => _ParentDashboardPageState();
}

class _ParentDashboardPageState extends State<ParentDashboardPage> {
  @override
  void initState() {
    super.initState();
    widget.state.loadParentDashboardFromFirebase();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.state,
      builder: (context, _) => _ParentDashboardContent(state: widget.state),
    );
  }
}

class _ParentDashboardContent extends StatelessWidget {
  const _ParentDashboardContent({required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final latestAttempt = state.latestAttempt;
    final insight = state.weakTopicInsight;
    final aiDiagnosis = state.recommendedAiDiagnosis;
    final story = _ParentLearningStory.fromState(state);

    return LogicOasisScaffold(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      children: [
        Text(
          l10n.parentDashboard,
          style: theme.textTheme.headlineLarge,
        ),
        const SizedBox(height: 8),
        Text(
          l10n.parentDashboardSummary(state.studentName),
          style: theme.textTheme.bodyLarge,
        ),
        if (state.isLoadingParentDashboard ||
            state.parentDashboardMessage != null) ...[
          const SizedBox(height: 14),
          _ParentDashboardStatusBanner(state: state),
        ],
        const SizedBox(height: 18),
        _ParentInsightSummary(
          story: story,
          focusLabel: state.t('Focus', 'Fokus'),
          meaningLabel: state.t('Meaning', 'Maksud'),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: l10n.overallRestoration,
          icon: Icons.eco_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              LinearProgressIndicator(value: state.restorationProgress),
              const SizedBox(height: 10),
              Text(
                l10n.oasisRestoredSummary(
                  (state.restorationProgress * 100).round(),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                state.t(
                  'Use this as a motivation signal: higher restoration means more consistent quiz effort and repair progress.',
                  'Gunakan ini sebagai isyarat motivasi: pemulihan lebih tinggi bermaksud usaha kuiz dan pembaikan lebih konsisten.',
                ),
                style: theme.textTheme.bodyMedium,
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: MetricCard(
                icon: Icons.trending_up,
                label: l10n.averageScore,
                value: '${state.averageScore}%',
                color: LogicOasisTheme.leaf,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: MetricCard(
                icon: Icons.history,
                label: l10n.latestQuiz,
                value: latestAttempt == null ? '-' : '${latestAttempt.score}%',
                color: LogicOasisTheme.clay,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: l10n.recentActivity,
          icon: Icons.history_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (state.recentAttempts.isEmpty)
                Text(
                  state.t(
                    'No quiz activity yet. Ask ${state.studentName} to complete one Formula Forge mission so the dashboard can form a clearer learning picture.',
                    'Belum ada aktiviti kuiz. Minta ${state.studentName} menyiapkan satu misi Formula Forge supaya papan pemuka dapat membentuk gambaran pembelajaran yang lebih jelas.',
                  ),
                )
              else
                for (final attempt in state.recentAttempts.take(3)) ...[
                  AttemptRow(
                    attempt: attempt,
                    isBahasaMelayu: state.isBahasaMelayu,
                  ),
                  if (attempt != state.recentAttempts.take(3).last)
                    const Divider(height: 24),
                ],
            ],
          ),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: l10n.predictionSummary,
          icon: Icons.lightbulb_outline,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l10n.weakTopic(insight.topicTitle),
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Text(insight.reason),
              if (aiDiagnosis != null) ...[
                const SizedBox(height: 12),
                _AiDiagnosisDetails(
                  masteryProbability: aiDiagnosis.bktMasteryProbability,
                  weaknessProbability: aiDiagnosis.weaknessProbability,
                  confidence: aiDiagnosis.confidence,
                  finalLabel: aiDiagnosis.finalMasteryLabel,
                  modelName: aiDiagnosis.modelName,
                  attemptsCount: aiDiagnosis.attemptsCount,
                  createdAt: aiDiagnosis.createdAt,
                  shapReasons: aiDiagnosis.explanationReasons,
                  isBahasaMelayu: state.isBahasaMelayu,
                ),
              ],
              const SizedBox(height: 12),
              RecommendationBox(
                text: l10n.suggestedAction(insight.recommendation),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: l10n.collaborationNote,
          icon: Icons.groups_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _ParentActionStep(
                icon: Icons.schedule_outlined,
                title: state.t('Tonight', 'Malam ini'),
                body: story.tonightAction,
              ),
              const SizedBox(height: 12),
              _ParentActionStep(
                icon: Icons.chat_bubble_outline,
                title: state.t('Ask gently', 'Tanya dengan lembut'),
                body: story.conversationPrompt,
              ),
              const SizedBox(height: 12),
              _ParentActionStep(
                icon: Icons.flag_outlined,
                title: state.t('This week', 'Minggu ini'),
                body: story.weekGoal,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ParentLearningStory {
  const _ParentLearningStory({
    required this.status,
    required this.statusDetail,
    required this.priority,
    required this.parentMeaning,
    required this.tonightAction,
    required this.conversationPrompt,
    required this.weekGoal,
    required this.statusColor,
    required this.statusIcon,
  });

  final String status;
  final String statusDetail;
  final String priority;
  final String parentMeaning;
  final String tonightAction;
  final String conversationPrompt;
  final String weekGoal;
  final Color statusColor;
  final IconData statusIcon;

  factory _ParentLearningStory.fromState(AppState state) {
    final insight = state.weakTopicInsight;
    final aiDiagnosis = state.recommendedAiDiagnosis;
    final average = state.averageScore;
    final trend = _trendText(state);
    final hasAttempts = state.currentYearAttempts.isNotEmpty;

    if (aiDiagnosis != null) {
      final weaknessPercent = (aiDiagnosis.weaknessProbability * 100).round();
      final masteryPercent = (aiDiagnosis.bktMasteryProbability * 100).round();
      final confidencePercent = (aiDiagnosis.confidence * 100).round();

      return _ParentLearningStory(
        status: state.t('AI focus found', 'Fokus AI ditemui'),
        statusDetail: state.t(
          'Grey Box AI marks ${insight.topicTitle} as ${aiDiagnosis.finalMasteryLabel}: $weaknessPercent% weakness risk, $masteryPercent% BKT mastery, $confidencePercent% confidence.',
          'AI Grey Box menanda ${insight.topicTitle} sebagai ${aiDiagnosis.finalMasteryLabel}: risiko kelemahan $weaknessPercent%, penguasaan BKT $masteryPercent%, keyakinan $confidencePercent%.',
        ),
        priority: state.t(
          'Main focus: ${insight.topicTitle}.',
          'Fokus utama: ${insight.topicTitle}.',
        ),
        parentMeaning: state.t(
          'For FYP1, this combines seeded/offline AI evidence with quiz-history fallback, so the recommendation remains explainable during the demo.',
          'Untuk FYP1, ini menggabungkan bukti AI berbenih/luar talian dengan sandaran sejarah kuiz supaya cadangan kekal boleh diterangkan semasa demo.',
        ),
        tonightAction: aiDiagnosis.recommendedAction,
        conversationPrompt: state.t(
          'Which part of ${insight.topicTitle} should we practise slowly together?',
          'Bahagian mana dalam ${insight.topicTitle} patut kita latih perlahan-lahan bersama?',
        ),
        weekGoal: state.t(
          'Complete 2 focused attempts and compare the next AI update with this one.',
          'Lengkapkan 2 cubaan berfokus dan bandingkan kemas kini AI seterusnya dengan yang ini.',
        ),
        statusColor: LogicOasisTheme.water,
        statusIcon: Icons.psychology_alt_outlined,
      );
    }

    if (!hasAttempts) {
      return _ParentLearningStory(
        status: state.t('Getting started', 'Mula membina rentak'),
        statusDetail: state.t(
          'The dashboard needs at least one completed quiz before it can identify a reliable pattern.',
          'Papan pemuka memerlukan sekurang-kurangnya satu kuiz lengkap sebelum corak pembelajaran yang boleh dipercayai dapat dikenal pasti.',
        ),
        priority: state.t(
          'First mission: complete one Year ${state.yearLevel} quiz.',
          'Misi pertama: lengkapkan satu kuiz Tahun ${state.yearLevel}.',
        ),
        parentMeaning: state.t(
          'At this stage, focus on helping ${state.studentName} begin without pressure.',
          'Pada tahap ini, bantu ${state.studentName} bermula tanpa tekanan.',
        ),
        tonightAction: state.t(
          'Sit nearby for 10 minutes and let ${state.studentName} try one short mission.',
          'Duduk berdekatan selama 10 minit dan biarkan ${state.studentName} mencuba satu misi pendek.',
        ),
        conversationPrompt: state.t(
          'Which question felt easiest, and which one should we look at together?',
          'Soalan mana yang paling mudah, dan soalan mana yang patut kita lihat bersama?',
        ),
        weekGoal: state.t(
          'Complete 2 short quiz attempts so the weak-topic insight becomes clearer.',
          'Lengkapkan 2 cubaan kuiz pendek supaya insight topik lemah menjadi lebih jelas.',
        ),
        statusColor: LogicOasisTheme.water,
        statusIcon: Icons.explore_outlined,
      );
    }

    if (average >= 80) {
      return _ParentLearningStory(
        status: state.t('On track', 'Berada di landasan baik'),
        statusDetail: state.t(
          'Average score is strong at $average%. $trend',
          'Purata markah kukuh pada $average%. $trend',
        ),
        priority: state.t(
          'Keep momentum on ${insight.topicTitle}.',
          'Kekalkan momentum untuk ${insight.topicTitle}.',
        ),
        parentMeaning: state.t(
          '${state.studentName} is showing good control. The best support now is consistency, not extra pressure.',
          '${state.studentName} menunjukkan kawalan yang baik. Sokongan terbaik sekarang ialah konsistensi, bukan tekanan tambahan.',
        ),
        tonightAction: state.t(
          'Let ${state.studentName} explain one solved question in their own words.',
          'Minta ${state.studentName} menerangkan satu soalan yang telah diselesaikan dengan ayat sendiri.',
        ),
        conversationPrompt: state.t(
          'What method helped you most today?',
          'Kaedah mana yang paling membantu hari ini?',
        ),
        weekGoal: state.t(
          'Complete one revision attempt and maintain 80% or above.',
          'Lengkapkan satu cubaan ulang kaji dan kekalkan 80% atau lebih.',
        ),
        statusColor: LogicOasisTheme.leaf,
        statusIcon: Icons.check_circle_outline,
      );
    }

    if (average >= 50) {
      return _ParentLearningStory(
        status: state.t('Needs steady practice', 'Perlu latihan konsisten'),
        statusDetail: state.t(
          'Average score is $average%. $trend',
          'Purata markah ialah $average%. $trend',
        ),
        priority: state.t(
          'Main focus: ${insight.topicTitle}.',
          'Fokus utama: ${insight.topicTitle}.',
        ),
        parentMeaning: state.t(
          '${state.studentName} understands some parts but may still be inconsistent. Short review works better than long drilling.',
          '${state.studentName} memahami sebahagian konsep tetapi mungkin belum konsisten. Ulang kaji pendek lebih sesuai daripada latihan terlalu panjang.',
        ),
        tonightAction: state.t(
          'Review 2 wrong answers together, then stop while the session still feels manageable.',
          'Semak 2 jawapan salah bersama-sama, kemudian berhenti sementara sesi masih terasa terkawal.',
        ),
        conversationPrompt: state.t(
          'Where did the question become confusing?',
          'Di bahagian mana soalan mula mengelirukan?',
        ),
        weekGoal: state.t(
          'Do 2 focused attempts on ${insight.topicTitle} and aim for a small score increase.',
          'Buat 2 cubaan berfokus pada ${insight.topicTitle} dan sasarkan peningkatan markah kecil.',
        ),
        statusColor: LogicOasisTheme.clay,
        statusIcon: Icons.trending_up,
      );
    }

    return _ParentLearningStory(
      status: state.t('Needs guided support', 'Perlu bimbingan rapat'),
      statusDetail: state.t(
        'Average score is $average%. $trend',
        'Purata markah ialah $average%. $trend',
      ),
      priority: state.t(
        'Start with ${insight.topicTitle}; it is currently the clearest learning gap.',
        'Mulakan dengan ${insight.topicTitle}; ini jurang pembelajaran paling jelas buat masa ini.',
      ),
      parentMeaning: state.t(
        '${state.studentName} may need the concept broken into smaller steps. Avoid treating the score as failure.',
        '${state.studentName} mungkin perlu konsep dipecahkan kepada langkah lebih kecil. Elakkan melihat markah sebagai kegagalan.',
      ),
      tonightAction: state.t(
        'Choose one easy example first, solve it together, then let ${state.studentName} try one similar question.',
        'Pilih satu contoh mudah dahulu, selesaikan bersama, kemudian biarkan ${state.studentName} cuba satu soalan yang serupa.',
      ),
      conversationPrompt: state.t(
        'What part should we practise slowly together?',
        'Bahagian mana yang patut kita latih perlahan-lahan bersama?',
      ),
      weekGoal: state.t(
        'Build confidence with 3 short practices, even if the first scores are low.',
        'Bina keyakinan dengan 3 latihan pendek, walaupun markah awal masih rendah.',
      ),
      statusColor: const Color(0xFFC45B45),
      statusIcon: Icons.support_outlined,
    );
  }

  static String _trendText(AppState state) {
    final attempts = state.recentAttempts;
    if (attempts.length < 2) {
      return state.t(
        'More attempts are needed to confirm the trend.',
        'Lebih banyak cubaan diperlukan untuk mengesahkan trend.',
      );
    }

    final latest = attempts[0].score;
    final previous = attempts[1].score;
    if (latest >= previous + 5) {
      return state.t(
        'Recent performance is improving.',
        'Prestasi terkini sedang meningkat.',
      );
    }
    if (latest <= previous - 5) {
      return state.t(
        'Recent performance has dropped, so gentle review is useful.',
        'Prestasi terkini menurun, jadi ulang kaji secara lembut adalah berguna.',
      );
    }
    return state.t(
      'Recent performance is stable.',
      'Prestasi terkini stabil.',
    );
  }
}

class _ParentInsightSummary extends StatelessWidget {
  const _ParentInsightSummary({
    required this.story,
    required this.focusLabel,
    required this.meaningLabel,
  });

  final _ParentLearningStory story;
  final String focusLabel;
  final String meaningLabel;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SoftCard(
      padding: const EdgeInsets.all(16),
      color: Color.alphaBlend(
        story.statusColor.withValues(alpha: 0.09),
        LogicOasisTheme.cream,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(story.statusIcon, color: story.statusColor, size: 26),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(story.status, style: theme.textTheme.titleLarge),
                    const SizedBox(height: 4),
                    Text(story.statusDetail),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          _InsightLine(
            icon: Icons.center_focus_strong_outlined,
            label: focusLabel,
            text: story.priority,
          ),
          const SizedBox(height: 10),
          _InsightLine(
            icon: Icons.psychology_alt_outlined,
            label: meaningLabel,
            text: story.parentMeaning,
          ),
        ],
      ),
    );
  }
}

class _InsightLine extends StatelessWidget {
  const _InsightLine({
    required this.icon,
    required this.label,
    required this.text,
  });

  final IconData icon;
  final String label;
  final String text;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 18, color: LogicOasisTheme.deepLeaf),
        const SizedBox(width: 8),
        Expanded(
          child: RichText(
            text: TextSpan(
              style: theme.textTheme.bodyMedium,
              children: [
                TextSpan(
                  text: '$label: ',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: LogicOasisTheme.ink,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                TextSpan(text: text),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _ParentActionStep extends StatelessWidget {
  const _ParentActionStep({
    required this.icon,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: LogicOasisTheme.leaf, size: 21),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: theme.textTheme.titleMedium),
              const SizedBox(height: 3),
              Text(body),
            ],
          ),
        ),
      ],
    );
  }
}

class _AiDiagnosisDetails extends StatelessWidget {
  const _AiDiagnosisDetails({
    required this.masteryProbability,
    required this.weaknessProbability,
    required this.confidence,
    required this.finalLabel,
    required this.modelName,
    required this.attemptsCount,
    required this.createdAt,
    required this.shapReasons,
    required this.isBahasaMelayu,
  });

  final double masteryProbability;
  final double weaknessProbability;
  final double confidence;
  final String finalLabel;
  final String modelName;
  final int attemptsCount;
  final DateTime createdAt;
  final List<String> shapReasons;
  final bool isBahasaMelayu;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final masteryText = (masteryProbability * 100).round();
    final weaknessText = (weaknessProbability * 100).round();
    final confidenceText = (confidence * 100).round();

    return SoftCard(
      padding: const EdgeInsets.all(12),
      color: LogicOasisTheme.mint,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.greyBoxAiResult,
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            isBahasaMelayu
                ? 'Bukti AI FYP1: $modelName, ${attemptsCount.clamp(0, 999)} rekod cubaan.'
                : 'FYP1 AI evidence: $modelName, ${attemptsCount.clamp(0, 999)} attempt records.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: LogicOasisTheme.ink,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            l10n.aiResultSummary(
              finalLabel,
              masteryText,
              weaknessText,
              confidenceText,
            ),
            style: theme.textTheme.bodyMedium,
          ),
          if (createdAt.millisecondsSinceEpoch > 0) ...[
            const SizedBox(height: 6),
            Text(
              isBahasaMelayu
                  ? 'Dikemas kini: ${formatAiUpdatedAt(createdAt)}'
                  : 'Updated: ${formatAiUpdatedAt(createdAt)}',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: LogicOasisTheme.ink,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
          if (shapReasons.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              l10n.shapReasons(shapReasons.take(3).join(', ')),
              style: theme.textTheme.bodyMedium,
            ),
          ],
          const SizedBox(height: 8),
          Text(
            isBahasaMelayu
                ? 'Jika rekod AI tiada, papan pemuka menggunakan logik topik lemah berdasarkan markah kuiz.'
                : 'If AI records are unavailable, the dashboard falls back to weak-topic logic from quiz scores.',
            style: theme.textTheme.bodySmall?.copyWith(
              color: LogicOasisTheme.deepLeaf,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

String formatAiUpdatedAt(DateTime value) {
  final malaysiaTime = _malaysiaTime(value);
  final hour = malaysiaTime.hour;
  final displayHour = hour == 0 ? 12 : hour > 12 ? hour - 12 : hour;
  final minute = malaysiaTime.minute.toString().padLeft(2, '0');
  final period = hour >= 12 ? 'PM' : 'AM';
  return '${malaysiaTime.day}/${malaysiaTime.month}/${malaysiaTime.year} '
      '$displayHour:$minute $period';
}

DateTime _malaysiaTime(DateTime value) {
  if (value.isUtc) {
    return value.add(const Duration(hours: 8));
  }
  return value.toUtc().add(const Duration(hours: 8));
}

class _ParentDashboardStatusBanner extends StatelessWidget {
  const _ParentDashboardStatusBanner({required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final isSuccess = state.loadedParentDashboardFromFirebase;
    final message = state.isLoadingParentDashboard
        ? l10n.loadingParentDashboard
        : state.parentDashboardMessage ?? '';

    return SoftCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      color: isSuccess ? LogicOasisTheme.mint : LogicOasisTheme.sand,
      child: Row(
        children: [
          SizedBox(
            width: 20,
            height: 20,
            child: state.isLoadingParentDashboard
                ? const CircularProgressIndicator(strokeWidth: 2.4)
                : Icon(
                    isSuccess
                        ? Icons.cloud_done_outlined
                        : Icons.cloud_off_outlined,
                    size: 20,
                    color: isSuccess
                        ? const Color(0xFF4F8F72)
                        : const Color(0xFF9A6514),
                  ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: const Color(0xFF33433D),
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
