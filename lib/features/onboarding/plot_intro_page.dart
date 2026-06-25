import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';

const _sceneDuration = Duration(milliseconds: 3300);
const _guardianSceneDuration = Duration(milliseconds: 5600);
const _sceneTransitionDuration = Duration(milliseconds: 720);

class PlotIntroPage extends StatefulWidget {
  const PlotIntroPage({super.key, required this.onFinished});

  final VoidCallback onFinished;

  @override
  State<PlotIntroPage> createState() => _PlotIntroPageState();
}

class _PlotIntroPageState extends State<PlotIntroPage>
    with SingleTickerProviderStateMixin {
  late final AnimationController motionController;
  Timer? timer;
  int sceneIndex = 0;
  bool finished = false;

  final scenes = const [
    _StorySceneData(
      title: 'Logic Oasis was thriving',
      body:
          'Bridges, gardens, waterways, and markets helped students practise, think, and learn together.',
      health: 1,
      virus: 0,
      showGuardian: false,
    ),
    _StorySceneData(
      title: 'A logic virus entered',
      body:
          'The virus attacked clear thinking. Paths became unstable, water slowed, and learning zones began to fade.',
      health: 0.68,
      virus: 0.42,
      showGuardian: false,
    ),
    _StorySceneData(
      title: 'The oasis withered away',
      body:
          'Without practice and collaboration, the city lost its energy until only barren land remained.',
      health: 0.08,
      virus: 0.92,
      showGuardian: false,
    ),
    _StorySceneData(
      title: 'AI Guardian activated',
      body:
          'Your mission is to restore Logic Oasis. Practise in Formula Forge, use Home to repair areas, and grow stronger with future collaboration energy.',
      health: 0,
      virus: 0.15,
      showGuardian: true,
    ),
  ];

  @override
  void initState() {
    super.initState();
    motionController = AnimationController(
      vsync: this,
      duration: _sceneDuration,
    )..forward();
    _scheduleNextScene();
  }

  @override
  void dispose() {
    timer?.cancel();
    motionController.dispose();
    super.dispose();
  }

  void _scheduleNextScene() {
    timer?.cancel();
    final duration = scenes[sceneIndex].showGuardian
        ? _guardianSceneDuration
        : _sceneDuration;
    timer = Timer(duration, _advanceScene);
  }

  void _advanceScene() {
    if (!mounted || finished) return;
    if (sceneIndex == scenes.length - 1) {
      _finish();
      return;
    }

    setState(() {
      sceneIndex += 1;
      motionController
        ..duration = scenes[sceneIndex].showGuardian
            ? _guardianSceneDuration
            : _sceneDuration
        ..reset()
        ..forward();
    });
    _scheduleNextScene();
  }

  void _finish() {
    if (finished) return;
    finished = true;
    timer?.cancel();
    widget.onFinished();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scene = scenes[sceneIndex];

    return Scaffold(
      body: SafeArea(
        child: Stack(
          children: [
            Positioned.fill(
              child: DecoratedBox(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [LogicOasisTheme.sky, Color(0xFFF7FAF6)],
                  ),
                ),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(18, 58, 18, 24),
                  child: Column(
                    children: [
                      Expanded(
                        child: AnimatedSwitcher(
                          duration: _sceneTransitionDuration,
                          switchInCurve: Curves.easeOutCubic,
                          switchOutCurve: Curves.easeInCubic,
                          child: _OasisStoryStage(
                            key: ValueKey(sceneIndex),
                            scene: scene,
                            motion: motionController,
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                      _SceneProgress(
                        sceneCount: scenes.length,
                        currentScene: sceneIndex,
                        motion: motionController,
                      ),
                      const SizedBox(height: 18),
                      AnimatedSwitcher(
                        duration: _sceneTransitionDuration,
                        child: _StoryCaption(
                          key: ValueKey('caption-$sceneIndex'),
                          scene: scene,
                          theme: theme,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            Positioned(
              top: 10,
              right: 14,
              child: TextButton(onPressed: _finish, child: const Text('Skip')),
            ),
          ],
        ),
      ),
    );
  }
}

class _StorySceneData {
  const _StorySceneData({
    required this.title,
    required this.body,
    required this.health,
    required this.virus,
    required this.showGuardian,
  });

  final String title;
  final String body;
  final double health;
  final double virus;
  final bool showGuardian;
}

class _OasisStoryStage extends StatelessWidget {
  const _OasisStoryStage({
    super.key,
    required this.scene,
    required this.motion,
  });

  final _StorySceneData scene;
  final Animation<double> motion;

  @override
  Widget build(BuildContext context) {
    final reveal = CurvedAnimation(parent: motion, curve: Curves.easeOutCubic);
    final pulse = CurvedAnimation(
      parent: motion,
      curve: const Interval(0.2, 1, curve: Curves.easeInOut),
    );

    return AnimatedBuilder(
      animation: motion,
      builder: (context, _) {
        final guardianOpacity = scene.showGuardian ? reveal.value : 0.0;
        final guardianLift = (1 - reveal.value) * 18;

        return Center(
          child: AspectRatio(
            aspectRatio: 0.9,
            child: Stack(
              alignment: Alignment.center,
              children: [
                Positioned.fill(
                  child: CustomPaint(
                    painter: _WitheringOasisPainter(
                      health: scene.health,
                      virus: scene.virus,
                      motion: pulse.value,
                    ),
                  ),
                ),
                if (scene.showGuardian)
                  Positioned(
                    top: 24 + guardianLift,
                    left: 22,
                    right: 22,
                    child: Opacity(
                      opacity: guardianOpacity,
                      child: const _GuardianBriefing(),
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _StoryCaption extends StatelessWidget {
  const _StoryCaption({super.key, required this.scene, required this.theme});

  final _StorySceneData scene;
  final ThemeData theme;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(
          scene.showGuardian
              ? Icons.smart_toy_outlined
              : scene.virus > 0.7
              ? Icons.warning_amber_rounded
              : Icons.auto_awesome_outlined,
          color: scene.virus > 0.7
              ? LogicOasisTheme.clay
              : LogicOasisTheme.leaf,
          size: 31,
        ),
        const SizedBox(height: 10),
        Text(
          scene.title,
          style: theme.textTheme.headlineLarge,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 10),
        Text(
          scene.body,
          style: theme.textTheme.bodyLarge,
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

class _GuardianBriefing extends StatelessWidget {
  const _GuardianBriefing();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.94),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: LogicOasisTheme.line),
        boxShadow: const [
          BoxShadow(
            color: Color(0x18000000),
            blurRadius: 16,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Container(
              width: 50,
              height: 50,
              decoration: const BoxDecoration(
                color: LogicOasisTheme.mint,
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.smart_toy_outlined,
                color: LogicOasisTheme.leaf,
                size: 28,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('Guardian Guide', style: theme.textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Text(
                    'Complete missions to collect crystals. Use Home to rebuild each area.',
                    style: theme.textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _WitheringOasisPainter extends CustomPainter {
  const _WitheringOasisPainter({
    required this.health,
    required this.virus,
    required this.motion,
  });

  final double health;
  final double virus;
  final double motion;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final scene = RRect.fromRectAndRadius(
      rect,
      Radius.circular(size.width * 0.07),
    );
    canvas.clipRRect(scene);

    _drawSky(canvas, size);
    _drawGround(canvas, size);
    _drawRiver(canvas, size);
    _drawTiles(canvas, size);
    _drawBuildings(canvas, size);
    _drawGarden(canvas, size);
    _drawVirus(canvas, size);
    _drawBarrenOverlay(canvas, size);
    _drawBorder(canvas, scene);
  }

  void _drawSky(Canvas canvas, Size size) {
    final infected = virus.clamp(0.0, 1.0);
    final skyTop = Color.lerp(
      const Color(0xFFEAF8F4),
      const Color(0xFFE9D8CC),
      infected,
    )!;
    final skyBottom = Color.lerp(
      const Color(0xFFF8F7E7),
      const Color(0xFFD4C1AA),
      infected,
    )!;
    canvas.drawRect(
      Offset.zero & size,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [skyTop, skyBottom],
        ).createShader(Offset.zero & size),
    );

    canvas.drawCircle(
      Offset(size.width * 0.77, size.height * 0.17),
      size.width * (0.1 + 0.01 * motion),
      Paint()
        ..color = Color.lerp(
          const Color(0x88F2D16B),
          const Color(0x66735A45),
          infected,
        )!,
    );

    _drawHill(
      canvas,
      size,
      y: 0.31,
      height: 0.11,
      color: Color.lerp(
        const Color(0x99B8D299),
        const Color(0x998F8066),
        infected,
      )!,
    );
    _drawHill(
      canvas,
      size,
      y: 0.39,
      height: 0.09,
      color: Color.lerp(
        const Color(0xB8D1DCA9),
        const Color(0xB89A8465),
        infected,
      )!,
    );
  }

  void _drawHill(
    Canvas canvas,
    Size size, {
    required double y,
    required double height,
    required Color color,
  }) {
    final path = Path()
      ..moveTo(0, size.height * y)
      ..quadraticBezierTo(
        size.width * 0.25,
        size.height * (y - height),
        size.width * 0.52,
        size.height * y,
      )
      ..quadraticBezierTo(
        size.width * 0.74,
        size.height * (y + height),
        size.width,
        size.height * (y - height * 0.36),
      )
      ..lineTo(size.width, size.height * 0.56)
      ..lineTo(0, size.height * 0.56)
      ..close();
    canvas.drawPath(path, Paint()..color = color);
  }

  void _drawGround(Canvas canvas, Size size) {
    final fieldPath = Path()
      ..moveTo(0, size.height * 0.54)
      ..quadraticBezierTo(
        size.width * 0.48,
        size.height * 0.47,
        size.width,
        size.height * 0.56,
      )
      ..lineTo(size.width, size.height)
      ..lineTo(0, size.height)
      ..close();

    final dry = 1 - health;
    canvas.drawPath(
      fieldPath,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color.lerp(const Color(0xFFBEDAA0), const Color(0xFFD6BE91), dry)!,
            Color.lerp(const Color(0xFF8FC486), const Color(0xFFA98D62), dry)!,
          ],
        ).createShader(Offset.zero & size),
    );
  }

  void _drawRiver(Canvas canvas, Size size) {
    final riverHealth = health.clamp(0.0, 1.0);
    final riverPaint = Paint()
      ..color = Color.lerp(
        const Color(0xFF7E7463),
        LogicOasisTheme.water,
        riverHealth,
      )!
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * (0.05 + riverHealth * 0.08)
      ..strokeCap = StrokeCap.round;

    final path = Path()
      ..moveTo(size.width * 0.61, size.height * 0.39)
      ..cubicTo(
        size.width * 0.45,
        size.height * 0.48,
        size.width * 0.68,
        size.height * 0.58,
        size.width * 0.48,
        size.height * 0.68,
      )
      ..cubicTo(
        size.width * 0.27,
        size.height * 0.78,
        size.width * 0.34,
        size.height * 0.89,
        size.width * 0.45,
        size.height * 0.96,
      );
    canvas.drawPath(path, riverPaint);
  }

  void _drawTiles(Canvas canvas, Size size) {
    final top = Color.lerp(
      const Color(0xFFC8DFA4),
      const Color(0xFFC9AD7B),
      1 - health,
    )!;
    final side = Color.lerp(
      const Color(0xFF8FB26E),
      const Color(0xFF8B7653),
      1 - health,
    )!;
    for (final tile in [
      (Offset(size.width * 0.31, size.height * 0.5), 0.28, 0.13),
      (Offset(size.width * 0.7, size.height * 0.62), 0.3, 0.14),
      (Offset(size.width * 0.27, size.height * 0.73), 0.32, 0.15),
      (Offset(size.width * 0.58, size.height * 0.82), 0.32, 0.13),
    ]) {
      _drawIsoTile(
        canvas,
        center: tile.$1,
        width: size.width * tile.$2,
        height: size.height * tile.$3,
        topColor: top,
        sideColor: side,
      );
    }
  }

  void _drawBuildings(Canvas canvas, Size size) {
    final alive = health.clamp(0.0, 1.0);
    _drawHouse(
      canvas,
      size,
      Offset(size.width * 0.32, size.height * 0.46),
      alive,
    );
    _drawMarket(
      canvas,
      size,
      Offset(size.width * 0.72, size.height * 0.63),
      alive,
    );
    _drawBridge(canvas, size, alive);
  }

  void _drawHouse(Canvas canvas, Size size, Offset center, double alive) {
    final base = Rect.fromCenter(
      center: center,
      width: size.width * 0.16,
      height: size.height * 0.08,
    );
    _drawShadow(canvas, base.center, size.width * 0.17, size.height * 0.032);
    canvas.drawRRect(
      RRect.fromRectAndRadius(base, const Radius.circular(5)),
      Paint()
        ..color = Color.lerp(
          const Color(0xFF8B745B),
          const Color(0xFFDAB77D),
          alive,
        )!,
    );

    final roof = Path()
      ..moveTo(base.left - size.width * 0.016, base.top + size.height * 0.01)
      ..lineTo(base.center.dx, base.top - size.height * 0.055)
      ..lineTo(base.right + size.width * 0.016, base.top + size.height * 0.01)
      ..close();
    canvas.drawPath(
      roof,
      Paint()
        ..color = Color.lerp(
          const Color(0xFF70503C),
          const Color(0xFFA46B45),
          alive,
        )!,
    );
  }

  void _drawMarket(Canvas canvas, Size size, Offset center, double alive) {
    final base = Rect.fromCenter(
      center: center,
      width: size.width * 0.18,
      height: size.height * 0.075,
    );
    _drawShadow(canvas, base.center, size.width * 0.18, size.height * 0.032);
    canvas.drawRRect(
      RRect.fromRectAndRadius(base, const Radius.circular(5)),
      Paint()
        ..color = Color.lerp(
          const Color(0xFF736751),
          const Color(0xFF6FAE78),
          alive,
        )!,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(
          base.left - size.width * 0.012,
          base.top - size.height * 0.025,
          base.width + size.width * 0.024,
          size.height * 0.035,
        ),
        const Radius.circular(5),
      ),
      Paint()
        ..color = Color.lerp(
          const Color(0xFF8A6C55),
          const Color(0xFF89C07D),
          alive,
        )!,
    );
  }

  void _drawBridge(Canvas canvas, Size size, double alive) {
    final bridgePath = Path()
      ..moveTo(size.width * 0.37, size.height * 0.58)
      ..quadraticBezierTo(
        size.width * 0.47,
        size.height * 0.51,
        size.width * 0.58,
        size.height * 0.58,
      );
    canvas.drawPath(
      bridgePath,
      Paint()
        ..color = Color.lerp(
          const Color(0xFF75614B),
          const Color(0xFFC28D61),
          alive,
        )!
        ..strokeWidth = 7
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round,
    );
  }

  void _drawGarden(Canvas canvas, Size size) {
    final alive = health.clamp(0.0, 1.0);
    for (final tree in [
      Offset(size.width * 0.12, size.height * 0.55),
      Offset(size.width * 0.82, size.height * 0.49),
      Offset(size.width * 0.2, size.height * 0.82),
      Offset(size.width * 0.88, size.height * 0.78),
    ]) {
      _drawTree(canvas, tree, size.width * 0.037, alive);
    }

    final flowerPaint = Paint()
      ..color = Color.lerp(
        const Color(0xFF8C765F),
        const Color(0xFFE98F79),
        alive,
      )!;
    for (final flower in [
      Offset(size.width * 0.26, size.height * 0.7),
      Offset(size.width * 0.31, size.height * 0.74),
      Offset(size.width * 0.68, size.height * 0.76),
    ]) {
      canvas.drawCircle(
        flower,
        size.width * 0.008 * (0.4 + alive),
        flowerPaint,
      );
    }
  }

  void _drawVirus(Canvas canvas, Size size) {
    if (virus <= 0) return;
    final paint = Paint()
      ..color = const Color(0xFF7B3F61).withValues(alpha: 0.18 + virus * 0.34);

    for (var i = 0; i < 9; i++) {
      final angle = i * 0.78 + motion * math.pi * 2;
      final radius = size.width * (0.08 + (i % 3) * 0.055);
      final center = Offset(
        size.width * (0.52 + math.cos(angle) * 0.45 * virus),
        size.height * (0.53 + math.sin(angle) * 0.35 * virus),
      );
      canvas.drawCircle(center, radius * virus, paint);
      for (var spike = 0; spike < 6; spike++) {
        final spikeAngle = angle + spike * math.pi / 3;
        final start = Offset(
          center.dx + math.cos(spikeAngle) * radius * virus * 0.75,
          center.dy + math.sin(spikeAngle) * radius * virus * 0.75,
        );
        final end = Offset(
          center.dx + math.cos(spikeAngle) * radius * virus * 1.25,
          center.dy + math.sin(spikeAngle) * radius * virus * 1.25,
        );
        canvas.drawLine(
          start,
          end,
          Paint()
            ..color = paint.color
            ..strokeWidth = 1.5,
        );
      }
    }
  }

  void _drawBarrenOverlay(Canvas canvas, Size size) {
    final barren = (1 - health).clamp(0.0, 1.0);
    if (barren < 0.4) return;

    final crackPaint = Paint()
      ..color = const Color(0xFF6F5A43).withValues(alpha: (barren - 0.35) * 0.7)
      ..strokeWidth = 1.4
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    for (final crack in const [
      [Offset(0.18, 0.72), Offset(0.27, 0.68), Offset(0.33, 0.75)],
      [Offset(0.55, 0.72), Offset(0.62, 0.78), Offset(0.74, 0.74)],
      [Offset(0.4, 0.88), Offset(0.49, 0.83), Offset(0.59, 0.9)],
    ]) {
      final path = Path()
        ..moveTo(size.width * crack[0].dx, size.height * crack[0].dy)
        ..lineTo(size.width * crack[1].dx, size.height * crack[1].dy)
        ..lineTo(size.width * crack[2].dx, size.height * crack[2].dy);
      canvas.drawPath(path, crackPaint);
    }
  }

  void _drawIsoTile(
    Canvas canvas, {
    required Offset center,
    required double width,
    required double height,
    required Color topColor,
    required Color sideColor,
  }) {
    final top = Path()
      ..moveTo(center.dx, center.dy - height * 0.5)
      ..lineTo(center.dx + width * 0.5, center.dy)
      ..lineTo(center.dx, center.dy + height * 0.5)
      ..lineTo(center.dx - width * 0.5, center.dy)
      ..close();
    final sidePath = Path()
      ..moveTo(center.dx - width * 0.5, center.dy)
      ..lineTo(center.dx, center.dy + height * 0.5)
      ..lineTo(center.dx + width * 0.5, center.dy)
      ..lineTo(center.dx, center.dy + height * 0.66)
      ..close();
    canvas.drawPath(sidePath, Paint()..color = sideColor);
    canvas.drawPath(top, Paint()..color = topColor);
    canvas.drawPath(
      top,
      Paint()
        ..color = const Color(0x22000000)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1,
    );
  }

  void _drawTree(Canvas canvas, Offset base, double size, double alive) {
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromCenter(
          center: Offset(base.dx, base.dy + size * 0.35),
          width: size * 0.28,
          height: size * 0.72,
        ),
        const Radius.circular(2),
      ),
      Paint()
        ..color = Color.lerp(
          const Color(0xFF76604A),
          const Color(0xFF9B7350),
          alive,
        )!,
    );
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset(base.dx, base.dy - size * 0.18),
        width: size * (0.45 + alive * 0.7),
        height: size * (0.48 + alive * 0.87),
      ),
      Paint()
        ..color = Color.lerp(
          const Color(0xFF8A7355),
          const Color(0xFF78A76C),
          alive,
        )!,
    );
  }

  void _drawShadow(Canvas canvas, Offset center, double width, double height) {
    canvas.drawOval(
      Rect.fromCenter(center: center, width: width, height: height),
      Paint()..color = const Color(0x22000000),
    );
  }

  void _drawBorder(Canvas canvas, RRect scene) {
    canvas.drawRRect(
      scene.deflate(0.5),
      Paint()
        ..color = LogicOasisTheme.line
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1,
    );
  }

  @override
  bool shouldRepaint(covariant _WitheringOasisPainter oldDelegate) {
    return oldDelegate.health != health ||
        oldDelegate.virus != virus ||
        oldDelegate.motion != motion;
  }
}

class _SceneProgress extends StatelessWidget {
  const _SceneProgress({
    required this.sceneCount,
    required this.currentScene,
    required this.motion,
  });

  final int sceneCount;
  final int currentScene;
  final Animation<double> motion;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        for (var i = 0; i < sceneCount; i++) ...[
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(99),
              child: Container(
                height: 7,
                color: LogicOasisTheme.line,
                child: i < currentScene
                    ? const ColoredBox(color: LogicOasisTheme.leaf)
                    : i == currentScene
                    ? AnimatedBuilder(
                        animation: motion,
                        builder: (context, _) {
                          return FractionallySizedBox(
                            alignment: Alignment.centerLeft,
                            widthFactor: motion.value,
                            child: const ColoredBox(
                              color: LogicOasisTheme.leaf,
                            ),
                          );
                        },
                      )
                    : null,
              ),
            ),
          ),
          if (i != sceneCount - 1) const SizedBox(width: 7),
        ],
      ],
    );
  }
}
