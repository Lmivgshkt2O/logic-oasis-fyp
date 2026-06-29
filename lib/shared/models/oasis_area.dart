enum OasisResource { crystals, mutualAid }

class OasisArea {
  const OasisArea({
    required this.id,
    required this.title,
    required this.description,
    required this.resource,
    required this.repairCost,
    required this.progress,
  });

  final String id;
  final String title;
  final String description;
  final OasisResource resource;
  final int repairCost;
  final double progress;

  bool get isComplete => progress >= 1;

  String localizedTitle(bool isBahasaMelayu) {
    if (!isBahasaMelayu) return title;
    return _titleBmFallback[title] ?? title;
  }

  String localizedDescription(bool isBahasaMelayu) {
    if (!isBahasaMelayu) return description;
    return _descriptionBmFallback[description] ?? description;
  }

  OasisArea copyWith({
    String? id,
    String? title,
    String? description,
    OasisResource? resource,
    int? repairCost,
    double? progress,
  }) {
    return OasisArea(
      id: id ?? this.id,
      title: title ?? this.title,
      description: description ?? this.description,
      resource: resource ?? this.resource,
      repairCost: repairCost ?? this.repairCost,
      progress: progress ?? this.progress,
    );
  }

  static const Map<String, String> _titleBmFallback = {
    'Fraction Bridge': 'Jambatan Pecahan',
    'Decimal Waterway': 'Laluan Air Perpuluhan',
    'Percentage Garden': 'Taman Peratus',
    'Market Corner': 'Sudut Pasar',
  };

  static const Map<String, String> _descriptionBmFallback = {
    'Reconnect oasis paths and learning routes.':
        'Sambungkan semula laluan oasis dan laluan pembelajaran.',
    'Bring clean water back to the oasis.':
        'Bawa air bersih kembali ke oasis.',
    'Grow green areas through steady practice.':
        'Suburkan kawasan hijau melalui latihan berterusan.',
    'Rebuild facilities with helpful community energy.':
        'Bina semula kemudahan dengan tenaga bantuan komuniti.',
  };
}
