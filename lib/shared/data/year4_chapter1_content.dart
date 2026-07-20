import 'package:logic_oasis/shared/models/question_bank.dart';
import 'package:logic_oasis/shared/models/quiz_question.dart';
import 'package:logic_oasis/shared/models/subtopic.dart';
import 'package:logic_oasis/shared/models/topic.dart';

const _topicId = 'whole_numbers_y4';
const _subtopicId = 'read_write_numbers';
const _skillId = 'y4_whole_numbers_read_write';
const _contentVersion = '2026.07.15';
const _createdAt = '2026-07-15T00:00:00Z';
const _source = 'KSSR Year 4 Whole Numbers 1.1.1';

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
    title: 'Whole Numbers up to 100 000',
    titleBm: 'Nombor Bulat hingga 100 000',
    area: 'Read and write whole numbers with place-value awareness.',
    areaBm: 'Baca dan tulis nombor bulat dengan kesedaran nilai tempat.',
    yearLevel: 4,
    progress: 0,
    mastery: 'New',
    subtopics: <Subtopic>[
      Subtopic(
        id: _subtopicId,
        title: 'Read and Write Numbers',
        titleBm: 'Baca dan Tulis Nombor',
        order: 1,
        description: 'Read and write whole numbers in numerals and words.',
        descriptionBm: 'Baca dan tulis nombor bulat dalam angka dan perkataan.',
        standardCode: _source,
        sourcePages: 'Buku Teks Matematik Tahun 4, pp. 2-3',
        skillIds: <String>[_skillId],
        contentVersion: _contentVersion,
        activeBankCount: 3,
        questions: year4ReadWriteNumberBanks
            .expand((bank) => bank.questions)
            .toList(growable: false),
      ),
      const Subtopic(
        id: 'place_digit_value',
        title: 'Place Value and Digit Value',
        titleBm: 'Nilai Tempat dan Nilai Digit',
        order: 2,
        description: 'Identify place value and digit value.',
        descriptionBm: 'Kenal nilai tempat dan nilai digit.',
        standardCode: 'KSSR Year 4: Whole Numbers 1.1.2',
        sourcePages: 'Buku Teks Matematik Tahun 4, pp. 4-5',
        skillIds: const <String>['y4_whole_numbers_place_value'],
        contentVersion: '2026.07.20',
        activeBankCount: 0,
      ),
      const Subtopic(
        id: 'compare_order_numbers',
        title: 'Compare and Order Numbers',
        titleBm: 'Banding dan Susun Nombor',
        order: 3,
        description: 'Compare numbers and arrange them in order.',
        descriptionBm: 'Banding nombor dan susun mengikut tertib.',
        standardCode: 'KSSR Year 4: Whole Numbers 1.1.2',
        sourcePages: 'Buku Teks Matematik Tahun 4, pp. 6-8',
        skillIds: const <String>['y4_whole_numbers_compare_order'],
        contentVersion: '2026.07.20',
        activeBankCount: 0,
      ),
      const Subtopic(
        id: 'odd_even_numbers',
        title: 'Odd and Even Numbers',
        titleBm: 'Nombor Ganjil dan Nombor Genap',
        order: 4,
        description: 'Classify whole numbers as odd or even.',
        descriptionBm: 'Kelaskan nombor bulat sebagai ganjil atau genap.',
        standardCode: 'KSSR Year 4: Whole Numbers 1.4.1',
        sourcePages: 'Buku Teks Matematik Tahun 4, pp. 9-10',
        skillIds: const <String>['y4_whole_numbers_odd_even'],
        contentVersion: '2026.07.20',
        activeBankCount: 0,
      ),
      const Subtopic(
        id: 'number_patterns',
        title: 'Number Patterns',
        titleBm: 'Pola Nombor',
        order: 5,
        description: 'Recognise and continue number patterns.',
        descriptionBm: 'Kenal dan sambung pola nombor.',
        standardCode: 'KSSR Year 4: Whole Numbers 1.5.1',
        sourcePages: 'Buku Teks Matematik Tahun 4, p. 11',
        skillIds: const <String>['y4_whole_numbers_patterns'],
        contentVersion: '2026.07.20',
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
    contentVersion: '2026.07.20',
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
  _question(
    'easy_06',
    'Easy',
    0.2,
    'Which numeral shows nine thousand eighty?',
    'Angka manakah menunjukkan sembilan ribu lapan puluh?',
    <String>['9 080', '9 800', '90 080', '9 008'],
    <String>['9 080', '9 800', '90 080', '9 008'],
  ),
  _question(
    'easy_07',
    'Easy',
    0.22,
    'Which wording matches 43 000?',
    'Perkataan manakah sepadan dengan 43 000?',
    <String>[
      'forty-three thousand',
      'four thousand three hundred',
      'forty thousand three',
      'fourteen thousand three',
    ],
    <String>[
      'empat puluh tiga ribu',
      'empat ribu tiga ratus',
      'empat puluh ribu tiga',
      'empat belas ribu tiga',
    ],
  ),
  _question(
    'easy_08',
    'Easy',
    0.22,
    'Write five thousand six in numerals.',
    'Tulis lima ribu enam dalam angka.',
    <String>['5 006', '5 060', '5 600', '50 006'],
    <String>['5 006', '5 060', '5 600', '50 006'],
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
  _question(
    'moderate_06',
    'Moderate',
    0.5,
    'Which wording is incorrect for 30 070?',
    'Perkataan manakah tidak betul untuk 30 070?',
    <String>[
      'thirty thousand seventy',
      'three thousand seventy',
      '30 070',
      'both A and C are correct',
    ],
    <String>[
      'tiga puluh ribu tujuh puluh',
      'tiga ribu tujuh puluh',
      '30 070',
      'kedua-dua A dan C betul',
    ],
  ),
  _question(
    'moderate_07',
    'Moderate',
    0.52,
    'A pupil writes 19 009 as nineteen thousand ninety. Which numeral exposes the mistake?',
    'Murid menulis 19 009 sebagai sembilan belas ribu sembilan puluh. Angka manakah menunjukkan kesilapan itu?',
    <String>[
      '19 009 has 9 ones, not 9 tens.',
      '19 009 has 9 thousands.',
      '19 009 has 90 ones.',
      '19 009 is less than 1 000.',
    ],
    <String>[
      '19 009 mempunyai 9 sa, bukan 9 puluh.',
      '19 009 mempunyai 9 ribu.',
      '19 009 mempunyai 90 sa.',
      '19 009 kurang daripada 1 000.',
    ],
  ),
  _question(
    'moderate_08',
    'Moderate',
    0.52,
    'Which numeral is formed by eighty thousand, two thousand, and sixty-five?',
    'Angka manakah dibentuk oleh lapan puluh ribu, dua ribu dan enam puluh lima?',
    <String>['82 065', '80 265', '82 650', '8 265'],
    <String>['82 065', '80 265', '82 650', '8 265'],
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
    <String>['30 006', '30 060', '36 000', '3 006'],
    <String>['30 006', '30 060', '36 000', '3 006'],
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
  _question(
    'hard_06',
    'Hard',
    0.8,
    'A number is read as ninety thousand, nine hundred and nine. Which numeral is correct?',
    'Satu nombor dibaca sebagai sembilan puluh ribu, sembilan ratus sembilan. Angka manakah betul?',
    <String>['90 909', '90 099', '99 009', '9 909'],
    <String>['90 909', '90 099', '99 009', '9 909'],
  ),
  _question(
    'hard_07',
    'Hard',
    0.82,
    'Which correction keeps every place value in 54 060?',
    'Pembetulan manakah mengekalkan setiap nilai tempat dalam 54 060?',
    <String>[
      'fifty-four thousand sixty',
      'fifty-four thousand six hundred',
      'five thousand four hundred sixty',
      'fifty thousand four hundred six',
    ],
    <String>[
      'lima puluh empat ribu enam puluh',
      'lima puluh empat ribu enam ratus',
      'lima ribu empat ratus enam puluh',
      'lima puluh ribu empat ratus enam',
    ],
  ),
  _question(
    'hard_08',
    'Hard',
    0.82,
    'Which numeral is closest to the phrase one hundred thousand less one?',
    'Angka manakah paling hampir dengan frasa seratus ribu tolak satu?',
    <String>['99 999', '100 001', '90 999', '9 999'],
    <String>['99 999', '100 001', '90 999', '9 999'],
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
