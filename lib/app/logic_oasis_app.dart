import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_shell.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/onboarding/login_page.dart';
import 'package:logic_oasis/features/onboarding/opening_animation_page.dart';
import 'package:logic_oasis/features/onboarding/plot_intro_page.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

class LogicOasisApp extends StatefulWidget {
  const LogicOasisApp({super.key});

  @override
  State<LogicOasisApp> createState() => _LogicOasisAppState();
}

class _LogicOasisAppState extends State<LogicOasisApp> {
  final AppState appState = AppState();
  _EntryStage stage = _EntryStage.opening;

  void moveTo(_EntryStage nextStage) {
    setState(() {
      stage = nextStage;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Logic Oasis',
      debugShowCheckedModeBanner: false,
      theme: LogicOasisTheme.light(),
      home: AnimatedSwitcher(
        duration: const Duration(milliseconds: 420),
        switchInCurve: Curves.easeOutCubic,
        switchOutCurve: Curves.easeInCubic,
        child: switch (stage) {
          _EntryStage.opening => OpeningAnimationPage(
            key: const ValueKey('opening'),
            onFinished: () => moveTo(_EntryStage.login),
          ),
          _EntryStage.login => LoginPage(
            key: const ValueKey('login'),
            onLogin: (isNewRegistration) {
              moveTo(isNewRegistration ? _EntryStage.intro : _EntryStage.home);
            },
          ),
          _EntryStage.intro => PlotIntroPage(
            key: const ValueKey('intro'),
            onFinished: () => moveTo(_EntryStage.home),
          ),
          _EntryStage.home => LogicOasisShell(
            key: const ValueKey('home'),
            state: appState,
            onLogout: () {
              appState.changeTab(0);
              moveTo(_EntryStage.login);
            },
          ),
        },
      ),
    );
  }
}

enum _EntryStage { opening, login, intro, home }
