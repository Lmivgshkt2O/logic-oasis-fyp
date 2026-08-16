import 'dart:async';

import 'package:logic_oasis/app/theme.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:cloud_functions/cloud_functions.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:logic_oasis/shared/models/forum_answer.dart';
import 'package:logic_oasis/shared/models/forum_question.dart';
import 'package:logic_oasis/shared/repositories/collaboration_repository.dart';
import 'package:logic_oasis/shared/services/forum_ai_status_service.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

class QaForumPage extends StatefulWidget {
  const QaForumPage({
    super.key,
    required this.state,
    this.repository,
    this.questionPager,
    this.latestQuestionsStream,
    this.blockedStudentIdsStream,
    this.deletedQuestionIdsStream,
    this.answersStreamForQuestion,
    this.authorFeedbackStreamForAnswer,
  });

  static const int pageSize = 20;

  final AppState state;
  final CollaborationRepository? repository;
  final Future<ForumQuestionPage> Function({
    required int limit,
    String? cursor,
  })?
  questionPager;
  final Stream<List<ForumQuestion>>? latestQuestionsStream;
  final Stream<Set<String>>? blockedStudentIdsStream;
  final Stream<Set<String>>? deletedQuestionIdsStream;
  final Stream<List<ForumAnswer>> Function(String questionId)?
  answersStreamForQuestion;
  final Stream<ForumAnswerFeedback> Function(String answerId)?
  authorFeedbackStreamForAnswer;

  @override
  State<QaForumPage> createState() => _QaForumPageState();
}

class _QaForumPageState extends State<QaForumPage> {
  CollaborationRepository? _repository;
  CollaborationRepository get _repo =>
      _repository ??= widget.repository ?? CollaborationRepository();
  final _filter = TextEditingController();
  final _questionTitle = TextEditingController();
  final _questionBody = TextEditingController();
  StreamSubscription<Set<String>>? _blockedSubscription;
  StreamSubscription<Set<String>>? _deletedSubscription;
  StreamSubscription<List<ForumQuestion>>? _latestSubscription;
  Set<String> _blockedAuthors = const {};
  Set<String> _deletedQuestions = const {};
  Object? _blockedError;
  bool _postingQuestion = false;
  String? _deleting;
  List<ForumQuestion> _questions = const [];
  String? _nextCursor;
  bool _hasMore = false;
  bool _loading = true;
  Object? _loadError;
  bool _loadingMore = false;
  Object? _loadMoreError;

  String _t(String english, String bahasaMelayu) =>
      widget.state.t(english, bahasaMelayu);

  @override
  void initState() {
    super.initState();
    final blockedIds =
        widget.blockedStudentIdsStream ??
        _repo.watchBlockedStudentIds(widget.state.currentStudentId);
    _blockedSubscription = blockedIds.listen(
      (ids) {
        if (mounted) {
          setState(() {
            _blockedAuthors = ids;
            _blockedError = null;
          });
        }
      },
      onError: (Object error) {
        if (mounted) setState(() => _blockedError = error);
      },
    );
    Stream<Set<String>> deletedIds;
    try {
      deletedIds =
          widget.deletedQuestionIdsStream ??
          _repo.watchDeletedQuestionIds(widget.state.currentStudentId);
    } catch (_) {
      // The deletion signal is advisory for the loaded list; widget-test
      // harnesses and degraded startup without Firestore fall back to empty.
      deletedIds = const Stream<Set<String>>.empty();
    }
    _deletedSubscription = deletedIds.listen(
      (ids) {
        if (mounted) setState(() => _deletedQuestions = ids);
      },
      onError: (Object error) {
        // A failed deletion signal must not break the loaded list.
        if (mounted) setState(() {});
      },
    );
    final latest =
        widget.latestQuestionsStream ??
        _repo.watchLatestForumQuestions(limit: QaForumPage.pageSize);
    _latestSubscription = latest.listen(
      (questions) {
        if (!mounted) return;
        _handleLatestPage(questions);
      },
      onError: (Object error) {
        // The latest-page signal is advisory; a failed signal must not break
        // the already-loaded paged list.
        if (mounted) setState(() {});
      },
    );
    _refresh();
  }

