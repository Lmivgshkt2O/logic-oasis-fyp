import 'package:flutter/material.dart';
import 'package:logic_oasis/features/quiz/widgets/answer_tile.dart';
import 'package:logic_oasis/shared/models/quiz_question.dart';
import 'package:logic_oasis/shared/models/topic.dart';
import 'package:logic_oasis/shared/widgets/recommendation_box.dart';

class QuizPage extends StatefulWidget {
  const QuizPage({super.key, required this.topic});

  final Topic topic;

  @override
  State<QuizPage> createState() => _QuizPageState();
}

class _QuizPageState extends State<QuizPage> {
  int questionIndex = 0;
  int correctCount = 0;
  int? selectedIndex;
  bool answered = false;

  QuizQuestion get currentQuestion => widget.topic.questions[questionIndex];

  void chooseAnswer(int index) {
    if (answered) return;
    setState(() {
      selectedIndex = index;
      answered = true;
      if (index == currentQuestion.answerIndex) {
        correctCount += 1;
      }
    });
  }

  void goNext() {
    if (questionIndex == widget.topic.questions.length - 1) {
      Navigator.of(context).pop(correctCount);
      return;
    }

    setState(() {
      questionIndex += 1;
      selectedIndex = null;
      answered = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final progress = (questionIndex + 1) / widget.topic.questions.length;

    return Scaffold(
      appBar: AppBar(title: Text(widget.topic.title)),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
          children: [
            LinearProgressIndicator(value: progress),
            const SizedBox(height: 18),
            Text(
              'Question ${questionIndex + 1} of ${widget.topic.questions.length}',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 8),
            Text(
              currentQuestion.question,
              style: theme.textTheme.headlineMedium,
            ),
            const SizedBox(height: 20),
            for (var i = 0; i < currentQuestion.options.length; i++) ...[
              AnswerTile(
                label: currentQuestion.options[i],
                selected: selectedIndex == i,
                correct: answered && currentQuestion.answerIndex == i,
                wrong:
                    answered &&
                    selectedIndex == i &&
                    currentQuestion.answerIndex != i,
                onTap: () => chooseAnswer(i),
              ),
              const SizedBox(height: 10),
            ],
            if (answered) ...[
              const SizedBox(height: 10),
              RecommendationBox(text: currentQuestion.explanation),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: goNext,
                icon: Icon(
                  questionIndex == widget.topic.questions.length - 1
                      ? Icons.check
                      : Icons.arrow_forward,
                ),
                label: Text(
                  questionIndex == widget.topic.questions.length - 1
                      ? 'Finish Quiz'
                      : 'Next Question',
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
