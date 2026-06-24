import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';

class RecommendationBox extends StatelessWidget {
  const RecommendationBox({super.key, required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: LogicOasisTheme.sand,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFF0D8B8)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.tips_and_updates_outlined,
            color: LogicOasisTheme.clay,
          ),
          const SizedBox(width: 10),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}
