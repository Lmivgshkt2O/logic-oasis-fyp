// ignore_for_file: unused_element

import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/models/oasis_area.dart';
import 'package:logic_oasis/shared/widgets/restoration_celebration.dart';

class AppSvgIcon extends StatelessWidget {
  const AppSvgIcon(this.assetName, {super.key, this.color, this.size});

  final String assetName;
  final Color? color;
  final double? size;

  @override
  Widget build(BuildContext context) {
    return SvgPicture.asset(
      'assets/icons/$assetName.svg',
      width: size,
      height: size,
      colorFilter: color != null
          ? ColorFilter.mode(color!, BlendMode.srcIn)
          : null,
    );
  }
}

class AppIllustration extends StatelessWidget {
  const AppIllustration(
    this.assetName, {
    super.key,
    this.fit = BoxFit.cover,
    this.width,
    this.height,
    this.softStyle = true,
  });

  final String assetName;
  final BoxFit fit;
  final double? width;
  final double? height;
  final bool softStyle;

  @override
  Widget build(BuildContext context) {
    Widget image = Image.asset(
      'assets/illustrations/$assetName',
      fit: fit,
      width: width,
      height: height,
    );

    if (softStyle) {
      // 1. Soft opacity and warm overlay
      image = ColorFiltered(
        colorFilter: const ColorFilter.mode(
          Color(0x14D6B37E), // very light warm tint
          BlendMode.srcOver,
        ),
        child: Opacity(opacity: 0.95, child: image),
      );

      // 2. Inner border and soft lighting gradient to blend with cards
      image = Container(
        foregroundDecoration: BoxDecoration(
          border: Border.all(
            color: const Color(0xFFF1E8D7).withValues(alpha: .6),
            width: 1.5,
          ),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Colors.white.withValues(alpha: .15),
              Colors.transparent,
              const Color(0xFF8A7659).withValues(alpha: .08),
            ],
          ),
        ),
        child: image,
      );
    }

    return image;
  }
}

class LogicOasisScaffold extends StatelessWidget {
  const LogicOasisScaffold({
    super.key,
    required this.children,
    this.padding = const EdgeInsets.fromLTRB(24, 24, 24, 120),
    this.topTint,
  });

  final List<Widget> children;
  final EdgeInsets padding;

  /// Optional feature-identity tint blended into the very top of the layered
  /// botanical canvas (Home aqua, Forge mint, Settings teal). The tint stays
  /// restrained so the page accent system remains the primary identity.
  final Color? topTint;

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    return Material(
      color: Colors.transparent,
      child: SizedBox.expand(
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                topTint ?? oasis.topCanvas,
                oasis.canvas,
                oasis.lowerCanvas,
              ],
            ),
          ),
          child: SafeArea(
            bottom: false,
            child: SingleChildScrollView(
              padding: padding,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: children,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class LogicHeader extends StatelessWidget {
  const LogicHeader({
    super.key,
    required this.title,
    required this.subtitle,
    this.leading,
    this.trailing,
  });

  final String title;
  final String subtitle;
  final Widget? leading;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        if (leading != null) ...[leading!, const SizedBox(width: 12)],
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.headlineSmall?.copyWith(
                  fontSize: 28,
                  height: 1.05,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                subtitle,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodyLarge?.copyWith(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  height: 1.18,
                ),
              ),
            ],
          ),
        ),
        if (trailing != null) ...[const SizedBox(width: 12), trailing!],
      ],
    );
  }
}

class SoftCard extends StatelessWidget {
  const SoftCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.color,
    this.radius = 20,
    this.onTap,
  });

  final Widget child;
  final EdgeInsets padding;
  final Color? color;
  final double radius;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    final card = AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      curve: Curves.easeOutCubic,
      padding: padding,
      decoration: BoxDecoration(
        color: color ?? oasis.surface,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: oasis.outline),
        boxShadow: oasis.softShadow,
      ),
      child: child,
    );

    if (onTap == null) return card;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(radius),
        onTap: onTap,
        child: card,
      ),
    );
  }
}

class SoftIconButton extends StatelessWidget {
  const SoftIconButton({
    super.key,
    required this.icon,
    this.onTap,
    this.color,
  });

  final String icon;
  final VoidCallback? onTap;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: color ?? oasis.surface,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: oasis.outline),
            boxShadow: oasis.softShadow,
          ),
          child: AppSvgIcon(
            icon,
            color: oasis.secondaryInk,
            size: 24,
          ),
        ),
      ),
    );
  }
}

class SproutAvatar extends StatelessWidget {
  const SproutAvatar({super.key, this.size = 48});