  @override
  void dispose() {
    _filter.dispose();
    _questionTitle.dispose();
    _questionBody.dispose();
    _blockedSubscription?.cancel();
    _deletedSubscription?.cancel();
    _latestSubscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(_t('Q&A Forum', 'Forum S&J')),
        actions: [
          IconButton(
            tooltip: _t('Manage blocked students', 'Urus murid yang disekat'),
            onPressed: _manageBlockedStudents,
            icon: const Icon(Icons.block_outlined),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _composeQuestion(context),
        backgroundColor: oasis.violet,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add_comment_outlined),
        label: Text(_t('Ask a question', 'Tanya soalan')),
      ),
      body: DecoratedBox(
        // Restrained lavender atmosphere near the header/search region so the
        // list page reads as part of the shared system while violet stays the
        // restrained identity accent.
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              const Color(0xFFEEE8F8),
              oasis.canvas,
              oasis.lowerCanvas,
            ],
          ),
        ),
        child: _buildQuestionList(context),
      ),
    );
  }

  Widget _buildQuestionList(BuildContext context) {
    if (_blockedError != null) {
      return _Message(_friendlyError(_blockedError!, widget.state));
    }
    if (_loading && _questions.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_loadError != null && _questions.isEmpty) {
      final error = _loadError!;
      final denied =
          error is FirebaseException && error.code == 'permission-denied';
      return Column(
        children: [
          _filterField(),
          Expanded(
            child: _Message(
              denied
                  ? _t(
                      'Forum access is unavailable for this account. Sign in with a student profile, then try again.',
                      'Akses forum tidak tersedia untuk akaun ini. Log masuk dengan profil murid dan cuba lagi.',
                    )
                  : _t(
                      'The forum could not be loaded. Please check your connection and try again.',
                      'Forum tidak dapat dimuatkan. Periksa sambungan anda dan cuba lagi.',
                    ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(bottom: 24),
            child: OutlinedButton.icon(
              onPressed: _refresh,
              icon: const Icon(Icons.refresh),
              label: Text(_t('Retry', 'Cuba semula')),
            ),
          ),
        ],
      );
    }
    final query = _filter.text.trim().toLowerCase();
    final questions = _questions
        .where(
          (question) =>
              !_blockedAuthors.contains(question.authorId) &&
              !_deletedQuestions.contains(question.id) &&
              (query.isEmpty ||
                  question.title.toLowerCase().contains(query) ||
                  question.text.toLowerCase().contains(query)),
        )
        .toList(growable: false);
    if (questions.isEmpty) {
      return Column(
        children: [
          _filterField(),
          Expanded(
            child: _Message(
              query.isEmpty
                  ? _t(
                      'No questions yet. Start the conversation by asking how you solved a problem.',
                      'Belum ada soalan. Mulakan perbualan dengan bertanya cara menyelesaikan masalah.',
                    )
                  : _t(
                      'No questions match this filter.',
                      'Tiada soalan sepadan dengan tapisan ini.',
                    ),
            ),
          ),
        ],
      );
    }
    final showFooter = _hasMore || _loadMoreError != null;
    return Column(
      children: [
        _filterField(),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
            itemCount: questions.length + (showFooter ? 1 : 0),
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (context, index) {
              if (index == questions.length) return _pagingFooter();
              final question = questions[index];
              final localizedPrompt =
                  widget.state.isBahasaMelayu &&
                      (question.promptBm?.isNotEmpty ?? false)
                  ? question.promptBm!
                  : null;
              return Card(
                child: ListTile(
                  title: Text(
                    localizedPrompt ?? question.title,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  subtitle: Text(
                    localizedPrompt ?? question.text,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (question.authorId ==
                                  widget.state.currentStudentId ||
                              question.mode == 'linked')
                        PopupMenuButton<_QuestionAction>(
                          tooltip: _t(
                            'Question actions',
                            'Tindakan soalan',
                          ),
                          enabled: _deleting != question.id,
                          onSelected: (action) =>
                              _questionAction(question, action),
                          itemBuilder: (_) => [
                            PopupMenuItem(
                              value: _QuestionAction.delete,
                              child: Text(
                                _t('Delete question', 'Padam soalan'),
                              ),
                            ),
                          ],
                        ),
                      const Icon(Icons.chevron_right),
                    ],
                  ),
                  onTap: () => _openAnswers(context, question),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _pagingFooter() {
    if (_loadMoreError != null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Column(
          children: [
            Text(
              _t(
                'Could not load more questions. Your current list is unchanged.',
                'Tidak dapat memuatkan lebih banyak soalan. Senarai semasa tidak berubah.',
              ),
              textAlign: TextAlign.center,
            ),
            TextButton.icon(
              onPressed: _loadingMore ? null : _loadMore,
              icon: const Icon(Icons.refresh),
              label: Text(_t('Retry', 'Cuba semula')),
            ),
          ],
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Center(
        child: _loadingMore
            ? const SizedBox.square(
                dimension: 22,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : OutlinedButton.icon(
                onPressed: _loadMore,
                icon: const Icon(Icons.expand_more),
                label: Text(_t('Load more', 'Muat lagi')),
              ),
      ),
    );
  }

  Future<ForumQuestionPage> _loadPage({required String? cursor}) {
    final pager =
        widget.questionPager ?? _repo.loadForumQuestions;
    return pager(limit: QaForumPage.pageSize, cursor: cursor);
  }

  Future<void> _questionAction(
    ForumQuestion question,
    _QuestionAction action,
  ) async {
    if (action != _QuestionAction.delete) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          question.mode == 'linked'
              ? _t(
                  'Remove this question from your list?',
                  'Buang soalan ini daripada senarai anda?',
                )
              : _t('Delete this question?', 'Padam soalan ini?'),
        ),
        content: Text(
          question.mode == 'linked'
              ? _t(
                  'This shared thread stays available to other students. It will be hidden from your forum list.',
                  'Benang kongsi ini masih tersedia untuk murid lain. Ia akan disembunyikan daripada senarai forum anda.',
                )
              : _t(
                  'This will also remove every answer to it. This action cannot be undone.',
                  'Ini juga akan memadam setiap jawapan kepadanya. Tindakan ini tidak boleh dibatalkan.',
                ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(_t('Cancel', 'Batal')),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(_t('Delete', 'Padam')),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _deleting = question.id);
    try {
      await _repo.deleteQuestion(question.id);
      _showMessage(_t('Question deleted.', 'Soalan telah dipadam.'));
      await _refresh();
    } catch (error) {
      _showMessage(_friendlyError(error, widget.state));
    } finally {
      if (mounted) setState(() => _deleting = null);
    }
  }

  Future<void> _refresh() async {
    setState(() {
      _loading = true;
      _loadError = null;
      _loadMoreError = null;
    });
    try {
      final page = await _loadPage(cursor: null);
      if (!mounted) return;
      setState(() {
        _questions = page.questions;
        _nextCursor = page.nextCursor;
        _hasMore = page.hasMore;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _loadError = error;
      });
    }
  }

  Future<void> _loadMore() async {
    if (_loading || _loadingMore || !_hasMore || _nextCursor == null) return;
    setState(() {
      _loadingMore = true;
      _loadMoreError = null;
    });
    try {
      final page = await _loadPage(cursor: _nextCursor);
      if (!mounted) return;
      setState(() {
        final seen = _questions.map((question) => question.id).toSet();
        _questions = [
          ..._questions,
          ...page.questions
              .where((question) => !seen.contains(question.id))
              .toList(growable: false),
        ];
        _nextCursor = page.nextCursor;
        _hasMore = page.hasMore;
        _loadingMore = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loadingMore = false;
        _loadMoreError = error;
      });
    }
  }

  void _handleLatestPage(List<ForumQuestion> latest) {
    final firstPageIds = _questions
        .take(QaForumPage.pageSize)
        .map((question) => question.id)
        .toList(growable: false);
    final latestIds = latest
        .map((question) => question.id)
        .toList(growable: false);
    final reordered = !listEquals(latestIds, firstPageIds);
    if (reordered && !_loading && !_loadingMore && mounted) {
      _refresh();
    }
  }

  void _onFilterChanged() {
    setState(() {});
    // Filters operate on loaded pages but reset the accumulated paging state
    // so a stale cursor cannot create gaps behind a narrower filter.
    _refresh();
  }

  Widget _filterField() => Padding(
    padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
    child: TextField(
      controller: _filter,
      onChanged: (_) => _onFilterChanged(),
      decoration: InputDecoration(
        // Tie the search field to the Forum accent with a faint lavender fill.
        fillColor: LogicOasisTheme.of(context).violet.withValues(alpha: .05),
        prefixIcon: Icon(
          Icons.search,
          color: LogicOasisTheme.of(context).violet,
        ),
        hintText: _t('Filter questions', 'Tapis soalan'),
        suffixIcon: _filter.text.isEmpty
            ? null
            : IconButton(
                tooltip: _t('Clear filter', 'Kosongkan tapisan'),
                onPressed: () {
                  _filter.clear();
                  _onFilterChanged();
                },
                icon: const Icon(Icons.clear),
              ),
      ),
    ),
  );

  Future<void> _manageBlockedStudents() async {
    if (_blockedAuthors.isEmpty) {
      _showMessage(
        _t(
          'You have not blocked any students.',
          'Anda belum menyekat mana-mana murid.',
        ),
      );
      return;
    }
    final blocked = _blockedAuthors.toList(growable: false)..sort();
    final selected = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(_t('Blocked students', 'Murid yang disekat')),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView.builder(
            shrinkWrap: true,
            itemCount: blocked.length,
            itemBuilder: (context, index) {
              final studentId = blocked[index];
              final shortId = studentId.length <= 8
                  ? studentId
                  : '…${studentId.substring(studentId.length - 8)}';
              return ListTile(
                leading: const Icon(Icons.person_off_outlined),
                title: Text(_t('Blocked student', 'Murid disekat')),
                subtitle: Text(shortId),
                trailing: TextButton(
                  onPressed: () => Navigator.pop(context, studentId),
                  child: Text(_t('Unblock', 'Buka sekatan')),
                ),
              );
            },
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(_t('Close', 'Tutup')),
          ),
        ],
      ),
    );
    if (selected == null) return;
    try {
      await _repo.unblock(
        studentId: widget.state.currentStudentId,
        blockedStudentId: selected,
      );
      if (mounted) {
        setState(
          () => _blockedAuthors = {..._blockedAuthors}..remove(selected),
        );
      }
      _showMessage(_t('Student unblocked.', 'Sekatan murid telah dibuka.'));
    } catch (error) {
      _showMessage(_friendlyError(error, widget.state));
    }
  }

  Future<void> _composeQuestion(BuildContext context) async {
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) => PopScope(
          canPop: !_postingQuestion,
          child: AlertDialog(
            title: Text(_t('Ask for help', 'Minta bantuan')),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: _questionTitle,
                  maxLength: 140,
                  decoration: InputDecoration(
                    labelText: _t('Question title', 'Tajuk soalan'),
                  ),
                ),
                TextField(
                  controller: _questionBody,
                  minLines: 3,
                  maxLines: 6,
                  maxLength: 3000,
                  decoration: InputDecoration(
                    labelText: _t(
                      'What have you tried?',
                      'Apakah yang telah anda cuba?',
                    ),
                  ),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: _postingQuestion
                    ? null
                    : () => Navigator.pop(dialogContext),
                child: Text(_t('Cancel', 'Batal')),
              ),
              FilledButton.icon(
                onPressed: _postingQuestion
                    ? null
                    : () async {
                        if (_questionTitle.text.trim().length < 8 ||
                            _questionBody.text.trim().length < 20) {
                          _showMessage(
                            _t(
                              'Add a clear title and explain what you tried.',
                              'Tambah tajuk yang jelas dan terangkan perkara yang telah dicuba.',
                            ),
                          );
                          return;
                        }
                        setDialogState(() => _postingQuestion = true);
                        try {
                          await _repo.createQuestion(
                            studentId: widget.state.currentStudentId,
                            title: _questionTitle.text,
                            text: _questionBody.text,
                          );
                          _questionTitle.clear();
                          _questionBody.clear();
                          if (dialogContext.mounted)
                            Navigator.pop(dialogContext);
                          _showMessage(
                            _t('Question posted.', 'Soalan telah dihantar.'),
                          );
                        } catch (error) {
                          _showMessage(_friendlyError(error, widget.state));
                          if (dialogContext.mounted) {
                            setDialogState(() => _postingQuestion = false);
                          }
                        }
                      },
                icon: _postingQuestion
                    ? const SizedBox.square(
                        dimension: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.send),
                label: Text(_t('Post', 'Hantar')),
              ),
            ],
          ),
        ),
      ),
    );
    _postingQuestion = false;
  }

  void _showMessage(String message) {
    if (mounted)
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
  }

  void _openAnswers(BuildContext context, ForumQuestion question) =>
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => ForumDiscussionPage(
            question: question,
            state: widget.state,
            repository: _repository ?? widget.repository,
            answersStream: widget.answersStreamForQuestion?.call(question.id),
            blockedStudentIdsStream: widget.blockedStudentIdsStream,
            authorFeedbackStreamForAnswer:
                widget.authorFeedbackStreamForAnswer,
          ),
        ),
      );
}

