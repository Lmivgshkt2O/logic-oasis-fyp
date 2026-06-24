import 'dart:async';

import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';

class OpeningAnimationPage extends StatefulWidget {
  const OpeningAnimationPage({super.key, required this.onFinished});

  final VoidCallback onFinished;

  @override
  State<OpeningAnimationPage> createState() => _OpeningAnimationPageState();
}

class _OpeningAnimationPageState extends State<OpeningAnimationPage>
    with SingleTickerProviderStateMixin {
  late final AnimationController controller;
  late final Animation<double> scale;
  late final Animation<double> fade;
  Timer? timer;

  @override
  void initState() {
    super.initState();
    controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..forward();
    scale = CurvedAnimation(parent: controller, curve: Curves.easeOutBack);
    fade = CurvedAnimation(parent: controller, curve: Curves.easeIn);
    timer = Timer(const Duration(milliseconds: 1850), widget.onFinished);
  }

  @override
  void dispose() {
    timer?.cancel();
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      body: SafeArea(
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(28),
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [LogicOasisTheme.sky, Color(0xFFF7FAF6)],
            ),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              ScaleTransition(
                scale: scale,
                child: Container(
                  width: 126,
                  height: 126,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(28),
                    border: Border.all(color: LogicOasisTheme.line),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x1F4F8F72),
                        blurRadius: 26,
                        offset: Offset(0, 14),
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.spa,
                    size: 64,
                    color: LogicOasisTheme.leaf,
                  ),
                ),
              ),
              const SizedBox(height: 26),
              FadeTransition(
                opacity: fade,
                child: Column(
                  children: [
                    Text('Logic Oasis', style: theme.textTheme.headlineLarge),
                    const SizedBox(height: 8),
                    Text(
                      'Learn. Restore. Grow together.',
                      style: theme.textTheme.bodyLarge,
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
