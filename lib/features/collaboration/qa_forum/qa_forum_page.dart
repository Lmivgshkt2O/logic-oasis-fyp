import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:cloud_functions/cloud_functions.dart';
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
    this.questionsStream,
    this.blockedStudentIdsStream,
    this.answersStreamForQuestion,
  });
  final AppState state;
  final CollaborationRepository? repository;
  final Stream<List<ForumQuestion>>? questionsStream;
  final Stream<Set<String>>? blockedStudentIdsStream;
  final Stream<List<ForumAnswer>> Function(String questionId)?
  answersStreamForQuestion;

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
  Set<String> _blockedAuthors = const {};
  Object? _blockedError;
  bool _postingQuestion = false;

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
  }

  @override
  void dispose() {
    _filter.dispose();
    _questionTitle.dispose();
    _questionBody.dispose();
    _blockedSubscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Q&A Forum')),
    floatingActionButton: FloatingActionButton.extended(
      onPressed: () => _composeQuestion(context),
      icon: const Icon(Icons.add_comment_outlined),
      label: const Text('Ask a question'),
    ),
    body: StreamBuilder<List<ForumQuestion>>(
      stream: widget.questionsStream ?? _repo.watchQuestions(),
      builder: (context, snapshot) {
        if (_blockedError != null) {
          return _Message(_friendlyError(_blockedError!));
        }
        if (snapshot.hasError) {
          final error = snapshot.error;
          final denied =
              error is FirebaseException && error.code == 'permission-denied';
          return _Message(
            denied
                ? 'Forum access is unavailable for this account. Sign in with a student profile, then try again.'
                : 'The forum could not be loaded. Please check your connection and try again.',
          );
        }
        if (!snapshot.hasData)
          return const Center(child: CircularProgressIndicator());
        final query = _filter.text.trim().toLowerCase();
        final questions = snapshot.data!
            .where(
              (question) =>
                  !_blockedAuthors.contains(question.authorId) &&
                  (query.isEmpty ||
                      question.title.toLowerCase().contains(query) ||
                      question.text.toLowerCase().contains(query)),
            )
            .toList(growable: false);
        if (questions.isEmpty)
          return Column(
            children: [
              _filterField(),
              Expanded(
                child: _Message(
                  query.isEmpty
                      ? 'No questions yet. Start the conversation by asking how you solved a problem.'
                      : 'No questions match this filter.',
                ),
              ),
            ],
          );
        return Column(
          children: [
            _filterField(),
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
                itemCount: questions.length,
                separatorBuilder: (_, _) => const SizedBox(height: 10),
                itemBuilder: (context, index) {
                  final question = questions[index];
                  return Card(
                    child: ListTile(
                      title: Text(question.title),
                      subtitle: Text(
                        question.text,
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                      ),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => _openAnswers(context, question),
                    ),
                  );
                },
              ),
            ),
          ],
        );
      },
    ),
  );

  Widget _filterField() => Padding(
    padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
    child: TextField(
      controller: _filter,
      onChanged: (_) => setState(() {}),
      decoration: InputDecoration(
        prefixIcon: const Icon(Icons.search),
        hintText: 'Filter questions',
        suffixIcon: _filter.text.isEmpty
            ? null
            : IconButton(
                tooltip: 'Clear filter',
                onPressed: () {
                  _filter.clear();
                  setState(() {});
                },
                icon: const Icon(Icons.clear),
              ),
      ),
    ),
  );

  Future<void> _composeQuestion(BuildContext context) async {
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) => PopScope(
          canPop: !_postingQuestion,
          child: AlertDialog(
            title: const Text('Ask for help'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: _questionTitle,
                  maxLength: 140,
                  decoration: const InputDecoration(
                    labelText: 'Question title',
                  ),
                ),
                TextField(
                  controller: _questionBody,
                  minLines: 3,
                  maxLines: 6,
                  maxLength: 3000,
                  decoration: const InputDecoration(
                    labelText: 'What have you tried?',
                  ),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: _postingQuestion
                    ? null
                    : () => Navigator.pop(dialogContext),
                child: const Text('Cancel'),
              ),
              FilledButton.icon(
                onPressed: _postingQuestion
                    ? null
                    : () async {
                        if (_questionTitle.text.trim().length < 8 ||
                            _questionBody.text.trim().length < 20) {
                          _showMessage(
                            'Add a clear title and explain what you tried.',
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
                          _showMessage('Question posted.');
                        } catch (error) {
                          _showMessage(_friendlyError(error));
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
                label: const Text('Post'),
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
          builder: (_) => _AnswersPage(
            question: question,
            state: widget.state,
            repository: _repository ?? widget.repository,
            answersStream: widget.answersStreamForQuestion?.call(question.id),
            blockedStudentIdsStream: widget.blockedStudentIdsStream,
          ),
        ),
      );
}

class _AnswersPage extends StatefulWidget {
  const _AnswersPage({
    required this.question,
    required this.state,
    this.repository,
    this.answersStream,
    this.blockedStudentIdsStream,
  });
  final ForumQuestion question;
  final AppState state;
  final CollaborationRepository? repository;
  final Stream<List<ForumAnswer>>? answersStream;
  final Stream<Set<String>>? blockedStudentIdsStream;
  @override
  State<_AnswersPage> createState() => _AnswersPageState();
}

class _AnswersPageState extends State<_AnswersPage> {
  final _answer = TextEditingController();
  final _status = const ForumAiStatusService();
  final Set<String> _inFlight = {};
  StreamSubscription<Set<String>>? _blockedSubscription;
  Set<String> _blockedAuthors = const {};
  Object? _blockedError;
  String? _acceptedAnswerId;
  bool _submitting = false;
  CollaborationRepository? _repository;
  CollaborationRepository get _repo =>
      _repository ??= widget.repository ?? CollaborationRepository();

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
    _blockedSubscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Answers')),
    body: Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.question.title,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 6),
              Text(widget.question.text),
            ],
          ),
        ),
        Expanded(
          child: StreamBuilder<List<ForumAnswer>>(
            stream:
                widget.answersStream ?? _repo.watchAnswers(widget.question.id),
            builder: (context, snapshot) {
              if (_blockedError != null) {
                return _Message(_friendlyError(_blockedError!));
              }
              if (snapshot.hasError) {
                return _Message(_friendlyError(snapshot.error!));
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
                return const _Message(
                  'No answers yet. Share the steps you tried.',
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
                            Text(answer.text),
                            if (answer.acceptedAt != null ||
                                effectiveAcceptedAnswerId == answer.id) ...[
                              const SizedBox(height: 8),
                              const Chip(
                                avatar: Icon(Icons.check_circle, size: 18),
                                label: Text('Accepted answer'),
                              ),
                            ],
                            const SizedBox(height: 8),
                            Text(
                              _status.statusText(answer.feedback),
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                            Row(
                              children: [
                                TextButton.icon(
                                  onPressed:
                                      _inFlight.contains('helpful:${answer.id}')
                                      ? null
                                      : () => _runAction(
                                          'helpful:${answer.id}',
                                          () => _repo.markHelpful(answer.id),
                                          'Marked helpful.',
                                        ),
                                  icon: const Icon(Icons.thumb_up_alt_outlined),
                                  label: const Text('Helpful'),
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
                                    label: const Text('Accept'),
                                  ),
                                const Spacer(),
                                PopupMenuButton<_AnswerAction>(
                                  tooltip: 'Answer actions',
                                  onSelected: (action) =>
                                      _answerAction(action, answer),
                                  itemBuilder: (_) => [
                                    if (answer.authorId ==
                                            widget.state.currentStudentId &&
                                        answer.acceptedAt == null)
                                      const PopupMenuItem(
                                        value: _AnswerAction.edit,
                                        child: Text('Edit answer'),
                                      ),
                                    if (answer.authorId !=
                                        widget.state.currentStudentId) ...[
                                      const PopupMenuItem(
                                        value: _AnswerAction.report,
                                        child: Text('Report'),
                                      ),
                                      const PopupMenuItem(
                                        value: _AnswerAction.block,
                                        child: Text('Block student'),
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
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _answer,
                    minLines: 2,
                    maxLines: 4,
                    maxLength: 4000,
                    decoration: const InputDecoration(
                      hintText: 'Explain how you worked it out…',
                    ),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.send),
                  tooltip: 'Post answer',
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
      _message('Answer posted and queued for review.');
    } catch (error) {
      _message(_friendlyError(error));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
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
      _message(_friendlyError(error));
      return false;
    } finally {
      if (mounted) setState(() => _inFlight.remove(key));
    }
  }

  Future<void> _accept(ForumAnswer answer) async {
    final accepted = await _runAction(
      'accept',
      () => _repo.acceptAnswer(answer.id),
      'Answer accepted.',
    );
    if (accepted && mounted) setState(() => _acceptedAnswerId = answer.id);
  }

  Future<void> _answerAction(_AnswerAction action, ForumAnswer answer) async {
    if (action == _AnswerAction.block) {
      final blocked = await _runAction(
        'block:${answer.authorId}',
        () => _repo.block(
          studentId: widget.state.currentStudentId,
          blockedStudentId: answer.authorId,
        ),
        'Student blocked on your forum view.',
      );
      if (blocked && mounted) {
        setState(() => _blockedAuthors = {..._blockedAuthors, answer.authorId});
      }
      return;
    }
    final controller = TextEditingController(
      text: action == _AnswerAction.edit ? answer.text : '',
    );
    final value = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          action == _AnswerAction.edit ? 'Edit answer' : 'Report answer',
        ),
        content: TextField(controller: controller, minLines: 3, maxLines: 6),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('Submit'),
          ),
        ],
      ),
    );
    controller.dispose();
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
          ? 'Revision queued for review.'
          : 'Report submitted.',
    );
  }

  void _message(String message) {
    if (mounted)
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
  }
}

enum _AnswerAction { edit, report, block }

String _friendlyError(Object error) {
  if (error is FirebaseFunctionsException &&
      error.code == 'permission-denied') {
    return 'This action is unavailable for your account.';
  }
  if (error is FirebaseFunctionsException &&
      (error.code == 'unavailable' || error.code == 'deadline-exceeded')) {
    return 'The forum is temporarily unavailable. Your draft is safe; please retry.';
  }
  if (error is FirebaseException && error.code == 'permission-denied') {
    return 'This action is unavailable for your account.';
  }
  if (error is FirebaseException &&
      (error.code == 'unavailable' || error.code == 'deadline-exceeded')) {
    return 'The forum is temporarily unavailable. Your draft is safe; please retry.';
  }
  return 'The action could not be completed. Please retry.';
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