class ForumDiscussionPage extends StatefulWidget {
  const ForumDiscussionPage({
    required this.question,
    required this.state,
    this.repository,
    this.answersStream,
    this.blockedStudentIdsStream,
    this.authorFeedbackStreamForAnswer,
    this.returnOnLinkedSubmit = false,
  });
  final ForumQuestion question;
  final AppState state;
  final CollaborationRepository? repository;
  final Stream<List<ForumAnswer>>? answersStream;
  final Stream<Set<String>>? blockedStudentIdsStream;
  final Stream<ForumAnswerFeedback> Function(String answerId)?
  authorFeedbackStreamForAnswer;
  /// When the thread was opened from quiz review, returning the student to
  /// the review card automatically after a successful linked submission.
  final bool returnOnLinkedSubmit;
  @override
  State<ForumDiscussionPage> createState() => _AnswersPageState();
}

class _AnswersPageState extends State<ForumDiscussionPage> {
  final _answer = TextEditingController();
  final _explanation = TextEditingController();
  final _status = const ForumAiStatusService();
  final Set<String> _inFlight = {};
  StreamSubscription<Set<String>>? _blockedSubscription;
  Timer? _returnTimer;
  Set<String> _blockedAuthors = const {};
  Object? _blockedError;
  String? _acceptedAnswerId;
  bool _submitting = false;

