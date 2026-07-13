import 'dart:ui';

enum OasisResource { crystals, mutualAid }

class OasisArea {
  const OasisArea({
    required this.id,
    required this.title,
    required this.description,
    required this.resource,
    required this.repairCost,
    required this.progress,
    this.topic = '',
    this.markerPosition = Offset.zero,
    this.damagedImage = '',
    this.repairingImage = '',
    this.restoredImage = '',
    this.homeOverlay50,
    this.homeOverlay100,
  });

  final String id;
  final String title;
  final String description;
  final OasisResource resource;
  final int repairCost;
  final double progress;

  /// The math topic this oasis area is linked to (e.g. 'Fractions').
  final String topic;

  /// Fractional position (0.0–1.0) within the scene for the repair marker.
  final Offset markerPosition;

  /// Standalone preview images for damaged / repairing / restored states.
  final String damagedImage;
  final String repairingImage;
  final String restoredImage;

  /// Scene-aligned transparent overlays for in-scene restoration visuals.
  final String? homeOverlay50;
  final String? homeOverlay100;

  bool get isComplete => progress >= 1;

  /// Returns the standalone preview image matching the current progress.
  String get currentImage {
    if (damagedImage.isEmpty) return '';
    if (progress >= 1.0) return restoredImage;
    if (progress >= 0.5) return repairingImage;
    return damagedImage;
  }

  /// Returns the scene overlay path for the current progress, or null.
  String? get currentOverlay {
    if (progress >= 1.0) return homeOverlay100;
    if (progress >= 0.5) return homeOverlay50;
    return null;
  }

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
    String? topic,
    Offset? markerPosition,
    String? damagedImage,
    String? repairingImage,
    String? restoredImage,
    String? homeOverlay50,
    String? homeOverlay100,
  }) {
    return OasisArea(
      id: id ?? this.id,
      title: title ?? this.title,
      description: description ?? this.description,
      resource: resource ?? this.resource,
      repairCost: repairCost ?? this.repairCost,
      progress: progress ?? this.progress,
      topic: topic ?? this.topic,
      markerPosition: markerPosition ?? this.markerPosition,
      damagedImage: damagedImage ?? this.damagedImage,
      repairingImage: repairingImage ?? this.repairingImage,
      restoredImage: restoredImage ?? this.restoredImage,
      homeOverlay50: homeOverlay50 ?? this.homeOverlay50,
      homeOverlay100: homeOverlay100 ?? this.homeOverlay100,
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
