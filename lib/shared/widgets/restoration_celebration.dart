import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';

/// A sparkle / particle burst overlay that plays after a successful repair.
///
/// Usage: insert as an overlay in a Stack and call [show] to trigger.
/// The widget auto-removes its particles after the animation completes.
class RestorationCelebration extends StatefulWidget {
  const RestorationCelebration({super.key});

  /// Creates a celebration overlay and immediately begins the animation.
  static OverlayEntry show(BuildContext context) {
    late final OverlayEntry entry;
    entry = OverlayEntry(
      builder: (_) => RestorationCelebration(
        key: UniqueKey(),
      ),
    );
    Overlay.of(context).insert(entry);

    // Auto-remove after the animation completes.
    Future.delayed(const Duration(milliseconds: 1800), () {
      if (entry.mounted) entry.remove();
    });
    return entry;
  }

  @override
  State<RestorationCelebration> createState() =>
      _RestorationCelebrationState();
}

class _RestorationCelebrationState extends State<RestorationCelebration>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final List<_Particle> _particles;

  static const _particleCount = 24;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1600),
    )..forward();

    final random = math.Random();
    _particles = List.generate(_particleCount, (_) {
      final angle = random.nextDouble() * math.pi * 2;
      final speed = 0.4 + random.nextDouble() * 0.6;
      final size = 3.0 + random.nextDouble() * 5.0;
      final color = _particleColors[random.nextInt(_particleColors.length)];
      return _Particle(
        angle: angle,
        speed: speed,
        size: size,
        color: color,
      );
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  static const _particleColors = [
    Color(0xFFFFD33D), // gold
    Color(0xFF50D2D7), // water/crystal
    Color(0xFF37BD61), // leaf green
    Color(0xFFFF9D3B), // orange
    Color(0xFFFFF4DD), // cream sparkle
    Color(0xFF7F70C8), // purple
  ];

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, _) {
          return CustomPaint(
            painter: _CelebrationPainter(
              progress: _controller.value,
              particles: _particles,
            ),
            child: const SizedBox.expand(),
          );
        },
      ),
    );
  }
}

class _Particle {
  const _Particle({
    required this.angle,
    required this.speed,
    required this.size,
    required this.color,
  });

  final double angle;
  final double speed;
  final double size;
  final Color color;
}

class _CelebrationPainter extends CustomPainter {
  const _CelebrationPainter({
    required this.progress,
    required this.particles,
  });

  final double progress;
  final List<_Particle> particles;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = size.width * 0.45;

    // Fade in quickly, then fade out.
    final opacity = progress < 0.15
        ? (progress / 0.15).clamp(0.0, 1.0)
        : (1.0 - ((progress - 0.15) / 0.85)).clamp(0.0, 1.0);

    // Central glow burst.
    if (progress < 0.4) {
      final glowProgress = (progress / 0.4).clamp(0.0, 1.0);
      final glowRadius = maxRadius * 0.3 * glowProgress;
      final glowOpacity = (1.0 - glowProgress) * 0.35;
      canvas.drawCircle(
        center,
        glowRadius,
        Paint()
          ..color = LogicOasisDesign.yellow.withValues(alpha: glowOpacity)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 20),
      );
    }

    // Sparkle particles.
    for (final particle in particles) {
      final distance = maxRadius * particle.speed * progress;
      final dx = math.cos(particle.angle) * distance;
      final dy = math.sin(particle.angle) * distance;
      final pos = center + Offset(dx, dy);

      // Sparkle size: grow then shrink.
      final sizeMultiplier = progress < 0.3
          ? (progress / 0.3)
          : (1.0 - ((progress - 0.3) / 0.7)).clamp(0.0, 1.0);
      final currentSize = particle.size * sizeMultiplier;

      if (currentSize <= 0) continue;

      final paint = Paint()
        ..color = particle.color.withValues(alpha: opacity * 0.9);
      canvas.drawCircle(pos, currentSize, paint);

      // Small highlight dot.
      canvas.drawCircle(
        pos + Offset(-currentSize * 0.2, -currentSize * 0.2),
        currentSize * 0.3,
        Paint()..color = Colors.white.withValues(alpha: opacity * 0.7),
      );
    }

    // Ring burst.
    if (progress > 0.05 && progress < 0.6) {
      final ringProgress = ((progress - 0.05) / 0.55).clamp(0.0, 1.0);
      final ringRadius = maxRadius * 0.6 * ringProgress;
      final ringOpacity = (1.0 - ringProgress) * 0.3;
      canvas.drawCircle(
        center,
        ringRadius,
        Paint()
          ..color = LogicOasisDesign.leaf.withValues(alpha: ringOpacity)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.5,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _CelebrationPainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}

/// A simpler in-place sparkle animation for use inside a specific widget
/// (e.g. the repair bottom sheet or the oasis hero card scene).
class InlineRestorationSparkle extends StatefulWidget {
  const InlineRestorationSparkle({super.key, this.onComplete});

  final VoidCallback? onComplete;

  @override
  State<InlineRestorationSparkle> createState() =>
      _InlineRestorationSparkleState();
}

class _InlineRestorationSparkleState extends State<InlineRestorationSparkle>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final List<_Particle> _particles;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..forward().then((_) => widget.onComplete?.call());

    final random = math.Random();
    _particles = List.generate(16, (_) {
      final angle = random.nextDouble() * math.pi * 2;
      final speed = 0.3 + random.nextDouble() * 0.5;
      final size = 2.0 + random.nextDouble() * 4.0;
      final color = _colors[random.nextInt(_colors.length)];
      return _Particle(angle: angle, speed: speed, size: size, color: color);
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  static const _colors = [
    Color(0xFFFFD33D),
    Color(0xFF50D2D7),
    Color(0xFF37BD61),
    Color(0xFFFFF4DD),
  ];

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, _) {
          return CustomPaint(
            painter: _CelebrationPainter(
              progress: _controller.value,
              particles: _particles,
            ),
            child: const SizedBox.expand(),
          );
        },
      ),
    );
  }
}