  bool get _isLinked => widget.question.mode == 'linked';

  List<String> get _options =>
      widget.state.isBahasaMelayu
          ? widget.question.optionsBm
          : widget.question.options;
  CollaborationRepository? _repository;
  CollaborationRepository get _repo =>
      _repository ??= widget.repository ?? CollaborationRepository();

  String _t(String english, String bahasaMelayu) =>
      widget.state.t(english, bahasaMelayu);

  @override
  void initState() {
    super.initState();
    _acceptedAnswerId = widget.question.acceptedAnswerId;
    _blockedSubscription =
        (widget.blockedStudentIdsStream ??
                _repo.watchBlockedStudentIds(widget.state.currentStudentId))
            .listen(
              (ids) {
                if (mounted) {
                  setState(() {
                    _blockedAuthors = ids;
                    _blockedError = null;
                  });
                }
              },
              onError: (Object error) {
                if (mounted) setState(() => _blockedError = error);
              },
            );
  }

  @override
  void dispose() {
    _answer.dispose();
    _explanation.dispose();
    _blockedSubscription?.cancel();
    _returnTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(_t('Answers', 'Jawapan'))),
    body: Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Builder(builder: (context) {
                final promptBm =
                    widget.state.isBahasaMelayu &&
                        (widget.question.promptBm?.isNotEmpty ?? false)
                    ? widget.question.promptBm!
                    : null;
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      promptBm ?? widget.question.title,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    if (promptBm == null) ...[
                      const SizedBox(height: 6),
                      Text(widget.question.text),
                    ],
                  ],
                );
              }),
            ],
          ),
        ),
        Expanded(
          child: StreamBuilder<List<ForumAnswer>>(
            stream:
                widget.answersStream ?? _repo.watchAnswers(widget.question.id),
            builder: (context, snapshot) {
              if (_blockedError != null) {
                return _Message(_friendlyError(_blockedError!, widget.state));
              }
              if (snapshot.hasError) {
                return _Message(_friendlyError(snapshot.error!, widget.state));
              }
              if (!snapshot.hasData)
                return const Center(child: CircularProgressIndicator());
              var effectiveAcceptedAnswerId = _acceptedAnswerId;
              for (final answer in snapshot.data!) {
                if (answer.acceptedAt != null) {
                  effectiveAcceptedAnswerId ??= answer.id;
                  break;
                }
              }
              final answers = snapshot.data!
                  .where((answer) => !_blockedAuthors.contains(answer.authorId))
                  .toList(growable: false);
              if (answers.isEmpty) {
                return _Message(
                  _t(
                    'No answers yet. Share the steps you tried.',
                    'Belum ada jawapan. Kongsikan langkah yang telah anda cuba.',
                  ),
                );
              }
              return ListView(
                children: [
                  for (final answer in answers)
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              answer.mode == 'linked'
                                  ? (answer.explanation ?? '')
                                  : answer.text,
                            ),
                            if (answer.mode == 'linked') ...[
                              const SizedBox(height: 6),
                              Text(
                                _t(
                                  'Final answer: ${_optionLabel(answer.selectedOption)}',
                                  'Jawapan akhir: ${_optionLabel(answer.selectedOption)}',
                                ),
                                style: Theme.of(context).textTheme.bodySmall
                                    ?.copyWith(fontWeight: FontWeight.w700),
                              ),
                            ],
                            if (answer.acceptedAt != null ||
                                effectiveAcceptedAnswerId == answer.id) ...[
                              const SizedBox(height: 8),
                              Chip(
                                avatar: const Icon(
                                  Icons.check_circle,
                                  size: 18,
                                ),
                                label: Text(
                                  _t('Accepted answer', 'Jawapan diterima'),
                                ),
                              ),
                            ],
                            const SizedBox(height: 8),
                            if (answer.authorId ==
                                widget.state.currentStudentId)
                              _AuthorFeedbackText(
                                legacyFeedbackPresent:
                                    answer.feedback.state != 'queued',
                                legacyFeedback: answer.feedback,
                                feedbackFactory: () =>
                                    widget.authorFeedbackStreamForAnswer?.call(
                                      answer.id,
                                    ) ??
                                    _repo.watchOwnFeedback(answer.id),
                                status: _status,
                                isBahasaMelayu:
                                    widget.state.isBahasaMelayu,
                              ),
                            if (_status.publicBadgeLabel(
                                  answer.aiPublicState,
                                  isBahasaMelayu:
                                      widget.state.isBahasaMelayu,
                                ) !=
                                null) ...[
                              const SizedBox(height: 8),
                              _PublicAdvisoryBadge(
                                label: _status.publicBadgeLabel(
                                      answer.aiPublicState,
                                      isBahasaMelayu:
                                          widget.state.isBahasaMelayu,
                                    )!,
                                explanation: _status.publicBadgeExplanation(
                                  answer.aiPublicState,
                                  isBahasaMelayu:
                                      widget.state.isBahasaMelayu,
                                ),
                                icon:
                                    answer.aiPublicState ==
                                        'may_be_irrelevant'
                                    ? Icons.help_outline
                                    : Icons.verified_outlined,
                              ),
                            ],
                            Row(
                              children: [
                                TextButton.icon(
                                  onPressed:
                                      _inFlight.contains('helpful:${answer.id}')
                                      ? null
                                      : () => _runAction(
                                          'helpful:${answer.id}',
                                          () => _repo.markHelpful(answer.id),
                                          _t(
                                            'Marked helpful.',
                                            'Ditanda sebagai membantu.',
                                          ),
                                        ),
                                  icon: const Icon(Icons.thumb_up_alt_outlined),
                                  label: Text(_t('Helpful', 'Membantu')),
                                ),
                                if (widget.question.authorId ==
                                        widget.state.currentStudentId &&
                                    answer.authorId !=
                                        widget.state.currentStudentId &&
                                    effectiveAcceptedAnswerId == null &&
                                    answer.acceptedAt == null)
                                  TextButton.icon(
                                    onPressed: _inFlight.contains('accept')
                                        ? null
                                        : () => _accept(answer),
                                    icon: const Icon(
                                      Icons.check_circle_outline,
                                    ),
                                    label: Text(_t('Accept', 'Terima')),
                                  ),
                                const Spacer(),
                                PopupMenuButton<_AnswerAction>(
                                  tooltip: _t(
                                    'Answer actions',
                                    'Tindakan jawapan',
                                  ),
                                  onSelected: (action) =>
                                      _answerAction(action, answer),
                                  itemBuilder: (_) => [
                                    if (answer.authorId ==
                                            widget.state.currentStudentId &&
                                        answer.acceptedAt == null &&
                                        effectiveAcceptedAnswerId !=
                                            answer.id) ...[
                                      PopupMenuItem(
                                        value: _AnswerAction.edit,
                                        child: Text(
                                          _t('Edit answer', 'Edit jawapan'),
                                        ),
                                      ),
                                      PopupMenuItem(
                                        value: _AnswerAction.delete,
                                        child: Text(
                                          _t('Delete answer', 'Padam jawapan'),
                                        ),
                                      ),
                                    ],
                                    if (answer.authorId !=
                                        widget.state.currentStudentId) ...[
                                      PopupMenuItem(
                                        value: _AnswerAction.report,
                                        child: Text(_t('Report', 'Laporkan')),
                                      ),
                                      PopupMenuItem(
                                        value: _AnswerAction.block,
                                        child: Text(
                                          _t('Block student', 'Sekat murid'),
                                        ),
                                      ),
                                    ],
                                  ],
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              );
            },
          ),
        ),
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: _isLinked
                ? ConstrainedBox(
                    constraints: const BoxConstraints(maxHeight: 360),
                    child: SingleChildScrollView(
                      child: _LinkedAnswerForm(
                        options: _options,
                        isBahasaMelayu: widget.state.isBahasaMelayu,
                        submitLabel: _t('Submit answer', 'Hantar jawapan'),
                        onSubmit: _submitLinked,
                      ),
                    ),
                  )
                : Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _answer,
                          minLines: 2,
                          maxLines: 4,
                          maxLength: 4000,
                          decoration: InputDecoration(
                            hintText: _t(
                              'Explain how you worked it out…',
                              'Terangkan cara anda menyelesaikannya…',
                            ),
                          ),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.send),
                        tooltip: _t('Post answer', 'Hantar jawapan'),
                        onPressed: _submitting ? null : _submit,
                      ),
                    ],
                  ),
          ),
        ),
      ],
    ),
  );
  Future<void> _submit() async {
    final submittedText = _answer.text;
    if (submittedText.trim().length < 8) return;
    setState(() => _submitting = true);
    try {
      await _repo.submitAnswer(
        studentId: widget.state.currentStudentId,
        questionId: widget.question.id,
        text: submittedText,
      );
      if (_answer.text == submittedText) _answer.clear();
      _message(
        _t(
          'Answer posted and queued for review.',
          'Jawapan telah dihantar dan menunggu semakan.',
        ),
      );
    } catch (error) {
      _message(_friendlyError(error, widget.state));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  String _optionLabel(int? index) {
    final options = _options;
    if (index == null || index < 0 || index >= options.length) return '';
    return options[index];
  }

  Future<bool> _submitLinked(int selectedOption, String explanation) async {
    try {
      await _repo.submitLinkedAnswer(
        discussionId: widget.question.id,
        selectedOption: selectedOption,
        explanation: explanation,
      );
      _message(
        _t(
          'Answer posted and queued for review.',
          'Jawapan telah dihantar dan menunggu semakan.',
        ),
      );
      if (widget.returnOnLinkedSubmit) {
        _returnTimer?.cancel();
        _returnTimer = Timer(const Duration(seconds: 2), () {
          if (mounted) Navigator.of(context).pop();
        });
      }
      return true;
    } catch (error) {
      _message(_friendlyError(error, widget.state));
      return false;
    }
  }

  Future<void> _editLinkedAnswer(ForumAnswer answer) async {
    final result = await showDialog<_LinkedAnswerResult>(
      context: context,
      builder: (_) => _LinkedAnswerDialog(
        options: _options,
        isBahasaMelayu: widget.state.isBahasaMelayu,
        initialOption: answer.selectedOption,
        initialExplanation: answer.explanation ?? '',
      ),
    );
    if (result == null) return;
    await _runAction(
      'edit:${answer.id}',
      () => _repo.editLinkedAnswer(
        answerId: answer.id,
        selectedOption: result.option,
        explanation: result.explanation,
      ),
      _t(
        'Response edited successfully. Feedback review queued.',
        'Jawapan berjaya diedit. Semakan maklum balas sedang menunggu.',
      ),
    );
  }

  Future<bool> _runAction(
    String key,
    Future<void> Function() action,
    String success,
  ) async {
    if (_inFlight.contains(key)) return false;
    setState(() => _inFlight.add(key));
    try {
      await action();
      _message(success);
      return true;
    } catch (error) {
      _message(_friendlyError(error, widget.state));
      return false;
    } finally {
      if (mounted) setState(() => _inFlight.remove(key));
    }
  }

  Future<void> _accept(ForumAnswer answer) async {
    final accepted = await _runAction(
      'accept',
      () => _repo.acceptAnswer(answer.id),
      _t('Answer accepted.', 'Jawapan diterima.'),
    );
    if (accepted && mounted) setState(() => _acceptedAnswerId = answer.id);
  }

  Future<void> _answerAction(_AnswerAction action, ForumAnswer answer) async {
    if (action == _AnswerAction.delete) {
      await _confirmDeleteAnswer(answer);
      return;
    }
    if (action == _AnswerAction.block) {
      final blocked = await _runAction(
        'block:${answer.authorId}',
        () => _repo.block(
          studentId: widget.state.currentStudentId,
          blockedStudentId: answer.authorId,
        ),
        _t(
          'Student blocked on your forum view.',
          'Murid disekat daripada paparan forum anda.',
        ),
      );
      if (blocked && mounted) {
        setState(() => _blockedAuthors = {..._blockedAuthors, answer.authorId});
      }
      return;
    }
    if (action == _AnswerAction.edit && answer.mode == 'linked') {
      await _editLinkedAnswer(answer);
      return;
    }
    final value = await showDialog<String>(
      context: context,
      builder: (_) => _AnswerActionDialog(
        initialText: action == _AnswerAction.edit ? answer.text : '',
        title: action == _AnswerAction.edit
            ? _t('Edit answer', 'Edit jawapan')
            : _t('Report answer', 'Laporkan jawapan'),
        cancelLabel: _t('Cancel', 'Batal'),
        submitLabel: _t('Submit', 'Hantar'),
      ),
    );
    if (value == null ||
        value.trim().length < (action == _AnswerAction.edit ? 8 : 3))
      return;
    await _runAction(
      '${action.name}:${answer.id}',
      action == _AnswerAction.edit
          ? () => _repo.editAnswer(
              studentId: widget.state.currentStudentId,
              answerId: answer.id,
              text: value,
            )
          : () => _repo.report(
              targetType: 'answer',
              targetId: answer.id,
              reason: value,
            ),
      action == _AnswerAction.edit
          ? _t(
              'Response edited successfully. Feedback review queued.',
              'Jawapan berjaya diedit. Semakan maklum balas sedang menunggu.',
            )
          : _t('Report submitted.', 'Laporan telah dihantar.'),
    );
  }

  Future<void> _confirmDeleteAnswer(ForumAnswer answer) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(_t('Delete this answer?', 'Padam jawapan ini?')),
        content: Text(
          _t(
            'Your answer and its AI review will be removed. This action cannot be undone.',
            'Jawapan anda dan semakan AI akan dipadam. Tindakan ini tidak boleh dibatalkan.',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(_t('Cancel', 'Batal')),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(_t('Delete', 'Padam')),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    await _runAction(
      'delete:${answer.id}',
      () => _repo.deleteAnswer(answer.id),
      _t('Answer deleted.', 'Jawapan telah dipadam.'),
    );
  }

  void _message(String message) {
    if (mounted)
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
  }
}

enum _AnswerAction { edit, report, block, delete }

enum _QuestionAction { delete }

class _AnswerActionDialog extends StatefulWidget {
  const _AnswerActionDialog({
    required this.initialText,
    required this.title,
    required this.cancelLabel,
    required this.submitLabel,
  });

  final String initialText;
  final String title;
  final String cancelLabel;
  final String submitLabel;

  @override
  State<_AnswerActionDialog> createState() => _AnswerActionDialogState();
}

class _AnswerActionDialogState extends State<_AnswerActionDialog> {
  late final TextEditingController _controller = TextEditingController(
    text: widget.initialText,
  );

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(widget.title),
    content: TextField(controller: _controller, minLines: 3, maxLines: 6),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: Text(widget.cancelLabel),
      ),
      FilledButton(
        onPressed: () => Navigator.pop(context, _controller.text),
        child: Text(widget.submitLabel),
      ),
    ],
  );
}

