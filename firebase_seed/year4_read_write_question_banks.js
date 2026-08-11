// Year 4 Whole Numbers - Recognise and Write Numbers (1.1.1).
//
// Source-grounded, reviewed, bilingual content. Every question carries:
//   - an exact textbook locator (EN + BM) and source material ID,
//   - an authored question type and review focus,
//   - per-wrong-option feedback (misconception code, hint, optional worked
//     example with different values, review focus),
//   - declared difficulty metadata that must match the labelled band.
// The answer index and feedback live only in the server-only answer key; the
// client projection never contains them.
const {
  CONTENT_VERSION,
  AUTHOR_ID,
  REVIEWER_ID,
  APPROVED_AT,
} = require("./content_source_manifest");

const topicId = "whole_numbers_y4";
const subtopicId = "read_write_numbers";
const skillId = "y4_whole_numbers_read_write";
const createdAt = "2026-08-12T00:00:00Z";
const enMaterialId = "en_y4";
const bmMaterialId = "bm_y4";
const enBook = "Mathematics Year 4 SK (DLP)";
const bmBook = "Buku Teks Matematik Tahun 4";
const standardCode = "1.1.1 Recognise and Write Numbers / Kenal dan Tulis Nombor";
const sectionClass = "exercise";

const bankIdFor = (difficulty) =>
  `y4_whole_read_write_${difficulty.toLowerCase()}_v1`;

const reviewFocusFor = {
  numeral_from_words:
    "Check how many thousands are named, then read the remaining three digits as ones, tens, and hundreds.",
  numeral_from_wordsBm:
    "Semak berapa ribu yang disebut, kemudian baca tiga digit selebihnya sebagai sa, puluh dan ratus.",
  words_from_numeral:
    "Read the thousands group first, then read the last three digits as a group.",
  words_from_numeralBm:
    "Baca kumpulan ribu dahulu, kemudian baca tiga digit terakhir sebagai satu kumpulan.",
};

function question(
  suffix,
  difficulty,
  estimatedDifficulty,
  questionText,
  questionTextBm,
  options,
  optionsBm,
  answerIndex,
  meta,
) {
  const questionId = `q_y4_whole_read_write_${suffix}`;
  const order = Number(suffix.slice(-2)) - 1;
  return {
    id: questionId,
    bankId: bankIdFor(difficulty),
    client: {
      questionId,
      bankId: bankIdFor(difficulty),
      topicId,
      subtopicId,
      skillId,
      yearLevel: 4,
      difficultyLevel: difficulty,
      estimatedDifficulty,
      contentVersion: CONTENT_VERSION,
      language: "bilingual",
      createdAt,
      order,
      questionText,
      questionTextBm,
      options,
      optionsBm,
      questionType: meta.questionType,
      questionTypeBm: meta.questionTypeBm,
      sourceMaterialId: enMaterialId,
      sourceMaterialIdBm: bmMaterialId,
      sourceLocator: meta.sourceLocator,
      sourceLocatorBm: meta.sourceLocatorBm,
      sourceSectionClass: meta.sourceSectionClass ?? sectionClass,
      sectionJustification: meta.sectionJustification ?? "",
      isActive: true,
    },
    answerKey: {
      questionId,
      answerIndex,
      feedbackByOption: meta.feedbackByOption,
      difficultyReview: meta.difficultyReview,
      contentVersion: CONTENT_VERSION,
      createdAt,
      isActive: true,
      sourceMaterialId: enMaterialId,
      sourceMaterialIdBm: bmMaterialId,
      authorId: AUTHOR_ID,
      reviewerId: REVIEWER_ID,
      approvedAt: APPROVED_AT,
    },
  };
}

