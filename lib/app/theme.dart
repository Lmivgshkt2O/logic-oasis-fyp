import 'package:flutter/material.dart';

class LogicOasisTheme {
  static const ink = Color(0xFF21322E);
  static const leaf = Color(0xFF4F8F72);
  static const mint = Color(0xFFE8F4EE);
  static const sand = Color(0xFFFFF7E8);
  static const clay = Color(0xFFE8915A);
  static const water = Color(0xFF5B9EAD);
  static const sky = Color(0xFFEAF5F7);
  static const line = Color(0xFFD9E6DF);

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
      scaffoldBackgroundColor: const Color(0xFFF7FAF6),
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        elevation: 0,
        backgroundColor: Color(0xFFF7FAF6),
        foregroundColor: ink,
      ),
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 1,
        margin: EdgeInsets.zero,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: line),
        ),
        shadowColor: const Color(0x12000000),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(42),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w700,
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
            fontSize: 11,
            fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
            height: 1.05,
          );
        }),
      ),
      textTheme: const TextTheme(
        headlineLarge: TextStyle(
          fontSize: 26,
          fontWeight: FontWeight.w800,
          color: ink,
          height: 1.08,
        ),
        headlineMedium: TextStyle(
          fontSize: 22,
          fontWeight: FontWeight.w800,
          color: ink,
          height: 1.12,
        ),
        titleLarge: TextStyle(
          fontSize: 17,
          fontWeight: FontWeight.w800,
          color: ink,
          height: 1.12,
        ),
        titleMedium: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w700,
          color: ink,
          height: 1.15,
        ),
        bodyLarge: TextStyle(fontSize: 13, color: ink, height: 1.25),
        bodyMedium: TextStyle(
          fontSize: 11.5,
          color: Color(0xFF5B6B66),
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
