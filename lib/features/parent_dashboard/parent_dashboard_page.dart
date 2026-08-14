import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/linked_child_context.dart';
import 'package:logic_oasis/shared/models/parent_dashboard_snapshot.dart';
import 'package:logic_oasis/shared/repositories/learning_repository.dart';
import 'package:logic_oasis/shared/services/parent_link_context_service.dart';
import 'package:logic_oasis/shared/services/parent_firebase_session.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/logic_oasis_figma_components.dart';
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
    } on ParentDashboardAuthException {
      if (!mounted || child.studentId != _selectedChild?.studentId) return;
      setState(() {
        _isLoading = false;
        _message = 'This learner link is no longer active. Please reconnect.';
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
            initialValue: selectedChild,
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
        if (selectedChild != null) ...[
          const SizedBox(height: 16),
          SectionCard(
            title: state.t('Learning map', 'Peta pembelajaran'),
            icon: Icons.map_outlined,
            child: _ParentInterimProgressMap(state: state, snapshot: snapshot),
          ),
        ],
      ],
    );
  }
}

/// Interim parent-safe summary of the three typed card inputs. U5 replaces
/// this with the approved Progress Map; this interim view never exposes
/// attempts, AI/model details, or raw maps.
class _ParentInterimProgressMap extends StatelessWidget {
  const _ParentInterimProgressMap({
    required this.state,
    required this.snapshot,
  });

  final AppState state;
  final ParentDashboardSnapshot? snapshot;

  @override
  Widget build(BuildContext context) {
    final mastery = snapshot?.mastery;
    final practice = snapshot?.practiceSummary;
    final mutualAid = snapshot?.forumParticipationSummary;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _InterimMapRow(
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
        ),
        const SizedBox(height: 10),
        _InterimMapRow(
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
        ),
        const SizedBox(height: 10),
        _InterimMapRow(
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
        ),
      ],
    );
  }
}

class _InterimMapRow extends StatelessWidget {
  const _InterimMapRow({
    required this.icon,
    required this.label,
    required this.body,
  });

  final IconData icon;
  final String label;
  final String body;

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
      ],
    );
  }
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
