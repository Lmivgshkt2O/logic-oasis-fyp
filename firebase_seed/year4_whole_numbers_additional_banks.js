const topicId = 'whole_numbers_y4';
const contentVersion = '2026.07.20';
const createdAt = '2026-07-20T00:00:00Z';

const definitions = [
  {
    subtopicId: 'place_digit_value', skillId: 'y4_whole_numbers_place_value',
    sourceReference: 'KSSR Year 4 Whole Numbers 1.1.2',
    questions: [
      ['01', 'In 54 321, what is the value of digit 4?', 'Dalam 54 321, apakah nilai digit 4?', ['4','40','4 000','40 000'], ['4','40','4 000','40 000'], 2, 'The 4 is in the thousands place.', '4 berada di tempat ribu.'],
      ['02', 'Which digit is in the hundreds place in 72 645?', 'Digit manakah berada di tempat ratus dalam 72 645?', ['7','2','6','4'], ['7','2','6','4'], 2, 'The hundreds digit is 6.', 'Digit ratus ialah 6.'],
      ['03', 'What is the place value of 8 in 18 209?', 'Apakah nilai tempat 8 dalam 18 209?', ['ones','tens','hundreds','thousands'], ['sa','puluh','ratus','ribu'], 3, '8 is in the thousands place.', '8 berada di tempat ribu.'],
      ['04', 'Which number has 5 in the ten-thousands place?', 'Nombor manakah mempunyai 5 di tempat puluh ribu?', ['15 432','25 432','50 432','45 321'], ['15 432','25 432','50 432','45 321'], 2, '50 432 has five ten-thousands.', '50 432 mempunyai lima puluh ribu.'],
      ['05', 'What is the value of digit 9 in 39 104?', 'Apakah nilai digit 9 dalam 39 104?', ['9','90','900','9 000'], ['9','90','900','9 000'], 3, '9 is in the thousands place.', '9 berada di tempat ribu.'],
      ['06', 'In 67 890, which digit has value 80?', 'Dalam 67 890, digit manakah bernilai 80?', ['7','8','9','0'], ['7','8','9','0'], 1, '8 is in the tens place.', '8 berada di tempat puluh.'],
      ['07', 'Which expanded form is 42 305?', 'Bentuk cerakin manakah ialah 42 305?', ['40 000 + 2 000 + 300 + 5','40 000 + 200 + 30 + 5','4 000 + 2 000 + 300 + 5','42 000 + 3050'], ['40 000 + 2 000 + 300 + 5','40 000 + 200 + 30 + 5','4 000 + 2 000 + 300 + 5','42 000 + 3050'], 0, 'Each non-zero digit keeps its place value.', 'Setiap digit bukan sifar mengekalkan nilai tempatnya.'],
      ['08', 'What is the digit value of 3 in 91 436?', 'Apakah nilai digit 3 dalam 91 436?', ['3','30','300','3 000'], ['3','30','300','3 000'], 1, '3 is in the tens place.', '3 berada di tempat puluh.'],
    ],
  },
  {
    subtopicId: 'compare_order_numbers', skillId: 'y4_whole_numbers_compare_order',
    sourceReference: 'KSSR Year 4 Whole Numbers 1.1.2',
    questions: [
      ['01', 'Which number is greater?', 'Nombor manakah lebih besar?', ['45 210','45 120','They are equal','Cannot tell'], ['45 210','45 120','Kedua-duanya sama','Tidak dapat ditentukan'], 0, 'Compare the tens after the first three digits match.', 'Bandingkan puluh apabila tiga digit pertama sama.'],
      ['02', 'Choose the correct sign: 32 405 __ 32 450.', 'Pilih tanda yang betul: 32 405 __ 32 450.', ['>','<','=','+'], ['>','<','=','+'], 1, '405 is less than 450.', '405 lebih kecil daripada 450.'],
      ['03', 'Which list is in ascending order?', 'Senarai manakah dalam tertib menaik?', ['12 099, 12 909, 19 009','19 009, 12 909, 12 099','12 909, 12 099, 19 009','19 009, 12 099, 12 909'], ['12 099, 12 909, 19 009','19 009, 12 909, 12 099','12 909, 12 099, 19 009','19 009, 12 099, 12 909'], 0, 'Ascending order goes from smallest to greatest.', 'Tertib menaik bergerak daripada paling kecil kepada paling besar.'],
      ['04', 'Which number is smallest?', 'Nombor manakah paling kecil?', ['60 008','6 080','60 080','68 000'], ['60 008','6 080','60 080','68 000'], 1, 'A four-digit number is smaller than these five-digit numbers.', 'Nombor empat digit lebih kecil daripada nombor lima digit ini.'],
      ['05', 'Choose the correct sign: 70 070 __ 70 007.', 'Pilih tanda yang betul: 70 070 __ 70 007.', ['>','<','=','+'], ['>','<','=','+'], 0, 'Seven tens is greater than seven ones.', 'Tujuh puluh lebih besar daripada tujuh sa.'],
      ['06', 'Which number comes next: 9 998, 9 999, __?', 'Nombor manakah seterusnya: 9 998, 9 999, __?', ['9 990','10 000','10 009','9 999'], ['9 990','10 000','10 009','9 999'], 1, 'One more than 9 999 is 10 000.', 'Satu lebih daripada 9 999 ialah 10 000.'],
      ['07', 'Which list is in descending order?', 'Senarai manakah dalam tertib menurun?', ['88 000, 80 800, 80 080','80 080, 80 800, 88 000','80 800, 88 000, 80 080','88 000, 80 080, 80 800'], ['88 000, 80 800, 80 080','80 080, 80 800, 88 000','80 800, 88 000, 80 080','88 000, 80 080, 80 800'], 0, 'Descending order goes from greatest to smallest.', 'Tertib menurun bergerak daripada paling besar kepada paling kecil.'],
      ['08', 'Which number is between 24 500 and 24 700?', 'Nombor manakah di antara 24 500 dan 24 700?', ['24 450','24 620','24 720','25 000'], ['24 450','24 620','24 720','25 000'], 1, '24 620 is greater than 24 500 and less than 24 700.', '24 620 lebih besar daripada 24 500 dan lebih kecil daripada 24 700.'],
    ],
  },
  {
    subtopicId: 'odd_even_numbers', skillId: 'y4_whole_numbers_odd_even',
    sourceReference: 'KSSR Year 4 Whole Numbers 1.4.1',
    questions: [
      ['01', 'Which number is even?', 'Nombor manakah genap?', ['34 567','12 348','90 123','7 891'], ['34 567','12 348','90 123','7 891'], 1, 'An even number ends in 0, 2, 4, 6, or 8.', 'Nombor genap berakhir dengan 0, 2, 4, 6, atau 8.'],
      ['02', 'Which number is odd?', 'Nombor manakah ganjil?', ['48 620','71 404','63 215','20 008'], ['48 620','71 404','63 215','20 008'], 2, 'An odd number ends in 1, 3, 5, 7, or 9.', 'Nombor ganjil berakhir dengan 1, 3, 5, 7, atau 9.'],
      ['03', 'Is 50 000 odd or even?', 'Adakah 50 000 ganjil atau genap?', ['Odd','Even','Both','Neither'], ['Ganjil','Genap','Kedua-duanya','Tiada satu pun'], 1, 'It ends in zero.', 'Ia berakhir dengan sifar.'],
      ['04', 'Which pair contains two odd numbers?', 'Pasangan manakah mengandungi dua nombor ganjil?', ['14 002 and 18 006','9 111 and 20 005','40 080 and 70 070','6 234 and 8 900'], ['14 002 dan 18 006','9 111 dan 20 005','40 080 dan 70 070','6 234 dan 8 900'], 1, 'Both numbers in that pair end in odd digits.', 'Kedua-dua nombor dalam pasangan itu berakhir dengan digit ganjil.'],
      ['05', 'What is the next even number after 6 998?', 'Apakah nombor genap seterusnya selepas 6 998?', ['6 999','7 000','7 001','6 990'], ['6 999','7 000','7 001','6 990'], 1, 'Add two to move to the next even number.', 'Tambah dua untuk ke nombor genap seterusnya.'],
      ['06', 'Which number has an odd ones digit?', 'Nombor manakah mempunyai digit sa ganjil?', ['45 320','70 016','91 248','12 739'], ['45 320','70 016','91 248','12 739'], 3, 'The ones digit is 9.', 'Digit sa ialah 9.'],
      ['07', 'Which statement is true?', 'Pernyataan manakah betul?', ['Every number ending in 5 is even.','Every number ending in 8 is odd.','Every number ending in 0 is even.','All five-digit numbers are odd.'], ['Setiap nombor berakhir 5 adalah genap.','Setiap nombor berakhir 8 adalah ganjil.','Setiap nombor berakhir 0 adalah genap.','Semua nombor lima digit adalah ganjil.'], 2, 'Zero is an even digit.', 'Sifar ialah digit genap.'],
      ['08', 'Which is an odd number between 30 000 and 30 010?', 'Yang manakah nombor ganjil antara 30 000 dan 30 010?', ['30 002','30 004','30 007','30 008'], ['30 002','30 004','30 007','30 008'], 2, '30 007 ends in 7.', '30 007 berakhir dengan 7.'],
    ],
  },
  {
    subtopicId: 'number_patterns', skillId: 'y4_whole_numbers_patterns',
    sourceReference: 'KSSR Year 4 Whole Numbers 1.5.1',
    questions: [
      ['01', 'What comes next: 1 000, 2 000, 3 000, __?', 'Apakah seterusnya: 1 000, 2 000, 3 000, __?', ['3 100','4 000','4 100','5 000'], ['3 100','4 000','4 100','5 000'], 1, 'The pattern increases by 1 000.', 'Pola bertambah sebanyak 1 000.'],
      ['02', 'What comes next: 9 500, 9 400, 9 300, __?', 'Apakah seterusnya: 9 500, 9 400, 9 300, __?', ['9 200','9 250','9 000','8 300'], ['9 200','9 250','9 000','8 300'], 0, 'The pattern decreases by 100.', 'Pola berkurang sebanyak 100.'],
      ['03', 'Which rule makes 2 010, 2 020, 2 030?', 'Peraturan manakah menghasilkan 2 010, 2 020, 2 030?', ['Add 1','Add 10','Add 100','Add 1 000'], ['Tambah 1','Tambah 10','Tambah 100','Tambah 1 000'], 1, 'Each term is ten more than the last.', 'Setiap nombor sepuluh lebih daripada sebelumnya.'],
      ['04', 'Fill the blank: 15 000, 20 000, __, 30 000.', 'Isi tempat kosong: 15 000, 20 000, __, 30 000.', ['22 000','24 000','25 000','26 000'], ['22 000','24 000','25 000','26 000'], 2, 'The pattern adds 5 000.', 'Pola menambah 5 000.'],
      ['05', 'What is the missing number: 800, 700, __, 500?', 'Apakah nombor hilang: 800, 700, __, 500?', ['400','500','600','650'], ['400','500','600','650'], 2, 'The pattern decreases by 100.', 'Pola berkurang sebanyak 100.'],
      ['06', 'Which sequence increases by 2?', 'Jujukan manakah bertambah sebanyak 2?', ['10, 12, 14, 16','10, 20, 30, 40','10, 11, 12, 13','10, 8, 6, 4'], ['10, 12, 14, 16','10, 20, 30, 40','10, 11, 12, 13','10, 8, 6, 4'], 0, 'Each term is two more than the previous one.', 'Setiap nombor dua lebih daripada nombor sebelumnya.'],
      ['07', 'What comes next: 48 000, 46 000, 44 000, __?', 'Apakah seterusnya: 48 000, 46 000, 44 000, __?', ['42 000','43 000','40 000','45 000'], ['42 000','43 000','40 000','45 000'], 0, 'The pattern decreases by 2 000.', 'Pola berkurang sebanyak 2 000.'],
      ['08', 'Which number completes 25 005, 25 010, 25 015, __?', 'Nombor manakah melengkapkan 25 005, 25 010, 25 015, __?', ['25 016','25 020','25 050','26 000'], ['25 016','25 020','25 050','26 000'], 1, 'The pattern adds 5.', 'Pola menambah 5.'],
    ],
  },
];

