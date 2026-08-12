import 'package:logic_oasis/shared/models/question_bank.dart';
import 'package:logic_oasis/shared/models/quiz_question.dart';
import 'package:logic_oasis/shared/models/subtopic.dart';
import 'package:logic_oasis/shared/models/topic.dart';

const _topicId = 'whole_numbers_y4';
const _subtopicId = 'read_write_numbers';
const _skillId = 'y4_whole_numbers_read_write';
const _contentVersion = '2026.08.12';
const _createdAt = '2026-08-12T00:00:00Z';
const _source = 'KSSR Year 4: Whole Numbers 1.1.1';

final List<QuestionBank> year4ReadWriteNumberBanks = <QuestionBank>[
  QuestionBank(
    id: 'y4_whole_read_write_easy_v1',
    topicId: _topicId,
    subtopicId: _subtopicId,
    skillId: _skillId,
    yearLevel: 4,
    difficulty: QuestionDifficulty.easy,
    contentVersion: _contentVersion,
    questions: _easyQuestions,
  ),
  QuestionBank(
    id: 'y4_whole_read_write_moderate_v1',
    topicId: _topicId,
    subtopicId: _subtopicId,
    skillId: _skillId,
    yearLevel: 4,
    difficulty: QuestionDifficulty.moderate,
    contentVersion: _contentVersion,
    questions: _moderateQuestions,
  ),
  QuestionBank(
    id: 'y4_whole_read_write_hard_v1',
    topicId: _topicId,
    subtopicId: _subtopicId,
    skillId: _skillId,
    yearLevel: 4,
    difficulty: QuestionDifficulty.hard,
    contentVersion: _contentVersion,
    questions: _hardQuestions,
  ),
];

/// Local metadata reserves the server-seeded follow-on banks. They remain
/// unplayable offline until Firestore confirms an active server bank.
final List<QuestionBank> year4WholeNumbersBanks = <QuestionBank>[
  ...year4ReadWriteNumberBanks,
  _catalogueBank(
    subtopicId: 'place_digit_value',
    skillId: 'y4_whole_numbers_place_value',
  ),
  _catalogueBank(
    subtopicId: 'compare_order_numbers',
    skillId: 'y4_whole_numbers_compare_order',
  ),
  _catalogueBank(
    subtopicId: 'odd_even_numbers',
    skillId: 'y4_whole_numbers_odd_even',
  ),
  _catalogueBank(
    subtopicId: 'number_patterns',
    skillId: 'y4_whole_numbers_patterns',
  ),
];

