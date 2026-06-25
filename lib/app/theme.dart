import 'package:flutter/material.dart';

class LogicOasisTheme {
  static const ink = Color(0xFF0F3028);
  static const bodyInk = Color(0xFF5D6763);
  static const leaf = Color(0xFF3F9675);
  static const deepLeaf = Color(0xFF1E7B60);
  static const mint = Color(0xFFE8F4EC);
  static const sand = Color(0xFFFFF5E4);
  static const clay = Color(0xFFC47B2D);
  static const water = Color(0xFF4FA5D8);
  static const sky = Color(0xFFEAF7F5);
  static const line = Color(0xFFE2E8E2);
  static const page = Color(0xFFF7FAF5);

  static ThemeData light() {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: leaf,
      brightness: Brightness.light,
      primary: leaf,
      secondary: water,
      surface: Colors.white,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: page,
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        elevation: 0,
        backgroundColor: page,
        foregroundColor: ink,
      ),
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 0.6,
        margin: EdgeInsets.zero,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: line),
        ),
        shadowColor: const Color(0x1A68856F),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(42),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w800,
            height: 1.05,
          ),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        height: 72,
        backgroundColor: Colors.white,
        indicatorColor: mint,
        elevation: 0,
        iconTheme: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return IconThemeData(
            size: selected ? 23 : 22,
            color: selected ? leaf : const Color(0xFF6D7470),
          );
        }),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return TextStyle(
            color: selected ? leaf : const Color(0xFF4F5954),
            fontSize: 11.5,
            fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
            height: 1.05,
          );
        }),
      ),
      textTheme: const TextTheme(
        headlineLarge: TextStyle(
          fontSize: 28,
          fontWeight: FontWeight.w800,
          color: ink,
          height: 1.05,
        ),
        headlineMedium: TextStyle(
          fontSize: 22,
          fontWeight: FontWeight.w800,
          color: ink,
          height: 1.12,
        ),
        titleLarge: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w800,
          color: ink,
          height: 1.12,
        ),
        titleMedium: TextStyle(
          fontSize: 15.5,
          fontWeight: FontWeight.w800,
          color: ink,
          height: 1.15,
        ),
        bodyLarge: TextStyle(fontSize: 15, color: bodyInk, height: 1.25),
        bodyMedium: TextStyle(
          fontSize: 13,
          color: bodyInk,
          height: 1.25,
        ),
      ),
    );
  }

  static ThemeData eyeComfort() {
    final base = light();
    return base.copyWith(
      scaffoldBackgroundColor: const Color(0xFFFAF8EF),
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        elevation: 0,
        backgroundColor: Color(0xFFFAF8EF),
        foregroundColor: ink,
      ),
      colorScheme: base.colorScheme.copyWith(
        surface: const Color(0xFFFFFCF4),
        primary: const Color(0xFF4F7F67),
      ),
    );
  }
}
