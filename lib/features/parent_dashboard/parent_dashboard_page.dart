import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_state.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/linked_child_context.dart';
import 'package:logic_oasis/shared/repositories/learning_repository.dart';
import 'package:logic_oasis/shared/services/parent_firebase_session.dart';
import 'package:logic_oasis/shared/services/parent_link_context_service.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/logic_oasis_figma_components.dart';
import 'package:logic_oasis/shared/widgets/section_card.dart';

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
  late final ParentDashboardState _dashboardState;
  late final Listenable _listenable;

  @override
  void initState() {
    super.initState();
    _dashboardState = ParentDashboardState(
      gateway: widget.linkedChildrenGateway ?? ParentLinkedChildrenService(),
      loaderFactory: _loaderFactory,
    );
    _listenable = Listenable.merge([widget.state, _dashboardState]);
    _dashboardState.loadLinkedChildren();
  }

  @override
  void dispose() {
    _dashboardState.dispose();
    super.dispose();
  }

  Future<ParentDashboardLoader> _loaderFactory() async {
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
    if (child == null) return;
    _dashboardState.selectChild(child);
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _listenable,
      builder: (context, _) => _ParentDashboardContent(
        state: widget.state,
        dashboard: _dashboardState,
        onChildSelected: _selectChild,
      ),
    );
  }
}

class _ParentDashboardContent extends StatelessWidget {
  const _ParentDashboardContent({
    required this.state,
    required this.dashboard,
    required this.onChildSelected,
  });

  final AppState state;
  final ParentDashboardState dashboard;
  final ValueChanged<LinkedChildContext?> onChildSelected;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final selectedChild = dashboard.selectedChild;
    final phase = dashboard.phase;

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
                  'Safe learning updates for ${selectedChild.displayName}.',
                  'Kemas kini pembelajaran selamat untuk ${selectedChild.displayName}.',
                ),
          style: theme.textTheme.bodyLarge,
        ),
        if (dashboard.children.length > 1) ...[
          const SizedBox(height: 14),
          DropdownButtonFormField<LinkedChildContext>(
            initialValue: selectedChild,
            decoration: const InputDecoration(labelText: 'Linked learner'),
            items: dashboard.children
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
        if (_showStatusBanner(phase)) ...[
          const SizedBox(height: 14),
          _ParentDashboardSafeStatusBanner(
            loading:
                phase == ParentDashboardPhase.loadingLinks ||
                phase == ParentDashboardPhase.loadingChild,
            text: _statusText(phase, dashboard.message),
            onRetry: switch (phase) {
              ParentDashboardPhase.linkError => dashboard.loadLinkedChildren,
              ParentDashboardPhase.childError => dashboard.retryCurrentChild,
              _ => null,
            },
          ),
        ],
        if (selectedChild != null && dashboard.isReady) ...[
          const SizedBox(height: 18),
          SectionCard(
            title: state.t(
              'Safe learning boundary',
              'Sempadan pembelajaran selamat',
            ),
            icon: Icons.verified_user_outlined,
            child: Text(
              state.t(
                'This dashboard uses only protected mastery, practice, and count-only participation projections.',
                'Papan pemuka ini menggunakan hanya unjuran penguasaan, latihan dan penyertaan kiraan sahaja yang dilindungi.',
              ),
              style: theme.textTheme.bodyMedium,
            ),
          ),
          const SizedBox(height: 16),
          SectionCard(
            title: state.t('Learning map', 'Peta pembelajaran'),
            icon: Icons.map_outlined,
            child: _ParentInterimProgressMap(
              state: state,
              dashboard: dashboard,
            ),
          ),
        ],
      ],
    );
  }

  static bool _showStatusBanner(ParentDashboardPhase phase) =>
      phase == ParentDashboardPhase.loadingLinks ||
      phase == ParentDashboardPhase.loadingChild ||
      phase == ParentDashboardPhase.linkError ||
      phase == ParentDashboardPhase.childError ||
      phase == ParentDashboardPhase.noActiveChild;

  static String _statusText(ParentDashboardPhase phase, String? message) {
    if (phase == ParentDashboardPhase.loadingLinks) {
      return 'Loading linked learners…';
    }
    if (phase == ParentDashboardPhase.loadingChild) {
      return 'Loading linked learner updates…';
    }
    return message ?? '';
  }
}

/// Interim parent-safe summary of the three typed card inputs. U5 replaces
/// this with the approved Progress Map; this interim view never exposes
/// attempts, AI/model details, or raw maps. A card-level retry marks only the
/// retried card as loading and keeps the other cards' committed data.
class _ParentInterimProgressMap extends StatelessWidget {
  const _ParentInterimProgressMap({
    required this.state,
    required this.dashboard,
  });

  final AppState state;
  final ParentDashboardState dashboard;