final List<Topic> year4Chapter1Topics = <Topic>[
  Topic(
    id: _topicId,
    title: 'Numbers and Operations',
    titleBm: 'Nombor dan Operasi',
    area:
        'Whole numbers up to 100 000: read, write, compare, classify, and continue patterns.',
    areaBm:
        'Nombor bulat hingga 100 000: kenal, tulis, banding, kelaskan dan sambung pola.',
    yearLevel: 4,
    progress: 0,
    mastery: 'New',
    subtopics: <Subtopic>[
      Subtopic(
        id: _subtopicId,
        title: 'Recognise and Write Numbers',
        titleBm: 'Kenal dan Tulis Nombor',
        order: 1,
        description: 'Recognise and write numbers in numerals and words.',
        descriptionBm: 'Kenal dan tulis nombor dalam angka dan perkataan.',
        standardCode: _source,
        sourcePages:
            'Buku Teks Matematik Tahun 4, hlm. 3-4; Mathematics Year 4 SK (DLP), pp. 3-4',
        skillIds: <String>[_skillId],
        contentVersion: _contentVersion,
        activeBankCount: 3,
        questions: year4ReadWriteNumberBanks
            .expand((bank) => bank.questions)
            .toList(growable: false),
      ),
      const Subtopic(
        id: 'place_digit_value',
        title: 'Explore Numbers',
        titleBm: 'Teroka Nombor',
        order: 2,
        description: 'Identify place value, digit value, and expanded form.',
        descriptionBm: 'Kenal nilai tempat, nilai digit dan bentuk cerakin.',
        standardCode: 'KSSR Year 4: Whole Numbers 1.1.2',
        sourcePages:
            'Buku Teks Matematik Tahun 4, hlm. 5; Mathematics Year 4 SK (DLP), p. 5',
        skillIds: const <String>['y4_whole_numbers_place_value'],
        contentVersion: '2026.08.12',
        activeBankCount: 0,
      ),
      const Subtopic(
        id: 'compare_order_numbers',
        title: 'Compare and Arrange Numbers',
        titleBm: 'Banding dan Susun Nombor',
        order: 3,
        description: 'Compare numbers and arrange them in order.',
        descriptionBm: 'Banding nombor dan susun mengikut tertib.',
        standardCode: 'KSSR Year 4: Whole Numbers 1.1.2',
        sourcePages:
            'Buku Teks Matematik Tahun 4, hlm. 6-8; Mathematics Year 4 SK (DLP), pp. 6-8',
        skillIds: const <String>['y4_whole_numbers_compare_order'],
        contentVersion: '2026.08.12',
        activeBankCount: 0,
      ),
      const Subtopic(
        id: 'odd_even_numbers',
        title: 'Even Numbers and Odd Numbers',
        titleBm: 'Nombor Genap dan Nombor Ganjil',
        order: 4,
        description: 'Classify whole numbers as odd or even.',
        descriptionBm: 'Kelaskan nombor bulat sebagai ganjil atau genap.',
        standardCode: 'KSSR Year 4: Whole Numbers 1.2.1-1.2.2',
        sourcePages:
            'Buku Teks Matematik Tahun 4, hlm. 9-10; Mathematics Year 4 SK (DLP), pp. 9-10',
        skillIds: const <String>['y4_whole_numbers_odd_even'],
        contentVersion: '2026.08.12',
        activeBankCount: 0,
      ),
      const Subtopic(
        id: 'number_patterns',
        title: 'Number Patterns',
        titleBm: 'Pola Nombor',
        order: 5,
        description: 'Recognise and continue number patterns.',
        descriptionBm: 'Kenal dan sambung pola nombor.',
        standardCode: 'KSSR Year 4: Whole Numbers 1.5.1-1.5.2',
        sourcePages:
            'Buku Teks Matematik Tahun 4, hlm. 11-12; Mathematics Year 4 SK (DLP), pp. 11-12',
        skillIds: const <String>['y4_whole_numbers_patterns'],
        contentVersion: '2026.08.12',
        activeBankCount: 0,
      ),
    ],
  ),
];

QuestionBank _catalogueBank({
  required String subtopicId,
  required String skillId,
}) {
  final bankId = 'y4_whole_${subtopicId}_easy_v1';
  return QuestionBank(
    id: bankId,
    topicId: _topicId,
    subtopicId: subtopicId,
    skillId: skillId,
    yearLevel: 4,
    difficulty: QuestionDifficulty.easy,
    contentVersion: '2026.08.12',
    questions: const <QuizQuestion>[],
  );
}

