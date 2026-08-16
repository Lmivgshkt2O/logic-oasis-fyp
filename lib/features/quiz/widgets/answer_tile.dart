import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';

class AnswerTile extends StatelessWidget {
  const AnswerTile({
    super.key,
    required this.label,
    required this.selected,
    required this.correct,
    required this.wrong,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final bool correct;
  final bool wrong;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    Color border = oasis.outline;
    Color background = oasis.surface;
    IconData? icon;

    if (correct) {
      border = oasis.leaf;
      background = oasis.mint;
      icon = Icons.check_circle_outline;
    } else if (wrong) {
      border = oasis.coral;
      background = oasis.coral.withValues(alpha: .12);
      icon = Icons.cancel_outlined;
    } else if (selected) {
      border = oasis.water;
      background = oasis.water.withValues(alpha: .12);
    }

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: border, width: 1.4),
          boxShadow: oasis.softShadow,
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                label,
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            if (icon != null) Icon(icon, color: border),
          ],
        ),
      ),
    );
  }
}