String _friendlyError(Object error, AppState state) {
  String t(String english, String bahasaMelayu) =>
      state.t(english, bahasaMelayu);
  if (error is FirebaseFunctionsException) {
    if ({
      'failed-precondition',
      'already-exists',
      'invalid-argument',
    }.contains(error.code)) {
      final message = error.message?.trim();
      if (message != null && message.isNotEmpty) {
        return _localizedFunctionMessage(message, state);
      }
    }
    if (error.code == 'permission-denied') {
      return t(
        'This action is not allowed for your account or this content.',
        'Tindakan ini tidak dibenarkan untuk akaun atau kandungan ini.',
      );
    }
    if (error.code == 'not-found') {
      return t(
        'This forum content is no longer available.',
        'Kandungan forum ini tidak lagi tersedia.',
      );
    }
    if ({
      'unavailable',
      'deadline-exceeded',
      'internal',
      'unimplemented',
    }.contains(error.code)) {
      return t(
        'The forum service is temporarily unavailable. Your draft is safe; please retry.',
        'Perkhidmatan forum tidak tersedia buat sementara waktu. Draf anda selamat; sila cuba lagi.',
      );
    }
  }
  if (error is FirebaseException && error.code == 'permission-denied') {
    return t(
      'This action is not allowed for your account or this content.',
      'Tindakan ini tidak dibenarkan untuk akaun atau kandungan ini.',
    );
  }
  if (error is FirebaseException &&
      (error.code == 'unavailable' || error.code == 'deadline-exceeded')) {
    return t(
      'The forum is temporarily unavailable. Your draft is safe; please retry.',
      'Forum tidak tersedia buat sementara waktu. Draf anda selamat; sila cuba lagi.',
    );
  }
  if (error is StateError) {
    final message = error.message.toString().trim();
    if (message.isNotEmpty) return message;
  }
  return t(
    'The action could not be completed. Please retry.',
    'Tindakan tidak dapat diselesaikan. Sila cuba lagi.',
  );
}

