import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
import 'package:logic_oasis/app/theme.dart';
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
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    final locked = onStart == null;
    final style = _TopicVisualStyle.fromTopic(topic);
    final status = _statusFor(topic, locked, oasis);
    final subtitle = locked && lockedReason != null
        ? lockedReason!
        : _restorationSubtitle(topic);
    final masteryLabel = !locked && topic.mastery == 'Locked'
        ? 'New'
        : topic.mastery;

    return Opacity(
      opacity: locked ? .74 : 1,
      child: SoftCard(
        onTap: onStart,
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
                          style: theme.textTheme.headlineSmall?.copyWith(
                            fontSize: 20,
                            height: 1.05,
                          ),
                        ),
                      ),
                      Icon(
                        locked
                            ? Icons.lock_outline_rounded
                            : Icons.chevron_right_rounded,
                        color: oasis.secondaryInk,
                        size: 24,
                      ),
                    ],
                  ),
                  const SizedBox(height: 5),
                  Text(
                    subtitle,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: oasis.secondaryInk,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                  ),

                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Text(
                        '${(topic.progress * 100).round()}%',
                        style: theme.textTheme.titleMedium?.copyWith(
                          color: style.accent,
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
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
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      _MasteryPill(label: masteryLabel, color: style.accent),
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

  _TopicStatus _statusFor(
    Topic topic,
    bool locked,
    OasisSemanticTheme oasis,
  ) {
    if (locked) {
      return _TopicStatus(
        label: 'Locked',
        icon: 'lock_outline',
        color: oasis.neutral,
        background: oasis.groupedSurface,
      );
    }
    if (topic.progress >= .7 || topic.mastery == 'Strong') {
      return _TopicStatus(
        label: 'Doing Great',
        icon: 'check',
        color: oasis.forest,
        background: oasis.mint,
      );
    }
    if (topic.progress < .35 || topic.mastery == 'Weak') {
      return _TopicStatus(
        label: 'Needs Help',
        icon: 'warning',
        color: oasis.coral,
        background: oasis.coral.withValues(alpha: .12),
      );
    }
    return _TopicStatus(
      label: 'Keep Practicing',
      icon: 'star',
      color: OasisSemanticTheme.continuedPracticeText,
      background: oasis.reward.withValues(alpha: .15),
    );
  }
}

class _MasteryPill extends StatelessWidget {
  const _MasteryPill({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    final displayLabel = label.trim().isEmpty ? 'Mastery' : label;
    return Container(
      constraints: const BoxConstraints(maxWidth: 92),
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
      decoration: BoxDecoration(
        color: oasis.groupedSurface,
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
          fontWeight: FontWeight.w600,
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
      return const _TopicVisualStyle(accent: LogicOasisDesign.leafAccent);
    }
    if (topic.id.startsWith('decimals')) {
      return const _TopicVisualStyle(accent: LogicOasisDesign.waterAccent);
    }
    if (topic.id.startsWith('percentages')) {
      return const _TopicVisualStyle(accent: LogicOasisDesign.forumViolet);
    }
    return const _TopicVisualStyle(accent: LogicOasisDesign.statusContinued);
  }
}
