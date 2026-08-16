import 'package:flutter/material.dart';

class LogicOasisDesign {
  const LogicOasisDesign._();

  // ---------------------------------------------------------------------------
  // Living Canopy semantic tokens (Stage 2 canonical definitions).
  //
  // These roles are the single source of truth for the shared visual system.
  // Both the default and the Eye Protecting theme expose the same roles so
  // ThemeData.lerp can interpolate between them without role gaps.
  // ---------------------------------------------------------------------------

  // Default theme.
  static const canvas = Color(0xFFF2F7F1);
  static const surface = Color(0xFFFFFFFF);
  static const groupedSurface = Color(0xFFEDF5F0);
  static const primaryInk = Color(0xFF17352B);
  static const secondaryInk = Color(0xFF587067);
  static const forestAction = Color(0xFF176B4D);
  static const leafAccent = Color(0xFF48A979);
  static const mintSurface = Color(0xFFDFF4E8);
  static const waterAccent = Color(0xFF5BC8CE);
  static const rewardGold = Color(0xFFF1C84A);
  static const sandClay = Color(0xFFD7B36A);
  // Coral and violet are tuned for WCAG AA contrast on white/botanical
  // surfaces while staying within their agreed colour families.
  static const coralDanger = Color(0xFFBF4238);
  static const forumViolet = Color(0xFF7E4FC6);
  static const outlineQuiet = Color(0xFFDCE8E1);
  static const neutralQuiet = Color(0xFF9AA8A0);
  static const statusContinued = Color(0xFF8F5E00);

  // Eye Protecting theme: lower luminance, lower saturation, quieter shadows,
  // while preserving text contrast and the botanical identity.
  static const comfortCanvas = Color(0xFFE9F1EB);
  static const comfortSurface = Color(0xFFF5FAF6);
  static const comfortGroupedSurface = Color(0xFFE3EDE6);
  static const comfortPrimaryInk = Color(0xFF142F26);
  static const comfortSecondaryInk = Color(0xFF4E655C);
  static const comfortForest = Color(0xFF146246);
  static const comfortLeaf = Color(0xFF3E9469);
  static const comfortMint = Color(0xFFCFE7D7);
  static const comfortWater = Color(0xFF4AA9AE);
  static const comfortReward = Color(0xFFDFB33D);
  static const comfortSand = Color(0xFFC7A55F);
  static const comfortCoral = Color(0xFFAE3B32);
  static const comfortViolet = Color(0xFF7145B5);
  static const comfortOutline = Color(0xFFD2DFD7);
  static const comfortNeutral = Color(0xFF8C9A92);

  // ---------------------------------------------------------------------------
  // Existing palette (kept for back-compatibility until consumers migrate to
  // semantic roles in later units; reachability scan happens before removal).
  // ---------------------------------------------------------------------------
  static const forest = Color(0xFF0A5A3E);
  static const ink = Color(0xFF17231F);
  static const body = Color(0xFF5A625D);
  static const mintLight = Color(0xFFEFF9EC);
  static const page = Color(0xFFFFFAED);
  static const line = Color(0xFFEDE7D9);
  static const yellow = Color(0xFFFFD33D);
  static const leaf = Color(0xFF37BD61);
  static const sky = Color(0xFFDDF5FF);
  static const sand = Color(0xFFFFF0C8);
  static const water = Color(0xFF50D2D7);
  static const orange = Color(0xFFFF9D3B);
  static const radiusCard = 18.0;
}

/// Central motion policy for the shared visual system.
///
/// Stage 2 keeps motion restrained: one coordinated ~350 ms theme crossfade
/// for Eye Protecting Mode under ordinary motion settings, and a materially
/// shortened (near-immediate) alternative when the platform requests reduced
/// motion. Consumers derive durations from this class instead of hardcoding
/// their own timings.
class LogicOasisMotion {
  const LogicOasisMotion._();

  /// Coordinated theme interpolation duration under ordinary motion settings.
  static const Duration themeTransition = Duration(milliseconds: 350);

  /// Materially shortened duration for reduced-motion preference.
  static const Duration themeTransitionReduced = Duration(milliseconds: 80);

  /// Restrained curve for the theme crossfade.
  static const Curve themeTransitionCurve = Curves.easeInOutCubic;

  /// Resolves the theme transition duration for [context], honouring the
  /// platform reduced-motion preference.
  static Duration themeTransitionFor(BuildContext context) {
    return MediaQuery.disableAnimationsOf(context)
        ? themeTransitionReduced
        : themeTransition;
  }
}