String _localizedFunctionMessage(String message, AppState state) {
  final bahasaMelayu = switch (message) {
    'You cannot mark your own answer helpful.' =>
      'Anda tidak boleh menandakan jawapan sendiri sebagai membantu.',
    'Only the question author may accept an answer.' =>
      'Hanya penulis soalan boleh menerima jawapan.',
    'You cannot accept your own answer.' =>
      'Anda tidak boleh menerima jawapan sendiri.',
    'This question already has an accepted answer.' =>
      'Soalan ini sudah mempunyai jawapan yang diterima.',
    'You cannot report your own content.' =>
      'Anda tidak boleh melaporkan kandungan sendiri.',
    'Report reason must be between 3 and 500 characters.' =>
      'Sebab laporan mestilah antara 3 hingga 500 aksara.',
    _ => message,
  };
  return state.t(message, bahasaMelayu);
}

class _Message extends StatelessWidget {
  const _Message(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Text(text, textAlign: TextAlign.center),
    ),
  );
}

class _LinkedAnswerForm extends StatefulWidget {
  const _LinkedAnswerForm({
    required this.options,
    required this.isBahasaMelayu,
    required this.submitLabel,
    required this.onSubmit,
    this.initialOption,
    this.initialExplanation = '',
  });

  final List<String> options;
  final bool isBahasaMelayu;
  final String submitLabel;
  final Future<bool> Function(int option, String explanation) onSubmit;
  final int? initialOption;
  final String initialExplanation;