final List<QuizQuestion> _easyQuestions = <QuizQuestion>[
  _question(
    'easy_01',
    'Easy',
    0.15,
    'Which numeral shows twenty thousand four?',
    'Angka manakah menunjukkan dua puluh ribu empat?',
    <String>['2 004', '20 004', '24 000', '200 004'],
    <String>['2 004', '20 004', '24 000', '200 004'],
  ),
  _question(
    'easy_02',
    'Easy',
    0.15,
    'Which number is written as 70 015?',
    'Nombor manakah ditulis sebagai 70 015?',
    <String>[
      'seventy thousand fifteen',
      'seventeen thousand fifteen',
      'seventy thousand fifty',
      'seven thousand fifteen',
    ],
    <String>[
      'tujuh puluh ribu lima belas',
      'tujuh belas ribu lima belas',
      'tujuh puluh ribu lima puluh',
      'tujuh ribu lima belas',
    ],
  ),
  _question(
    'easy_03',
    'Easy',
    0.18,
    'Which numeral matches sixty-one thousand seven hundred?',
    'Angka manakah sepadan dengan enam puluh satu ribu tujuh ratus?',
    <String>['61 070', '61 700', '16 700', '60 170'],
    <String>['61 070', '61 700', '16 700', '60 170'],
  ),
  _question(
    'easy_04',
    'Easy',
    0.18,
    'Which wording is correct for 14 906?',
    'Perkataan manakah betul untuk 14 906?',
    <String>[
      'fourteen thousand nine hundred six',
      'fourteen thousand ninety-six',
      'one thousand four hundred ninety-six',
      'forty thousand nine hundred six',
    ],
    <String>[
      'empat belas ribu sembilan ratus enam',
      'empat belas ribu sembilan puluh enam',
      'seribu empat ratus sembilan puluh enam',
      'empat puluh ribu sembilan ratus enam',
    ],
  ),
  _question(
    'easy_05',
    'Easy',
    0.2,
    'Write thirty-eight thousand two hundred nine in numerals.',
    'Tulis tiga puluh lapan ribu dua ratus sembilan dalam angka.',
    <String>['38 029', '38 209', '30 809', '83 209'],
    <String>['38 029', '38 209', '30 809', '83 209'],
  ),
];

final List<QuizQuestion> _moderateQuestions = <QuizQuestion>[
  _question(
    'moderate_01',
    'Moderate',
    0.45,
    'A card says 50 813. Which sentence reads it correctly?',
    'Kad menunjukkan 50 813. Ayat manakah membacanya dengan betul?',
    <String>[
      'fifty thousand eight hundred thirteen',
      'five thousand eight hundred thirteen',
      'fifty thousand eighty-three',
      'fifteen thousand eight hundred thirteen',
    ],
    <String>[
      'lima puluh ribu lapan ratus tiga belas',
      'lima ribu lapan ratus tiga belas',
      'lima puluh ribu lapan puluh tiga',
      'lima belas ribu lapan ratus tiga belas',
    ],
  ),
  _question(
    'moderate_02',
    'Moderate',
    0.45,
    'Which numeral represents forty thousand three hundred?',
    'Angka manakah mewakili empat puluh ribu tiga ratus?',
    <String>['40 030', '40 300', '43 000', '4 300'],
    <String>['40 030', '40 300', '43 000', '4 300'],
  ),
  _question(
    'moderate_03',
    'Moderate',
    0.48,
    'Which words match 80 409?',
    'Perkataan manakah sepadan dengan 80 409?',
    <String>[
      'eighty thousand four hundred nine',
      'eighty thousand forty-nine',
      'eight thousand four hundred nine',
      'eighty-four thousand nine',
    ],
    <String>[
      'lapan puluh ribu empat ratus sembilan',
      'lapan puluh ribu empat puluh sembilan',
      'lapan ribu empat ratus sembilan',
      'lapan puluh empat ribu sembilan',
    ],
  ),
  _question(
    'moderate_04',
    'Moderate',
    0.48,
    'Write seventy-two thousand forty in numerals.',
    'Tulis tujuh puluh dua ribu empat puluh dalam angka.',
    <String>['72 040', '72 400', '70 240', '72 004'],
    <String>['72 040', '72 400', '70 240', '72 004'],
  ),
  _question(
    'moderate_05',
    'Moderate',
    0.5,
    'Which number has 6 ten-thousands, 0 thousands, 5 hundreds, 2 tens, and 9 ones?',
    'Nombor manakah mempunyai 6 puluh ribu, 0 ribu, 5 ratus, 2 puluh dan 9 sa?',
    <String>['60 529', '65 029', '60 259', '6 529'],
    <String>['60 529', '65 029', '60 259', '6 529'],
  ),
];

