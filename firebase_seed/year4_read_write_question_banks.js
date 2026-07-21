const topicId = 'whole_numbers_y4';
const subtopicId = 'read_write_numbers';
const skillId = 'y4_whole_numbers_read_write';
const contentVersion = '2026.07.15';
const createdAt = '2026-07-15T00:00:00Z';
const sourceReference = 'KSSR Year 4 Whole Numbers 1.1.1';

const bankIdFor = (difficulty) =>
  `y4_whole_read_write_${difficulty.toLowerCase()}_v1`;

function question(suffix, difficulty, estimatedDifficulty, questionText, questionTextBm, options, optionsBm, answerIndex, explanation, explanationBm) {
  const questionId = `q_y4_whole_read_write_${suffix}`;
  const order = Number(suffix.slice(-2)) - 1;
  return {
    id: questionId,
    bankId: bankIdFor(difficulty),
    client: {
      questionId, bankId: bankIdFor(difficulty), topicId, subtopicId, skillId,
      yearLevel: 4, difficultyLevel: difficulty, estimatedDifficulty,
      contentVersion, language: 'bilingual', createdAt, order, questionText, questionTextBm, options, optionsBm,
      sourceReference, isActive: true,
    },
    answerKey: {
      questionId, answerIndex, explanation, explanationBm, contentVersion, createdAt,
      isActive: true, sourceReference,
    },
  };
}