function makeBank(definition) {
  const bankId = `y4_whole_${definition.subtopicId}_easy_v1`;
  const questions = definition.questions.map((item, index) => {
    const [suffix, questionText, questionTextBm, options, optionsBm, answerIndex, explanation, explanationBm] = item;
    const questionId = `q_y4_whole_${definition.subtopicId}_${suffix}`;
    return {
      id: questionId,
      bankId,
      client: {
        questionId, bankId, topicId, subtopicId: definition.subtopicId,
        skillId: definition.skillId, yearLevel: 4, difficultyLevel: 'Easy',
        estimatedDifficulty: .2 + index * .01, contentVersion, language: 'bilingual', createdAt,
        questionText, questionTextBm, options, optionsBm,
        sourceReference: definition.sourceReference, isActive: true, order: index + 1,
      },
      answerKey: {
        questionId, answerIndex, explanation, explanationBm, contentVersion, createdAt,
        isActive: true, sourceReference: definition.sourceReference,
      },
    };
  });
  return {
    bank: {
      bankId, topicId, subtopicId: definition.subtopicId, skillId: definition.skillId,
      yearLevel: 4, difficultyLevel: 'Easy', questionIds: questions.map((item) => item.id),
      version: contentVersion, isActive: true, sourceReference: definition.sourceReference,
    },
    questions,
  };
}

const built = definitions.map(makeBank);
const questionBanks = Object.fromEntries(built.map(({ bank }) => [bank.bankId, bank]));
const questions = built.flatMap(({ questions }) => questions);

function validateAdditionalQuestionBanks() {
  for (const bank of Object.values(questionBanks)) {
    if (bank.questionIds.length !== 8) throw new Error(`Invalid bank ${bank.bankId}.`);
  }
}

module.exports = { questionBanks, questions, validateAdditionalQuestionBanks };
