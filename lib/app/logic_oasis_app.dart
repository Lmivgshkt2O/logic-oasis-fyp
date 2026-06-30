import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:logic_oasis/app/logic_oasis_shell.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/onboarding/login_page.dart';
import 'package:logic_oasis/features/onboarding/opening_animation_page.dart';
import 'package:logic_oasis/features/onboarding/plot_intro_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/repositories/auth_repository.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/state/app_state_scope.dart';

class LogicOasisApp extends StatefulWidget {
  const LogicOasisApp({super.key, this.loadFirebaseTopics = true});

  final bool loadFirebaseTopics;

  @override
  State<LogicOasisApp> createState() => _LogicOasisAppState();
}

class _LogicOasisAppState extends State<LogicOasisApp>
    with WidgetsBindingObserver {
  late final AppState appState = AppState(persistQuizResults: true);
  final AuthRepository authRepository = AuthRepository();
  _EntryStage stage = _EntryStage.opening;
  String? loggedInStudentName;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    if (widget.loadFirebaseTopics) {
      appState.loadTopicsFromFirebase();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    appState.saveAppSession();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.inactive ||
        state == AppLifecycleState.paused ||
        state == AppLifecycleState.detached) {
      appState.saveAppSession();
    }
  }

  void moveTo(_EntryStage nextStage) {
    setState(() {
      stage = nextStage;
    });
  }

  Future<void> completeOpening() async {
    await appState.loadSavedAppPreferences();
    final profile = await authRepository.loadCurrentStudentProfile();
    if (!mounted) return;

    if (profile == null) {
      moveTo(_EntryStage.login);
      return;
    }

    loggedInStudentName = profile.displayName;
    appState.updateSignedInStudent(
      uid: profile.uid,
      email: profile.email,
      name: profile.displayName,
      year: profile.yearLevel,
    );
    appState.changeTab(0);
    moveTo(_EntryStage.home);
  }

  Future<void> logout() async {
    await authRepository.signOutStudent();
    await appState.clearSavedSessionPosition();
    if (!mounted) return;
    loggedInStudentName = null;
    moveTo(_EntryStage.login);
  }

  @override
  Widget build(BuildContext context) {
    return AppStateScope(
      state: appState,
      child: Builder(
        builder: (context) {
          final state = AppStateScope.watch(context);

          return MaterialApp(
            title: 'Logic Oasis',
            debugShowCheckedModeBanner: false,
            theme: LogicOasisTheme.light(),
            locale: state.locale,
            supportedLocales: AppLocalizations.supportedLocales,
            localizationsDelegates: const [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
            ],
            home: AnimatedSwitcher(
              duration: const Duration(milliseconds: 420),
              switchInCurve: Curves.easeOutCubic,
              switchOutCurve: Curves.easeInCubic,
              child: switch (stage) {
                _EntryStage.opening => OpeningAnimationPage(
                  key: const ValueKey('opening'),
                  onFinished: completeOpening,
                ),
                _EntryStage.login => LoginPage(
                  key: const ValueKey('login'),
                  onLogin: (profile) {
                    loggedInStudentName = profile.displayName;
                    appState.updateSignedInStudent(
                      uid: profile.uid,
                      email: profile.email,
                      name: profile.displayName,
                      year: profile.yearLevel,
                    );
                    moveTo(_EntryStage.home);
                  },
                ),
                _EntryStage.intro => PlotIntroPage(
                  key: const ValueKey('intro'),
                  onFinished: () => moveTo(_EntryStage.home),
                ),
                _EntryStage.home => LogicOasisShell(
                  key: const ValueKey('home'),
                  welcomeStudentName: loggedInStudentName,
                  onLogout: () {
                    state.changeTab(0);
                    logout();
                  },
                ),
              },
            ),
          );
        },
      ),
    );
  }
}

enum _EntryStage { opening, login, intro, home }