  final double size;

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: oasis.mint,
        borderRadius: BorderRadius.circular(size * .28),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(size * .28),
        child: const AppIllustration('sprout_avatar.jpg'),
      ),
    );
  }
}

class StatCard extends StatelessWidget {
  const StatCard({
    super.key,
    required this.icon,
    required this.value,
    required this.label,
    required this.iconColor,
    this.compact = false,
  });

  final String icon;
  final String value;
  final String label;
  final Color iconColor;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    final theme = Theme.of(context);
    return SoftCard(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 8 : 10,
        vertical: compact ? 10 : 12,
      ),
      radius: 16,
      child: ConstrainedBox(
        constraints: BoxConstraints(minHeight: compact ? 64 : 78),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AppSvgIcon(icon, color: iconColor, size: compact ? 22 : 26),
            const SizedBox(height: 6),
            FittedBox(
              fit: BoxFit.scaleDown,
              child: Text(
                value,
                style: theme.textTheme.titleMedium?.copyWith(
                  color: oasis.primaryInk,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  height: 1,
                ),
              ),
            ),
            const SizedBox(height: 4),
            FittedBox(
              fit: BoxFit.scaleDown,
              child: Text(
                label,
                maxLines: 1,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: oasis.secondaryInk,
                  fontSize: 11.5,
                  fontWeight: FontWeight.w700,
                  height: 1,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class StatusChip extends StatelessWidget {
  const StatusChip({
    super.key,
    required this.label,
    required this.color,
    this.icon,
    this.background,
  });

  final String label;
  final Color color;
  final Color? background;
  final String? icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: 24),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: background ?? color.withValues(alpha: .12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: .18)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            AppSvgIcon(icon!, color: color, size: 13),
            const SizedBox(width: 4),
          ],
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: color,
                fontSize: 11,
                fontWeight: FontWeight.w700,
                height: 1,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class MissionCard extends StatelessWidget {
  const MissionCard({
    super.key,
    required this.topicLabel,
    required this.durationLabel,
    required this.title,
    required this.rewardLabel,
    required this.progress,
    required this.progressLabel,
    required this.onTap,
    required this.readyToClaim,
  });

  final String topicLabel;
  final String durationLabel;
  final String title;
  final String rewardLabel;
  final double progress;
  final String progressLabel;
  final VoidCallback onTap;
  final bool readyToClaim;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _SectionLabel(label: "TODAY'S MISSION"),
        const SizedBox(height: 8),
        SoftCard(
          onTap: onTap,
          padding: const EdgeInsets.all(12),
          radius: 20,
          child: Row(
            children: [
              const FractionMissionIcon(size: 44),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: StatusChip(
                            label: topicLabel,
                            color: oasis.forest,
                            background: oasis.mint,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Flexible(
                          child: Text(
                            durationLabel,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color: oasis.secondaryInk,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontSize: 15,
                        height: 1.05,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      rewardLabel,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: oasis.secondaryInk,
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: ProgressBar(
                            value: progress,
                            height: 6,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          progressLabel,
                          style: theme.textTheme.labelMedium?.copyWith(
                            color: oasis.forest,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Container(
                width: 42,
                height: 42,
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [Color(0xFF58C878), Color(0xFF259D55)],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Color(0x33369E58),
                      blurRadius: 15,
                      offset: Offset(0, 8),
                    ),
                  ],
                ),
                child: AppSvgIcon(
                  readyToClaim ? 'card_giftcard' : 'play',
                  color: Colors.white,
                  size: 24,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class OasisHeroCard extends StatelessWidget {
  const OasisHeroCard({
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
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    final markerAreas = _heroAreas();

    return SoftCard(
      padding: EdgeInsets.zero,
      radius: 20,
      color: oasis.mint,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: SizedBox(
          height: 410,
          child: Stack(
            children: [
              // Progress-responsive oasis scene with overlays.
              Positioned.fill(
                child: LowPolyOasisScene(
                  areas: areas,
                  restorationProgress: progress,
                ),
              ),
              const Positioned(
                left: 20,
                top: 18,
                right: 20,
                child: _HeroTitleBlock(),
              ),
              // Progress-aware repair markers.
              Positioned(
                left: 44,
                bottom: 72,
                child: RepairMarker(
                  label: _markerLabel(markerAreas.garden),
                  progress: markerAreas.garden.progress,
                  recommended:
                      !markerAreas.garden.isComplete &&
                      canRepair(markerAreas.garden),
                  enabled: canRepair(markerAreas.garden),
                  onTap: () => _showRepairSheet(context, markerAreas.garden),
                ),
              ),
              Positioned(
                left: 148,
                bottom: 112,
                child: RepairMarker(
                  label: _markerLabel(markerAreas.bridge),
                  progress: markerAreas.bridge.progress,
                  enabled: canRepair(markerAreas.bridge),
                  onTap: () => _showRepairSheet(context, markerAreas.bridge),
                ),
              ),
              Positioned(
                right: 28,
                top: 128,
                child: RepairMarker(
                  label: _markerLabel(markerAreas.tower),
                  progress: markerAreas.tower.progress,
                  enabled: canRepair(markerAreas.tower),
                  onTap: () => _showRepairSheet(context, markerAreas.tower),
                ),
              ),
              Positioned(
                right: 10,
                bottom: 76,
                child: RepairMarker(
                  label: _markerLabel(markerAreas.market),
                  progress: markerAreas.market.progress,
                  enabled: canRepair(markerAreas.market),
                  onTap: () => _showRepairSheet(context, markerAreas.market),
                ),
              ),
              // Bottom info bar with overall restoration percentage.
              Positioned(
                left: 0,
                right: 0,
                bottom: 0,
                child: Container(
                  padding: const EdgeInsets.fromLTRB(12, 9, 12, 10),
                  decoration: BoxDecoration(
                    color: oasis.surface.withValues(alpha: 0.92),
                  ),
                  child: Row(
                    children: [
                      AppSvgIcon(
                        'repair_marker',
                        color: oasis.secondaryInk,
                        size: 16,
                      ),
                      const SizedBox(width: 7),
                      Expanded(
                        child: Text(
                          AppLocalizations.of(
                            context,
                          )!.tapMarkersToRestoreOasis,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context)
                              .textTheme
                              .bodyMedium
                              ?.copyWith(
                                color: oasis.secondaryInk,
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                              ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '${(progress * 100).round()}%',
                        style: Theme.of(context)
                            .textTheme
                            .labelMedium
                            ?.copyWith(
                              color: oasis.forest,
                              fontSize: 12.5,
                            ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  ({OasisArea bridge, OasisArea tower, OasisArea garden, OasisArea market})
  _heroAreas() {
    OasisArea byId(String id, int fallback) {
      return areas.firstWhere(
        (area) => area.id == id,
        orElse: () => areas[fallback.clamp(0, areas.length - 1)],
      );
    }

    return (
      bridge: byId('fraction_bridge', 0),
      tower: byId('decimal_waterway', 1),
      garden: byId('percentage_garden', 2),
      market: byId('market_corner', 3),
    );
  }

  static String _markerLabel(OasisArea area) {
    if (area.isComplete) return 'Restored ✓';
    if (area.id == 'fraction_bridge') return 'Fix Bridge';
    if (area.id == 'decimal_waterway') return 'Repair Tower';
    if (area.id == 'percentage_garden') return 'Restore Garden';
    if (area.id == 'market_corner') return 'Market';
    return 'Repair';
  }

  int _availableResourceFor(OasisArea area) {
    return switch (area.resource) {
      OasisResource.crystals => crystals,
      OasisResource.mutualAid => mutualAidEnergy,
    };
  }

  Future<void> _showRepairSheet(BuildContext context, OasisArea area) async {
    final result = await showModalBottomSheet<_RepairFeedback>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        return _RepairDetailSheet(
          area: area,
          isBahasaMelayu: isBahasaMelayu,
          availableResource: _availableResourceFor(area),
          canRepair: canRepair(area),
          onRepair: () {
            final repaired = onRepair(area.id);
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

    // Play celebration sparkle on successful repair.
    if (result == _RepairFeedback.success) {
      RestorationCelebration.show(context);
    }

    final l10n = AppLocalizations.of(context)!;
    final areaTitle = area.localizedTitle(isBahasaMelayu);
    final message = switch (result) {
      _RepairFeedback.success => l10n.areaRepaired(areaTitle),
      _RepairFeedback.notEnough => l10n.notEnoughResource(
        _resourceLabel(area.resource, l10n),
      ),
      _RepairFeedback.complete => l10n.areaFullyRestored(areaTitle),
    };

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }
}

enum _RepairFeedback { success, notEnough, complete }

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
    final l10n = AppLocalizations.of(context)!;
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    final resourceIcon = area.resource == OasisResource.crystals
        ? 'stat_crystal'
        : 'stat_energy';
    final resourceColor = area.resource == OasisResource.crystals
        ? oasis.water
        : oasis.reward;
    final resourceLabel = _resourceLabel(area.resource, l10n);
    final hasImage = area.currentImage.isNotEmpty;

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Flexible(
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Structure preview image with crossfade transition.
                    if (hasImage) ...[
                      ClipRRect(
                        borderRadius: BorderRadius.circular(16),
                        child: AnimatedSwitcher(
                          duration: const Duration(milliseconds: 400),
                          child: Image.asset(
                            area.currentImage,
                            key: ValueKey(area.currentImage),
                            height: 140,
                            width: double.infinity,
                            fit: BoxFit.contain,
                            errorBuilder: (_, __, ___) => Container(
                              height: 140,
                              decoration: BoxDecoration(
                                color: resourceColor.withValues(alpha: .08),
                                borderRadius: BorderRadius.circular(16),
                              ),
                              child: Center(
                                child: AppSvgIcon(
                                  resourceIcon,
                                  color: resourceColor.withValues(alpha: .4),
                                  size: 48,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    Row(
                      children: [
                        Container(
                          width: 48,
                          height: 48,
                          decoration: BoxDecoration(
                            color: resourceColor.withValues(alpha: .14),
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: AppSvgIcon(
                            resourceIcon,
                            color: resourceColor,
                            size: 26,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                area.localizedTitle(isBahasaMelayu),
                                style: theme.textTheme.headlineSmall?.copyWith(
                                  fontSize: 20,
                                ),
                              ),
                              const SizedBox(height: 2),
                              // Show topic label.
                              if (area.topic.isNotEmpty)
                                Text(
                                  'Topic: ${area.topic}',
                                  style: TextStyle(
                                    color: resourceColor,
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              const SizedBox(height: 2),
                              Text(
                                area.localizedDescription(isBahasaMelayu),
                                style: theme.textTheme.bodyMedium?.copyWith(
                                  color: oasis.secondaryInk,
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    ProgressBar(
                      value: area.progress,
                      color: resourceColor,
                      height: 8,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      l10n.restoredPercent((area.progress * 100).round()),
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: oasis.secondaryInk,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 18),
                    Row(
                      children: [
                        Expanded(
                          child: _SheetMetric(
                            icon: area.resource == OasisResource.crystals
                                ? Icons.diamond_outlined
                                : Icons.handshake_outlined,
                            label: l10n.available,
                            value: '$availableResource',
                            color: resourceColor,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _SheetMetric(
                            icon: Icons.handyman_rounded,
                            label: l10n.repairCost,
                            value: '${area.repairCost}',
                            color: oasis.leaf,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: canRepair ? onRepair : null,
                icon: Icon(
                  area.isComplete
                      ? Icons.check_rounded
                      : Icons.handyman_rounded,
                ),
                label: Text(
                  area.isComplete
                      ? l10n.fullyRestored
                      : canRepair
                      ? l10n.repairWithResource(resourceLabel)
                      : l10n.needMoreResource(resourceLabel),
                ),
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
    final oasis = LogicOasisTheme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: oasis.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: oasis.outline),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  value,
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: oasis.primaryInk,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  label,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: oasis.secondaryInk,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
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

class RepairMarker extends StatefulWidget {
  const RepairMarker({
    super.key,
    required this.label,
    required this.onTap,
    this.progress = 0.0,
    this.enabled = true,
    this.recommended = false,
  });

  final String label;
  final VoidCallback onTap;
  final double progress;
  final bool enabled;
  final bool recommended;

  @override
  State<RepairMarker> createState() => _RepairMarkerState();
}

class _RepairMarkerState extends State<RepairMarker>
    with SingleTickerProviderStateMixin {
  late final AnimationController controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1500),
  )..repeat(reverse: true);

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    // Determine marker appearance based on area progress.
    final isComplete = widget.progress >= 1.0;
    final isRepairing = widget.progress > 0 && widget.progress < 1.0;

    final Color markerColor;
    final IconData markerIcon;
    final Color labelBgColor;

    if (isComplete) {
      markerColor = oasis.leaf;
      markerIcon = Icons.check_rounded;
      labelBgColor = oasis.mint;
    } else if (isRepairing) {
      markerColor = oasis.reward;
      markerIcon = Icons.construction_rounded;
      labelBgColor = oasis.reward.withValues(alpha: .18);
    } else {
      markerColor = oasis.coral;
      markerIcon = Icons.add_rounded;
      labelBgColor = oasis.coral.withValues(alpha: .12);
    }

    // Pulse animation: active for recommended + repairing, off for completed.
    final reducedMotion = MediaQuery.disableAnimationsOf(context);
    final shouldPulse =
        !isComplete && !reducedMotion && (widget.recommended || isRepairing);

    return AnimatedBuilder(
      animation: controller,
      builder: (context, child) {
        final glow = shouldPulse ? 5 + controller.value * 7 : 0.0;
        return Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(18),
            onTap: widget.onTap,
            child: Opacity(
              opacity: widget.enabled || isComplete ? 1 : .72,
              child: SizedBox(
                width: 92,
                height: 50,
                child: Stack(
                  alignment: Alignment.topCenter,
                  children: [
                    Container(
                      width: 32,
                      height: 32,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: markerColor,
                        border: Border.all(color: Colors.white, width: 2),
                        boxShadow: [
                          BoxShadow(
                            color: markerColor.withValues(alpha: .35),
                            blurRadius: glow,
                            spreadRadius: shouldPulse ? 2 : 0,
                          ),
                          const BoxShadow(
                            color: Color(0x334A2F12),
                            blurRadius: 8,
                            offset: Offset(0, 4),
                          ),
                        ],
                      ),
                      child: Icon(markerIcon, color: Colors.white, size: 20),
                    ),
                    Positioned(
                      top: 29,
                      child: Container(
                        width: 88,
                        height: 18,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: labelBgColor,
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          widget.label,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: oasis.forest,
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                            height: 1,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class SettingsRow extends StatelessWidget {
  const SettingsRow({
    super.key,
    required this.icon,
    required this.iconColor,
    required this.label,
    this.value,
    this.progress,
    this.trailingSwitch,
    required this.onTap,
    this.showDivider = true,
  });

  final String icon;
  final Color iconColor;
  final String label;
  final String? value;
  final VoidCallback onTap;
  final bool showDivider;
  final double? progress;
  final bool? trailingSwitch;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Column(
          children: [
            ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 62),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 10,
                ),
                child: Row(
                  children: [
                    _CircleIcon(icon: icon, color: iconColor),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        label,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontSize: 14,
                          height: 1.15,
                        ),
                      ),
                    ),
                    if (value != null) ...[
                      const SizedBox(width: 8),
                      Flexible(
                        flex: 0,
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 150),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                value!,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: theme.textTheme.bodyMedium?.copyWith(
                                  color: oasis.secondaryInk,
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              if (progress != null) ...[
                                const SizedBox(height: 5),
                                SizedBox(
                                  width: 52,
                                  child: ProgressBar(
                                    value: progress!,
                                    height: 5,
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ],
                    const SizedBox(width: 8),
                    if (trailingSwitch != null)
                      _MiniSwitch(value: trailingSwitch!)
                    else
                      Icon(
                        Icons.chevron_right_rounded,
                        color: oasis.secondaryInk,
                        size: 24,
                      ),
                  ],
                ),
              ),
            ),
            if (showDivider)
              Padding(
                padding: const EdgeInsets.only(left: 62, right: 14),
                child: Divider(height: 1, color: oasis.outline),
              ),
          ],
        ),
      ),
    );
  }
}

class BottomNavBar extends StatelessWidget {
  const BottomNavBar({
    super.key,
    required this.selectedIndex,
    required this.onSelected,
    required this.items,
  });

  final int selectedIndex;
  final ValueChanged<int> onSelected;
  final List<BottomNavItemData> items;

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    return SafeArea(
      top: false,
      child: Container(
        height: 78,
        margin: const EdgeInsets.fromLTRB(24, 0, 24, 12),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: oasis.surface,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: oasis.outline),
          boxShadow: oasis.softShadow,
        ),
        child: Row(
          children: [
            for (var index = 0; index < items.length; index += 1)
              Expanded(
                child: _BottomNavItem(
                  data: items[index],
                  selected: index == selectedIndex,
                  onTap: () => onSelected(index),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class BottomNavItemData {
  const BottomNavItemData({required this.icon, required this.label});

  final String icon;
  final String label;
}

class ProgressBar extends StatelessWidget {
  const ProgressBar({
    super.key,
    required this.value,
    this.height = 7,
    this.color,
  });

  final double value;
  final double height;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    return ClipRRect(
      borderRadius: BorderRadius.circular(999),
      child: LinearProgressIndicator(
        value: value.clamp(0.0, 1.0).toDouble(),
        minHeight: height,
        backgroundColor: oasis.outline,
        color: color ?? oasis.leaf,
      ),
    );
  }
}

class TopicThumbnail extends StatelessWidget {
  const TopicThumbnail({super.key, required this.topicId});

  final String topicId;

  @override
  Widget build(BuildContext context) {
    String assetName = 'topic_fraction_bridge.jpg';
    if (topicId.startsWith('decimals'))
      assetName = 'topic_decimal_waterway.jpg';
    if (topicId.startsWith('percentages'))
      assetName = 'topic_percentage_garden.jpg';
    if (topicId.startsWith('money')) assetName = 'topic_money_market.jpg';

    return Container(
      width: 96,
      height: 96,
      decoration: BoxDecoration(
        color: const Color(0xFFD8F1EC),
        borderRadius: BorderRadius.circular(18),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(18),
        child: AppIllustration(assetName),
      ),
    );
  }
}

class FractionMissionIcon extends StatelessWidget {
  const FractionMissionIcon({super.key, required this.size});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: const Color(0xFFD8F1EC),
        borderRadius: BorderRadius.circular(size * 0.22),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(size * 0.22),
        child: const AppIllustration('topic_fraction_bridge.jpg'),
      ),
    );
  }
}

class LowPolyOasisScene extends StatefulWidget {
  const LowPolyOasisScene({
    super.key,
    this.areas = const [],
    this.restorationProgress = 0.0,
  });

  /// All oasis areas with their current progress for overlay rendering.
  final List<OasisArea> areas;

  /// Overall restoration progress (0.0–1.0) for scene tinting.
  final double restorationProgress;

  @override
  State<LowPolyOasisScene> createState() => _LowPolyOasisSceneState();
}

class _LowPolyOasisSceneState extends State<LowPolyOasisScene>
    with SingleTickerProviderStateMixin {
  late final AnimationController _shimmerController;

  @override
  void initState() {
    super.initState();
    _shimmerController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3200),
    );
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // The shimmer is nonessential ambience; reduced-motion preference keeps
    // the scene static while progress glows and markers still convey state.
    final reducedMotion = MediaQuery.disableAnimationsOf(context);
    if (reducedMotion && _shimmerController.isAnimating) {
      _shimmerController.stop();
    } else if (!reducedMotion && !_shimmerController.isAnimating) {
      _shimmerController.repeat();
    }
  }

  @override
  void dispose() {
    _shimmerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final progress = widget.restorationProgress.clamp(0.0, 1.0);

    return AnimatedBuilder(
      animation: _shimmerController,
      builder: (context, baseImage) {
        return Stack(
          fit: StackFit.expand,
          children: [
            // Base oasis image with adaptive tint based on restoration.
            ColorFiltered(
              colorFilter: ColorFilter.mode(
                Color.lerp(
                  const Color(0x1AD4A96A), // warm sepia when damaged
                  const Color(0x0A2E7D32), // subtle green when restored
                  progress,
                )!,
                BlendMode.srcOver,
              ),
              child: baseImage!,
            ),

            // Vibrancy overlay — scene gets lusher as restoration increases.
            Positioned.fill(
              child: IgnorePointer(
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 600),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        Colors.transparent,
                        Color.lerp(
                          const Color(0x0C8B6914), // dusty at bottom
                          const Color(0x142E7D32), // green at bottom
                          progress,
                        )!,
                      ],
                    ),
                  ),
                ),
              ),
            ),

            // Per-area restoration glow indicators.
            for (final area in widget.areas)
              if (area.progress > 0 && area.markerPosition != Offset.zero)
                Positioned.fill(
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      return CustomPaint(
                        painter: _AreaGlowPainter(
                          area: area,
                          shimmer: _shimmerController.value,
                          sceneWidth: constraints.maxWidth,
                          sceneHeight: constraints.maxHeight,
                        ),
                      );
                    },
                  ),
                ),

            // Scene-aligned transparent overlays (ready for PNG overlays).
            for (final area in widget.areas)
              if (area.currentOverlay != null)
                Positioned.fill(
                  child: IgnorePointer(
                    child: AnimatedSwitcher(
                      duration: const Duration(milliseconds: 500),
                      child: Image.asset(
                        area.currentOverlay!,
                        key: ValueKey(area.currentOverlay),
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => const SizedBox.shrink(),
                      ),
                    ),
                  ),
                ),
          ],
        );
      },
      child: const AppIllustration(
        'oasis_stage_1_damaged.jpg',
        fit: BoxFit.cover,
        softStyle: false,
      ),
    );
  }
}

/// Draws a soft radial glow at each area's marker position to indicate
/// restoration progress — green for complete, amber for in-progress.
class _AreaGlowPainter extends CustomPainter {
  const _AreaGlowPainter({
    required this.area,
    required this.shimmer,
    required this.sceneWidth,
    required this.sceneHeight,
  });

  final OasisArea area;
  final double shimmer;
  final double sceneWidth;
  final double sceneHeight;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(
      area.markerPosition.dx * sceneWidth,
      area.markerPosition.dy * sceneHeight,
    );
    final isComplete = area.progress >= 1.0;
    final baseColor = isComplete
        ? const Color(0xFF37BD61)
        : const Color(0xFFE8A92E);

    // Pulsing glow radius.
    final pulseOffset = math.sin(shimmer * math.pi * 2) * 4;
    final glowRadius = (sceneWidth * 0.06) + pulseOffset;
    final glowOpacity = isComplete
        ? 0.18
        : 0.12 + (math.sin(shimmer * math.pi * 2) * 0.06);

    canvas.drawCircle(
      center,
      glowRadius,
      Paint()
        ..color = baseColor.withValues(alpha: glowOpacity)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14),
    );

    // Bright core dot.
    canvas.drawCircle(
      center,
      sceneWidth * 0.012,
      Paint()..color = baseColor.withValues(alpha: 0.35),
    );
  }

  @override
  bool shouldRepaint(covariant _AreaGlowPainter oldDelegate) {
    return oldDelegate.shimmer != shimmer ||
        oldDelegate.area.progress != area.progress;
  }
}

class _BottomNavItem extends StatelessWidget {
  const _BottomNavItem({
    required this.data,
    required this.selected,
    required this.onTap,
  });

  final BottomNavItemData data;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    final color = selected ? oasis.forest : oasis.secondaryInk;
    return Material(
      color: Colors.transparent,
      child: Semantics(
        selected: selected,
        button: true,
        child: InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            curve: Curves.easeOutCubic,
            height: 60,
            decoration: BoxDecoration(
              color: selected ? oasis.mint : Colors.transparent,
              borderRadius: BorderRadius.circular(18),
            ),
            child: FittedBox(
              fit: BoxFit.scaleDown,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  AppSvgIcon(data.icon, color: color, size: selected ? 25 : 23),
                  const SizedBox(height: 4),
                  Text(
                    data.label,
                    maxLines: 1,
                    softWrap: false,
                    style: TextStyle(
                      color: color,
                      fontSize: 11.5,
                      fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
                      height: 1,
                    ),
                  ),
                  const SizedBox(height: 5),
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 180),
                    curve: Curves.easeOutCubic,
                    width: selected ? 22 : 0,
                    height: 4,
                    decoration: BoxDecoration(
                      color: oasis.forest,
                      borderRadius: BorderRadius.circular(99),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _CircleIcon extends StatelessWidget {
  const _CircleIcon({required this.icon, required this.color});

  final String icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: color.withValues(alpha: .18),
      ),
      child: Center(child: AppSvgIcon(icon, color: color, size: 20)),
    );
  }
}

class _MiniSwitch extends StatelessWidget {
  const _MiniSwitch({required this.value});

  final bool value;

  @override
  Widget build(BuildContext context) {
    final oasis = LogicOasisTheme.of(context);
    return AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      width: 46,
      height: 28,
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: value ? oasis.leaf : oasis.outline,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Align(
        alignment: value ? Alignment.centerRight : Alignment.centerLeft,
        child: Container(
          width: 22,
          height: 22,
          decoration: const BoxDecoration(
            color: Colors.white,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: Color(0x22000000),
                blurRadius: 4,
                offset: Offset(0, 2),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    return Row(
      children: [
        Icon(Icons.eco_rounded, color: oasis.leaf, size: 16),
        const SizedBox(width: 5),
        Flexible(
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: theme.textTheme.labelMedium?.copyWith(
              color: oasis.secondaryInk,
              fontSize: 13,
              letterSpacing: .2,
            ),
          ),
        ),
      ],
    );
  }
}

class _HeroTitleBlock extends StatelessWidget {
  const _HeroTitleBlock();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oasis = LogicOasisTheme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Logic Oasis',
          style: theme.textTheme.headlineSmall?.copyWith(
            color: oasis.primaryInk,
            fontSize: 28,
            height: 1.02,
          ),
        ),
        const SizedBox(height: 5),
        Text(
          'Learn. Restore. Grow together.',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: oasis.secondaryInk,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _TopicThumbnailPainter extends CustomPainter {
  const _TopicThumbnailPainter(this.topicId);

  final String topicId;

  @override
  void paint(Canvas canvas, Size size) {
    final sand = Paint()..color = const Color(0xFFF0D29B);
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(
          size.width * .12,
          size.height * .68,
          size.width * .76,
          size.height * .18,
        ),
        const Radius.circular(8),
      ),
      sand,
    );
    if (topicId.startsWith('fractions')) {
      _bridge(canvas, size);
    } else if (topicId.startsWith('decimals')) {
      _fountain(canvas, size);
    } else if (topicId.startsWith('percentages')) {
      _garden(canvas, size);
    } else {
      _market(canvas, size);
    }
  }

  void _bridge(Canvas canvas, Size size) {
    canvas.drawLine(
      Offset(size.width * .2, size.height * .72),
      Offset(size.width * .82, size.height * .72),
      Paint()
        ..color = LogicOasisDesign.water
        ..strokeWidth = 6
        ..strokeCap = StrokeCap.round,
    );
    canvas.drawArc(
      Rect.fromLTWH(
        size.width * .18,
        size.height * .4,
        size.width * .62,
        size.height * .32,
      ),
      math.pi,
      math.pi,
      false,
      Paint()
        ..color = const Color(0xFFC8965F)
        ..strokeWidth = 8
        ..strokeCap = StrokeCap.round,
    );
  }

  void _fountain(Canvas canvas, Size size) {
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset(size.width * .5, size.height * .7),
        width: size.width * .58,
        height: size.height * .18,
      ),
      Paint()..color = LogicOasisDesign.water,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(
          size.width * .42,
          size.height * .36,
          size.width * .18,
          size.height * .28,
        ),
        const Radius.circular(6),
      ),
      Paint()..color = const Color(0xFFE4C087),
    );
    final crystal = Path()
      ..moveTo(size.width * .5, size.height * .16)
      ..lineTo(size.width * .65, size.height * .42)
      ..lineTo(size.width * .54, size.height * .63)
      ..lineTo(size.width * .38, size.height * .62)
      ..lineTo(size.width * .33, size.height * .42)
      ..close();
    canvas.drawPath(crystal, Paint()..color = const Color(0xFF3FBFDD));
  }

  void _garden(Canvas canvas, Size size) {
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(
          size.width * .24,
          size.height * .48,
          size.width * .52,
          size.height * .22,
        ),
        const Radius.circular(8),
      ),
      Paint()..color = const Color(0xFFEBD39A),
    );
    final trunk = Paint()
      ..color = const Color(0xFF94724A)
      ..strokeWidth = 7
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(
      Offset(size.width * .5, size.height * .62),
      Offset(size.width * .5, size.height * .3),
      trunk,
    );
    final leaf = Paint()..color = const Color(0xFF55AE62);
    for (final angle in [-.8, -.3, .3, .8]) {
      canvas.save();
      canvas.translate(size.width * .5, size.height * .3);
      canvas.rotate(angle);
      canvas.drawOval(
        Rect.fromCenter(
          center: Offset(size.width * .16, 0),
          width: size.width * .33,
          height: size.height * .12,
        ),
        leaf,
      );
      canvas.restore();
    }
  }

  void _market(Canvas canvas, Size size) {
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(
          size.width * .25,
          size.height * .42,
          size.width * .5,
          size.height * .34,
        ),
        const Radius.circular(7),
      ),
      Paint()..color = const Color(0xFFE5B977),
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromLTWH(
          size.width * .2,
          size.height * .28,
          size.width * .6,
          size.height * .2,
        ),
        const Radius.circular(5),
      ),
      Paint()..color = LogicOasisDesign.orange,
    );
    for (final x in [.34, .5, .66]) {
      canvas.drawCircle(
        Offset(size.width * x, size.height * .67),
        size.width * .055,
        Paint()..color = LogicOasisDesign.yellow,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _FractionIconPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final bg = Paint()..color = const Color(0xFFDDF4E4);
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Offset.zero & size,
        Radius.circular(size.width * .22),
      ),
      bg,
    );
    final colors = [
      const Color(0xFFAEE7C4),
      const Color(0xFF72C986),
      const Color(0xFFD7F5E1),
      const Color(0xFF9CE0B3),
    ];
    final center = Offset(size.width * .5, size.height * .5);
    final radius = size.width * .37;
    for (var i = 0; i < 4; i += 1) {
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        -math.pi / 2 + i * math.pi / 2,
        math.pi / 2,
        true,
        Paint()..color = colors[i],
      );
    }
    canvas.drawLine(
      Offset(center.dx, center.dy - radius),
      Offset(center.dx, center.dy + radius),
      Paint()
        ..color = Colors.white
        ..strokeWidth = 3,
    );
    canvas.drawLine(
      Offset(center.dx - radius, center.dy),
      Offset(center.dx + radius, center.dy),
      Paint()
        ..color = Colors.white
        ..strokeWidth = 3,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
