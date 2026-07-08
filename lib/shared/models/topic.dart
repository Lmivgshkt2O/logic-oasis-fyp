import 'package:logic_oasis/shared/models/quiz_question.dart';
import 'package:logic_oasis/shared/models/subtopic.dart';

class Topic {
  const Topic({
    required this.id,
    required this.title,
    required this.titleBm,
    required this.area,
    this.areaBm,
    required this.yearLevel,
    required this.progress,
    required this.mastery,
    List<QuizQuestion> questions = const [],
    this.subtopics = const [],
  }) : _questions = questions;

  final String id;
  final String title;
  final String titleBm;
  final String area;
  final String? areaBm;
  final int yearLevel;
  final double progress;
  final String mastery;
  final List<QuizQuestion> _questions;
  final List<Subtopic> subtopics;

  List<QuizQuestion> get questions {
    if (_questions.isNotEmpty || subtopics.isEmpty) return _questions;
    return subtopics
        .expand((subtopic) => subtopic.questions)
        .toList(growable: false);
  }

  Topic copyWith({
    String? id,
    String? title,
    String? titleBm,
    String? area,
    String? areaBm,
    int? yearLevel,
    double? progress,
    String? mastery,
    List<QuizQuestion>? questions,
    List<Subtopic>? subtopics,
  }) {
    return Topic(
      id: id ?? this.id,
      title: title ?? this.title,
      titleBm: titleBm ?? this.titleBm,
      area: area ?? this.area,
      areaBm: areaBm ?? this.areaBm,
      yearLevel: yearLevel ?? this.yearLevel,
      progress: progress ?? this.progress,
      mastery: mastery ?? this.mastery,
      questions: questions ?? this.questions,
      subtopics: subtopics ?? this.subtopics,
    );
  }

  String localizedTitle(bool isBahasaMelayu) {
    return isBahasaMelayu ? titleBm : title;
  }

  String localizedArea(bool isBahasaMelayu) {
    if (!isBahasaMelayu) return area;
    if (areaBm != null && areaBm!.trim().isNotEmpty) return areaBm!;
    return _areaBmFallback[area] ?? area;
  }

  static const Map<String, String> _areaBmFallback = {
    'Understand and compare fractions': 'Fahami dan bandingkan pecahan',
    'Decimals and place value': 'Perpuluhan dan nilai tempat',
    'Percentages in real life': 'Peratus dalam kehidupan harian',
    'Money and daily spending': 'Wang dan perbelanjaan harian',
    'Mixed numbers and fraction operations':
        'Nombor bercampur dan operasi pecahan',
    'Decimal addition and subtraction': 'Tambah dan tolak perpuluhan',
    'Percentage of quantities': 'Peratus daripada kuantiti',
    'Length, mass, and volume conversion': 'Penukaran panjang, jisim dan isi padu',
    'Fraction problem solving': 'Penyelesaian masalah pecahan',
    'Discounts, profit, and loss': 'Diskaun, untung dan rugi',
    'Compare quantities using ratios': 'Bandingkan kuantiti menggunakan nisbah',
    'Read charts and calculate averages': 'Baca carta dan kira purata',
  };
}
