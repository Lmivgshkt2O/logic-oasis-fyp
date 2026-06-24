import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';

class MasteryChip extends StatelessWidget {
  const MasteryChip({super.key, required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final color = switch (label) {
      'Strong' => LogicOasisTheme.leaf,
      'Moderate' => LogicOasisTheme.water,
      'Locked' => const Color(0xFF8F8F8F),
      _ => LogicOasisTheme.clay,
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(99),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w700,
          fontSize: 11,
          height: 1,
        ),
      ),
    );
  }
}