const questions = [
  // ----------------------------- Easy -----------------------------
  question(
    "easy_01",
    "Easy",
    0.15,
    "Which numeral shows twenty thousand four?",
    "Angka manakah menunjukkan dua puluh ribu empat?",
    ["2 004", "20 004", "24 000", "200 004"],
    ["2 004", "20 004", "24 000", "200 004"],
    1,
    {
      questionType: "Choose a numeral for a number in words",
      questionTypeBm: "Pilih angka bagi nombor dalam perkataan",
      sourceLocator:
        `${enBook}, ${standardCode}, Recognise and Write Numbers, p. 3`,
      sourceLocatorBm:
        `${bmBook}, ${standardCode}, Kenal dan Tulis Nombor, hlm. 3`,
      difficultyReview: {
        cognitiveDemand: "direct_recall",
        reasoningStepCount: 1,
        transferRequired: false,
      },
      feedbackByOption: {
        "0": {
          misconceptionCode: "thousands_group_miscounted",
          hint:
            "Twenty thousand has 20 groups of one thousand. Write 20, then add the ones after it.",
          hintBm:
            "Dua puluh ribu mempunyai 20 kumpulan seribu. Tulis 20, kemudian tambahkan sa selepasnya.",
          example: "In 43 007, the 43 shows 43 thousands.",
          exampleBm: "Dalam 43 007, angka 43 menunjukkan 43 ribu.",
          reviewFocus:
            "Check how many thousands are named before the ones.",
          reviewFocusBm:
            "Semak berapa ribu yang disebut sebelum sa.",
        },
        "2": {
          misconceptionCode: "zero_places_omitted",
          hint:
            "The ones part of the number is just 4, so the tens and hundreds must stay zero.",
          hintBm:
            "Bahagian sa nombor itu hanyalah 4, jadi puluh dan ratus mesti kekal sifar.",
          example: "75 009 ends with 9 in the ones place.",
          exampleBm: "75 009 berakhir dengan 9 di tempat sa.",
          reviewFocus:
            "Keep zero in the tens and hundreds places when only ones are named.",
          reviewFocusBm:
            "Kekalkan sifar di tempat puluh dan ratus apabila hanya sa disebut.",
        },
        "3": {
          misconceptionCode: "digit_count_misread",
          hint:
            "Twenty thousand has five digits, not six. Count the digits in the number before choosing.",
          hintBm:
            "Dua puluh ribu mempunyai lima digit, bukan enam. Kira digit dalam nombor sebelum memilih.",
          example: "Nine thousand eight is 9 008, a five-digit number.",
          exampleBm: "Sembilan ribu lapan ialah 9 008, nombor lima digit.",
          reviewFocus:
            "Check the number of digits matches the words.",
          reviewFocusBm:
            "Semak bilangan digit sepadan dengan perkataan.",
        },
      },
    },
  ),
  question(
    "easy_02",
    "Easy",
    0.15,
    "Which number is written as 70 015?",
    "Nombor manakah ditulis sebagai 70 015?",
    [
      "seventy thousand fifteen",
      "seventeen thousand fifteen",
      "seventy thousand fifty",
      "seven thousand fifteen",
    ],
    [
      "tujuh puluh ribu lima belas",
      "tujuh belas ribu lima belas",
      "tujuh puluh ribu lima puluh",
      "tujuh ribu lima belas",
    ],
    0,
    {
      questionType: "Read a numeral in words",
      questionTypeBm: "Baca angka dalam perkataan",
      sourceLocator:
        `${enBook}, ${standardCode}, Test Yourself (Say the numbers), p. 4`,
      sourceLocatorBm:
        `${bmBook}, ${standardCode}, Uji Diri (Sebut nombor), hlm. 4`,
      difficultyReview: {
        cognitiveDemand: "direct_recall",
        reasoningStepCount: 1,
        transferRequired: false,
      },
      feedbackByOption: {
        "1": {
          misconceptionCode: "digit_swap",
          hint:
            "The tens-thousands digit is 7, so the number begins with seventy, not seventeen.",
          hintBm:
            "Digit puluh ribu ialah 7, jadi nombor bermula dengan tujuh puluh, bukan tujuh belas.",
          example: "43 200 begins with forty-three.",
          exampleBm: "43 200 bermula dengan empat puluh tiga.",
          reviewFocus:
            "Read the first two digits as the thousands group.",
          reviewFocusBm:
            "Baca dua digit pertama sebagai kumpulan ribu.",
        },
        "2": {
          misconceptionCode: "tens_ones_misread",
          hint:
            "The last three digits are 015. Fifteen means 1 ten and 5 ones.",
          hintBm:
            "Tiga digit terakhir ialah 015. Lima belas bermaksud 1 puluh dan 5 sa.",
          example: "In 21 016, the ending is sixteen.",
          exampleBm: "Dalam 21 016, hujungnya ialah enam belas.",
          reviewFocus:
            "Read the last three digits as one group.",
          reviewFocusBm:
            "Baca tiga digit terakhir sebagai satu kumpulan.",
        },
        "3": {
          misconceptionCode: "zero_thousands_dropped",
          hint:
            "There is a zero in the thousands place. The number still has seventy thousands before it.",
          hintBm:
            "Terdapat sifar di tempat ribu. Nombor itu masih mempunyai tujuh puluh ribu sebelum sifar itu.",
          example: "60 012 has sixty thousands.",
          exampleBm: "60 012 mempunyai enam puluh ribu.",
          reviewFocus:
            "Keep the zero thousands place inside the number.",
          reviewFocusBm:
            "Kekalkan tempat ribu sifar di dalam nombor.",
        },
      },
    },
  ),
  question(
    "easy_03",
    "Easy",
    0.18,
    "Which numeral matches seventy-six thousand one hundred?",
    "Angka manakah sepadan dengan tujuh puluh enam ribu seratus?",
    ["76 010", "76 100", "67 100", "70 610"],
    ["76 010", "76 100", "67 100", "70 610"],
    1,
    {
      questionType: "Choose a numeral for a number in words",
      questionTypeBm: "Pilih angka bagi nombor dalam perkataan",
      sourceLocator:
        `${enBook}, ${standardCode}, Test Yourself (Write the numbers in numerals), p. 4`,
      sourceLocatorBm:
        `${bmBook}, ${standardCode}, Uji Diri (Tulis nombor dalam angka), hlm. 4`,
      difficultyReview: {
        cognitiveDemand: "direct_recall",
        reasoningStepCount: 1,
        transferRequired: false,
      },
      feedbackByOption: {
        "0": {
          misconceptionCode: "hundreds_tens_swapped",
          hint:
            "One hundred belongs in the hundreds place, not the tens place.",
          hintBm:
            "Seratus berada di tempat ratus, bukan di tempat puluh.",
          example: "Ninety thousand two hundred is 90 200.",
          exampleBm: "Sembilan puluh ribu dua ratus ialah 90 200.",
          reviewFocus:
            "Place the named hundred value in the hundreds place.",
          reviewFocusBm:
            "Letakkan nilai ratus yang disebut di tempat ratus.",
        },
        "2": {
          misconceptionCode: "digit_group_swap",
          hint:
            "Say the thousands group again: seventy-six, not sixty-seven.",
          hintBm:
            "Sebut kumpulan ribu sekali lagi: tujuh puluh enam, bukan enam puluh tujuh.",
          example: "Eighty-three thousand is 83 000.",
          exampleBm: "Lapan puluh tiga ribu ialah 83 000.",
          reviewFocus:
            "Keep the thousands group in the same order as the words.",
          reviewFocusBm:
            "Kekalkan kumpulan ribu dalam tertib yang sama seperti perkataan.",
        },
        "3": {
          misconceptionCode: "zero_place_shifted",
          hint:
            "The six is in the hundreds place, so write 6 hundreds, then zero tens and zero ones.",
          hintBm:
            "Enam berada di tempat ratus, jadi tulis 6 ratus, kemudian sifar puluh dan sifar sa.",
          example: "52 400 has 4 hundreds and no tens or ones.",
          exampleBm: "52 400 mempunyai 4 ratus dan tiada puluh atau sa.",
          reviewFocus:
            "Fill every place after the hundreds with zero.",
          reviewFocusBm:
            "Isikan setiap tempat selepas ratus dengan sifar.",
        },
      },
    },
  ),
  question(
    "easy_04",
    "Easy",
    0.18,
    "Which wording is correct for 14 906?",
    "Perkataan manakah betul untuk 14 906?",
    [
      "fourteen thousand nine hundred six",
      "fourteen thousand ninety-six",
      "one thousand four hundred ninety-six",
      "forty thousand nine hundred six",
    ],
    [
      "empat belas ribu sembilan ratus enam",
      "empat belas ribu sembilan puluh enam",
      "seribu empat ratus sembilan puluh enam",
      "empat puluh ribu sembilan ratus enam",
    ],
    0,
    {
      questionType: "Write a numeral in words",
      questionTypeBm: "Tulis angka dalam perkataan",
      sourceLocator:
        `${enBook}, ${standardCode}, Write 14 906 in words, p. 4`,
      sourceLocatorBm:
        `${bmBook}, ${standardCode}, Tulis 14 906 dalam perkataan, hlm. 4`,
      difficultyReview: {
        cognitiveDemand: "direct_recall",
        reasoningStepCount: 1,
        transferRequired: false,
      },
      feedbackByOption: {
        "1": {
          misconceptionCode: "tens_ones_misread",
          hint:
            "The final three digits are 906. The 0 is in the tens place, so the ending is nine hundred six, not ninety-six.",
          hintBm:
            "Tiga digit terakhir ialah 906. Angka 0 berada di tempat puluh, jadi hujungnya ialah sembilan ratus enam, bukan sembilan puluh enam.",
          example: "In 25 803, the ending 803 is eight hundred three.",
          exampleBm: "Dalam 25 803, hujung 803 ialah lapan ratus tiga.",
          reviewFocus:
            "Read the last three digits together as hundreds, tens, and ones.",
          reviewFocusBm:
            "Baca tiga digit terakhir bersama-sama sebagai ratus, puluh dan sa.",
        },
        "2": {
          misconceptionCode: "thousands_group_dropped",
          hint:
            "There are fourteen thousands, so the number starts with fourteen thousand, not one thousand.",
          hintBm:
            "Terdapat empat belas ribu, jadi nombor bermula dengan empat belas ribu, bukan seribu.",
          example: "31 204 begins with thirty-one thousand.",
          exampleBm: "31 204 bermula dengan tiga puluh satu ribu.",
          reviewFocus:
            "Name the thousands group at the start.",
          reviewFocusBm:
            "Sebut kumpulan ribu pada permulaan.",
        },
        "3": {
          misconceptionCode: "digit_order_swapped",
          hint:
            "The first two digits are 1 and 4, so the thousands group is fourteen, not forty.",
          hintBm:
            "Dua digit pertama ialah 1 dan 4, jadi kumpulan ribu ialah empat belas, bukan empat puluh.",
          example: "18 700 begins with eighteen thousand.",
          exampleBm: "18 700 bermula dengan lapan belas ribu.",
          reviewFocus:
            "Keep the digit order when naming the thousands group.",
          reviewFocusBm:
            "Kekalkan tertib digit apabila menyebut kumpulan ribu.",
        },
      },
    },
  ),
  question(
    "easy_05",
    "Easy",
    0.2,
    "Write twenty-eight thousand and fifty in numerals.",
    "Tulis dua puluh lapan ribu lima puluh dalam angka.",
    ["28 005", "28 050", "20 850", "82 050"],
    ["28 005", "28 050", "20 850", "82 050"],
    1,
    {
      questionType: "Write a number in words as numerals",
      questionTypeBm: "Tulis nombor dalam perkataan sebagai angka",
      sourceLocator:
        `${enBook}, ${standardCode}, Test Yourself (Write the numbers in numerals), p. 4`,
      sourceLocatorBm:
        `${bmBook}, ${standardCode}, Uji Diri (Tulis nombor dalam angka), hlm. 4`,
      difficultyReview: {
        cognitiveDemand: "direct_recall",
        reasoningStepCount: 1,
        transferRequired: false,
      },
      feedbackByOption: {
        "0": {
          misconceptionCode: "tens_ones_misread",
          hint:
            "Fifty means 5 tens, so the 5 belongs in the tens place.",
          hintBm:
            "Lima puluh bermaksud 5 puluh, jadi digit 5 berada di tempat puluh.",
          example: "Seventy thousand forty is 70 040.",
          exampleBm: "Tujuh puluh ribu empat puluh ialah 70 040.",
          reviewFocus:
            "Put the tens value in the tens place and keep the ones as zero.",
          reviewFocusBm:
            "Letakkan nilai puluh di tempat puluh dan kekalkan sa sebagai sifar.",
        },
        "2": {
          misconceptionCode: "hundreds_tens_mixed",
          hint:
            "No hundreds are named, so the hundreds place stays zero.",
          hintBm:
            "Tiada ratus disebut, jadi tempat ratus kekal sifar.",
          example: "Ninety thousand sixty is 90 060.",
          exampleBm: "Sembilan puluh ribu enam puluh ialah 90 060.",
          reviewFocus:
            "Only fill the places that the words name.",
          reviewFocusBm:
            "Hanya isi tempat yang disebut dalam perkataan.",
        },
        "3": {
          misconceptionCode: "digit_group_swap",
          hint:
            "The thousands group is twenty-eight, so it begins with 28, not 82.",
          hintBm:
            "Kumpulan ribu ialah dua puluh lapan, jadi ia bermula dengan 28, bukan 82.",
          example: "Thirty-nine thousand is 39 000.",
          exampleBm: "Tiga puluh sembilan ribu ialah 39 000.",
          reviewFocus:
            "Write the thousands group in the same order as the words.",
          reviewFocusBm:
            "Tulis kumpulan ribu dalam tertib yang sama seperti perkataan.",
        },
      },
    },
  ),

  // ---------------------------- Moderate ----------------------------
  question(
    "moderate_01",
    "Moderate",
    0.45,
    "A card says 50 813. Which sentence reads it correctly?",
    "Kad menunjukkan 50 813. Ayat manakah membacanya dengan betul?",
    [
      "fifty thousand eight hundred thirteen",
      "five thousand eight hundred thirteen",
      "fifty thousand eighty-three",
      "fifteen thousand eight hundred thirteen",
    ],
    [
      "lima puluh ribu lapan ratus tiga belas",
      "lima ribu lapan ratus tiga belas",
      "lima puluh ribu lapan puluh tiga",
      "lima belas ribu lapan ratus tiga belas",
    ],
    0,
    {
      questionType: "Read a numeral in words",
      questionTypeBm: "Baca angka dalam perkataan",
      sourceLocator:
        `${enBook}, ${standardCode}, Test Yourself (Say the numbers), p. 4`,
      sourceLocatorBm:
        `${bmBook}, ${standardCode}, Uji Diri (Sebut nombor), hlm. 4`,
      difficultyReview: {
        cognitiveDemand: "linked_step",
        reasoningStepCount: 2,
        transferRequired: false,
      },
      feedbackByOption: {
        "1": {
          misconceptionCode: "zero_thousands_dropped",
          hint:
            "There are fifty thousands, not five. The zero in the thousands place does not remove the fifty.",
          hintBm:
            "Terdapat lima puluh ribu, bukan lima ribu. Sifar di tempat ribu tidak menghilangkan lima puluh itu.",
          example: "60 204 is sixty thousand two hundred four.",
          exampleBm: "60 204 ialah enam puluh ribu dua ratus empat.",
          reviewFocus:
            "Read the ten-thousands digit and keep the zero thousands place.",
          reviewFocusBm:
            "Baca digit puluh ribu dan kekalkan tempat ribu sifar.",
        },
        "2": {
          misconceptionCode: "hundreds_omitted",
          hint:
            "The final three digits are 813: eight hundred thirteen. Read the hundreds part before the tens.",
          hintBm:
            "Tiga digit terakhir ialah 813: lapan ratus tiga belas. Baca bahagian ratus sebelum puluh.",
          example: "42 917 ends with nine hundred seventeen.",
          exampleBm: "42 917 berakhir dengan sembilan ratus tujuh belas.",
          reviewFocus:
            "Read the hundreds digit as a hundred value.",
          reviewFocusBm:
            "Baca digit ratus sebagai nilai ratus.",
        },
        "3": {
          misconceptionCode: "digit_swap",
          hint:
            "The tens-thousands digit is 5, so the number begins with fifty, not fifteen.",
          hintBm:
            "Digit puluh ribu ialah 5, jadi nombor bermula dengan lima puluh, bukan lima belas.",
          example: "71 036 begins with seventy-one.",
          exampleBm: "71 036 bermula dengan tujuh puluh satu.",
          reviewFocus:
            "Name the tens-thousands digit correctly first.",
          reviewFocusBm:
            "Sebut digit puluh ribu dengan betul dahulu.",
        },
      },
    },
  ),
  question(
    "moderate_02",
    "Moderate",
    0.45,
    "Which numeral represents forty thousand three hundred?",
    "Angka manakah mewakili empat puluh ribu tiga ratus?",
    ["40 030", "40 300", "43 000", "4 300"],
    ["40 030", "40 300", "43 000", "4 300"],
    1,
    {
      questionType: "Choose a numeral for a number in words",
      questionTypeBm: "Pilih angka bagi nombor dalam perkataan",
      sourceLocator:
        `${enBook}, ${standardCode}, Recognise and Write Numbers, p. 3`,
      sourceLocatorBm:
        `${bmBook}, ${standardCode}, Kenal dan Tulis Nombor, hlm. 3`,
      difficultyReview: {
        cognitiveDemand: "linked_step",
        reasoningStepCount: 2,
        transferRequired: false,
      },
      feedbackByOption: {
        "0": {
          misconceptionCode: "hundreds_tens_swapped",
          hint:
            "Three hundred is 3 hundreds, not 3 tens. The 3 must sit two places from the ones.",
          hintBm:
            "Tiga ratus ialah 3 ratus, bukan 3 puluh. Digit 3 mesti berada dua tempat daripada sa.",
          example: "Eight thousand five hundred is 8 500.",
          exampleBm: "Lapan ribu lima ratus ialah 8 500.",
          reviewFocus:
            "Match the word hundred with the hundreds place.",
          reviewFocusBm:
            "Padankan perkataan ratus dengan tempat ratus.",
        },
        "2": {
          misconceptionCode: "zero_places_omitted",
          hint:
            "The words say three hundred, not just three. Keep the tens and ones places as zeros.",
          hintBm:
            "Perkataan menyebut tiga ratus, bukan sekadar tiga. Kekalkan tempat puluh dan sa sebagai sifar.",
          example: "Twelve thousand seven hundred is 12 700.",
          exampleBm: "Dua belas ribu tujuh ratus ialah 12 700.",
          reviewFocus:
            "Write zeros in the places that are not named.",
          reviewFocusBm:
            "Tulis sifar pada tempat yang tidak disebut.",
        },
        "3": {
          misconceptionCode: "thousands_group_miscounted",
          hint:
            "Forty thousand needs four digits for the thousands group: 40, then three more digits.",
          hintBm:
            "Empat puluh ribu memerlukan empat digit untuk kumpulan ribu: 40, kemudian tiga digit lagi.",
          example: "Twenty thousand is written 20 000.",
          exampleBm: "Dua puluh ribu ditulis 20 000.",
          reviewFocus:
            "Check the number of digits in the thousands group.",
          reviewFocusBm:
            "Semak bilangan digit dalam kumpulan ribu.",
        },
      },
    },
  ),
  question(
    "moderate_03",
    "Moderate",
    0.48,
    "Which words match 80 309?",
    "Perkataan manakah sepadan dengan 80 309?",
    [
      "eighty thousand three hundred and nine",
      "eighty thousand thirty-nine",
      "eight thousand three hundred and nine",
      "eighty-three thousand nine",
    ],
    [
      "lapan puluh ribu tiga ratus sembilan",
      "lapan puluh ribu tiga puluh sembilan",
      "lapan ribu tiga ratus sembilan",
      "lapan puluh tiga ribu sembilan",
    ],
    0,
    {
      questionType: "Write a numeral in words",
      questionTypeBm: "Tulis angka dalam perkataan",
      sourceLocator:
        `${enBook}, ${standardCode}, Test Yourself (Write the numbers in words), p. 4`,
      sourceLocatorBm:
        `${bmBook}, ${standardCode}, Uji Diri (Tulis nombor dalam perkataan), hlm. 4`,
      difficultyReview: {
        cognitiveDemand: "linked_step",
        reasoningStepCount: 2,
        transferRequired: false,
      },
      feedbackByOption: {
        "1": {
          misconceptionCode: "tens_ones_misread",
          hint:
            "The last three digits are 309: the 0 is in the tens place, so the ending is three hundred and nine, not thirty-nine.",
          hintBm:
            "Tiga digit terakhir ialah 309: angka 0 di tempat puluh, jadi hujungnya ialah tiga ratus sembilan, bukan tiga puluh sembilan.",
          example: "In 17 402, the ending is four hundred two.",
          exampleBm: "Dalam 17 402, hujungnya ialah empat ratus dua.",
          reviewFocus:
            "Read the hundreds digit, then the tens and ones digits.",
          reviewFocusBm:
            "Baca digit ratus, kemudian digit puluh dan sa.",
        },
        "2": {
          misconceptionCode: "zero_thousands_dropped",
          hint:
            "Eighty thousand has 8 in the ten-thousands place. Keep the zero in the thousands place.",
          hintBm:
            "Lapan puluh ribu mempunyai 8 di tempat puluh ribu. Kekalkan sifar di tempat ribu.",
          example: "90 507 has ninety thousands.",
          exampleBm: "90 507 mempunyai sembilan puluh ribu.",
          reviewFocus:
            "Keep the zero thousands place between the groups.",
          reviewFocusBm:
            "Kekalkan tempat ribu sifar di antara kumpulan.",
        },
        "3": {
          misconceptionCode: "digit_group_swap",
          hint:
            "The thousands group is 80, so the number begins with eighty, not eighty-three.",
          hintBm:
            "Kumpulan ribu ialah 80, jadi nombor bermula dengan lapan puluh, bukan lapan puluh tiga.",
          example: "74 100 begins with seventy-four.",
          exampleBm: "74 100 bermula dengan tujuh puluh empat.",
          reviewFocus:
            "Keep the thousands group separate from the last three digits.",
          reviewFocusBm:
            "Kekalkan kumpulan ribu berasingan daripada tiga digit terakhir.",
        },
      },
    },
  ),
  question(
    "moderate_04",
    "Moderate",
    0.48,
    "Write fifteen thousand and six in numerals.",
    "Tulis lima belas ribu enam dalam angka.",
    ["15 006", "15 060", "15 600", "150 006"],
    ["15 006", "15 060", "15 600", "150 006"],
    0,
    {
      questionType: "Write a number in words as numerals",
      questionTypeBm: "Tulis nombor dalam perkataan sebagai angka",
      sourceLocator:
        `${enBook}, ${standardCode}, Test Yourself (Write the numbers in numerals), p. 4`,
      sourceLocatorBm:
        `${bmBook}, ${standardCode}, Uji Diri (Tulis nombor dalam angka), hlm. 4`,
      difficultyReview: {
        cognitiveDemand: "linked_step",
        reasoningStepCount: 2,
        transferRequired: false,
      },
      feedbackByOption: {
        "1": {
          misconceptionCode: "tens_ones_misread",
          hint:
            "The word is six, not sixty. Six belongs in the ones place.",
          hintBm:
            "Perkataan ialah enam, bukan enam puluh. Enam berada di tempat sa.",
          example: "Thirty thousand two is 30 002.",
          exampleBm: "Tiga puluh ribu dua ialah 30 002.",
          reviewFocus:
            "Place the named ones value at the end of the number.",
          reviewFocusBm:
            "Letakkan nilai sa yang disebut di hujung nombor.",
        },
        "2": {
          misconceptionCode: "zero_places_omitted",
          hint:
            "No hundreds are named, so the hundreds place must be zero.",
          hintBm:
            "Tiada ratus disebut, jadi tempat ratus mesti sifar.",
          example: "Forty-one thousand five is 41 005.",
          exampleBm: "Empat puluh satu ribu lima ialah 41 005.",
          reviewFocus:
            "Fill unnamed middle places with zero.",
          reviewFocusBm:
            "Isikan tempat tengah yang tidak disebut dengan sifar.",
        },
        "3": {
          misconceptionCode: "digit_count_misread",
          hint:
            "Fifteen thousand has five digits. Count the places: ten-thousands, thousands, hundreds, tens, ones.",
          hintBm:
            "Lima belas ribu mempunyai lima digit. Kira tempat: puluh ribu, ribu, ratus, puluh, sa.",
          example: "Twelve thousand three is 12 003.",
          exampleBm: "Dua belas ribu tiga ialah 12 003.",
          reviewFocus:
            "Check the number has exactly five digits.",
          reviewFocusBm:
            "Semak nombor mempunyai tepat lima digit.",
        },
      },
    },
  ),
  question(
    "moderate_05",
    "Moderate",
    0.5,
    "Which number has 6 ten-thousands, 0 thousands, 5 hundreds, 2 tens, and 9 ones?",
    "Nombor manakah mempunyai 6 puluh ribu, 0 ribu, 5 ratus, 2 puluh dan 9 sa?",
    ["60 529", "65 029", "60 259", "6 529"],
    ["60 529", "65 029", "60 259", "6 529"],
    0,
    {
      questionType: "Build a number from place values",
      questionTypeBm: "Bina nombor daripada nilai tempat",
      sourceLocator:
        `${enBook}, 1.1.2 Explore Numbers, partition by place value, p. 5`,
      sourceLocatorBm:
        `${bmBook}, 1.1.2 Teroka Nombor, cerakin mengikut nilai tempat, hlm. 5`,
      difficultyReview: {
        cognitiveDemand: "linked_step",
        reasoningStepCount: 2,
        transferRequired: false,
      },
      feedbackByOption: {
        "1": {
          misconceptionCode: "zero_thousands_skipped",
          hint:
            "There are zero thousands, so the thousands digit must be 0, not 5.",
          hintBm:
            "Terdapat sifar ribu, jadi digit ribu mesti 0, bukan 5.",
          example: "3 ten-thousands, 0 thousands, 1 hundred is 30 100.",
          exampleBm: "3 puluh ribu, 0 ribu, 1 ratus ialah 30 100.",
          reviewFocus:
            "Keep the zero thousands digit in place.",
          reviewFocusBm:
            "Kekalkan digit ribu sifar pada tempatnya.",
        },
        "2": {
          misconceptionCode: "hundreds_tens_swapped",
          hint:
            "5 hundreds comes before 2 tens. Write the hundreds digit, then the tens digit.",
          hintBm:
            "5 ratus datang sebelum 2 puluh. Tulis digit ratus, kemudian digit puluh.",
          example: "4 hundreds and 3 tens makes 430.",
          exampleBm: "4 ratus dan 3 puluh menjadi 430.",
          reviewFocus:
            "Order the digits from the largest place to the smallest.",
          reviewFocusBm:
            "Susun digit daripada tempat terbesar kepada terkecil.",
        },
        "3": {
          misconceptionCode: "digit_count_misread",
          hint:
            "Six ten-thousands needs a five-digit number. Count the digits to check.",
          hintBm:
            "Enam puluh ribu memerlukan nombor lima digit. Kira digit untuk menyemak.",
          example: "2 ten-thousands and 4 hundreds is 20 400.",
          exampleBm: "2 puluh ribu dan 4 ratus ialah 20 400.",
          reviewFocus:
            "Check the number of digits before comparing.",
          reviewFocusBm:
            "Semak bilangan digit sebelum membandingkan.",
        },
      },
    },
  ),

  // ------------------------------ Hard ------------------------------
  question(
    "hard_01",
    "Hard",
    0.75,
    "Which pair does not match?",
    "Pasangan manakah tidak sepadan?",
    [
      "47 293 - forty-seven thousand two hundred ninety-three",
      "20 008 - twenty thousand eight",
      "76 100 - seventy-six thousand one hundred",
      "61 700 - sixty-one thousand seventy",
    ],
    [
      "47 293 - empat puluh tujuh ribu dua ratus sembilan puluh tiga",
      "20 008 - dua puluh ribu lapan",
      "76 100 - tujuh puluh enam ribu seratus",
      "61 700 - enam puluh satu ribu tujuh puluh",
    ],
    3,
    {
      questionType: "Check number-word pairs",
      questionTypeBm: "Semak pasangan nombor-perkataan",
      sourceLocator:
        `${enBook}, ${standardCode}, Test Yourself (Write the numbers in words), p. 4`,
      sourceLocatorBm:
        `${bmBook}, ${standardCode}, Uji Diri (Tulis nombor dalam perkataan), hlm. 4`,
      difficultyReview: {
        cognitiveDemand: "transfer",
        reasoningStepCount: 3,
        transferRequired: true,
      },
      feedbackByOption: {
        "0": {
          misconceptionCode: "pair_misread",
          hint:
            "Read the ending of 47 293: two hundred ninety-three. Does the pair say the same?",
          hintBm:
            "Baca hujung 47 293: dua ratus sembilan puluh tiga. Adakah pasangan itu menyebut perkara yang sama?",
          example: "53 486 ends with four hundred eighty-six.",
          exampleBm: "53 486 berakhir dengan empat ratus lapan puluh enam.",
          reviewFocus:
            "Check the ending words against the last three digits.",
          reviewFocusBm:
            "Semak perkataan akhir dengan tiga digit terakhir.",
        },
        "1": {
          misconceptionCode: "pair_misread",
          hint:
            "20 008 has 8 in the ones place, so the words end with eight.",
          hintBm:
            "20 008 mempunyai 8 di tempat sa, jadi perkataan berakhir dengan lapan.",
          example: "In 30 007, the ending is seven.",
          exampleBm: "Dalam 30 007, hujungnya ialah tujuh.",
          reviewFocus:
            "Match the ones digit with the last word.",
          reviewFocusBm:
            "Padankan digit sa dengan perkataan terakhir.",
        },
        "2": {
          misconceptionCode: "pair_misread",
          hint:
            "76 100 has one hundred, so the words must end with one hundred.",
          hintBm:
            "76 100 mempunyai seratus, jadi perkataan mesti berakhir dengan seratus.",
          example: "92 300 ends with three hundred.",
          exampleBm: "92 300 berakhir dengan tiga ratus.",
          reviewFocus:
            "Check the hundreds digit is named correctly.",
          reviewFocusBm:
            "Semak digit ratus disebut dengan betul.",
        },
      },
    },
  ),
  question(
    "hard_02",
    "Hard",
    0.75,
    "Which number has the same wording pattern as 20 004?",
    "Nombor manakah mempunyai pola bacaan yang sama seperti 20 004?",
    ["30 006", "30 060", "36 000", "30 600"],
    ["30 006", "30 060", "36 000", "30 600"],
    0,
    {
      questionType: "Compare wording patterns",
      questionTypeBm: "Bandingkan pola bacaan",
      sourceLocator:
        `${enBook}, ${standardCode}, Recognise and Write Numbers, p. 3`,
      sourceLocatorBm:
        `${bmBook}, ${standardCode}, Kenal dan Tulis Nombor, hlm. 3`,
      difficultyReview: {
        cognitiveDemand: "transfer",
        reasoningStepCount: 3,
        transferRequired: true,
      },
      feedbackByOption: {
        "1": {
          misconceptionCode: "zero_place_shift",
          hint:
            "20 004 ends with four in the ones place. Look for a number whose last three digits also end with a ones value and zeros before it.",
          hintBm:
            "20 004 berakhir dengan empat di tempat sa. Cari nombor yang tiga digit terakhirnya juga berakhir dengan nilai sa dan sifar sebelumnya.",
          example: "40 009 is forty thousand and nine.",
          exampleBm: "40 009 ialah empat puluh ribu dan sembilan.",
          reviewFocus:
            "Compare the last three digits of each option.",
          reviewFocusBm:
            "Bandingkan tiga digit terakhir setiap pilihan.",
        },
        "2": {
          misconceptionCode: "group_value_mixed",
          hint:
            "In 20 004 the 20 is the thousands group and 4 is the ones. The tens and hundreds places are both zero.",
          hintBm:
            "Dalam 20 004, 20 ialah kumpulan ribu dan 4 ialah sa. Tempat puluh dan ratus kedua-duanya sifar.",
          example: "50 003 is fifty thousand and three.",
          exampleBm: "50 003 ialah lima puluh ribu dan tiga.",
          reviewFocus:
            "Look at both the thousands group and the ones digit.",
          reviewFocusBm:
            "Lihat kumpulan ribu dan digit sa.",
        },
        "3": {
          misconceptionCode: "hundreds_added",
          hint:
            "20 004 has no hundreds or tens in the last three digits. 30 600 ends with six hundred, so its wording is different.",
          hintBm:
            "20 004 tiada ratus atau puluh dalam tiga digit terakhir. 30 600 berakhir dengan enam ratus, jadi pola bacaannya berbeza.",
          example: "40 500 is forty thousand five hundred.",
          exampleBm: "40 500 ialah empat puluh ribu lima ratus.",
          reviewFocus:
            "Check the last three digits of each option.",
          reviewFocusBm:
            "Semak tiga digit terakhir setiap pilihan.",
        },
      },
    },
  ),
  question(
    "hard_03",
    "Hard",
    0.78,
    "A pupil writes 40 300 as forty thousand three. What is the best correction?",
    "Murid menulis 40 300 sebagai empat puluh ribu tiga. Apakah pembetulan terbaik?",
    [
      "It should be forty thousand three hundred.",
      "It should be four thousand three hundred.",
      "It should be forty-three thousand.",
      "It should be forty thousand thirty.",
    ],
    [
      "Sepatutnya empat puluh ribu tiga ratus.",
      "Sepatutnya empat ribu tiga ratus.",
      "Sepatutnya empat puluh tiga ribu.",
      "Sepatutnya empat puluh ribu tiga puluh.",
    ],
    0,
    {
      questionType: "Correct a number written in words",
      questionTypeBm: "Betulkan nombor yang ditulis dalam perkataan",
      sourceLocator:
        `${enBook}, ${standardCode}, Recognise and Write Numbers, p. 3`,
      sourceLocatorBm:
        `${bmBook}, ${standardCode}, Kenal dan Tulis Nombor, hlm. 3`,
      difficultyReview: {
        cognitiveDemand: "multi_step",
        reasoningStepCount: 3,
        transferRequired: true,
      },
      feedbackByOption: {
        "1": {
          misconceptionCode: "thousands_group_miscounted",
          hint:
            "40 300 has forty thousands, so the words must begin with forty thousand, not four thousand.",
          hintBm:
            "40 300 mempunyai empat puluh ribu, jadi perkataan mesti bermula dengan empat puluh ribu, bukan empat ribu.",
          example: "60 200 begins with sixty thousand.",
          exampleBm: "60 200 bermula dengan enam puluh ribu.",
          reviewFocus:
            "Read the thousands group before correcting.",
          reviewFocusBm:
            "Baca kumpulan ribu sebelum membetulkan.",
        },
        "2": {
          misconceptionCode: "group_value_mixed",
          hint:
            "The digits 4 and 0 are the thousands group; the 3 is not in the thousands group.",
          hintBm:
            "Digit 4 dan 0 ialah kumpulan ribu; digit 3 bukan dalam kumpulan ribu.",
          example: "50 400 is fifty thousand four hundred.",
          exampleBm: "50 400 ialah lima puluh ribu empat ratus.",
          reviewFocus:
            "Keep each digit in its own place value group.",
          reviewFocusBm:
            "Kekalkan setiap digit dalam kumpulan nilai tempatnya sendiri.",
        },
        "3": {
          misconceptionCode: "hundreds_tens_swapped",
          hint:
            "40 300 has zeros in the tens and ones places, so the 3 must be three hundred, not thirty.",
          hintBm:
            "40 300 mempunyai sifar di tempat puluh dan sa, jadi 3 mesti tiga ratus, bukan tiga puluh.",
          example: "In 72 400, the 4 is four hundred.",
          exampleBm: "Dalam 72 400, digit 4 ialah empat ratus.",
          reviewFocus:
            "Check which place the 3 sits in before naming it.",
          reviewFocusBm:
            "Semak tempat digit 3 sebelum menyebutnya.",
        },
      },
    },
  ),
  question(
    "hard_04",
    "Hard",
    0.78,
    "Which number fits: 6 ten-thousands, 3 thousands, 8 hundreds, 4 tens, 1 one?",
    "Nombor manakah sepadan: 6 puluh ribu, 3 ribu, 8 ratus, 4 puluh, 1 sa?",
    ["63 841", "68 341", "36 841", "63 481"],
    ["63 841", "68 341", "36 841", "63 481"],
    0,
    {
      questionType: "Build a number from place values",
      questionTypeBm: "Bina nombor daripada nilai tempat",
      sourceLocator:
        `${enBook}, 1.1.2 Explore Numbers, place value and digit value, p. 5`,
      sourceLocatorBm:
        `${bmBook}, 1.1.2 Teroka Nombor, nilai tempat dan nilai digit, hlm. 5`,
      difficultyReview: {
        cognitiveDemand: "multi_step",
        reasoningStepCount: 3,
        transferRequired: true,
      },
      feedbackByOption: {
        "1": {
          misconceptionCode: "place_order_swapped",
          hint:
            "The hundreds digit is 8 and the thousands digit is 3. Keep thousands before hundreds.",
          hintBm:
            "Digit ratus ialah 8 dan digit ribu ialah 3. Kekalkan ribu sebelum ratus.",
          example: "5 thousands and 2 hundreds is 5 200.",
          exampleBm: "5 ribu dan 2 ratus ialah 5 200.",
          reviewFocus:
            "Write the places from left to right in order.",
          reviewFocusBm:
            "Tulis tempat dari kiri ke kanan mengikut tertib.",
        },
        "2": {
          misconceptionCode: "ten_thousands_swapped",
          hint:
            "There are 6 ten-thousands, so the first digit is 6, not 3.",
          hintBm:
            "Terdapat 6 puluh ribu, jadi digit pertama ialah 6, bukan 3.",
          example: "4 ten-thousands and 1 thousand is 41 000.",
          exampleBm: "4 puluh ribu dan 1 ribu ialah 41 000.",
          reviewFocus:
            "Start with the ten-thousands digit.",
          reviewFocusBm:
            "Mulakan dengan digit puluh ribu.",
        },
        "3": {
          misconceptionCode: "tens_ones_swapped",
          hint:
            "4 tens comes before 1 one, so the tens digit is 4 and the ones digit is 1.",
          hintBm:
            "4 puluh datang sebelum 1 sa, jadi digit puluh ialah 4 dan digit sa ialah 1.",
          example: "In 7 542, the tens digit is 4 and the ones digit is 2.",
          exampleBm: "Dalam 7 542, digit puluh ialah 4 dan digit sa ialah 2.",
          reviewFocus:
            "Check the last two places are in order.",
          reviewFocusBm:
            "Semak dua tempat terakhir mengikut tertib.",
        },
      },
    },
  ),
  question(
    "hard_05",
    "Hard",
    0.8,
    "Which statement correctly compares 70 007 and 70 070?",
    "Pernyataan manakah membandingkan 70 007 dan 70 070 dengan betul?",
    [
      "70 070 is greater because it has 7 tens.",
      "70 007 is greater because it has 7 ones.",
      "They are equal.",
      "70 007 has 7 thousands.",
    ],
    [
      "70 070 lebih besar kerana mempunyai 7 puluh.",
      "70 007 lebih besar kerana mempunyai 7 sa.",
      "Kedua-duanya sama.",
      "70 007 mempunyai 7 ribu.",
    ],
    0,
    {
      questionType: "Compare two numbers",
      questionTypeBm: "Bandingkan dua nombor",
      sourceLocator:
        `${enBook}, 1.1.2 Compare and Arrange Numbers, compare place by place, p. 6`,
      sourceLocatorBm:
        `${bmBook}, 1.1.2 Banding dan Susun Nombor, banding tempat demi tempat, hlm. 6`,
      difficultyReview: {
        cognitiveDemand: "transfer",
        reasoningStepCount: 3,
        transferRequired: true,
      },
      feedbackByOption: {
        "1": {
          misconceptionCode: "ones_vs_tens_value",
          hint:
            "A digit in the tens place is worth more than a digit in the ones place.",
          hintBm:
            "Digit di tempat puluh bernilai lebih daripada digit di tempat sa.",
          example: "In 41 and 14, 41 is greater because the 4 is in the tens place.",
          exampleBm: "Dalam 41 dan 14, 41 lebih besar kerana 4 berada di tempat puluh.",
          reviewFocus:
            "Compare the value of the places that differ.",
          reviewFocusBm:
            "Bandingkan nilai tempat yang berbeza.",
        },
        "2": {
          misconceptionCode: "place_ignored",
          hint:
            "The numbers look similar, but the last three digits are 007 and 070. Compare those digits place by place.",
          hintBm:
            "Nombor kelihatan sama, tetapi tiga digit terakhir ialah 007 dan 070. Bandingkan digit itu satu per satu.",
          example: "30 005 and 30 050 are not equal.",
          exampleBm: "30 005 dan 30 050 tidak sama.",
          reviewFocus:
            "Compare from the largest place to the smallest.",
          reviewFocusBm:
            "Bandingkan daripada tempat terbesar kepada terkecil.",
        },
        "3": {
          misconceptionCode: "group_value_mixed",
          hint:
            "The thousands digit in both numbers is 0, not 7. The 7 in 70 070 is in the tens place.",
          hintBm:
            "Digit ribu dalam kedua-dua nombor ialah 0, bukan 7. Angka 7 dalam 70 070 berada di tempat puluh.",
          example: "In 60 060, the thousands digit is 0.",
          exampleBm: "Dalam 60 060, digit ribu ialah 0.",
          reviewFocus:
            "Name each digit's place before comparing.",
          reviewFocusBm:
            "Sebut tempat setiap digit sebelum membandingkan.",
        },
      },
    },
  ),
];

