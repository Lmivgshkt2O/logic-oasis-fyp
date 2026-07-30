import 'package:flutter/material.dart';
import 'package:logic_oasis/shared/models/forum_answer.dart';
import 'package:logic_oasis/shared/models/forum_question.dart';
import 'package:logic_oasis/shared/repositories/collaboration_repository.dart';
import 'package:logic_oasis/shared/services/forum_ai_status_service.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

class QaForumPage extends StatefulWidget {
  const QaForumPage({super.key, required this.state, this.repository});
  final AppState state;
  final CollaborationRepository? repository;

  @override
  State<QaForumPage> createState() => _QaForumPageState();
}

class _QaForumPageState extends State<QaForumPage> {
  late final CollaborationRepository _repository =
      widget.repository ?? CollaborationRepository();

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Q&A Forum')),
    floatingActionButton: FloatingActionButton.extended(
      onPressed: () => _composeQuestion(context),
      icon: const Icon(Icons.add_comment_outlined),
      label: const Text('Ask a question'),
    ),
    body: StreamBuilder<List<ForumQuestion>>(
      stream: _repository.watchQuestions(),
      builder: (context, snapshot) {
        if (snapshot.hasError)
          return const _Message(
            'The forum could not be loaded. Please check your connection and try again.',
          );
        if (!snapshot.hasData)
          return const Center(child: CircularProgressIndicator());
        final questions = snapshot.data!;
        if (questions.isEmpty)
          return const _Message(
            'No questions yet. Start the conversation by asking how you solved a problem.',
          );
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
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
        );
      },
    ),
  );

  Future<void> _composeQuestion(BuildContext context) async {
    final title = TextEditingController();
    final body = TextEditingController();
    final submitted = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Ask for help'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: title,
              maxLength: 140,
              decoration: const InputDecoration(labelText: 'Question title'),
            ),
            TextField(
              controller: body,
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
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Post'),
          ),
        ],
      ),
    );
    if (submitted != true ||
        title.text.trim().length < 8 ||
        body.text.trim().length < 20)
      return;
    await _repository.createQuestion(
      studentId: widget.state.currentStudentId,
      title: title.text,
      text: body.text,
    );
  }

  void _openAnswers(BuildContext context, ForumQuestion question) =>
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => _AnswersPage(
            question: question,
            state: widget.state,
            repository: _repository,
          ),
        ),
      );
}

class _AnswersPage extends StatefulWidget {
  const _AnswersPage({
    required this.question,
    required this.state,
    required this.repository,
  });
  final ForumQuestion question;
  final AppState state;
  final CollaborationRepository repository;
  @override
  State<_AnswersPage> createState() => _AnswersPageState();
}

class _AnswersPageState extends State<_AnswersPage> {
  final _answer = TextEditingController();
  final _status = const ForumAiStatusService();
  @override
  void dispose() {
    _answer.dispose();
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
            stream: widget.repository.watchAnswers(widget.question.id),
            builder: (context, snapshot) {
              if (!snapshot.hasData)
                return const Center(child: CircularProgressIndicator());
              return ListView(
                children: [
                  for (final answer in snapshot.data!)
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(answer.text),
                            const SizedBox(height: 8),
                            Text(
                              _status.statusText(answer.feedback),
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                            Row(
                              children: [
                                TextButton.icon(
                                  onPressed: () =>
                                      widget.repository.markHelpful(answer.id),
                                  icon: const Icon(Icons.thumb_up_alt_outlined),
                                  label: const Text('Helpful'),
                                ),
                                if (widget.question.authorId ==
                                        widget.state.currentStudentId &&
                                    answer.authorId !=
                                        widget.state.currentStudentId &&
                                    answer.acceptedAt == null)
                                  TextButton.icon(
                                    onPressed: () => widget.repository
                                        .acceptAnswer(answer.id),
                                    icon: const Icon(
                                      Icons.check_circle_outline,
                                    ),
                                    label: const Text('Accept'),
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
                  onPressed: _submit,
                ),
              ],
            ),
          ),
        ),
      ],
    ),
  );
  Future<void> _submit() async {
    if (_answer.text.trim().length < 8) return;
    await widget.repository.submitAnswer(
      studentId: widget.state.currentStudentId,
      questionId: widget.question.id,
      text: _answer.text,
    );
    _answer.clear();
  }
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