  @override
  Widget build(BuildContext context) {
    final snapshot = dashboard.snapshot;
    final mastery = snapshot?.mastery;
    final practice = snapshot?.practiceSummary;
    final mutualAid = snapshot?.forumParticipationSummary;
    final retrying = dashboard.retryingCard;
    final canRetry =
        dashboard.phase == ParentDashboardPhase.readyPartial ||
        dashboard.phase == ParentDashboardPhase.retryingCard;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _cardRow(
          kind: ParentCardKind.understanding,
          icon: Icons.psychology_outlined,
          label: state.t('Understanding', 'Pemahaman'),
          body: mastery == null
              ? state.t(
                  'Learning evidence is temporarily unavailable.',
                  'Bukti pembelajaran tidak tersedia buat sementara waktu.',
                )
              : mastery.isEmpty
              ? state.t(
                  'More learning evidence is needed before a focus can be named.',
                  'Lebih banyak bukti pembelajaran diperlukan sebelum fokus dapat dinamakan.',
                )
              : state.t(
                  '${mastery.length} learning records are ready.',
                  '${mastery.length} rekod pembelajaran sudah sedia.',
                ),
          unavailable: mastery == null,
          retrying: retrying == ParentCardKind.understanding,
          canRetry: canRetry && mastery == null,
        ),
        const SizedBox(height: 10),
        _cardRow(
          kind: ParentCardKind.practice,
          icon: Icons.task_alt_outlined,
          label: state.t('Practice effort', 'Usaha latihan'),
          body: practice == null
              ? state.t(
                  'Practice effort is unavailable this week.',
                  'Usaha latihan tidak tersedia minggu ini.',
                )
              : state.t(
                  'This week: ${practice.completedPracticeCount} completed practices across ${practice.activeDayCount} active days.',
                  'Minggu ini: ${practice.completedPracticeCount} latihan lengkap sepanjang ${practice.activeDayCount} hari aktif.',
                ),
          unavailable: practice == null,
          retrying: retrying == ParentCardKind.practice,
          canRetry: canRetry && practice == null,
        ),
        const SizedBox(height: 10),
        _cardRow(
          kind: ParentCardKind.mutualAid,
          icon: Icons.forum_outlined,
          label: state.t('Mutual aid', 'Saling membantu'),
          body: mutualAid == null
              ? state.t(
                  'Participation summary is unavailable this week.',
                  'Ringkasan penyertaan tidak tersedia minggu ini.',
                )
              : state.t(
                  'This week: ${mutualAid.questionsPostedCount} questions, ${mutualAid.answersSubmittedCount} replies, ${mutualAid.acceptedAnswersCount} accepted answers, ${mutualAid.helpfulReceivedCount} helpful marks.',
                  'Minggu ini: ${mutualAid.questionsPostedCount} soalan, ${mutualAid.answersSubmittedCount} jawapan, ${mutualAid.acceptedAnswersCount} jawapan diterima, ${mutualAid.helpfulReceivedCount} tanda membantu.',
                ),
          unavailable: mutualAid == null,
          retrying: retrying == ParentCardKind.mutualAid,
          canRetry: canRetry && mutualAid == null,
        ),
      ],
    );
  }

  Widget _cardRow({
    required ParentCardKind kind,
    required IconData icon,
    required String label,
    required String body,
    required bool unavailable,
    required bool retrying,
    required bool canRetry,
  }) {
    return _InterimMapRow(
      icon: icon,
      label: label,
      body: body,
      trailing: retrying
          ? const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : canRetry
          ? TextButton(
              onPressed: () => dashboard.retryCard(kind),
              child: const Text('Retry'),
            )
          : null,
    );
  }
}

class _InterimMapRow extends StatelessWidget {
  const _InterimMapRow({
    required this.icon,
    required this.label,
    required this.body,
    this.trailing,
  });

  final IconData icon;
  final String label;
  final String body;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 20, color: LogicOasisTheme.deepLeaf),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: theme.textTheme.labelLarge?.copyWith(
                  color: LogicOasisTheme.ink,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 2),
              Text(body, style: theme.textTheme.bodyMedium),
            ],
          ),
        ),
        if (trailing != null) ...[const SizedBox(width: 8), trailing!],
      ],
    );
  }
}

class _ParentDashboardSafeStatusBanner extends StatelessWidget {
  const _ParentDashboardSafeStatusBanner({
    required this.loading,
    required this.text,
    this.onRetry,
  });

  final bool loading;
  final String text;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return SoftCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      color: loading ? LogicOasisTheme.mint : LogicOasisTheme.sand,
      child: Row(
        children: [
          SizedBox(
            width: 20,
            height: 20,
            child: loading
                ? const CircularProgressIndicator(strokeWidth: 2.4)
                : const Icon(Icons.cloud_off_outlined, size: 20),
          ),
          const SizedBox(width: 10),
          Expanded(child: Text(text)),
          if (!loading && onRetry != null)
            TextButton(onPressed: onRetry, child: const Text('Retry')),
        ],
      ),
    );
  }
}
