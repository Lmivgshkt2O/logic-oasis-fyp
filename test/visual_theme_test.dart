import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
import 'package:logic_oasis/app/theme.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('semantic theme roles', () {
    test('both variants expose the same complete Oasis role set', () {
      for (final (label, theme, isComfort) in [
        ('default', LogicOasisTheme.light(), false),
        ('eye protecting', LogicOasisTheme.eyeComfort(), true),
      ]) {
        final oasis = theme.extension<OasisSemanticTheme>();
        expect(oasis, isNotNull, reason: '$label theme missing extension');
        expect(oasis!.isComfort, isComfort);

        expect(oasis.canvas, isNot(oasis.surface));
        expect(oasis.surface, isNot(oasis.groupedSurface));
        expect(oasis.primaryInk, isNot(oasis.secondaryInk));
        expect(oasis.forest, isNot(oasis.water));
        expect(oasis.leaf, isNot(oasis.reward));
        expect(oasis.coral, isNot(oasis.neutral));
        expect(oasis.softShadow, isNotEmpty);
        expect(oasis.liftShadow, isNotEmpty);
        expect(oasis.statusStrong, oasis.leaf);
        expect(oasis.statusNeedsHelp, oasis.coral);
        expect(oasis.statusLocked, oasis.neutral);
      }
    });

    test('extension lerp is non-null at endpoints and midpoint', () {
      final a = OasisSemanticTheme.defaults();
      final b = OasisSemanticTheme.comfort();

      final aEnd = a.lerp(a, 0);
      expect(aEnd.canvas, a.canvas);
      expect(aEnd.primaryInk, a.primaryInk);
      expect(aEnd.isComfort, a.isComfort);
      expect(aEnd.softShadow, a.softShadow);

      final bEnd = a.lerp(b, 1);
      expect(bEnd.canvas, b.canvas);
      expect(bEnd.primaryInk, b.primaryInk);
      expect(bEnd.isComfort, b.isComfort);
      expect(a.lerp(null, 0.5), same(a));

      final mid = a.lerp(b, 0.5);
      expect(mid, isNotNull);
      expect(mid.canvas, Color.lerp(a.canvas, b.canvas, 0.5));
      expect(mid.primaryInk, Color.lerp(a.primaryInk, b.primaryInk, 0.5));
      expect(mid.softShadow, hasLength(a.softShadow.length));

      final themeMid = ThemeData.lerp(LogicOasisTheme.light(),
          LogicOasisTheme.eyeComfort(), 0.5);
      expect(themeMid.extension<OasisSemanticTheme>(), isNotNull);
    });
  });

  group('component themes use semantic roles', () {
    test('default and comfort components resolve from Oasis roles', () {
      for (final theme in [
        LogicOasisTheme.light(),
        LogicOasisTheme.eyeComfort(),
      ]) {
        final oasis = theme.extension<OasisSemanticTheme>()!;
        expect(theme.scaffoldBackgroundColor, oasis.canvas);
        expect(theme.colorScheme.primary, oasis.forest);
        expect(theme.colorScheme.surface, oasis.surface);
        expect(theme.cardTheme.color, oasis.surface);
        expect(theme.snackBarTheme.backgroundColor, oasis.forest);
        expect(
          theme.filledButtonTheme.style?.backgroundColor?.resolve({}),
          oasis.forest,
        );
        expect(
          theme.filledButtonTheme.style?.foregroundColor?.resolve({}),
          Colors.white,
        );
        expect(
          theme.outlinedButtonTheme.style?.foregroundColor?.resolve({}),
          oasis.forest,
        );
        expect(theme.progressIndicatorTheme.color, oasis.leaf);
        expect(theme.inputDecorationTheme.fillColor, oasis.surface);
      }
    });
  });

  group('mixed typography', () {
    test('Fredoka carries short emphasis roles and Nunito carries body roles',
        () {
      for (final theme in [
        LogicOasisTheme.light(),
        LogicOasisTheme.eyeComfort(),
      ]) {
        final textTheme = theme.textTheme;
        final oasis = theme.extension<OasisSemanticTheme>()!;

        for (final style in [
          textTheme.displayLarge,
          textTheme.headlineLarge,
          textTheme.headlineMedium,
          textTheme.titleLarge,
          textTheme.titleMedium,
          textTheme.labelLarge,
          textTheme.labelMedium,
        ]) {
          expect(style!.fontFamily, 'Fredoka');
          expect(style.fontWeight, FontWeight.w600);
          expect(style.color, oasis.primaryInk);
        }

        for (final style in [
          textTheme.bodyLarge,
          textTheme.bodyMedium,
          textTheme.bodySmall,
        ]) {
          expect(style!.fontFamily, 'Nunito');
          expect(style.fontWeight, FontWeight.w400);
          expect(style.color, oasis.secondaryInk);
          expect(style.height, greaterThanOrEqualTo(1.3));
        }

      }
    });
  });

  group('status non-colour contracts', () {
    test('every status has a readable label and icon cue', () {
      expect(OasisSemanticTheme.statusCues.keys.toSet(),
          OasisStatus.values.toSet());
      for (final cue in OasisSemanticTheme.statusCues.values) {
        expect(cue.label.trim(), isNotEmpty);
        expect(cue.icon, isNotNull);
      }
    });
  });

  group('motion policy', () {
    test('normal and reduced theme transition durations are centralised', () {
      expect(LogicOasisMotion.themeTransition,
          const Duration(milliseconds: 350));
      expect(LogicOasisMotion.themeTransitionReduced,
          const Duration(milliseconds: 80));
      expect(LogicOasisMotion.themeTransitionCurve, Curves.easeInOutCubic);
    });

    testWidgets('reduced-motion preference shortens the theme transition', (
      tester,
    ) async {
      Future<Duration> resolve({required bool reduced}) async {
        late Duration result;
        await tester.pumpWidget(
          MediaQuery(
            data: MediaQueryData(disableAnimations: reduced),
            child: Builder(
              builder: (context) {
                result = LogicOasisMotion.themeTransitionFor(context);
                return const SizedBox.shrink();
              },
            ),
          ),
        );
        return result;
      }

      expect(await resolve(reduced: false), LogicOasisMotion.themeTransition);
      expect(
        await resolve(reduced: true),
        LogicOasisMotion.themeTransitionReduced,
      );
    });
  });

  group('bundled fonts resolve offline', () {
    testWidgets('requested Fredoka and Nunito weights are bundled assets', (
      tester,
    ) async {
      GoogleFonts.config.allowRuntimeFetching = false;

      const fonts = <String, int>{
        'assets/fonts/Fredoka-Medium.ttf': 48768,
        'assets/fonts/Fredoka-SemiBold.ttf': 48744,
        'assets/fonts/Fredoka-Bold.ttf': 48564,
        'assets/fonts/Nunito-Regular.ttf': 125504,
        'assets/fonts/Nunito-Medium.ttf': 125628,
        'assets/fonts/Nunito-SemiBold.ttf': 125512,
      };

      for (final entry in fonts.entries) {
        final data = await rootBundle.load(entry.key);
        final bytes = data.buffer.asUint8List();
        expect(bytes.length, entry.value,
            reason: '${entry.key} size drift from upstream metadata');
        // TTF magic: 0x00010000.
        expect(bytes.sublist(0, 4), [0x00, 0x01, 0x00, 0x00],
            reason: '${entry.key} is not a TTF file');
      }

      // The theme references the same families directly, so no google_fonts
      // runtime fetch is involved anywhere in the app chrome.
      expect(LogicOasisTheme.light().textTheme.headlineLarge!.fontFamily,
          'Fredoka');
      expect(LogicOasisTheme.light().textTheme.bodyLarge!.fontFamily,
          'Nunito');
    });
  });

  group('semantic contrast', () {
    test('primary text pairs meet WCAG AA normal-text contrast', () {
      for (final theme in [
        LogicOasisTheme.light(),
        LogicOasisTheme.eyeComfort(),
      ]) {
        final oasis = theme.extension<OasisSemanticTheme>()!;
        final pairs = <(Color, Color, String)>[
          (oasis.primaryInk, oasis.canvas, 'primary ink on canvas'),
          (oasis.primaryInk, oasis.surface, 'primary ink on surface'),
          (oasis.primaryInk, oasis.mint, 'primary ink on mint'),
          (oasis.primaryInk, oasis.groupedSurface, 'primary ink on grouped'),
          (oasis.secondaryInk, oasis.surface, 'secondary ink on surface'),
          (oasis.secondaryInk, oasis.canvas, 'secondary ink on canvas'),
          (Colors.white, oasis.forest, 'white on forest action'),
          (oasis.primaryInk, oasis.reward, 'primary ink on reward'),
          (oasis.coral, oasis.surface, 'coral on surface'),
          (oasis.coral, oasis.canvas, 'coral on canvas'),
          (oasis.violet, oasis.surface, 'violet on surface'),
        ];
        for (final (foreground, background, label) in pairs) {
          expect(
            _contrast(foreground, background),
            greaterThanOrEqualTo(4.5),
            reason: '$label must meet AA normal-text contrast',
          );
        }
      }
    });
  });
}

double _contrast(Color foreground, Color background) {
  final lighter = math.max(_luminance(foreground), _luminance(background));
  final darker = math.min(_luminance(foreground), _luminance(background));
  return (lighter + 0.05) / (darker + 0.05);
}

double _luminance(Color color) {
  double channel(double value) {
    if (value <= 0.03928) return value / 12.92;
    return math.pow((value + 0.055) / 1.055, 2.4).toDouble();
  }

  return 0.2126 * channel(color.r) +
      0.7152 * channel(color.g) +
      0.0722 * channel(color.b);
}
