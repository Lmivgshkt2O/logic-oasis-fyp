import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';

class LogicOasisTheme {
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

  static ThemeData light() {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: LogicOasisDesign.leaf,
      brightness: Brightness.light,
      primary: LogicOasisDesign.leaf,
      secondary: LogicOasisDesign.water,
      surface: LogicOasisDesign.cream,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: LogicOasisDesign.page,
      fontFamily: 'Roboto',
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        elevation: 0,
        backgroundColor: Colors.transparent,
        foregroundColor: LogicOasisDesign.ink,
        surfaceTintColor: Colors.transparent,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: LogicOasisDesign.card,
        prefixIconColor: LogicOasisDesign.forest,
        suffixIconColor: LogicOasisDesign.body,
        labelStyle: const TextStyle(
          color: LogicOasisDesign.body,
          fontWeight: FontWeight.w700,
        ),
        floatingLabelStyle: const TextStyle(
          color: LogicOasisDesign.forest,
          fontWeight: FontWeight.w900,
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 15,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: LogicOasisDesign.line),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: LogicOasisDesign.line),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(
            color: LogicOasisDesign.leaf,
            width: 1.6,
          ),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Color(0xFFC45B45)),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(
            color: Color(0xFFC45B45),
            width: 1.6,
          ),
        ),
      ),
      cardTheme: CardThemeData(
        color: LogicOasisDesign.card,
        elevation: 0,
        margin: EdgeInsets.zero,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(LogicOasisDesign.radiusCard),
          side: const BorderSide(color: LogicOasisDesign.line),
        ),
        shadowColor: const Color(0x33496F55),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: LogicOasisDesign.deepForest,
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
          backgroundColor: LogicOasisDesign.yellow,
          foregroundColor: LogicOasisDesign.forest,
          minimumSize: const Size.fromHeight(48),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w900,
            height: 1.05,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: LogicOasisDesign.forest,
          minimumSize: const Size.fromHeight(48),
          side: const BorderSide(color: LogicOasisDesign.line),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w900,
            height: 1.05,
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: LogicOasisDesign.forest,
          textStyle: const TextStyle(fontWeight: FontWeight.w900),
        ),
      ),
      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return LogicOasisDesign.leaf;
          }
          return LogicOasisDesign.card;
        }),
        checkColor: const WidgetStatePropertyAll(Colors.white),
        side: const BorderSide(color: LogicOasisDesign.line, width: 1.4),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
      ),
      segmentedButtonTheme: SegmentedButtonThemeData(
        style: SegmentedButton.styleFrom(
          backgroundColor: LogicOasisDesign.card,
          foregroundColor: LogicOasisDesign.body,
          selectedBackgroundColor: LogicOasisDesign.mintLight,
          selectedForegroundColor: LogicOasisDesign.forest,
          side: const BorderSide(color: LogicOasisDesign.line),
          textStyle: const TextStyle(fontWeight: FontWeight.w900),
        ),
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: LogicOasisDesign.leaf,
        linearTrackColor: Color(0xFFE7E0D3),
      ),
      textTheme: const TextTheme(
        headlineLarge: TextStyle(
          fontSize: 38,
          fontWeight: FontWeight.w900,
          color: LogicOasisDesign.forest,
          height: 1.04,
        ),
        headlineMedium: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.w900,
          color: LogicOasisDesign.forest,
          height: 1.08,
        ),
        titleLarge: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w900,
          color: LogicOasisDesign.deepForest,
          height: 1.12,
        ),
        titleMedium: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w900,
          color: LogicOasisDesign.deepForest,
          height: 1.16,
        ),
        bodyLarge: TextStyle(
          fontSize: 15,
          color: LogicOasisDesign.body,
          height: 1.25,
        ),
        bodyMedium: TextStyle(
          fontSize: 13,
          color: LogicOasisDesign.body,
          height: 1.25,
        ),
      ),
    );
  }

  static ThemeData eyeComfort() {
    final base = light();
    return base.copyWith(
      scaffoldBackgroundColor: const Color(0xFFFFF1CE),
      colorScheme: base.colorScheme.copyWith(
        surface: const Color(0xFFFFF8E7),
        primary: const Color(0xFF5E7E59),
      ),
    );
  }
}
