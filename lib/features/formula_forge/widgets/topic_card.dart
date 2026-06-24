import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/shared/models/topic.dart';
import 'package:logic_oasis/shared/widgets/mastery_chip.dart';

class TopicCard extends StatelessWidget {
  const TopicCard({
    super.key,
    required this.topic,
    required this.isBahasaMelayu,
    required this.onStart,
  });

  final Topic topic;
  final bool isBahasaMelayu;
  final VoidCallback? onStart;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final style = _TopicVisuals.forId(topic.id);
    final progress = (topic.progress * 100).round();
    final isLocked = onStart == null;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(13),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: style.color.withValues(alpha: 0.13),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(style.icon, color: style.color, size: 28),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          isBahasaMelayu ? topic.titleBm : topic.title,
                          style: theme.textTheme.titleLarge,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      MasteryChip(label: topic.mastery),
                    ],
                  ),
                  const SizedBox(height: 3),
                  Text(
                    topic.area,
                    style: theme.textTheme.bodyMedium,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 13),
                  Row(
                    children: [
                      Expanded(
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(99),
                          child: LinearProgressIndicator(
                            minHeight: 6,
                            value: topic.progress,
                            backgroundColor: const Color(0xFFECEDE8),
                            color: style.color,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      SizedBox(
                        width: 34,
                        child: Text(
                          '$progress%',
                          textAlign: TextAlign.right,
                          style: theme.textTheme.bodyMedium,
                        ),
                      ),
                      const SizedBox(width: 10),
                      SizedBox(
                        width: 102,
                        child: FilledButton(
                          onPressed: onStart,
                          style: FilledButton.styleFrom(
                            backgroundColor: isLocked
                                ? const Color(0xFFE6E6E6)
                                : LogicOasisTheme.leaf,
                            foregroundColor: isLocked
                                ? const Color(0xFF696969)
                                : Colors.white,
                            minimumSize: const Size.fromHeight(40),
                            padding: const EdgeInsets.symmetric(horizontal: 8),
                          ),
                          child: FittedBox(
                            fit: BoxFit.scaleDown,
                            child: Text(
                              isLocked
                                  ? isBahasaMelayu
                                        ? 'Dikunci'
                                        : 'Locked'
                                  : isBahasaMelayu
                                  ? 'Mula Latihan'
                                  : 'Start Practice',
                              maxLines: 1,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TopicVisuals {
  const _TopicVisuals({required this.icon, required this.color});

  final IconData icon;
  final Color color;

  static _TopicVisuals forId(String id) {
    if (id.startsWith('fractions')) {
      return const _TopicVisuals(
        icon: Icons.pie_chart_outline,
        color: LogicOasisTheme.leaf,
      );
    }
    if (id.startsWith('decimals')) {
      return const _TopicVisuals(
        icon: Icons.water_drop_outlined,
        color: LogicOasisTheme.water,
      );
    }
    if (id.startsWith('percentages')) {
      return const _TopicVisuals(icon: Icons.percent, color: Color(0xFFE6A93C));
    }
    return const _TopicVisuals(
      icon: Icons.shopping_bag_outlined,
      color: Color(0xFFC09A67),
    );
  }
}
