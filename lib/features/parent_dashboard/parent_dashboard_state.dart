import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:logic_oasis/shared/models/linked_child_context.dart';
import 'package:logic_oasis/shared/models/parent_dashboard_snapshot.dart';
import 'package:logic_oasis/shared/services/parent_link_context_service.dart';

/// The three independently available Progress Map cards.
enum ParentCardKind { understanding, practice, mutualAid }

/// Explicit child-scoped dashboard phases. Loading, no-child, link error,
/// child loading, ready-all, ready-partial, card retry, and child error are
/// visually distinct and never conflated.
enum ParentDashboardPhase {
  loadingLinks,
  noActiveChild,
  linkError,
  loadingChild,
  readyAll,
  readyPartial,
  retryingCard,
  childError,
}

typedef ParentDashboardLoader =
    Future<ParentDashboardSnapshot> Function(LinkedChildContext child);
typedef ParentDashboardWatcher =
    Stream<ParentDashboardSnapshot> Function(LinkedChildContext child);

/// Child-scoped parent dashboard state with monotonic request generations.
///
/// Every child load clears the previous child's content before requesting the
/// new child, and a result is committed only when both the selected child and
/// the request generation still match, so stale or out-of-order responses can
/// never overwrite the current view. A permission-denied/revocation response
/// clears the whole child view; a card-level retry preserves the other valid
/// cards and marks only the failed card as loading.
class ParentDashboardState extends ChangeNotifier {
  ParentDashboardState({
    required ParentLinkedChildrenGateway gateway,
    required Future<ParentDashboardLoader> Function() loaderFactory,
    Future<ParentDashboardWatcher> Function()? watcherFactory,
  }) : _gateway = gateway,
       _loaderFactory = loaderFactory,
       _watcherFactory = watcherFactory;

  final ParentLinkedChildrenGateway _gateway;
  final Future<ParentDashboardLoader> Function() _loaderFactory;
  final Future<ParentDashboardWatcher> Function()? _watcherFactory;
  StreamSubscription<ParentDashboardSnapshot>? _watchSubscription;

  ParentDashboardPhase _phase = ParentDashboardPhase.loadingLinks;
  List<LinkedChildContext> _children = const [];
  LinkedChildContext? _selectedChild;
  ParentDashboardSnapshot? _snapshot;
  String? _message;
  ParentCardKind? _retryingCard;
  int _linksGeneration = 0;
  int _requestGeneration = 0;
  bool _disposed = false;

  ParentDashboardPhase get phase => _phase;
  List<LinkedChildContext> get children => _children;
  LinkedChildContext? get selectedChild => _selectedChild;
  ParentDashboardSnapshot? get snapshot => _snapshot;
  String? get message => _message;
  ParentCardKind? get retryingCard => _retryingCard;

  bool get isReady =>
      _phase == ParentDashboardPhase.readyAll ||
      _phase == ParentDashboardPhase.readyPartial ||
      _phase == ParentDashboardPhase.retryingCard;

  @override
  void dispose() {
    _disposed = true;
    unawaited(_watchSubscription?.cancel());
    _watchSubscription = null;
    super.dispose();
  }

  /// Loads (or reloads) the active linked children. On a reload the previously
  /// selected child is kept when still present; otherwise the first remaining
  /// active child is chosen explicitly. Removed or revoked children never
  /// retain content.
  Future<void> loadLinkedChildren() async {
    final generation = ++_linksGeneration;
    ++_requestGeneration;
    unawaited(_watchSubscription?.cancel());
    _watchSubscription = null;
    _phase = ParentDashboardPhase.loadingLinks;
    _message = null;
    _clearChildView();
    _notify();
    try {
      final children = await _gateway.loadLinkedChildren();
      if (generation != _linksGeneration) return;
      _children = children;
      final selected = _selectedChild;
      if (children.isEmpty) {
        _selectedChild = null;
        _phase = ParentDashboardPhase.noActiveChild;
        _message = 'No active linked learner is available for this account.';
        _notify();
        return;
      }
      final next = children.firstWhere(
        (child) => child.studentId == selected?.studentId,
        orElse: () => children.first,
      );
      _selectedChild = next;
      _phase = ParentDashboardPhase.loadingChild;
      _notify();
      await _loadChild(next, ++_requestGeneration);
    } on ParentLinkContextException catch (error) {
      if (generation != _linksGeneration) return;
      _phase = ParentDashboardPhase.linkError;
      _message = error.message;
      _notify();
    } catch (_) {
      if (generation != _linksGeneration) return;
      _phase = ParentDashboardPhase.linkError;
      _message = 'Linked learner updates are temporarily unavailable.';
      _notify();
    }
  }

