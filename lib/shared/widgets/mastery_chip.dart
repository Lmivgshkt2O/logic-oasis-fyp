import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';

class MasteryChip extends StatelessWidget {
  const MasteryChip({
    super.key,
    required this.label,
    this.isBahasaMelayu = false,
  });

  final String label;
  final bool isBahasaMelayu;

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    final color = switch (label) {
      'Strong' => oasis.statusStrong,
      'Moderate' => oasis.water,
      'Locked' => oasis.statusLocked,
      _ => oasis.statusNeedsHelp,
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.13),
        borderRadius: BorderRadius.circular(99),
      ),
      child: Text(
        _displayLabel(label, isBahasaMelayu),
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.w600,
          fontSize: 12.5,
          height: 1,
        ),
      ),
    );
  }

  static String _displayLabel(String label, bool isBahasaMelayu) {
    if (!isBahasaMelayu) return label.isEmpty ? 'Mastery' : label;
    return switch (label) {
      'Strong' => 'Kukuh',
      'Moderate' => 'Sederhana',
      'Weak' => 'Lemah',
      'New' => 'Baharu',
      'Locked' => 'Dikunci',
      '' => 'Penguasaan',
      _ => label,
    };
  }
}
