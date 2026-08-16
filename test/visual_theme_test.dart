import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
import 'package:logic_oasis/app/logic_oasis_shell.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/state/app_state_scope.dart';
import 'package:shared_preferences/shared_preferences.dart';

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

        expect(oasis.topCanvas, isNot(oasis.canvas));
        expect(oasis.canvas, isNot(oasis.surface));
        expect(oasis.canvas, isNot(oasis.lowerCanvas));
        expect(oasis.surface, isNot(oasis.quietSurface));
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
      expect(mid.topCanvas, Color.lerp(a.topCanvas, b.topCanvas, 0.5));
      expect(mid.canvas, Color.lerp(a.canvas, b.canvas, 0.5));
      expect(mid.lowerCanvas, Color.lerp(a.lowerCanvas, b.lowerCanvas, 0.5));
      expect(mid.quietSurface, Color.lerp(a.quietSurface, b.quietSurface, 0.5));
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

  group('app-level theme ownership', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    Widget appHarness(AppState state) {
      return AppStateScope(
        state: state,
        child: Builder(
          builder: (context) {
            final watched = AppStateScope.watch(context);
            return MaterialApp(
              theme: watched.eyeComfortMode
                  ? LogicOasisTheme.eyeComfort()
                  : LogicOasisTheme.light(),
              themeAnimationStyle: AnimationStyle(
                duration: LogicOasisMotion.themeTransitionFor(context),
                curve: LogicOasisMotion.themeTransitionCurve,
              ),
              home: Scaffold(
                body: Builder(
                  builder: (context) {
                    final oasis = LogicOasisTheme.of(context);
                    return ColoredBox(
                      color: oasis.canvas,
                      child: const SizedBox.expand(),
                    );
                  },
                ),
              ),
            );
          },
        ),
      );
    }

    Color canvasColor(WidgetTester tester) {
      return tester.widget<ColoredBox>(find.byType(ColoredBox)).color;
    }

    testWidgets('comfort toggle animates presentation without changing state', (
      tester,
    ) async {
      final state = AppState();
      await tester.pumpWidget(appHarness(state));

      final app = tester.widget<MaterialApp>(find.byType(MaterialApp));
      expect(app.themeAnimationStyle?.duration,
          LogicOasisMotion.themeTransition);

      final start = canvasColor(tester);
      expect(start, OasisSemanticTheme.defaults().canvas);

      state.updateEyeComfortMode(true);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 175));
      final mid = canvasColor(tester);
      await tester.pump(const Duration(milliseconds: 200));
      final end = canvasColor(tester);

      expect(mid, isNot(start));
      expect(mid, isNot(OasisSemanticTheme.comfort().canvas));
      expect(end, OasisSemanticTheme.comfort().canvas);
      expect(state.eyeComfortMode, isTrue);
      expect(state.selectedTab, 0);
      expect(tester.takeException(), isNull);
    });

    testWidgets('reduced motion switches the comfort theme near-instantly', (
      tester,
    ) async {
      final state = AppState();
      await tester.pumpWidget(
        MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: appHarness(state),
        ),
      );

      final app = tester.widget<MaterialApp>(find.byType(MaterialApp));
      expect(app.themeAnimationStyle?.duration,
          LogicOasisMotion.themeTransitionReduced);

      state.updateEyeComfortMode(true);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(canvasColor(tester), OasisSemanticTheme.comfort().canvas);
      expect(state.eyeComfortMode, isTrue);
      expect(state.selectedTab, 0);
      expect(tester.takeException(), isNull);
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

  group('accessibility guidelines', () {
    for (final (label, theme) in [
      ('default', LogicOasisTheme.light()),
      ('eye protecting', LogicOasisTheme.eyeComfort()),
    ]) {
      testWidgets('$label theme meets tap-target and text-contrast guidelines', (
        tester,
      ) async {
        final semanticsHandle = tester.ensureSemantics();
        await tester.pumpWidget(
          MaterialApp(
            theme: theme,
            home: Scaffold(
              body: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Sample heading', style: theme.textTheme.headlineMedium),
                    const SizedBox(height: 8),
                    Text(
                      'Readable body copy under the Living Canopy theme.',
                      style: theme.textTheme.bodyLarge,
                    ),
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: () {},
                      icon: const Icon(Icons.check),
                      label: const Text('Primary action'),
                    ),
                    const SizedBox(height: 8),
                    OutlinedButton.icon(
                      onPressed: () {},
                      icon: const Icon(Icons.arrow_forward),
                      label: const Text('Secondary action'),
                    ),
                    const SizedBox(height: 8),
                    IconButton(
                      tooltip: 'Icon action',
                      onPressed: () {},
                      icon: const Icon(Icons.settings_outlined),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );

        expect(tester, meetsGuideline(androidTapTargetGuideline));
        expect(tester, meetsGuideline(iOSTapTargetGuideline));
        expect(tester, meetsGuideline(labeledTapTargetGuideline));
        expect(tester, meetsGuideline(textContrastGuideline));
        semanticsHandle.dispose();
      });
    }
  });

  group('portrait and localization matrix', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    for (final (width, theme, label) in [
      (320, LogicOasisTheme.light(), '320 default'),
      (360, LogicOasisTheme.light(), '360 default'),
      (412, LogicOasisTheme.light(), '412 default'),
      (412, LogicOasisTheme.eyeComfort(), '412 eye protecting'),
    ]) {
      testWidgets('$label portrait renders without overflow', (tester) async {
        tester.view.physicalSize = Size(width.toDouble(), 800);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final state = AppState();
        await tester.pumpWidget(
          AppStateScope(
            state: state,
            child: MaterialApp(
              theme: theme,
              localizationsDelegates: AppLocalizations.localizationsDelegates,
              supportedLocales: AppLocalizations.supportedLocales,
              home: LogicOasisShell(onLogout: () {}),
            ),
          ),
        );

        expect(find.text('Home'), findsOneWidget);
        expect(find.text('Q&A Forum'), findsOneWidget);
        expect(tester.takeException(), isNull);
      });
    }
  });

  group('state-invariance gate', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    testWidgets('Eye Protecting transition preserves every functional value', (
      tester,
    ) async {
      final state = AppState()
        ..switchYear(5)
        ..language = 'Bahasa Melayu'
        ..accessibilityMode = true;

      await tester.pumpWidget(
        AppStateScope(
          state: state,
          child: Builder(
            builder: (context) {
              final watched = AppStateScope.watch(context);
              return MaterialApp(
                theme: watched.eyeComfortMode
                    ? LogicOasisTheme.eyeComfort()
                    : LogicOasisTheme.light(),
                themeAnimationStyle: AnimationStyle(
                  duration: LogicOasisMotion.themeTransitionFor(context),
                  curve: LogicOasisMotion.themeTransitionCurve,
                ),
                localizationsDelegates: AppLocalizations.localizationsDelegates,
                supportedLocales: AppLocalizations.supportedLocales,
                home: LogicOasisShell(onLogout: () {}),
              );
            },
          ),
        ),
      );

      final captured = (
        tab: state.selectedTab,
        year: state.yearLevel,
        locale: state.language,
        largerText: state.accessibilityMode,
        restoration: state.restorationProgress,
        crystals: state.crystals,
        energy: state.mutualAidEnergy,
        streak: state.currentYearAttempts.length,
        progress: state.oasisAreas.map((area) => area.progress).toList(),
      );

      state.updateEyeComfortMode(true);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 175));
      expect(state.selectedTab, captured.tab);
      expect(state.yearLevel, captured.year);
      expect(state.language, captured.locale);
      expect(state.accessibilityMode, captured.largerText);
      expect(state.restorationProgress, captured.restoration);
      expect(state.crystals, captured.crystals);
      expect(state.mutualAidEnergy, captured.energy);
      expect(state.currentYearAttempts.length, captured.streak);
      expect(
        state.oasisAreas.map((area) => area.progress),
        orderedEquals(captured.progress),
      );

      await tester.pump(const Duration(milliseconds: 200));
      expect(state.selectedTab, captured.tab);
      expect(state.yearLevel, captured.year);
      expect(state.language, captured.locale);
      expect(state.accessibilityMode, captured.largerText);
      expect(state.restorationProgress, captured.restoration);
      expect(state.crystals, captured.crystals);
      expect(state.mutualAidEnergy, captured.energy);
      expect(state.currentYearAttempts.length, captured.streak);
      expect(
        state.oasisAreas.map((area) => area.progress),
        orderedEquals(captured.progress),
      );
      expect(state.eyeComfortMode, isTrue);
      expect(tester.takeException(), isNull);
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