  /// Switches to [child], clearing every child-derived value of the previous
  /// child before the new request starts.
  Future<void> selectChild(LinkedChildContext child) async {
    if (child.studentId == _selectedChild?.studentId) return;
    _selectedChild = child;
    _phase = ParentDashboardPhase.loadingChild;
    _clearChildView();
    _notify();
    await _loadChild(child, ++_requestGeneration);
  }

  /// Whole-context retry of the currently selected child.
  Future<void> retryCurrentChild() async {
    final child = _selectedChild;
    if (child == null) {
      await loadLinkedChildren();
      return;
    }
    _phase = ParentDashboardPhase.loadingChild;
    _clearChildView();
    _notify();
    await _loadChild(child, ++_requestGeneration);
  }

  /// Card-level retry: keeps the committed snapshot for the other cards and
  /// marks only [kind] as loading. If the retry still cannot provide the card,
  /// the state returns to [ParentDashboardPhase.readyPartial] with the old
  /// snapshot preserved.
  Future<void> retryCard(ParentCardKind kind) async {
    final child = _selectedChild;
    if (child == null || _snapshot == null) return;
    _phase = ParentDashboardPhase.retryingCard;
    _retryingCard = kind;
    _message = null;
    _notify();
    await _loadChild(child, ++_requestGeneration, cardRetry: true);
  }

  Future<void> _loadChild(
    LinkedChildContext child,
    int generation, {
    bool cardRetry = false,
  }) async {
    final watcherFactory = _watcherFactory;
    if (watcherFactory != null) {
      await _watchChild(
        child,
        generation,
        watcherFactory,
        cardRetry: cardRetry,
      );
      return;
    }
    try {
      final loader = await _loaderFactory();
      final snapshot = await loader(child);
      if (!_isCurrent(child, generation)) return;
      _commitSnapshot(snapshot);
    } catch (error) {
      if (!_isCurrent(child, generation)) return;
      _commitLoadError(error, cardRetry: cardRetry);
    }
  }

  Future<void> _watchChild(
    LinkedChildContext child,
    int generation,
    Future<ParentDashboardWatcher> Function() watcherFactory, {
    required bool cardRetry,
  }) async {
    await _watchSubscription?.cancel();
    _watchSubscription = null;
    try {
      final watcher = await watcherFactory();
      if (!_isCurrent(child, generation)) return;
      final firstEvent = Completer<void>();
      _watchSubscription = watcher(child).listen(
        (snapshot) {
          if (!_isCurrent(child, generation)) return;
          _commitSnapshot(snapshot);
          if (!firstEvent.isCompleted) firstEvent.complete();
        },
        onError: (Object error, StackTrace stackTrace) {
          if (!_isCurrent(child, generation)) return;
          _commitLoadError(error, cardRetry: cardRetry);
          if (!firstEvent.isCompleted) firstEvent.complete();
        },
        onDone: () {
          if (!firstEvent.isCompleted) {
            _commitLoadError(
              StateError('Parent dashboard stream closed before loading.'),
              cardRetry: cardRetry,
            );
            firstEvent.complete();
          }
        },
      );
      await firstEvent.future;
    } catch (error) {
      if (!_isCurrent(child, generation)) return;
      _commitLoadError(error, cardRetry: cardRetry);
    }
  }

  bool _isCurrent(LinkedChildContext child, int generation) =>
      !_disposed &&
      generation == _requestGeneration &&
      child.studentId == _selectedChild?.studentId;

  void _commitSnapshot(ParentDashboardSnapshot snapshot) {
    _snapshot = snapshot;
    _retryingCard = null;
    _message = null;
    _phase = _allCardsAvailable(snapshot)
        ? ParentDashboardPhase.readyAll
        : ParentDashboardPhase.readyPartial;
    _notify();
  }

  void _commitLoadError(Object error, {required bool cardRetry}) {
    if (error is ParentDashboardAuthException) {
      _snapshot = null;
      _retryingCard = null;
      _message = 'This learner link is no longer active. Please reconnect.';
      _phase = ParentDashboardPhase.childError;
    } else if (cardRetry && _snapshot != null) {
      _retryingCard = null;
      _phase = ParentDashboardPhase.readyPartial;
    } else {
      _snapshot = null;
      _retryingCard = null;
      _message = 'Safe learner updates are temporarily unavailable.';
      _phase = ParentDashboardPhase.childError;
    }
    _notify();
  }

  void _notify() {
    if (_disposed) return;
    notifyListeners();
  }

  void _clearChildView() {
    _snapshot = null;
    _retryingCard = null;
    _message = null;
  }

  static bool _allCardsAvailable(ParentDashboardSnapshot snapshot) =>
      snapshot.mastery != null &&
      snapshot.practiceSummary != null &&
      snapshot.forumParticipationSummary != null;
}
