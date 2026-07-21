import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/ai_diagnosis.dart';
import 'package:logic_oasis/shared/models/linked_child_context.dart';
import 'package:logic_oasis/shared/models/parent_dashboard_snapshot.dart';
import 'package:logic_oasis/shared/repositories/learning_repository.dart';
import 'package:logic_oasis/shared/services/parent_link_context_service.dart';
import 'package:logic_oasis/shared/services/parent_firebase_session.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/logic_oasis_figma_components.dart';
import 'package:logic_oasis/shared/widgets/metric_card.dart';
import 'package:logic_oasis/shared/widgets/recommendation_box.dart';
import 'package:logic_oasis/shared/widgets/section_card.dart';

typedef ParentDashboardLoader =
    Future<ParentDashboardSnapshot> Function(LinkedChildContext child);

class ParentDashboardPage extends StatefulWidget {
  const ParentDashboardPage({
    super.key,
    required this.state,
    this.linkedChildrenGateway,
    this.dashboardLoader,
  });

  final AppState state;
  final ParentLinkedChildrenGateway? linkedChildrenGateway;
  final ParentDashboardLoader? dashboardLoader;

  @override
  State<ParentDashboardPage> createState() => _ParentDashboardPageState();
}

class _ParentDashboardPageState extends State<ParentDashboardPage> {
  late final ParentLinkedChildrenGateway _linkedChildrenGateway;
  List<LinkedChildContext> _children = const [];
  LinkedChildContext? _selectedChild;
  ParentDashboardSnapshot? _snapshot;
  bool _isLoading = true;
  String? _message;

  @override
  void initState() {
    super.initState();
    _linkedChildrenGateway =
        widget.linkedChildrenGateway ?? ParentLinkedChildrenService();
    _loadLinkedChildren();
  }

  Future<void> _loadLinkedChildren() async {
    setState(() {
      _isLoading = true;
      _message = null;
    });
    try {
      final children = await _linkedChildrenGateway.loadLinkedChildren();
      if (!mounted) return;
      setState(() {
        _children = children;
        _selectedChild = children.isEmpty ? null : children.first;
      });
      if (_selectedChild != null) {
        await _loadSelectedChild();
      } else if (mounted) {
        setState(() {
          _isLoading = false;
          _message = 'No active linked learner is available for this account.';
        });
      }
    } on ParentLinkContextException catch (error) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _message = error.message;
      });
    }
  }

  Future<void> _loadSelectedChild() async {
    final child = _selectedChild;
    if (child == null) return;
    setState(() {
      _isLoading = true;
      _message = null;
    });
    try {
      final loader = await _dashboardLoader();
      final snapshot = await loader(child);
      if (!mounted || child.studentId != _selectedChild?.studentId) return;
      setState(() {
        _snapshot = snapshot;
        _isLoading = false;
        _message = null;
      });
    } catch (_) {
      if (!mounted || child.studentId != _selectedChild?.studentId) return;
      setState(() {
        _isLoading = false;
        _message = 'Safe learner updates are temporarily unavailable.';
      });
    }
  }

  Future<ParentDashboardLoader> _dashboardLoader() async {
    final provided = widget.dashboardLoader;
    if (provided != null) return provided;
    // Use the named parent Firebase app so Rules evaluate the parent identity,
    // while the student stays signed in through the default app.
    final repository = LearningRepository(
      firestore: await ParentFirebaseSession.firestore(),
    );
    return (LinkedChildContext selectedChild) =>
        repository.fetchParentDashboardSnapshot(
          studentId: selectedChild.studentId,
          yearLevel: selectedChild.yearLevel,
          topics: widget.state.topics,
        );
  }

  void _selectChild(LinkedChildContext? child) {
    if (child == null || child.studentId == _selectedChild?.studentId) return;
    setState(() {
      _selectedChild = child;
      _snapshot = null;
    });
    _loadSelectedChild();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.state,
      builder: (context, _) => _ParentDashboardContent(
        state: widget.state,
        children: _children,
        selectedChild: _selectedChild,
        snapshot: _snapshot,
        isLoading: _isLoading,
        message: _message,
        onChildSelected: _selectChild,
      ),
    );
  }
}

