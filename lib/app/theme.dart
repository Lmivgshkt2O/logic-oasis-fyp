import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';

/// Learning-status roles shared by Forge, quizzes, and Q&A surfaces.
///
/// Colour is never the sole indicator of a status: every status also carries a
/// readable [OasisStatusCue] (label plus icon/shape cue) defined in
/// [OasisSemanticTheme.statusCues].
enum OasisStatus { strong, continued, needsHelp, locked }

/// The non-colour cue paired with a learning status.
@immutable
class OasisStatusCue {
  const OasisStatusCue({required this.label, required this.icon});

  /// Human-readable label that is always shown with the status.
  final String label;

  /// Icon or shape cue that is always shown with the status.
  final IconData icon;
}

/// Oasis-specific semantic roles for the Living Canopy visual system.
///
/// One immutable extension is registered in both theme variants so
/// `ThemeData.lerp` interpolates between the default and Eye Protecting
/// presentations without role gaps. Consumers should look up these roles from
/// `Theme.of(context).extension<OasisSemanticTheme>()` instead of hardcoding
/// literal chrome colours.
@immutable
class OasisSemanticTheme extends ThemeExtension<OasisSemanticTheme> {
  const OasisSemanticTheme({
    required this.canvas,
    required this.surface,
    required this.groupedSurface,
    required this.primaryInk,
    required this.secondaryInk,
    required this.forest,
    required this.leaf,
    required this.mint,
    required this.water,
    required this.reward,
    required this.sand,
    required this.coral,
    required this.violet,
    required this.outline,
    required this.neutral,
    required this.softShadow,
    required this.liftShadow,
    required this.isComfort,
  });

  /// Default Living Canopy presentation.
  factory OasisSemanticTheme.defaults() {
    return const OasisSemanticTheme(
      canvas: LogicOasisDesign.canvas,
      surface: LogicOasisDesign.surface,
      groupedSurface: LogicOasisDesign.groupedSurface,
      primaryInk: LogicOasisDesign.primaryInk,
      secondaryInk: LogicOasisDesign.secondaryInk,
      forest: LogicOasisDesign.forestAction,
      leaf: LogicOasisDesign.leafAccent,
      mint: LogicOasisDesign.mintSurface,
      water: LogicOasisDesign.waterAccent,
      reward: LogicOasisDesign.rewardGold,
      sand: LogicOasisDesign.sandClay,
      coral: LogicOasisDesign.coralDanger,
      violet: LogicOasisDesign.forumViolet,
      outline: LogicOasisDesign.outlineQuiet,
      neutral: LogicOasisDesign.neutralQuiet,
      softShadow: [
        BoxShadow(
          color: Color(0x1F496F55),
          blurRadius: 24,
          offset: Offset(0, 10),
        ),
      ],
      liftShadow: [
        BoxShadow(
          color: Color(0x29496F55),
          blurRadius: 30,
          offset: Offset(0, 14),
        ),
      ],
      isComfort: false,
    );
  }

  /// Low-glare Eye Protecting presentation.
  factory OasisSemanticTheme.comfort() {
    return const OasisSemanticTheme(
      canvas: LogicOasisDesign.comfortCanvas,
      surface: LogicOasisDesign.comfortSurface,
      groupedSurface: LogicOasisDesign.comfortGroupedSurface,
      primaryInk: LogicOasisDesign.comfortPrimaryInk,
      secondaryInk: LogicOasisDesign.comfortSecondaryInk,
      forest: LogicOasisDesign.comfortForest,
      leaf: LogicOasisDesign.comfortLeaf,
      mint: LogicOasisDesign.comfortMint,
      water: LogicOasisDesign.comfortWater,
      reward: LogicOasisDesign.comfortReward,
      sand: LogicOasisDesign.comfortSand,
      coral: LogicOasisDesign.comfortCoral,
      violet: LogicOasisDesign.comfortViolet,
      outline: LogicOasisDesign.comfortOutline,
      neutral: LogicOasisDesign.comfortNeutral,
      softShadow: [
        BoxShadow(
          color: Color(0x124A6B5A),
          blurRadius: 18,
          offset: Offset(0, 7),
        ),
      ],
      liftShadow: [
        BoxShadow(
          color: Color(0x1A4A6B5A),
          blurRadius: 24,
          offset: Offset(0, 11),
        ),
      ],
      isComfort: true,
    );
  }

  /// Cool botanical neutral for page and shell backgrounds.
  final Color canvas;

  /// White or lightly botanical surface for primary cards, forms, and sheets.
  final Color surface;

  /// Quiet grouped surface for settings groups and secondary panels.
  final Color groupedSurface;

