import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/oasis_area.dart';

class OasisMap extends StatefulWidget {
  const OasisMap({
    super.key,
    required this.progress,
    required this.areas,
    required this.crystals,
    required this.mutualAidEnergy,
    required this.isBahasaMelayu,
    required this.canRepair,
    required this.onRepair,
  });

  final double progress;
  final List<OasisArea> areas;
  final int crystals;
  final int mutualAidEnergy;
  final bool isBahasaMelayu;
  final bool Function(OasisArea area) canRepair;
  final bool Function(String areaId) onRepair;

  @override
  State<OasisMap> createState() => _OasisMapState();
}

class _OasisMapState extends State<OasisMap> with TickerProviderStateMixin {
  late final AnimationController introController;
  late final AnimationController pulseController;

  @override
  void initState() {
    super.initState();
    introController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..forward();
    pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2600),
    )..repeat();
  }

  @override
  void dispose() {
    introController.dispose();
    pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final restoration = widget.progress.clamp(0.0, 1.0);
    final areaProgress = {
      for (final area in widget.areas) area.id: area.progress,
    };

    return SizedBox.expand(
      child: AnimatedBuilder(
        animation: Listenable.merge([introController, pulseController]),
        builder: (context, _) {
          final intro = Curves.easeOutCubic.transform(introController.value);
          final pulse = math.sin(pulseController.value * math.pi * 2);

          return Stack(
            alignment: Alignment.center,
            children: [
              Positioned.fill(
                child: CustomPaint(
                  painter: _OasisScenePainter(
                    restoration: restoration,
                    bridge: areaProgress['fraction_bridge'] ?? 0,
                    waterway: areaProgress['decimal_waterway'] ?? 0,
                    garden: areaProgress['percentage_garden'] ?? 0,
                    market: areaProgress['market_corner'] ?? 0,
                    intro: intro,
                    pulse: pulse,
                  ),
                ),
              ),
              Positioned(
                top: 18,
                left: 18,
                child: _ResourceBubble(
                  icon: Icons.diamond_outlined,
                  value: widget.crystals,
                  color: LogicOasisTheme.water,
                ),
              ),
              Positioned(
                top: 18,
                left: 122,
                child: _ResourceBubble(
                  icon: Icons.handshake_outlined,
                  value: widget.mutualAidEnergy,
                  color: LogicOasisTheme.clay,
                ),
              ),
              for (final area in widget.areas)
                _PositionedRepairHotspot(
                  area: area,
                  canRepair: widget.canRepair(area),
                  onOpenDetails: () => _showRepairSheet(context, area),
                ),
            ],
          );
        },
      ),
    );
  }

  int _availableResourceFor(OasisArea area) {
    return switch (area.resource) {
      OasisResource.crystals => widget.crystals,
      OasisResource.mutualAid => widget.mutualAidEnergy,
    };
  }

  Future<void> _showRepairSheet(BuildContext context, OasisArea area) async {
    final result = await showModalBottomSheet<_RepairFeedback>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        return _RepairDetailSheet(
          area: area,
          isBahasaMelayu: widget.isBahasaMelayu,
          availableResource: _availableResourceFor(area),
          canRepair: widget.canRepair(area),
          onRepair: () {
            final repaired = widget.onRepair(area.id);
            Navigator.of(context).pop(
              repaired
                  ? _RepairFeedback.success
                  : area.isComplete
                  ? _RepairFeedback.complete
                  : _RepairFeedback.notEnough,
            );
          },
        );
      },
    );

    if (!context.mounted || result == null) return;
    final l10n = AppLocalizations.of(context)!;
    final areaTitle = area.localizedTitle(widget.isBahasaMelayu);

    final message = switch (result) {
      _RepairFeedback.success => l10n.areaRepaired(areaTitle),
      _RepairFeedback.notEnough =>
        l10n.notEnoughResource(_resourceLabel(area.resource, l10n)),
      _RepairFeedback.complete => l10n.areaFullyRestored(areaTitle),
    };

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }
}

enum _RepairFeedback { success, notEnough, complete }

class _PositionedRepairHotspot extends StatelessWidget {
  const _PositionedRepairHotspot({
    required this.area,
    required this.canRepair,
    required this.onOpenDetails,
  });