class _ParentDashboardContent extends StatelessWidget {
  const _ParentDashboardContent({
    required this.state,
    required this.children,
    required this.selectedChild,
    required this.snapshot,
    required this.isLoading,
    required this.message,
    required this.onChildSelected,
  });

  final AppState state;
  final List<LinkedChildContext> children;
  final LinkedChildContext? selectedChild;
  final ParentDashboardSnapshot? snapshot;
  final bool isLoading;
  final String? message;
  final ValueChanged<LinkedChildContext?> onChildSelected;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final diagnoses = snapshot?.aiDiagnoses ?? const <AiDiagnosis>[];
    final aiDiagnosis = diagnoses.isEmpty ? null : diagnoses.first;
    final story = _ParentLearningStory.fromSafeProjection(
      state,
      child: selectedChild,
      diagnosis: aiDiagnosis,
    );

    return LogicOasisScaffold(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
      children: [
        Text(l10n.parentDashboard, style: theme.textTheme.headlineLarge),
        const SizedBox(height: 8),
        Text(
          selectedChild == null
              ? state.t(
                  'Sign in with a linked parent account to view safe learner updates.',
                  'Log masuk dengan akaun ibu bapa yang dipautkan untuk melihat kemas kini pembelajaran selamat.',
                )
              : state.t(
                  'Safe learning updates for ${selectedChild!.displayName}.',
                  'Kemas kini pembelajaran selamat untuk ${selectedChild!.displayName}.',
                ),
          style: theme.textTheme.bodyLarge,
        ),
        if (children.length > 1) ...[
          const SizedBox(height: 14),
          DropdownButtonFormField<LinkedChildContext>(
            value: selectedChild,
            decoration: const InputDecoration(labelText: 'Linked learner'),
            items: children
                .map(
                  (child) => DropdownMenuItem(
                    value: child,
                    child: Text(
                      '${child.displayName} (Year ${child.yearLevel})',
                    ),
                  ),
                )
                .toList(growable: false),
            onChanged: onChildSelected,
          ),
        ],
        if (isLoading || message != null) ...[
          const SizedBox(height: 14),
          _ParentDashboardSafeStatusBanner(
            isLoading: isLoading,
            message: message,
          ),
        ],
        const SizedBox(height: 18),
        _ParentInsightSummary(
          story: story,
          focusLabel: state.t('Focus', 'Fokus'),
          meaningLabel: state.t('Meaning', 'Maksud'),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: state.t(
            'Safe learning boundary',
            'Sempadan pembelajaran selamat',
          ),
          icon: Icons.verified_user_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                state.t(
                  'This dashboard uses only protected status, mastery, assignment, and count-only participation projections.',
                  'Papan pemuka ini menggunakan hanya unjuran status, penguasaan, tugasan dan penyertaan kiraan sahaja yang dilindungi.',
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
                label: state.t('Safe updates', 'Kemas kini selamat'),
                value: '${diagnoses.length}',
                color: LogicOasisTheme.leaf,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: MetricCard(
                icon: Icons.history,
                label: state.t('Mastery records', 'Rekod penguasaan'),
                value: '${snapshot?.masteryRecordCount ?? 0}',
                color: LogicOasisTheme.clay,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: state.t('Latest safe analysis', 'Analisis selamat terkini'),
          icon: Icons.history_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (aiDiagnosis == null)
                Text(
                  state.t(
                    'No safe analysis is available yet. It will appear after a linked learner completes a server-validated quiz.',
                    'Belum ada analisis selamat. Ia akan dipaparkan selepas pelajar yang dipautkan melengkapkan kuiz yang disahkan pelayan.',
                  ),
                )
              else ...[
                Text(aiDiagnosis.childFacingStatus),
                const SizedBox(height: 12),
                _AiDiagnosisDetails(
                  masteryProbability: aiDiagnosis.bktMasteryProbability,
                  finalLabel: aiDiagnosis.finalMasteryLabel,
                  attemptsCount: aiDiagnosis.attemptsCount,
                  createdAt: aiDiagnosis.createdAt,
                  shapReasons: aiDiagnosis.explanationReasons,
                  evidenceLevel: aiDiagnosis.evidenceLevel,
                  isBahasaMelayu: state.isBahasaMelayu,
                ),
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
                aiDiagnosis == null
                    ? state.t(
                        'Advice is updating',
                        'Nasihat sedang dikemas kini',
                      )
                    : aiDiagnosis.finalMasteryLabel,
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              RecommendationBox(
                text:
                    aiDiagnosis?.recommendedAction ??
                    state.t(
                      'Complete one short server-validated practice to prepare safe advice.',
                      'Lengkapkan satu latihan ringkas yang disahkan pelayan untuk menyediakan nasihat selamat.',
                    ),
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
        if (snapshot?.forumParticipationSummary != null) ...[
          const SizedBox(height: 16),
          SectionCard(
            title: state.t('Participation summary', 'Ringkasan penyertaan'),
            icon: Icons.forum_outlined,
            child: Text(
              state.t(
                '${snapshot!.forumParticipationSummary!.questionsPostedCount} questions, ${snapshot!.forumParticipationSummary!.answersSubmittedCount} answers, and ${snapshot!.forumParticipationSummary!.helpfulReceivedCount} helpful marks.',
                '${snapshot!.forumParticipationSummary!.questionsPostedCount} soalan, ${snapshot!.forumParticipationSummary!.answersSubmittedCount} jawapan dan ${snapshot!.forumParticipationSummary!.helpfulReceivedCount} tanda membantu.',
              ),
            ),
          ),
        ],
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

  factory _ParentLearningStory.fromSafeProjection(
    AppState state, {
    required LinkedChildContext? child,
    required AiDiagnosis? diagnosis,
  }) {
    final learnerName =
        child?.displayName ??
        state.t('your linked learner', 'pelajar yang dipautkan');
    if (diagnosis == null) {
      return _ParentLearningStory(
        status: state.t(
          'Waiting for safe updates',
          'Menunggu kemas kini selamat',
        ),
        statusDetail: state.t(
          'Complete one server-validated quiz for $learnerName to prepare a protected learning update.',
          'Lengkapkan satu kuiz yang disahkan pelayan untuk $learnerName bagi menyediakan kemas kini pembelajaran terlindung.',
        ),
        priority: state.t(
          'First focus: one short practice.',
          'Fokus pertama: satu latihan ringkas.',
        ),
        parentMeaning: state.t(
          'No local or seeded quiz history is used in this parent view.',
          'Tiada sejarah kuiz setempat atau benih digunakan dalam paparan ibu bapa ini.',
        ),
        tonightAction: state.t(
          'Encourage one short practice without pressure.',
          'Galakkan satu latihan ringkas tanpa tekanan.',
        ),
        conversationPrompt: state.t(
          'Which part would feel good to practise together?',
          'Bahagian mana yang sesuai untuk dilatih bersama?',
        ),
        weekGoal: state.t(
          'Wait for the first safe update before drawing conclusions.',
          'Tunggu kemas kini selamat pertama sebelum membuat kesimpulan.',
        ),
        statusColor: LogicOasisTheme.water,
        statusIcon: Icons.hourglass_top_outlined,
      );
    }
    final masteryPercent = (diagnosis.bktMasteryProbability * 100).round();
    return _ParentLearningStory(
      status: state.t('Practice focus ready', 'Fokus latihan sedia'),
      statusDetail: state.t(
        'The latest protected update for $learnerName shows $masteryPercent% current mastery.',
        'Kemas kini terlindung terkini untuk $learnerName menunjukkan $masteryPercent% penguasaan semasa.',
      ),
      priority: state.t(
        'Follow the assigned next practice.',
        'Ikut latihan seterusnya yang ditugaskan.',
      ),
      parentMeaning: state.t(
        'This advice comes only from a compatible server projection. Low evidence remains preliminary.',
        'Nasihat ini datang hanya daripada unjuran pelayan yang serasi. Bukti rendah kekal sebagai awal.',
      ),
      tonightAction: diagnosis.recommendedAction,
      conversationPrompt: state.t(
        'Which step should we practise slowly together?',
        'Langkah mana yang patut kita latih perlahan-lahan bersama?',
      ),
      weekGoal: state.t(
        'Complete two focused practices and compare the next safe update.',
        'Lengkapkan dua latihan berfokus dan bandingkan kemas kini selamat seterusnya.',
      ),
      statusColor: LogicOasisTheme.water,
      statusIcon: Icons.psychology_alt_outlined,
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
    required this.finalLabel,
    required this.attemptsCount,
    required this.createdAt,
    required this.shapReasons,
    required this.evidenceLevel,
    required this.isBahasaMelayu,
  });

  final double masteryProbability;
  final String finalLabel;
  final int attemptsCount;
  final DateTime createdAt;
  final List<String> shapReasons;
  final String? evidenceLevel;
  final bool isBahasaMelayu;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final masteryText = (masteryProbability * 100).round();

    return SoftCard(
      padding: const EdgeInsets.all(12),
      color: LogicOasisTheme.mint,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            isBahasaMelayu
                ? 'Kemas kini pembelajaran selamat'
                : 'Safe learning update',
            style: theme.textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            isBahasaMelayu
                ? 'Status pelayan: ${attemptsCount.clamp(0, 999)} pemerhatian pembelajaran.'
                : 'Server status: ${attemptsCount.clamp(0, 999)} learning observations.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: LogicOasisTheme.ink,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            isBahasaMelayu
                ? 'Tahap pembelajaran: $finalLabel. Penguasaan semasa: $masteryText%.'
                : 'Learning status: $finalLabel. Current mastery: $masteryText%.',
            style: theme.textTheme.bodyMedium,
          ),
          if (evidenceLevel != null) ...[
            const SizedBox(height: 6),
            Text(
              isBahasaMelayu
                  ? 'Tahap bukti: $evidenceLevel.'
                  : 'Evidence level: $evidenceLevel.',
              style: theme.textTheme.bodySmall,
            ),
          ],
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
              isBahasaMelayu
                  ? 'Sebab sokongan: ${shapReasons.take(3).join(', ')}'
                  : 'Supportive reason: ${shapReasons.take(3).join(', ')}',
              style: theme.textTheme.bodyMedium,
            ),
          ],
          const SizedBox(height: 8),
          Text(
            isBahasaMelayu
                ? 'Nasihat sandaran menggunakan kemajuan kuiz yang disahkan oleh pelayan.'
                : 'Fallback advice uses server-confirmed quiz progress.',
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

DateTime _malaysiaTime(DateTime value) {
  if (value.isUtc) {
    return value.add(const Duration(hours: 8));
  }
  return value.toUtc().add(const Duration(hours: 8));
}

class _ParentDashboardSafeStatusBanner extends StatelessWidget {
  const _ParentDashboardSafeStatusBanner({
    required this.isLoading,
    required this.message,
  });

  final bool isLoading;
  final String? message;

  @override
  Widget build(BuildContext context) {
    final text = isLoading ? 'Loading linked learner updates…' : message ?? '';
    return SoftCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      color: isLoading ? LogicOasisTheme.mint : LogicOasisTheme.sand,
      child: Row(
        children: [
          SizedBox(
            width: 20,
            height: 20,
            child: isLoading
                ? const CircularProgressIndicator(strokeWidth: 2.4)
                : const Icon(Icons.cloud_off_outlined, size: 20),
          ),
          const SizedBox(width: 10),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}