const difficulties = ["Easy", "Moderate", "Hard"];
const questionBanks = Object.fromEntries(
  difficulties.map((difficulty) => {
    const bankId = bankIdFor(difficulty);
    return [
      bankId,
      {
        bankId,
        topicId,
        subtopicId,
        skillId,
        yearLevel: 4,
        difficultyLevel: difficulty,
        questionIds: questions
          .filter((item) => item.bankId === bankId)
          .map((item) => item.id),
        version: CONTENT_VERSION,
        isActive: true,
        sourceMaterialId: enMaterialId,
        sourceMaterialIdBm: bmMaterialId,
      },
    ];
  }),
);

function validateQuestionBankSeed() {
  if (Object.keys(questionBanks).length !== 3) {
    throw new Error("Expected exactly three read/write question banks.");
  }
  const ids = new Set();
  for (const [bankId, bank] of Object.entries(questionBanks)) {
    if (!difficulties.includes(bank.difficultyLevel) || bank.questionIds.length !== 5) {
      throw new Error(`Invalid bank ${bankId}: expected exactly five questions.`);
    }
    for (const id of bank.questionIds) {
      if (ids.has(id)) throw new Error(`Question ${id} appears in more than one active bank.`);
      ids.add(id);
      const item = questions.find((candidate) => candidate.id === id);
      if (!item || item.bankId !== bankId) {
        throw new Error(`Invalid question link for ${id}.`);
      }
    }
  }
}

module.exports = { questionBanks, questions, validateQuestionBankSeed };
