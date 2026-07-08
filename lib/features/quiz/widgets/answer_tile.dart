import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
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
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    Color border = LogicOasisTheme.line;
    Color background = LogicOasisDesign.card;
    IconData? icon;

    if (correct) {
      border = LogicOasisTheme.leaf;
      background = LogicOasisTheme.mint;
      icon = Icons.check_circle_outline;
    } else if (wrong) {
      border = LogicOasisTheme.clay;
      background = LogicOasisTheme.sand;
      icon = Icons.cancel_outlined;
    } else if (selected) {
      border = LogicOasisTheme.water;
      background = LogicOasisTheme.sky;
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
          boxShadow: LogicOasisDesign.softShadow,
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
