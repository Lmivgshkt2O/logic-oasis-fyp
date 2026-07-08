class QuizQuestion {
  const QuizQuestion({
    this.subtopicId,
    this.order,
    this.bloomLevel,
    required this.question,
    this.questionBm,
    required this.options,
    this.optionsBm,
    required this.answerIndex,
    required this.explanation,
    this.explanationBm,
  });

  final String? subtopicId;
  final int? order;
  final String? bloomLevel;
  final String question;
  final String? questionBm;
  final List<String> options;
  final List<String>? optionsBm;
  final int answerIndex;
  final String explanation;
  final String? explanationBm;

  String localizedQuestion(bool isBahasaMelayu) {
    if (!isBahasaMelayu) return question;
    if (questionBm != null && questionBm!.trim().isNotEmpty) {
      return questionBm!;
    }
    return _questionBmFallback[question] ?? question;
  }

  List<String> localizedOptions(bool isBahasaMelayu) {
    if (!isBahasaMelayu) return options;
    if (optionsBm == null || optionsBm!.length != options.length) {
      return options;
    }
    return optionsBm!;
  }

  String localizedExplanation(bool isBahasaMelayu) {
    if (!isBahasaMelayu) return explanation;
    if (explanationBm != null && explanationBm!.trim().isNotEmpty) {
      return explanationBm!;
    }
    return _explanationBmFallback[explanation] ?? explanation;
  }

  static const Map<String, String> _questionBmFallback = {
    'Which fraction is equal to 1/2?': 'Pecahan manakah yang sama dengan 1/2?',
    'Which fraction is larger?': 'Pecahan manakah yang lebih besar?',
    'What is 1/4 + 1/4?': 'Berapakah 1/4 + 1/4?',
    'Which shows three out of four equal parts?':
        'Yang manakah menunjukkan tiga daripada empat bahagian yang sama?',
    'What is 2/6 simplified?': 'Apakah bentuk ringkas bagi 2/6?',
    'What is 1 1/2 + 1/2?': 'Berapakah 1 1/2 + 1/2?',
    'Which fraction is equivalent to 3/5?':
        'Pecahan manakah yang setara dengan 3/5?',
    'What is 2.35 + 1.4?': 'Berapakah 2.35 + 1.4?',
    'What is 5.0 - 0.75?': 'Berapakah 5.0 - 0.75?',
    'What is 25% of 80?': 'Berapakah 25% daripada 80?',
    '50% is the same as which fraction?':
        '50% adalah sama dengan pecahan yang mana?',
    'How many centimetres are in 2.5 metres?':
        'Berapakah sentimeter dalam 2.5 meter?',
    'How many grams are in 3 kg?': 'Berapakah gram dalam 3 kg?',
    'What is 2/3 of 24?': 'Berapakah 2/3 daripada 24?',
    'What is 3/4 x 20?': 'Berapakah 3/4 x 20?',
    'A RM50 bag has a 10% discount. What is the discount?':
        'Beg berharga RM50 mendapat diskaun 10%. Berapakah diskaunnya?',
    'A price increases from RM40 to RM50. What is the increase?':
        'Harga meningkat daripada RM40 kepada RM50. Berapakah peratus kenaikan?',
    'The ratio of red to blue beads is 2:3. If there are 10 red beads, how many blue beads are there?':
        'Nisbah manik merah kepada biru ialah 2:3. Jika terdapat 10 manik merah, berapa manik biru?',
    'Simplify the ratio 12:18.': 'Ringkaskan nisbah 12:18.',
    'Find the average of 6, 8, and 10.':
        'Cari purata bagi 6, 8 dan 10.',
    'The mode of 3, 5, 5, 7, 8 is...':
        'Mod bagi 3, 5, 5, 7, 8 ialah...',
  };

  static const Map<String, String> _explanationBmFallback = {
    '2/4 can be simplified by dividing both numbers by 2.':
        '2/4 boleh diringkaskan dengan membahagi kedua-dua nombor dengan 2.',
    'For unit fractions, the smaller denominator is larger.':
        'Bagi pecahan unit, penyebut yang lebih kecil memberi nilai lebih besar.',
    'One quarter plus one quarter makes two quarters, or 1/2.':
        'Satu perempat tambah satu perempat menjadi dua perempat, iaitu 1/2.',
    '3/4 means three selected parts from four equal parts.':
        '3/4 bermaksud tiga bahagian dipilih daripada empat bahagian yang sama.',
    'Divide 2 and 6 by 2. The answer is 1/3.':
        'Bahagi 2 dan 6 dengan 2. Jawapannya ialah 1/3.',
    '1 1/2 plus 1/2 makes 2 wholes.':
        '1 1/2 tambah 1/2 menjadi 2 penuh.',
    'Multiply both numerator and denominator by 2.':
        'Darabkan pengangka dan penyebut dengan 2.',
    'Line up decimal places: 2.35 + 1.40 = 3.75.':
        'Selaraskan tempat perpuluhan: 2.35 + 1.40 = 3.75.',
    '5.00 minus 0.75 equals 4.25.':
        '5.00 tolak 0.75 bersamaan 4.25.',
    '25% is one quarter. One quarter of 80 is 20.':
        '25% ialah satu perempat. Satu perempat daripada 80 ialah 20.',
    '50% means half of the whole.':
        '50% bermaksud separuh daripada keseluruhan.',
    '1 metre is 100 cm, so 2.5 metres is 250 cm.':
        '1 meter ialah 100 cm, jadi 2.5 meter ialah 250 cm.',
    '1 kg is 1000 g, so 3 kg is 3000 g.':
        '1 kg ialah 1000 g, jadi 3 kg ialah 3000 g.',
    'One third of 24 is 8, so two thirds is 16.':
        'Satu pertiga daripada 24 ialah 8, jadi dua pertiga ialah 16.',
    'A quarter of 20 is 5, so three quarters is 15.':
        'Satu perempat daripada 20 ialah 5, jadi tiga perempat ialah 15.',
    '10% of RM50 is RM5.': '10% daripada RM50 ialah RM5.',
    'The increase is RM10. RM10 out of RM40 is 25%.':
        'Kenaikan ialah RM10. RM10 daripada RM40 ialah 25%.',
    '2 parts equals 10, so 1 part equals 5. Blue is 3 parts, so 15.':
        '2 bahagian bersamaan 10, jadi 1 bahagian bersamaan 5. Biru ialah 3 bahagian, jadi 15.',
    'Divide both numbers by 6 to get 2:3.':
        'Bahagi kedua-dua nombor dengan 6 untuk mendapat 2:3.',
    '6 + 8 + 10 = 24, and 24 divided by 3 is 8.':
        '6 + 8 + 10 = 24, dan 24 dibahagi 3 ialah 8.',
    'The mode is the value that appears most often.':
        'Mod ialah nilai yang muncul paling kerap.',
  };
}