const questions = [
  question('easy_01', 'Easy', .15, 'Which numeral shows twenty thousand four?', 'Angka manakah menunjukkan dua puluh ribu empat?', ['2 004','20 004','24 000','200 004'], ['2 004','20 004','24 000','200 004'], 1, 'Twenty thousand four is 20 004.', 'Dua puluh ribu empat ialah 20 004.'),
  question('easy_02', 'Easy', .15, 'Which number is written as 70 015?', 'Nombor manakah ditulis sebagai 70 015?', ['seventy thousand fifteen','seventeen thousand fifteen','seventy thousand fifty','seven thousand fifteen'], ['tujuh puluh ribu lima belas','tujuh belas ribu lima belas','tujuh puluh ribu lima puluh','tujuh ribu lima belas'], 0, '70 015 has seventy thousands and fifteen ones.', '70 015 mempunyai tujuh puluh ribu dan lima belas sa.'),
  question('easy_03', 'Easy', .18, 'Which numeral matches sixty-one thousand seven hundred?', 'Angka manakah sepadan dengan enam puluh satu ribu tujuh ratus?', ['61 070','61 700','16 700','60 170'], ['61 070','61 700','16 700','60 170'], 1, 'Sixty-one thousand plus seven hundred is 61 700.', 'Enam puluh satu ribu tambah tujuh ratus ialah 61 700.'),
  question('easy_04', 'Easy', .18, 'Which wording is correct for 14 906?', 'Perkataan manakah betul untuk 14 906?', ['fourteen thousand nine hundred six','fourteen thousand ninety-six','one thousand four hundred ninety-six','forty thousand nine hundred six'], ['empat belas ribu sembilan ratus enam','empat belas ribu sembilan puluh enam','seribu empat ratus sembilan puluh enam','empat puluh ribu sembilan ratus enam'], 0, 'The final three digits are nine hundred six.', 'Tiga digit terakhir ialah sembilan ratus enam.'),
  question('easy_05', 'Easy', .20, 'Write thirty-eight thousand two hundred nine in numerals.', 'Tulis tiga puluh lapan ribu dua ratus sembilan dalam angka.', ['38 029','38 209','30 809','83 209'], ['38 029','38 209','30 809','83 209'], 1, '38 thousand and 209 makes 38 209.', '38 ribu dan 209 menjadi 38 209.'),
  question('easy_06', 'Easy', .20, 'Which numeral shows nine thousand eighty?', 'Angka manakah menunjukkan sembilan ribu lapan puluh?', ['9 080','9 800','90 080','9 008'], ['9 080','9 800','90 080','9 008'], 0, 'There are eight tens and no hundreds.', 'Terdapat lapan puluh dan tiada ratus.'),
  question('easy_07', 'Easy', .22, 'Which wording matches 43 000?', 'Perkataan manakah sepadan dengan 43 000?', ['forty-three thousand','four thousand three hundred','forty thousand three','fourteen thousand three'], ['empat puluh tiga ribu','empat ribu tiga ratus','empat puluh ribu tiga','empat belas ribu tiga'], 0, '43 is in the thousands group.', '43 berada dalam kumpulan ribu.'),
  question('easy_08', 'Easy', .22, 'Write five thousand six in numerals.', 'Tulis lima ribu enam dalam angka.', ['5 006','5 060','5 600','50 006'], ['5 006','5 060','5 600','50 006'], 0, 'The six is in the ones place.', 'Enam berada di tempat sa.'),
  question('moderate_01', 'Moderate', .45, 'A card says 50 813. Which sentence reads it correctly?', 'Kad menunjukkan 50 813. Ayat manakah membacanya dengan betul?', ['fifty thousand eight hundred thirteen','five thousand eight hundred thirteen','fifty thousand eighty-three','fifteen thousand eight hundred thirteen'], ['lima puluh ribu lapan ratus tiga belas','lima ribu lapan ratus tiga belas','lima puluh ribu lapan puluh tiga','lima belas ribu lapan ratus tiga belas'], 0, 'Read each non-zero place value from left to right.', 'Baca setiap nilai tempat bukan sifar dari kiri ke kanan.'),
  question('moderate_02', 'Moderate', .45, 'Which numeral represents forty thousand three hundred?', 'Angka manakah mewakili empat puluh ribu tiga ratus?', ['40 030','40 300','43 000','4 300'], ['40 030','40 300','43 000','4 300'], 1, 'Three hundred is in the hundreds place.', 'Tiga ratus berada di tempat ratus.'),
  question('moderate_03', 'Moderate', .48, 'Which words match 80 409?', 'Perkataan manakah sepadan dengan 80 409?', ['eighty thousand four hundred nine','eighty thousand forty-nine','eight thousand four hundred nine','eighty-four thousand nine'], ['lapan puluh ribu empat ratus sembilan','lapan puluh ribu empat puluh sembilan','lapan ribu empat ratus sembilan','lapan puluh empat ribu sembilan'], 0, '409 is four hundred and nine.', '409 ialah empat ratus dan sembilan.'),
  question('moderate_04', 'Moderate', .48, 'Write seventy-two thousand forty in numerals.', 'Tulis tujuh puluh dua ribu empat puluh dalam angka.', ['72 040','72 400','70 240','72 004'], ['72 040','72 400','70 240','72 004'], 0, 'Forty occupies the tens place.', 'Empat puluh berada di tempat puluh.'),
  question('moderate_05', 'Moderate', .50, 'Which number has 6 ten-thousands, 0 thousands, 5 hundreds, 2 tens, and 9 ones?', 'Nombor manakah mempunyai 6 puluh ribu, 0 ribu, 5 ratus, 2 puluh dan 9 sa?', ['60 529','65 029','60 259','6 529'], ['60 529','65 029','60 259','6 529'], 0, 'Combine the given place values in order.', 'Gabungkan nilai tempat yang diberi mengikut tertib.'),
  question('moderate_06', 'Moderate', .50, 'Which wording is incorrect for 30 070?', 'Perkataan manakah tidak betul untuk 30 070?', ['thirty thousand seventy','three thousand seventy','30 070','both A and C are correct'], ['tiga puluh ribu tujuh puluh','tiga ribu tujuh puluh','30 070','kedua-dua A dan C betul'], 1, '30 070 has thirty thousands, not three thousands.', '30 070 mempunyai tiga puluh ribu, bukan tiga ribu.'),
  question('moderate_07', 'Moderate', .52, 'A pupil writes 19 009 as nineteen thousand ninety. Which numeral exposes the mistake?', 'Murid menulis 19 009 sebagai sembilan belas ribu sembilan puluh. Angka manakah menunjukkan kesilapan itu?', ['19 009 has 9 ones, not 9 tens.','19 009 has 9 thousands.','19 009 has 90 ones.','19 009 is less than 1 000.'], ['19 009 mempunyai 9 sa, bukan 9 puluh.','19 009 mempunyai 9 ribu.','19 009 mempunyai 90 sa.','19 009 kurang daripada 1 000.'], 0, 'The final 9 is in the ones place.', '9 terakhir berada di tempat sa.'),
  question('moderate_08', 'Moderate', .52, 'Which numeral is formed by eighty thousand, two thousand, and sixty-five?', 'Angka manakah dibentuk oleh lapan puluh ribu, dua ribu dan enam puluh lima?', ['82 065','80 265','82 650','8 265'], ['82 065','80 265','82 650','8 265'], 0, '80 000 + 2 000 + 65 = 82 065.', '80 000 + 2 000 + 65 = 82 065.'),
  question('hard_01', 'Hard', .75, 'Which pair does not match?', 'Pasangan manakah tidak sepadan?', ['47 293 - forty-seven thousand two hundred ninety-three','20 008 - twenty thousand eight','76 100 - seventy-six thousand one hundred','61 700 - sixty-one thousand seventy'], ['47 293 - empat puluh tujuh ribu dua ratus sembilan puluh tiga','20 008 - dua puluh ribu lapan','76 100 - tujuh puluh enam ribu seratus','61 700 - enam puluh satu ribu tujuh puluh'], 3, '61 700 ends with seven hundred, not seventy.', '61 700 berakhir dengan tujuh ratus, bukan tujuh puluh.'),
  question('hard_02', 'Hard', .75, 'Which number has the same wording pattern as 20 004?', 'Nombor manakah mempunyai pola bacaan yang sama seperti 20 004?', ['30 006','30 060','36 000','3 006'], ['30 006','30 060','36 000','3 006'], 0, 'Both have thousands and ones with zero hundreds and tens.', 'Kedua-duanya mempunyai ribu dan sa dengan sifar ratus dan puluh.'),
  question('hard_03', 'Hard', .78, 'A pupil writes 40 300 as forty thousand three. What is the best correction?', 'Murid menulis 40 300 sebagai empat puluh ribu tiga. Apakah pembetulan terbaik?', ['It should be forty thousand three hundred.','It should be four thousand three hundred.','It should be forty-three thousand.','It should be forty thousand thirty.'], ['Sepatutnya empat puluh ribu tiga ratus.','Sepatutnya empat ribu tiga ratus.','Sepatutnya empat puluh tiga ribu.','Sepatutnya empat puluh ribu tiga puluh.'], 0, 'The 3 represents three hundreds.', '3 mewakili tiga ratus.'),
  question('hard_04', 'Hard', .78, 'Which number fits: 6 ten-thousands, 3 thousands, 8 hundreds, 4 tens, 1 one?', 'Nombor manakah sepadan: 6 puluh ribu, 3 ribu, 8 ratus, 4 puluh, 1 sa?', ['63 841','68 341','36 841','63 481'], ['63 841','68 341','36 841','63 481'], 0, 'Read the place values from left to right.', 'Baca nilai tempat dari kiri ke kanan.'),
  question('hard_05', 'Hard', .80, 'Which statement correctly compares 70 007 and 70 070?', 'Pernyataan manakah membandingkan 70 007 dan 70 070 dengan betul?', ['70 070 is greater because it has 7 tens.','70 007 is greater because it has 7 ones.','They are equal.','70 007 has 7 thousands.'], ['70 070 lebih besar kerana mempunyai 7 puluh.','70 007 lebih besar kerana mempunyai 7 sa.','Kedua-duanya sama.','70 007 mempunyai 7 ribu.'], 0, 'Tens have greater value than ones.', 'Puluh mempunyai nilai lebih besar daripada sa.'),
  question('hard_06', 'Hard', .80, 'A number is read as ninety thousand, nine hundred and nine. Which numeral is correct?', 'Satu nombor dibaca sebagai sembilan puluh ribu, sembilan ratus sembilan. Angka manakah betul?', ['90 909','90 099','99 009','9 909'], ['90 909','90 099','99 009','9 909'], 0, 'The hundreds and ones digits are both nine.', 'Digit ratus dan sa kedua-duanya sembilan.'),
  question('hard_07', 'Hard', .82, 'Which correction keeps every place value in 54 060?', 'Pembetulan manakah mengekalkan setiap nilai tempat dalam 54 060?', ['fifty-four thousand sixty','fifty-four thousand six hundred','five thousand four hundred sixty','fifty thousand four hundred six'], ['lima puluh empat ribu enam puluh','lima puluh empat ribu enam ratus','lima ribu empat ratus enam puluh','lima puluh ribu empat ratus enam'], 0, 'The number has five ten-thousands, four thousands, and six tens.', 'Nombor mempunyai lima puluh ribu, empat ribu dan enam puluh.'),
  question('hard_08', 'Hard', .82, 'Which numeral is closest to the phrase one hundred thousand less one?', 'Angka manakah paling hampir dengan frasa seratus ribu tolak satu?', ['99 999','100 001','90 999','9 999'], ['99 999','100 001','90 999','9 999'], 0, 'One less than 100 000 is 99 999.', 'Satu kurang daripada 100 000 ialah 99 999.'),
];