  /// Deep forest ink for titles, values, and active controls.
  final Color primaryInk;

  /// Readable secondary ink for explanations and metadata.
  final Color secondaryInk;

  /// Primary action and navigation green.
  final Color forest;

  /// Positive-progress green and Forge accent.
  final Color leaf;

  /// Accepted, safe, and selected mint surfaces.
  final Color mint;

  /// Home and ecological water accent.
  final Color water;

  /// Crystals, achievements, and sunlight emphasis.
  final Color reward;

  /// Damaged Oasis context (kept inside world artwork, not page chrome).
  final Color sand;

  /// Warning, error, and needs-help coral.
  final Color coral;

  /// Q&A Forum identity accent.
  final Color violet;

  /// Quiet botanical-grey borders and dividers.
  final Color outline;

  /// Neutral tone for locked and disabled states.
  final Color neutral;

  /// Soft shadow for ordinary content grouping.
  final List<BoxShadow> softShadow;

  /// Stronger shadow for overlays, dialogs, and draggable objects.
  final List<BoxShadow> liftShadow;

  /// Whether this is the low-glare Eye Protecting variant.
  final bool isComfort;

  // Semantic status aliases. Each status also carries a label and icon cue so
  // colour is never the only indicator (see [statusCues]).
  Color get statusStrong => leaf;
  Color get statusContinued => reward;
  Color get statusNeedsHelp => coral;
  Color get statusLocked => neutral;

  /// Non-colour cues paired with every learning status.
  static const Map<OasisStatus, OasisStatusCue> statusCues = {
    OasisStatus.strong: OasisStatusCue(
      label: 'Strong',
      icon: Icons.check_circle_outline,
    ),
    OasisStatus.continued: OasisStatusCue(
      label: 'Keep practising',
      icon: Icons.replay,
    ),
    OasisStatus.needsHelp: OasisStatusCue(
      label: 'Needs help',
      icon: Icons.help_outline,
    ),
    OasisStatus.locked: OasisStatusCue(
      label: 'Locked',
      icon: Icons.lock_outline,
    ),
  };

  /// Readable dark amber for continued-practice status text and accents.
  ///
  /// The reward gold is reserved for fills and highlights; this darker shade
  /// keeps the amber meaning while meeting contrast on white/botanical
  /// surfaces for text and icons.
  static const Color continuedPracticeText = LogicOasisDesign.statusContinued;

  @override
  OasisSemanticTheme copyWith({
    Color? canvas,
    Color? surface,
    Color? groupedSurface,
    Color? primaryInk,
    Color? secondaryInk,
    Color? forest,
    Color? leaf,
    Color? mint,
    Color? water,
    Color? reward,
    Color? sand,
    Color? coral,
    Color? violet,
    Color? outline,
    Color? neutral,
    List<BoxShadow>? softShadow,
    List<BoxShadow>? liftShadow,
    bool? isComfort,
  }) {
    return OasisSemanticTheme(
      canvas: canvas ?? this.canvas,
      surface: surface ?? this.surface,
      groupedSurface: groupedSurface ?? this.groupedSurface,
      primaryInk: primaryInk ?? this.primaryInk,
      secondaryInk: secondaryInk ?? this.secondaryInk,
      forest: forest ?? this.forest,
      leaf: leaf ?? this.leaf,
      mint: mint ?? this.mint,
      water: water ?? this.water,
      reward: reward ?? this.reward,
      sand: sand ?? this.sand,
      coral: coral ?? this.coral,
      violet: violet ?? this.violet,
      outline: outline ?? this.outline,
      neutral: neutral ?? this.neutral,
      softShadow: softShadow ?? this.softShadow,
      liftShadow: liftShadow ?? this.liftShadow,
      isComfort: isComfort ?? this.isComfort,
    );
  }

  @override
  OasisSemanticTheme lerp(covariant OasisSemanticTheme? other, double t) {
    if (other == null) return this;
    return OasisSemanticTheme(
      canvas: Color.lerp(canvas, other.canvas, t)!,
      surface: Color.lerp(surface, other.surface, t)!,
      groupedSurface: Color.lerp(groupedSurface, other.groupedSurface, t)!,
      primaryInk: Color.lerp(primaryInk, other.primaryInk, t)!,
      secondaryInk: Color.lerp(secondaryInk, other.secondaryInk, t)!,
      forest: Color.lerp(forest, other.forest, t)!,
      leaf: Color.lerp(leaf, other.leaf, t)!,
      mint: Color.lerp(mint, other.mint, t)!,
      water: Color.lerp(water, other.water, t)!,
      reward: Color.lerp(reward, other.reward, t)!,
      sand: Color.lerp(sand, other.sand, t)!,
      coral: Color.lerp(coral, other.coral, t)!,
      violet: Color.lerp(violet, other.violet, t)!,
      outline: Color.lerp(outline, other.outline, t)!,
      neutral: Color.lerp(neutral, other.neutral, t)!,
      softShadow: BoxShadow.lerpList(softShadow, other.softShadow, t) ??
          softShadow,
      liftShadow: BoxShadow.lerpList(liftShadow, other.liftShadow, t) ??
          liftShadow,
      isComfort: t < 0.5 ? isComfort : other.isComfort,
    );
  }
}