  @override
  State<_LinkedAnswerForm> createState() => _LinkedAnswerFormState();
}

class _LinkedAnswerFormState extends State<_LinkedAnswerForm> {
  int? _selectedOption;
  late final TextEditingController _explanation = TextEditingController(
    text: widget.initialExplanation,
  );
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _selectedOption = widget.initialOption;
  }

  @override
  void dispose() {
    _explanation.dispose();
    super.dispose();
  }

  String _t(String english, String bahasaMelayu) =>
      widget.isBahasaMelayu ? bahasaMelayu : english;

  void _message(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _submit() async {
    final option = _selectedOption;
    final explanation = _explanation.text.trim();
    if (option == null) {
      _message(_t('Select an option first.', 'Pilih satu pilihan dahulu.'));
      return;
    }
    if (explanation.length < 8) {
      _message(
        _t(
          'Add at least 8 characters of explanation.',
          'Tambah sekurang-kurangnya 8 aksara penerangan.',
        ),
      );
      return;
    }
    setState(() => _submitting = true);
    try {
      final success = await widget.onSubmit(option, explanation);
      if (success && mounted) {
        setState(() {
          _selectedOption = null;
          _explanation.clear();
        });
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          _t('Choose your final answer', 'Pilih jawapan akhir'),
          style: theme.textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        for (var index = 0; index < widget.options.length; index++) ...[
          _OptionTile(
            label: widget.options[index],
            selected: _selectedOption == index,
            onTap: _submitting
                ? null
                : () => setState(() => _selectedOption = index),
          ),
          if (index < widget.options.length - 1) const SizedBox(height: 8),
        ],
        const SizedBox(height: 12),
        TextField(
          controller: _explanation,
          minLines: 2,
          maxLines: 4,
          maxLength: 4000,
          decoration: InputDecoration(
            labelText: _t('Explain your answer', 'Terangkan jawapan anda'),
            hintText: _t(
              'Show the steps you used…',
              'Tunjukkan langkah yang anda gunakan…',
            ),
          ),
        ),
        const SizedBox(height: 8),
        FilledButton.icon(
          onPressed: _submitting ? null : _submit,
          icon: _submitting
              ? const SizedBox.square(
                  dimension: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.send),
          label: Text(widget.submitLabel),
        ),
      ],
    );
  }
}

