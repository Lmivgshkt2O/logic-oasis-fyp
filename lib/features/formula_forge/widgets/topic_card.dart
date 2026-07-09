import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
import 'package:logic_oasis/shared/models/topic.dart';
import 'package:logic_oasis/shared/widgets/logic_oasis_figma_components.dart';

class TopicCard extends StatelessWidget {
  const TopicCard({
    super.key,
    required this.topic,
    required this.isBahasaMelayu,
    required this.onStart,
    this.lockedReason,
  });

  final Topic topic;
  final bool isBahasaMelayu;
  final VoidCallback? onStart;
  final String? lockedReason;

  @override
  Widget build(BuildContext context) {
    final locked = onStart == null;
    final style = _TopicVisualStyle.fromTopic(topic);
    final status = _statusFor(topic, locked);
    final subtitle = locked && lockedReason != null
        ? lockedReason!
        : _restorationSubtitle(topic);
    final learningArea = topic.localizedArea(isBahasaMelayu);
    final masteryLabel = !locked && topic.mastery == 'Locked'
        ? 'New'
        : topic.mastery;

    return Opacity(
      opacity: locked ? .74 : 1,
      child: SoftCard(
        onTap: onStart,
        color: const Color(0xFFFFFDF4),
        child: Row(
          children: [
            TopicThumbnail(topicId: topic.id),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          topic.localizedTitle(isBahasaMelayu),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: LogicOasisDesign.ink,
                            fontSize: 20,
                            fontWeight: FontWeight.w900,
                            height: 1.05,
                          ),
                        ),
                      ),
                      Icon(
                        locked
                            ? Icons.lock_outline_rounded
                            : Icons.chevron_right_rounded,
                        color: const Color(0xFF85745C),
                        size: 24,
                      ),
                    ],
                  ),
                  const SizedBox(height: 5),
                  Text(
                    subtitle,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: LogicOasisDesign.body,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),

                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Text(
                        '${(topic.progress * 100).round()}%',
                        style: TextStyle(
                      color: style.accent,
                      fontSize: 16,
                      fontWeight: FontWeight.w900,
                    ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: ProgressBar(
                          value: topic.progress,
                          color: style.accent,
                          height: 7,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      _MasteryPill(label: masteryLabel, color: style.accent),
                      const Spacer(),
                      StatusChip(
                        label: status.label,
                        icon: status.icon,
                        color: status.color,
                        background: status.background,
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

  String _restorationSubtitle(Topic topic) {
    if (topic.id.startsWith('fractions')) return 'Repair the Fraction Bridge';
    if (topic.id.startsWith('decimals')) return 'Refresh the Waterway';
    if (topic.id.startsWith('percentages')) return 'Grow the Palm Garden';
    if (topic.id.startsWith('money')) return 'Rebuild the Market Corner';
    return topic.localizedArea(isBahasaMelayu);
  }

  _TopicStatus _statusFor(Topic topic, bool locked) {
    if (locked) {
      return const _TopicStatus(
        label: 'Locked',
        icon: 'lock_outline',
        color: Color(0xFF8C7A61),
        background: Color(0xFFF1E8D7),
      );
    }
    if (topic.progress >= .7 || topic.mastery == 'Strong') {
      return const _TopicStatus(
        label: 'Doing Great',
        icon: 'check',
        color: LogicOasisDesign.forest,
        background: Color(0xFFE3F5DB),
      );
    }
    if (topic.progress < .35 || topic.mastery == 'Weak') {
      return const _TopicStatus(
        label: 'Needs Help',
        icon: 'warning',
        color: Color(0xFFD84D45),
        background: Color(0xFFFFE8E0),
      );
    }
    return const _TopicStatus(
      label: 'Keep Practicing',
      icon: 'star',
      color: Color(0xFFB96E00),
      background: Color(0xFFFFF0CC),
    );
  }
}

class _MasteryPill extends StatelessWidget {
  const _MasteryPill({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final displayLabel = label.trim().isEmpty ? 'Mastery' : label;
    return Container(
      constraints: const BoxConstraints(maxWidth: 92),
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF8EC),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: .18)),
      ),
      child: Text(
        displayLabel,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          color: color,
          fontSize: 11.5,
          fontWeight: FontWeight.w900,
          height: 1,
        ),
      ),
    );
  }
}

class _TopicStatus {
  const _TopicStatus({
    required this.label,
    required this.icon,
    required this.color,
    required this.background,
  });

  final String label;
  final String icon;
  final Color color;
  final Color background;
}

class _TopicVisualStyle {
  const _TopicVisualStyle({required this.accent});

  final Color accent;

  static _TopicVisualStyle fromTopic(Topic topic) {
    if (topic.id.startsWith('fractions')) {
      return const _TopicVisualStyle(accent: LogicOasisDesign.leaf);
    }
    if (topic.id.startsWith('decimals')) {
      return const _TopicVisualStyle(accent: Color(0xFF35ABC1));
    }
    if (topic.id.startsWith('percentages')) {
      return const _TopicVisualStyle(accent: LogicOasisDesign.purple);
    }
    return const _TopicVisualStyle(accent: Color(0xFFE9A924));
  }
}