const difficulties = ['Easy', 'Moderate', 'Hard'];
const questionBanks = Object.fromEntries(difficulties.map((difficulty) => {
  const bankId = bankIdFor(difficulty);
  return [bankId, { bankId, topicId, subtopicId, skillId, yearLevel: 4,
    difficultyLevel: difficulty, questionIds: questions.filter((item) => item.bankId === bankId).map((item) => item.id),
    version: contentVersion, isActive: true, sourceReference }];
}));

function validateQuestionBankSeed() {
  if (Object.keys(questionBanks).length !== 3) throw new Error('Expected exactly three FYP1 question banks.');
  const ids = new Set();
  for (const [bankId, bank] of Object.entries(questionBanks)) {
    if (!difficulties.includes(bank.difficultyLevel) || bank.questionIds.length < 8 || bank.questionIds.length > 10) {
      throw new Error(`Invalid bank ${bankId}.`);
    }
    for (const id of bank.questionIds) {
      if (ids.has(id)) throw new Error(`Question ${id} appears in more than one active bank.`);
      ids.add(id);
      const item = questions.find((candidate) => candidate.id === id);
      if (
        !item || item.bankId !== bankId || item.client.options.length !== 4 ||
        item.client.optionsBm.length !== 4 || item.client.language !== 'bilingual' ||
        !Number.isInteger(item.client.order) || item.client.order < 0 ||
        !item.client.createdAt || item.answerKey.questionId !== id ||
        item.answerKey.answerIndex < 0 || item.answerKey.answerIndex >= item.client.options.length ||
        !item.answerKey.explanation || !item.answerKey.explanationBm ||
        item.answerKey.contentVersion !== item.client.contentVersion ||
        item.answerKey.isActive !== item.client.isActive
      ) {
        throw new Error(`Invalid question link for ${id}.`);
      }
    }
  }
}

module.exports = { questionBanks, questions, validateQuestionBankSeed };
