import 'package:flutter/material.dart';
import 'package:logic_oasis/features/quiz/widgets/answer_tile.dart';
import 'package:logic_oasis/features/quiz/result_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/question_response.dart';
import 'package:logic_oasis/shared/models/quiz_completion.dart';
import 'package:logic_oasis/shared/models/quiz_question.dart';
import 'package:logic_oasis/shared/models/quiz_session.dart';
import 'package:logic_oasis/shared/services/quiz_session_service.dart';
import 'package:logic_oasis/shared/services/ai_status_service.dart';
import 'package:logic_oasis/shared/widgets/logic_oasis_figma_components.dart';
import 'package:logic_oasis/shared/widgets/recommendation_box.dart';

class QuizPage extends StatefulWidget {
  const QuizPage({
    super.key,
    required this.session,
    required this.title,
    required this.isBahasaMelayu,
    this.sessionService,
  });

  final QuizSession session;
  final String title;
  final bool isBahasaMelayu;
  final QuizSessionService? sessionService;

  @override
  State<QuizPage> createState() => _QuizPageState();
}

class _QuizPageState extends State<QuizPage> {
  late final QuizSessionService _sessionService;
  int questionIndex = 0;
  DateTime? _questionStartedAt;
  QuestionResponse? _pendingResponse;
  QuestionResponse? _validatedResponse;
  bool _submitting = false;
  bool _finalizing = false;
  late final AiStatusService _aiStatusService;

  QuizQuestion get currentQuestion => widget.session.questions[questionIndex];
  bool get _hasSelection =>
      _pendingResponse != null || _validatedResponse != null;

  @override
  void initState() {
    super.initState();
    _sessionService = widget.sessionService ?? QuizSessionService();
    _aiStatusService = AiStatusService();
    _questionStartedAt = DateTime.now();
  }

  Future<void> chooseAnswer(int index) async {
    if (_hasSelection || _submitting || _finalizing) return;
    final pending = QuestionResponse(
      sessionId: widget.session.id,
      questionId: currentQuestion.id,
      selectedIndex: index,
      sequenceIndex: questionIndex,
      // Deterministic across retries; the server seals exactly this response.
      idempotencyKey:
          '${widget.session.id}:${currentQuestion.id}:$questionIndex',
    );
    setState(() {
      _pendingResponse = pending;
      _submitting = true;
    });
    await _submitPendingResponse();
  }

  Future<void> _submitPendingResponse() async {
    final pending = _pendingResponse;
    if (pending == null) return;
    if (!_submitting) {
      setState(() => _submitting = true);
    }
    try {
      final response = await _sessionService.submitResponse(
        pendingResponse: pending,
        responseTimeMs: DateTime.now()
            .difference(_questionStartedAt!)
            .inMilliseconds,
      );
      if (!mounted) return;
      if (response.sessionId != widget.session.id ||
          response.questionId != currentQuestion.id ||
          !response.isValidated) {
        throw const QuizSessionException(
          'The secure response did not match this question.',
        );
      }
      setState(() {
        _validatedResponse = response;
        _pendingResponse = null;
        _submitting = false;
      });
    } on QuizSessionException catch (error) {
      if (!mounted) return;
      setState(() => _submitting = false);
      _showRetryMessage(error.message);
    } catch (_) {
      if (!mounted) return;
      setState(() => _submitting = false);
      _showRetryMessage(
        widget.isBahasaMelayu
            ? 'Sambungan belum selesai. Cuba semula semakan selamat ini.'
            : 'The connection did not finish. Retry this secure check.',
      );
    }
  }