class _OptionTile extends StatelessWidget {
  const _OptionTile({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: selected
              ? oasis.violet.withValues(alpha: .10)
              : oasis.surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: selected ? oasis.violet : oasis.outline,
            width: 1.4,
          ),
        ),
        child: Row(
          children: [
            Icon(
              selected
                  ? Icons.radio_button_checked
                  : Icons.radio_button_off,
              color: selected ? oasis.violet : oasis.secondaryInk,
              size: 20,
            ),
            const SizedBox(width: 10),
            Expanded(child: Text(label, style: theme.textTheme.bodyMedium)),
          ],
        ),
      ),
    );
  }
}

class _LinkedAnswerResult {
  const _LinkedAnswerResult(this.option, this.explanation);

  final int option;
  final String explanation;
}

class _LinkedAnswerDialog extends StatelessWidget {
  const _LinkedAnswerDialog({
    required this.options,
    required this.isBahasaMelayu,
    this.initialOption,
    this.initialExplanation,
  });

  final List<String> options;
  final bool isBahasaMelayu;
  final int? initialOption;
  final String? initialExplanation;

  @override
  Widget build(BuildContext context) {
    final isBahasaMelayu = this.isBahasaMelayu;
    return AlertDialog(
      title: Text(
        isBahasaMelayu ? 'Edit jawapan' : 'Edit answer',
      ),
      content: SingleChildScrollView(
        child: _LinkedAnswerForm(
          options: options,
          isBahasaMelayu: isBahasaMelayu,
          initialOption: initialOption,
          initialExplanation: initialExplanation ?? '',
          submitLabel: isBahasaMelayu ? 'Hantar' : 'Submit',
          onSubmit: (option, explanation) async {
            Navigator.of(
              context,
            ).pop(_LinkedAnswerResult(option, explanation));
            return true;
          },
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(isBahasaMelayu ? 'Batal' : 'Cancel'),
        ),
      ],
    );
  }
}

class _AuthorFeedbackText extends StatefulWidget {
  const _AuthorFeedbackText({
    required this.legacyFeedbackPresent,
    required this.legacyFeedback,
    required this.feedbackFactory,
    required this.status,
    required this.isBahasaMelayu,
  });

  final bool legacyFeedbackPresent;
  final ForumAnswerFeedback legacyFeedback;
  final Stream<ForumAnswerFeedback> Function() feedbackFactory;
  final ForumAiStatusService status;
  final bool isBahasaMelayu;

  @override
  State<_AuthorFeedbackText> createState() => _AuthorFeedbackTextState();
}

class _AuthorFeedbackTextState extends State<_AuthorFeedbackText> {
  Stream<ForumAnswerFeedback>? _stream;

  @override
  void initState() {
    super.initState();
    if (!widget.legacyFeedbackPresent) {
      _stream = widget.feedbackFactory();
    }
  }

  @override
  Widget build(BuildContext context) {
    final stream = _stream;
    if (stream == null) {
      return Text(
        widget.status.statusText(
          widget.legacyFeedback,
          isBahasaMelayu: widget.isBahasaMelayu,
        ),
        style: Theme.of(context).textTheme.bodySmall,
      );
    }
    return StreamBuilder<ForumAnswerFeedback>(
      stream: stream,
      builder: (context, snapshot) {
        final feedback = snapshot.data;
        if (feedback == null) return const SizedBox.shrink();
        return Text(
          widget.status.statusText(
            feedback,
            isBahasaMelayu: widget.isBahasaMelayu,
          ),
          style: Theme.of(context).textTheme.bodySmall,
        );
      },
    );
  }
}

class _PublicAdvisoryBadge extends StatelessWidget {
  const _PublicAdvisoryBadge({
    required this.label,
    required this.explanation,
    required this.icon,
  });

  final String label;
  final String? explanation;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: explanation ?? label,
      container: true,
      child: Chip(
        avatar: Icon(icon, size: 18),
        label: Text(label),
      ),
    );
  }
}