class LogicOasisTheme {
  const LogicOasisTheme._();

  // Back-compatible palette aliases used by existing pages and shared
  // widgets. They are intentionally preserved until consumers migrate to
  // semantic roles (reachability scan runs before any removal).
  static const ink = LogicOasisDesign.ink;
  static const bodyInk = LogicOasisDesign.body;
  static const leaf = LogicOasisDesign.leaf;
  static const deepLeaf = LogicOasisDesign.forest;
  static const mint = LogicOasisDesign.mintLight;
  static const sand = LogicOasisDesign.sand;
  static const clay = LogicOasisDesign.orange;
  static const water = LogicOasisDesign.water;
  static const sky = LogicOasisDesign.sky;
  static const line = LogicOasisDesign.line;
  static const cream = LogicOasisDesign.cream;
  static const page = LogicOasisDesign.page;

  /// Resolves the active Oasis semantic roles from [context].
  static OasisSemanticTheme of(BuildContext context) {
    return Theme.of(context).extension<OasisSemanticTheme>()!;
  }

  /// Default Living Canopy theme.
  static ThemeData light() => _build(comfort: false);

  /// Eye Protecting (low-glare) Living Canopy theme.
  static ThemeData eyeComfort() => _build(comfort: true);

  static ThemeData _build({required bool comfort}) {
    final oasis = comfort
        ? OasisSemanticTheme.comfort()
        : OasisSemanticTheme.defaults();

    final colorScheme = ColorScheme.fromSeed(
      seedColor: oasis.forest,
      brightness: Brightness.light,
      primary: oasis.forest,
      onPrimary: Colors.white,
      primaryContainer: oasis.mint,
      onPrimaryContainer: oasis.primaryInk,
      secondary: oasis.water,
      onSecondary: oasis.primaryInk,
      secondaryContainer: oasis.mint,
      onSecondaryContainer: oasis.primaryInk,
      surface: oasis.surface,
      onSurface: oasis.primaryInk,
      onSurfaceVariant: oasis.secondaryInk,
      outline: oasis.outline,
      error: oasis.coral,
      onError: Colors.white,
      errorContainer: const Color(0xFFFFE3E0),
      onErrorContainer: const Color(0xFF8B2A22),
    );

    final base = ThemeData.light().textTheme;
    final textTheme = base.copyWith(
      // Fredoka carries playful short-form emphasis (page titles, student
      // names, topic and mission titles, resource numbers, buttons, labels).
      displayLarge: base.displayLarge?.copyWith(
        fontFamily: 'Fredoka',
        fontWeight: FontWeight.w600,
        color: oasis.primaryInk,
      ),
      displayMedium: base.displayMedium?.copyWith(
        fontFamily: 'Fredoka',
        fontWeight: FontWeight.w600,
        color: oasis.primaryInk,
      ),
      displaySmall: base.displaySmall?.copyWith(
        fontFamily: 'Fredoka',
        fontWeight: FontWeight.w600,
        color: oasis.primaryInk,
      ),
      headlineLarge: base.headlineLarge?.copyWith(
        fontFamily: 'Fredoka',
        fontSize: 38,
        fontWeight: FontWeight.w600,
        color: oasis.primaryInk,
        height: 1.04,
      ),
      headlineMedium: base.headlineMedium?.copyWith(
        fontFamily: 'Fredoka',
        fontSize: 24,
        fontWeight: FontWeight.w600,
        color: oasis.primaryInk,
        height: 1.08,
      ),
      headlineSmall: base.headlineSmall?.copyWith(
        fontFamily: 'Fredoka',
        fontWeight: FontWeight.w600,
        color: oasis.primaryInk,
        height: 1.1,
      ),
      titleLarge: base.titleLarge?.copyWith(
        fontFamily: 'Fredoka',
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: oasis.primaryInk,
        height: 1.12,
      ),
      titleMedium: base.titleMedium?.copyWith(
        fontFamily: 'Fredoka',
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: oasis.primaryInk,
        height: 1.16,
      ),
      titleSmall: base.titleSmall?.copyWith(
        fontFamily: 'Fredoka',
        fontWeight: FontWeight.w600,
        color: oasis.primaryInk,
        height: 1.18,
      ),
      labelLarge: base.labelLarge?.copyWith(
        fontFamily: 'Fredoka',
        fontWeight: FontWeight.w600,
        color: oasis.primaryInk,
      ),
      labelMedium: base.labelMedium?.copyWith(
        fontFamily: 'Fredoka',
        fontWeight: FontWeight.w600,
        color: oasis.primaryInk,
      ),
      labelSmall: base.labelSmall?.copyWith(
        fontFamily: 'Fredoka',
        fontWeight: FontWeight.w600,
        color: oasis.primaryInk,
      ),
      // Nunito carries longer instructional, discussion, safety, settings,
      // and explanation text with comfortable line spacing.
      bodyLarge: base.bodyLarge?.copyWith(
        fontFamily: 'Nunito',
        fontSize: 15,
        fontWeight: FontWeight.w400,
        color: oasis.secondaryInk,
        height: 1.35,
      ),
      bodyMedium: base.bodyMedium?.copyWith(
        fontFamily: 'Nunito',
        fontSize: 13,
        fontWeight: FontWeight.w400,
        color: oasis.secondaryInk,
        height: 1.35,
      ),
      bodySmall: base.bodySmall?.copyWith(
        fontFamily: 'Nunito',
        fontWeight: FontWeight.w400,
        color: oasis.secondaryInk,
        height: 1.35,
      ),
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: oasis.canvas,
      fontFamily: 'Nunito',
      extensions: [oasis],
      appBarTheme: AppBarTheme(
        centerTitle: false,
        elevation: 0,
        backgroundColor: Colors.transparent,
        foregroundColor: oasis.primaryInk,
        surfaceTintColor: Colors.transparent,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: oasis.surface,
        prefixIconColor: oasis.forest,
        suffixIconColor: oasis.secondaryInk,
        labelStyle: TextStyle(
          fontFamily: 'Nunito',
          color: oasis.secondaryInk,
          fontWeight: FontWeight.w600,
        ),
        floatingLabelStyle: TextStyle(
          fontFamily: 'Nunito',
          color: oasis.forest,
          fontWeight: FontWeight.w600,
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 15,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: oasis.outline),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: oasis.outline),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: oasis.forest, width: 1.6),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: oasis.coral),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: oasis.coral, width: 1.6),
        ),
      ),
      cardTheme: CardThemeData(
        color: oasis.surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(LogicOasisDesign.radiusCard),
          side: BorderSide(color: oasis.outline),
        ),
        shadowColor: oasis.softShadow.isEmpty
            ? Colors.transparent
            : oasis.softShadow.first.color,
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: oasis.forest,
        contentTextStyle: const TextStyle(
          color: Colors.white,
          fontSize: 14,
          fontWeight: FontWeight.w700,
        ),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        behavior: SnackBarBehavior.floating,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: oasis.forest,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          textStyle: const TextStyle(
            fontFamily: 'Fredoka',
            fontSize: 15,
            fontWeight: FontWeight.w600,
            height: 1.05,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: oasis.forest,
          backgroundColor: oasis.surface,
          minimumSize: const Size.fromHeight(48),
          side: BorderSide(color: oasis.outline),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          textStyle: const TextStyle(
            fontFamily: 'Fredoka',
            fontSize: 15,
            fontWeight: FontWeight.w600,
            height: 1.05,
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: oasis.forest,
          textStyle: const TextStyle(
            fontFamily: 'Fredoka',
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return oasis.leaf;
          }
          return oasis.surface;
        }),
        checkColor: const WidgetStatePropertyAll(Colors.white),
        side: BorderSide(color: oasis.outline, width: 1.4),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
      ),
      segmentedButtonTheme: SegmentedButtonThemeData(
        style: SegmentedButton.styleFrom(
          backgroundColor: oasis.groupedSurface,
          foregroundColor: oasis.secondaryInk,
          selectedBackgroundColor: oasis.mint,
          selectedForegroundColor: oasis.forest,
          side: BorderSide(color: oasis.outline),
          textStyle: const TextStyle(
            fontFamily: 'Fredoka',
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: oasis.leaf,
        linearTrackColor: oasis.outline,
      ),
      dialogTheme: DialogThemeData(backgroundColor: oasis.surface),
      bottomSheetTheme: BottomSheetThemeData(backgroundColor: oasis.surface),
      textTheme: textTheme,
    );
  }
}