  void _showRetryMessage(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> goNext() async {
    if (_validatedResponse == null || _finalizing) return;
    if (questionIndex < widget.session.questions.length - 1) {
      setState(() {
        questionIndex += 1;
        _pendingResponse = null;
        _validatedResponse = null;
        _questionStartedAt = DateTime.now();
      });
      return;
    }
    setState(() => _finalizing = true);
    try {
      final completion = await _sessionService.finalizeSession(
        widget.session.id,
      );
      if (!mounted) return;
      await _showCompletion(completion);
      if (mounted) Navigator.of(context).pop(completion);
    } on QuizSessionException catch (error) {
      if (!mounted) return;
      setState(() => _finalizing = false);
      _showRetryMessage(error.message);
    } catch (_) {
      if (!mounted) return;
      setState(() => _finalizing = false);
      _showRetryMessage(
        widget.isBahasaMelayu
            ? 'Markah belum dapat dimuktamadkan. Cuba semula.'
            : 'Your score could not be finalized yet. Please retry.',
      );
    }
  }

  Future<void> _showCompletion(QuizCompletion completion) {
    final correct = completion.correctCount;
    final total = completion.totalQuestions ?? widget.session.questions.length;
    final score = completion.score ?? 0;
    final attemptId = completion.attemptId;
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        title: Text(widget.isBahasaMelayu ? 'Kuiz selesai!' : 'Quiz complete!'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              widget.isBahasaMelayu
                  ? 'Semakan pelayan mengesahkan $correct daripada $total betul ($score%).'
                  : 'The server confirmed $correct out of $total correct ($score%).',
            ),
            if (attemptId != null && attemptId.isNotEmpty) ...[
              const SizedBox(height: 14),
              StreamBuilder(
                stream: _aiStatusService.watchAttempt(attemptId),
                builder: (context, snapshot) {
                  final diagnosis = snapshot.data;
                  if (diagnosis == null) {
                    return Text(
                      widget.isBahasaMelayu
                          ? 'Markah anda disimpan. Analisis sedang bermula…'
                          : 'Your score is saved. Analysis is starting…',
                    );
                  }
                  return AiAnalysisStatusCard(
                    diagnosis: diagnosis,
                    isBahasaMelayu: widget.isBahasaMelayu,
                  );
                },
              ),
            ],
          ],
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(widget.isBahasaMelayu ? 'Selesai' : 'Done'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    final progress = (questionIndex + 1) / widget.session.questions.length;
    final options = currentQuestion.localizedOptions(widget.isBahasaMelayu);
    final feedback = _validatedResponse;
    final selectedIndex =
        feedback?.selectedIndex ?? _pendingResponse?.selectedIndex;

    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: LogicOasisScaffold(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
        children: [
          LinearProgressIndicator(value: progress),
          const SizedBox(height: 18),
          Text(
            l10n.questionProgress(
              questionIndex + 1,
              widget.session.questions.length,
            ),
            style: theme.textTheme.bodyMedium,
          ),
          const SizedBox(height: 8),
          Text(
            currentQuestion.localizedQuestion(widget.isBahasaMelayu),
            style: theme.textTheme.headlineMedium,
          ),
          const SizedBox(height: 20),
          for (var i = 0; i < options.length; i++) ...[
            AnswerTile(
              label: options[i],
              selected: selectedIndex == i,
              correct: feedback?.isCorrect == true && selectedIndex == i,
              wrong: feedback?.isCorrect == false && selectedIndex == i,
              onTap: () => chooseAnswer(i),
            ),
            const SizedBox(height: 10),
          ],
          if (_submitting) ...[
            const SizedBox(height: 10),
            const Center(child: CircularProgressIndicator()),
          ] else if (_pendingResponse != null) ...[
            const SizedBox(height: 10),
            RecommendationBox(
              text: widget.isBahasaMelayu
                  ? 'Pilihan anda menunggu semakan selamat.'
                  : 'Your choice is waiting for a secure check.',
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _submitPendingResponse,
              icon: const Icon(Icons.refresh),
              label: Text(
                widget.isBahasaMelayu
                    ? 'Cuba Semula Semakan'
                    : 'Retry Secure Check',
              ),
            ),
          ] else if (feedback != null) ...[
            const SizedBox(height: 10),
            RecommendationBox(
              text:
                  feedback
                      .localizedExplanation(widget.isBahasaMelayu)
                      .isNotEmpty
                  ? feedback.localizedExplanation(widget.isBahasaMelayu)
                  : widget.isBahasaMelayu
                  ? 'Pilihan anda telah disemak dengan selamat.'
                  : 'Your choice has been securely checked.',
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: goNext,
              icon: Icon(
                questionIndex == widget.session.questions.length - 1
                    ? Icons.check
                    : Icons.arrow_forward,
              ),
              label: Text(
                _finalizing
                    ? (widget.isBahasaMelayu
                          ? 'Memuktamadkan...'
                          : 'Finalizing...')
                    : questionIndex == widget.session.questions.length - 1
                    ? l10n.finishQuiz
                    : l10n.nextQuestion,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
