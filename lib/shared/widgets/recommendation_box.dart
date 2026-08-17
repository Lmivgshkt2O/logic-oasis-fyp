import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';

class RecommendationBox extends StatelessWidget {
  const RecommendationBox({super.key, required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: oasis.mint,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: oasis.outline),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.tips_and_updates_outlined,
            color: oasis.leaf,
          ),
          const SizedBox(width: 10),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}
