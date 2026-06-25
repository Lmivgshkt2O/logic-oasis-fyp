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
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.13),
        borderRadius: BorderRadius.circular(99),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w800,
          fontSize: 12.5,
          height: 1,
        ),
      ),
    );
  }
}
