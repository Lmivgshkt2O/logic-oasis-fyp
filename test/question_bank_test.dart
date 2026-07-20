import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/data/year4_chapter1_content.dart';
import 'package:logic_oasis/shared/models/question_bank.dart';

void main() {
  test('FYP1 content has exactly three valid Year 4 banks', () {
    expect(year4ReadWriteNumberBanks, hasLength(3));
    expect(
      year4ReadWriteNumberBanks.map((bank) => bank.difficulty.label).toSet(),
      <String>{'Easy', 'Moderate', 'Hard'},
    );

    final allQuestionIds = <String>{};
    for (final bank in year4ReadWriteNumberBanks) {
      expect(bank.validate(), isEmpty, reason: bank.id);
      expect(bank.questions, hasLength(8));
      for (final question in bank.questions) {
        expect(allQuestionIds.add(question.id), isTrue);
      }
    }

    final adaptiveSubtopic = year4Chapter1Topics.single.subtopics.first;
    expect(adaptiveSubtopic.skillIds, <String>['y4_whole_numbers_read_write']);
    expect(adaptiveSubtopic.contentVersion, '2026.07.15');
    expect(adaptiveSubtopic.activeBankCount, 3);
  });

  test('a form has five unique valid prompts and avoids recent prompts', () {
    final bank = year4ReadWriteNumberBanks.first;
    final recentIds = bank.questions.take(3).map((question) => question.id);

    final form = bank.sampleFive(recentlySeenQuestionIds: recentIds);

    expect(form, hasLength(5));
    expect(form.map((question) => question.id).toSet(), hasLength(5));
    expect(
      form
          .map((question) => question.id)
          .toSet()
          .intersection(recentIds.toSet()),
      isEmpty,
    );
  });

  test('a malformed bank link fails validation', () {
    final source = year4ReadWriteNumberBanks.first;
    final malformed = QuestionBank(
      id: 'different_bank_id',
      topicId: source.topicId,
      subtopicId: source.subtopicId,
      skillId: source.skillId,
      yearLevel: source.yearLevel,
      difficulty: source.difficulty,
      contentVersion: source.contentVersion,
      questions: source.questions,
    );

    expect(malformed.validate(), isNotEmpty);
  });

  test('client question documents contain no answer key or explanation', () {
    final document = year4ReadWriteNumberBanks.first.questions.first
        .toFirestoreDocument();

    expect(document.containsKey('answerIndex'), isFalse);
    expect(document.containsKey('explanation'), isFalse);
    expect(document.containsKey('explanationBm'), isFalse);
    expect(document['language'], 'bilingual');
    expect(document['createdAt'], isNotEmpty);
    expect(document['questionText'], isNotEmpty);
    expect(document['options'], hasLength(4));
  });

  test('negative offsets still produce a valid wrapped form', () {
    final form = year4ReadWriteNumberBanks.first.sampleFive(offset: -1);

    expect(form, hasLength(5));
    expect(form.map((question) => question.id).toSet(), hasLength(5));
  });
}
