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
}
