import 'package:flutter/material.dart';
import 'package:logic_oasis/shared/models/topic.dart';
import 'package:logic_oasis/shared/widgets/mastery_chip.dart';

class TopicProgressRow extends StatelessWidget {
  const TopicProgressRow({super.key, required this.topic});

  final Topic topic;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(topic.title, style: theme.textTheme.titleMedium),
            ),
            MasteryChip(label: topic.mastery),
          ],
        ),
        const SizedBox(height: 8),
        LinearProgressIndicator(value: topic.progress),
      ],
    );
  }
}