final List<QuizQuestion> _hardQuestions = <QuizQuestion>[
  _question(
    'hard_01',
    'Hard',
    0.75,
    'Which pair does not match?',
    'Pasangan manakah tidak sepadan?',
    <String>[
      '47 293 - forty-seven thousand two hundred ninety-three',
      '20 008 - twenty thousand eight',
      '76 100 - seventy-six thousand one hundred',
      '61 700 - sixty-one thousand seventy',
    ],
    <String>[
      '47 293 - empat puluh tujuh ribu dua ratus sembilan puluh tiga',
      '20 008 - dua puluh ribu lapan',
      '76 100 - tujuh puluh enam ribu seratus',
      '61 700 - enam puluh satu ribu tujuh puluh',
    ],
  ),
  _question(
    'hard_02',
    'Hard',
    0.75,
    'Which number has the same wording pattern as 20 004?',
    'Nombor manakah mempunyai pola bacaan yang sama seperti 20 004?',
    <String>['30 006', '30 060', '36 000', '30 600'],
    <String>['30 006', '30 060', '36 000', '30 600'],
  ),
  _question(
    'hard_03',
    'Hard',
    0.78,
    'A pupil writes 40 300 as forty thousand three. What is the best correction?',
    'Murid menulis 40 300 sebagai empat puluh ribu tiga. Apakah pembetulan terbaik?',
    <String>[
      'It should be forty thousand three hundred.',
      'It should be four thousand three hundred.',
      'It should be forty-three thousand.',
      'It should be forty thousand thirty.',
    ],
    <String>[
      'Sepatutnya empat puluh ribu tiga ratus.',
      'Sepatutnya empat ribu tiga ratus.',
      'Sepatutnya empat puluh tiga ribu.',
      'Sepatutnya empat puluh ribu tiga puluh.',
    ],
  ),
  _question(
    'hard_04',
    'Hard',
    0.78,
    'Which number fits: 6 ten-thousands, 3 thousands, 8 hundreds, 4 tens, 1 one?',
    'Nombor manakah sepadan: 6 puluh ribu, 3 ribu, 8 ratus, 4 puluh, 1 sa?',
    <String>['63 841', '68 341', '36 841', '63 481'],
    <String>['63 841', '68 341', '36 841', '63 481'],
  ),
  _question(
    'hard_05',
    'Hard',
    0.8,
    'Which statement correctly compares 70 007 and 70 070?',
    'Pernyataan manakah membandingkan 70 007 dan 70 070 dengan betul?',
    <String>[
      '70 070 is greater because it has 7 tens.',
      '70 007 is greater because it has 7 ones.',
      'They are equal.',
      '70 007 has 7 thousands.',
    ],
    <String>[
      '70 070 lebih besar kerana mempunyai 7 puluh.',
      '70 007 lebih besar kerana mempunyai 7 sa.',
      'Kedua-duanya sama.',
      '70 007 mempunyai 7 ribu.',
    ],
  ),
];

QuizQuestion _question(
  String suffix,
  String difficulty,
  double estimatedDifficulty,
  String question,
  String questionBm,
  List<String> options,
  List<String> optionsBm,
) {
  final bankId = switch (difficulty) {
    'Easy' => 'y4_whole_read_write_easy_v1',
    'Moderate' => 'y4_whole_read_write_moderate_v1',
    'Hard' => 'y4_whole_read_write_hard_v1',
    _ => throw ArgumentError.value(difficulty, 'difficulty'),
  };
  return QuizQuestion(
    id: 'q_y4_whole_read_write_$suffix',
    bankId: bankId,
    topicId: _topicId,
    subtopicId: _subtopicId,
    skillId: _skillId,
    yearLevel: 4,
    difficultyLevel: difficulty,
    estimatedDifficulty: estimatedDifficulty,
    contentVersion: _contentVersion,
    language: 'bilingual',
    createdAt: _createdAt,
    question: question,
    questionBm: questionBm,
    options: options,
    optionsBm: optionsBm,
    sourceReference: _source,
  );
}