  final OasisArea area;
  final bool canRepair;
  final VoidCallback onOpenDetails;

  @override
  Widget build(BuildContext context) {
    final position = switch (area.id) {
      'fraction_bridge' => const _HotspotPosition(left: 64, top: 184),
      'decimal_waterway' => const _HotspotPosition(right: 34, bottom: 212),
      'percentage_garden' => const _HotspotPosition(left: 42, bottom: 194),
      'market_corner' => const _HotspotPosition(right: 48, top: 252),
      _ => const _HotspotPosition(left: 40, bottom: 82),
    };

    return Positioned(
      left: position.left,
      right: position.right,
      top: position.top,
      bottom: position.bottom,
      child: _RepairHotspot(
        area: area,
        canRepair: canRepair,
        onOpenDetails: onOpenDetails,
      ),
    );
  }
}

class _HotspotPosition {
  const _HotspotPosition({this.left, this.right, this.top, this.bottom});

  final double? left;
  final double? right;
  final double? top;
  final double? bottom;
}

class _RepairHotspot extends StatelessWidget {
  const _RepairHotspot({
    required this.area,
    required this.canRepair,
    required this.onOpenDetails,
  });

  final OasisArea area;
  final bool canRepair;
  final VoidCallback onOpenDetails;

  @override
  Widget build(BuildContext context) {
    final resourceIcon = area.resource == OasisResource.crystals
        ? Icons.diamond_outlined
        : Icons.handshake_outlined;
    final color = area.resource == OasisResource.crystals
        ? LogicOasisTheme.water
        : LogicOasisTheme.clay;
    final stateIcon = area.isComplete
        ? Icons.check_circle
        : canRepair
        ? Icons.construction
        : Icons.lock_outline;
    final stateColor = area.isComplete
        ? LogicOasisTheme.leaf
        : canRepair
        ? color
        : const Color(0xFF8B9892);

    return SizedBox(
      width: 62,
      height: 68,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Material(
            color: Colors.white,
            shape: const CircleBorder(),
            elevation: 3,
            shadowColor: const Color(0x22000000),
            child: InkWell(
              customBorder: const CircleBorder(),
              onTap: onOpenDetails,
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: color.withValues(alpha: 0.5)),
                ),
                child: Icon(stateIcon, color: stateColor, size: 25),
              ),
            ),
          ),
          Positioned(
            right: -1,
            bottom: 10,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(99),
                border: Border.all(color: Colors.white, width: 1.5),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(resourceIcon, size: 10, color: Colors.white),
                  const SizedBox(width: 2),
                  Text(
                    '${area.repairCost}',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
            ),
          ),
          Positioned(
            left: 7,
            right: 7,
            bottom: 1,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(99),
              child: LinearProgressIndicator(
                minHeight: 4,
                value: area.progress,
                backgroundColor: Colors.white.withValues(alpha: 0.86),
                color: color,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RepairDetailSheet extends StatelessWidget {
  const _RepairDetailSheet({
    required this.area,
    required this.isBahasaMelayu,
    required this.availableResource,
    required this.canRepair,
    required this.onRepair,
  });

  final OasisArea area;
  final bool isBahasaMelayu;
  final int availableResource;
  final bool canRepair;
  final VoidCallback onRepair;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final resourceIcon = area.resource == OasisResource.crystals
        ? Icons.diamond_outlined
        : Icons.handshake_outlined;
    final resourceColor = area.resource == OasisResource.crystals
        ? LogicOasisTheme.water
        : LogicOasisTheme.clay;
    final l10n = AppLocalizations.of(context)!;
    final resourceLabel = _resourceLabel(area.resource, l10n);

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 46,
                  height: 46,
                  decoration: BoxDecoration(
                    color: resourceColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(resourceIcon, color: resourceColor),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        area.localizedTitle(isBahasaMelayu),
                        style: theme.textTheme.titleLarge,
                      ),
                      Text(
                        area.localizedDescription(isBahasaMelayu),
                        style: theme.textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            LinearProgressIndicator(value: area.progress),
            const SizedBox(height: 8),
            Text(
              l10n.restoredPercent((area.progress * 100).round()),
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                Expanded(
                  child: _SheetMetric(
                    icon: resourceIcon,
                    label: l10n.available,
                    value: '$availableResource',
                    color: resourceColor,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _SheetMetric(
                    icon: Icons.construction_outlined,
                    label: l10n.repairCost,
                    value: '${area.repairCost}',
                    color: LogicOasisTheme.leaf,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: canRepair ? onRepair : null,
              icon: Icon(area.isComplete ? Icons.check : Icons.construction),
              label: Text(
                area.isComplete
                    ? l10n.fullyRestored
                    : canRepair
                    ? l10n.repairWithResource(resourceLabel)
                    : l10n.needMoreResource(resourceLabel),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SheetMetric extends StatelessWidget {
  const _SheetMetric({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: LogicOasisTheme.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color),
          const SizedBox(height: 8),
          Text(value, style: theme.textTheme.titleLarge),
          Text(label, style: theme.textTheme.bodyMedium),
        ],
      ),
    );
  }
}

String _resourceLabel(OasisResource resource, AppLocalizations l10n) {
  return switch (resource) {
    OasisResource.crystals => l10n.mathCrystals,
    OasisResource.mutualAid => l10n.mutualAid,
  };
}

class _ResourceBubble extends StatelessWidget {
  const _ResourceBubble({
    required this.icon,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final int value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.94),
        borderRadius: BorderRadius.circular(99),
        border: Border.all(color: color.withValues(alpha: 0.22)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x14000000),
            blurRadius: 12,
            offset: Offset(0, 6),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 6),
          Text(
            '$value',
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.w800,
              fontSize: 14,
            ),
          ),
        ],
      ),
    );
  }
}

class _OasisScenePainter extends CustomPainter {
  const _OasisScenePainter({
    required this.restoration,
    required this.bridge,
    required this.waterway,
    required this.garden,
    required this.market,
    required this.intro,
    required this.pulse,
  });

  final double restoration;
  final double bridge;
  final double waterway;
  final double garden;
  final double market;
  final double intro;
  final double pulse;

  static const _water = Color(0xFF69CDCF);
  static const _landRestored = Color(0xFFDCEAB3);
  static const _landDry = Color(0xFFCDBB89);
  static const _landSide = Color(0xFF93B66E);
  static const _stoneTop = Color(0xFFEFE9CB);
  static const _stoneSide = Color(0xFFC2BC97);

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final radius = Radius.circular(size.width * 0.045);
    final scene = RRect.fromRectAndRadius(rect, radius);
    canvas.clipRRect(scene);

    _drawSky(canvas, size);
    _drawGround(canvas, size);
    _drawWater(canvas, size);
    _drawLandTiles(canvas, size);
    _drawDecor(canvas, size);
    _drawHouse(canvas, size);
    _drawBridge(canvas, size);
    _drawMarket(canvas, size);
    _drawGarden(canvas, size);
    _drawPond(canvas, size);
    _drawBorder(canvas, scene);
  }

  void _drawSky(Canvas canvas, Size size) {
    final skyPaint = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [Color(0xFFEEF9F7), Color(0xFFFBF8E5)],
      ).createShader(Offset.zero & size);
    canvas.drawRect(Offset.zero & size, skyPaint);

    canvas.drawCircle(
      Offset(size.width * 0.77, size.height * 0.18),
      size.width * (0.108 + 0.004 * pulse),
      Paint()..color = const Color(0x78F0D56E),
    );

    _drawHill(
      canvas,
      size,
      y: 0.28,
      color: const Color(0xFFC7DCA8).withValues(alpha: 0.76),
      height: 0.11,
    );
    _drawHill(
      canvas,
      size,
      y: 0.36,
      color: const Color(0xFFD5E2AF).withValues(alpha: 0.86),
      height: 0.1,
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
        size.width * 0.5,
        size.height * y,
      )
      ..quadraticBezierTo(
        size.width * 0.75,
        size.height * (y + height),
        size.width,
        size.height * (y - height * 0.4),
      )
      ..lineTo(size.width, size.height * 0.55)
      ..lineTo(0, size.height * 0.55)
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
        size.height * 0.55,
      )
      ..lineTo(size.width, size.height)
      ..lineTo(0, size.height)
      ..close();
    final groundPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          Color.lerp(
            const Color(0xFFD8C393),
            const Color(0xFFC9E0A4),
            restoration,
          )!,
          Color.lerp(
            const Color(0xFFBCA779),
            const Color(0xFF9DC98B),
            restoration,
          )!,
        ],
      ).createShader(Offset.zero & size);
    canvas.drawPath(fieldPath, groundPaint);
  }

  void _drawWater(Canvas canvas, Size size) {
    final amount = (0.62 + waterway.clamp(0.0, 1.0) * 0.38) * intro;
    final waterPaint = Paint()
      ..color = Color.lerp(const Color(0xFF79B6B0), _water, amount)!;
    final riverPath = Path()
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
    canvas.drawPath(
      riverPath,
      Paint()
        ..color = waterPaint.color
        ..style = PaintingStyle.stroke
        ..strokeWidth = size.width * 0.14
        ..strokeCap = StrokeCap.round,
    );

    final shimmerPaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.42)
      ..strokeWidth = 2.1
      ..strokeCap = StrokeCap.round;
    for (var i = 0; i < 3; i++) {
      final y = size.height * (0.52 + i * 0.1);
      canvas.drawLine(
        Offset(size.width * (0.43 + i * 0.02), y),
        Offset(size.width * (0.57 + i * 0.02), y + pulse),
        shimmerPaint,
      );
    }
  }

  void _drawLandTiles(Canvas canvas, Size size) {
    _drawIsoTile(
      canvas,
      center: Offset(size.width * 0.32, size.height * 0.48),
      width: size.width * 0.31,
      height: size.height * 0.145,
      topColor: _landTop,
      sideColor: _landSide,
    );
    _drawIsoTile(
      canvas,
      center: Offset(size.width * 0.71, size.height * 0.61),
      width: size.width * 0.33,
      height: size.height * 0.15,
      topColor: _landTop,
      sideColor: _landSide,
    );
    _drawIsoTile(
      canvas,
      center: Offset(size.width * 0.27, size.height * 0.72),
      width: size.width * 0.34,
      height: size.height * 0.155,
      topColor: _landTop,
      sideColor: _landSide,
    );
    _drawIsoTile(
      canvas,
      center: Offset(size.width * 0.58, size.height * 0.8),
      width: size.width * 0.36,
      height: size.height * 0.145,
      topColor: _stoneTop,
      sideColor: _stoneSide,
    );
  }

  void _drawDecor(Canvas canvas, Size size) {
    for (final tree in [
      Offset(size.width * 0.1, size.height * 0.54),
      Offset(size.width * 0.78, size.height * 0.47),
      Offset(size.width * 0.89, size.height * 0.69),
      Offset(size.width * 0.18, size.height * 0.86),
      Offset(size.width * 0.38, size.height * 0.39),
    ]) {
      _drawTree(canvas, tree, size.width * 0.038);
    }

    final pebblePaint = Paint()
      ..color = const Color(0xFF759C6A).withValues(alpha: 0.62);
    for (final pebble in [
      Offset(size.width * 0.16, size.height * 0.8),
      Offset(size.width * 0.4, size.height * 0.66),
      Offset(size.width * 0.77, size.height * 0.78),
      Offset(size.width * 0.88, size.height * 0.86),
    ]) {
      canvas.drawOval(
        Rect.fromCenter(
          center: pebble,
          width: size.width * 0.032,
          height: size.height * 0.01,
        ),
        pebblePaint,
      );
    }
  }

  void _drawHouse(Canvas canvas, Size size) {
    final amount = (0.6 + bridge.clamp(0.0, 1.0) * 0.4) * intro;
    final base = Rect.fromCenter(
      center: Offset(size.width * 0.33, size.height * 0.435),
      width: size.width * 0.18,
      height: size.height * 0.105,
    );
    _drawShadow(canvas, base.center, size.width * 0.2, size.height * 0.04);

    final wallPaint = Paint()
      ..color = Color.lerp(
        const Color(0xFFBA9661),
        const Color(0xFFDDBA7A),
        amount,
      )!;
    canvas.drawRRect(
      RRect.fromRectAndRadius(base, const Radius.circular(5)),
      wallPaint,
    );
    canvas.drawRect(
      Rect.fromLTWH(
        base.right - base.width * 0.22,
        base.top,
        base.width * 0.22,
        base.height,
      ),
      Paint()..color = const Color(0xFFB08455),
    );

    final roof = Path()
      ..moveTo(base.left - size.width * 0.022, base.top + size.height * 0.012)
      ..lineTo(base.center.dx, base.top - size.height * 0.062)
      ..lineTo(base.right + size.width * 0.022, base.top + size.height * 0.012)
      ..close();
    canvas.drawPath(roof, Paint()..color = const Color(0xFFA8633E));
    canvas.drawLine(
      Offset(base.left, base.top + size.height * 0.012),
      Offset(base.right, base.top + size.height * 0.012),
      Paint()
        ..color = const Color(0xFF7E543B)
        ..strokeWidth = 1.7,
    );

    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(
          base.left + base.width * 0.42,
          base.top + base.height * 0.46,
          base.width * 0.18,
          base.height * 0.48,
        ),
        const Radius.circular(3),
      ),
      Paint()..color = const Color(0xFF8D6442),
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(
          base.left + base.width * 0.14,
          base.top + base.height * 0.32,
          base.width * 0.18,
          base.height * 0.2,
        ),
        const Radius.circular(3),
      ),
      Paint()..color = const Color(0xFFE6F3E7),
    );
  }

  void _drawBridge(Canvas canvas, Size size) {
    final amount = bridge.clamp(0.0, 1.0) * intro;
    final bridgeColor = Color.lerp(
      const Color(0xFF8D6D4C),
      const Color(0xFFC28D61),
      amount,
    )!;
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
        ..color = bridgeColor
        ..strokeWidth = 10
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round,
    );

    final railPaint = Paint()
      ..color = const Color(0xFF704F38)
      ..strokeWidth = 2.4
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(
      bridgePath.shift(Offset(0, -size.height * 0.014)),
      railPaint,
    );
    canvas.drawPath(
      bridgePath.shift(Offset(0, size.height * 0.014)),
      railPaint,
    );
    for (var i = 0; i < 4; i++) {
      final x = size.width * (0.4 + i * 0.045);
      canvas.drawLine(
        Offset(x, size.height * 0.55),
        Offset(x, size.height * 0.61),
        railPaint,
      );
    }
  }

  void _drawMarket(Canvas canvas, Size size) {
    final amount = (0.58 + market.clamp(0.0, 1.0) * 0.42) * intro;
    final base = Rect.fromCenter(
      center: Offset(size.width * 0.73, size.height * 0.595),
      width: size.width * 0.22,
      height: size.height * 0.095,
    );
    _drawShadow(canvas, base.center, size.width * 0.23, size.height * 0.038);

    canvas.drawRRect(
      RRect.fromRectAndRadius(base, const Radius.circular(5)),
      Paint()
        ..color = Color.lerp(
          const Color(0xFF6F9667),
          const Color(0xFF64A66F),
          amount,
        )!,
    );
    final awning = Rect.fromLTWH(
      base.left - size.width * 0.014,
      base.top - size.height * 0.03,
      base.width + size.width * 0.028,
      size.height * 0.042,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(awning, const Radius.circular(5)),
      Paint()..color = const Color(0xFF8BC37A),
    );
    final stripePaint = Paint()..color = const Color(0xFFE9F5D7);
    for (var i = 0; i < 3; i++) {
      final x = awning.left + awning.width * (0.2 + i * 0.25);
      canvas.drawRect(
        Rect.fromLTWH(x, awning.top, awning.width * 0.1, awning.height),
        stripePaint,
      );
    }
    canvas.drawRect(
      Rect.fromLTWH(
        base.left + base.width * 0.36,
        base.top + base.height * 0.35,
        base.width * 0.28,
        base.height * 0.5,
      ),
      Paint()..color = const Color(0xFF5B7D58),
    );
  }

  void _drawGarden(Canvas canvas, Size size) {
    final amount = (0.5 + garden.clamp(0.0, 1.0) * 0.5) * intro;
    final center = Offset(size.width * 0.27, size.height * 0.705);
    _drawShadow(canvas, center, size.width * 0.2, size.height * 0.035);

    final leafPaint = Paint()
      ..color = LogicOasisTheme.leaf.withValues(alpha: 0.68 + amount * 0.24);
    for (final spot in [
      Offset(center.dx - size.width * 0.045, center.dy),
      Offset(center.dx + size.width * 0.015, center.dy - size.height * 0.02),
      Offset(center.dx + size.width * 0.052, center.dy + size.height * 0.018),
    ]) {
      canvas.drawOval(
        Rect.fromCenter(
          center: spot,
          width: size.width * 0.078 * amount,
          height: size.height * 0.031 * amount,
        ),
        leafPaint,
      );
    }

    final flowerPaint = Paint()..color = const Color(0xFFE88973);
    for (final flower in [
      Offset(center.dx - size.width * 0.07, center.dy + size.height * 0.035),
      Offset(center.dx + size.width * 0.07, center.dy - size.height * 0.005),
    ]) {
      canvas.drawCircle(flower, size.width * 0.008, flowerPaint);
    }
  }

  void _drawPond(Canvas canvas, Size size) {
    final center = Offset(size.width * 0.58, size.height * 0.785);
    canvas.drawOval(
      Rect.fromCenter(
        center: center,
        width: size.width * 0.27,
        height: size.height * 0.095,
      ),
      Paint()..color = const Color(0xFFE5E0C3),
    );
    canvas.drawOval(
      Rect.fromCenter(
        center: center,
        width: size.width * 0.215,
        height: size.height * 0.069,
      ),
      Paint()..color = _water,
    );
    canvas.drawCircle(
      center,
      size.width * 0.018,
      Paint()..color = const Color(0xFFEAF9F5).withValues(alpha: 0.86),
    );
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
    final leftSide = Path()
      ..moveTo(center.dx - width * 0.5, center.dy)
      ..lineTo(center.dx, center.dy + height * 0.5)
      ..lineTo(center.dx, center.dy + height * 0.66)
      ..lineTo(center.dx - width * 0.5, center.dy + height * 0.16)
      ..close();
    final rightSide = Path()
      ..moveTo(center.dx + width * 0.5, center.dy)
      ..lineTo(center.dx, center.dy + height * 0.5)
      ..lineTo(center.dx, center.dy + height * 0.66)
      ..lineTo(center.dx + width * 0.5, center.dy + height * 0.16)
      ..close();

    canvas.drawPath(leftSide, Paint()..color = sideColor);
    canvas.drawPath(
      rightSide,
      Paint()
        ..color = Color.alphaBlend(
          Colors.black.withValues(alpha: 0.05),
          sideColor,
        ),
    );
    canvas.drawPath(top, Paint()..color = topColor);
    canvas.drawPath(
      top,
      Paint()
        ..color = const Color(0x22000000)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1,
    );
  }

  void _drawTree(Canvas canvas, Offset base, double size) {
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromCenter(
          center: Offset(base.dx, base.dy + size * 0.35),
          width: size * 0.28,
          height: size * 0.72,
        ),
        const Radius.circular(2),
      ),
      Paint()..color = const Color(0xFF9B7350),
    );
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset(base.dx, base.dy - size * 0.18),
        width: size * 1.15,
        height: size * 1.35,
      ),
      Paint()..color = const Color(0xFF78A76C),
    );
  }

  void _drawShadow(Canvas canvas, Offset center, double width, double height) {
    canvas.drawOval(
      Rect.fromCenter(center: center, width: width, height: height),
      Paint()..color = const Color(0x22000000),
    );
  }

  void _drawBorder(Canvas canvas, RRect scene) {
    final borderPaint = Paint()
      ..color = LogicOasisTheme.line
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    canvas.drawRRect(scene.deflate(0.5), borderPaint);
  }

  Color get _landTop => Color.lerp(_landDry, _landRestored, restoration)!;

  @override
  bool shouldRepaint(covariant _OasisScenePainter oldDelegate) {
    return oldDelegate.restoration != restoration ||
        oldDelegate.bridge != bridge ||
        oldDelegate.waterway != waterway ||
        oldDelegate.garden != garden ||
        oldDelegate.market != market ||
        oldDelegate.intro != intro ||
        oldDelegate.pulse != pulse;
  }
}
