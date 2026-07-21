import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:logic_oasis/app/logic_oasis_shell.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_page.dart';
import 'package:logic_oasis/features/onboarding/login_page.dart';
import 'package:logic_oasis/features/onboarding/opening_animation_page.dart';
import 'package:logic_oasis/features/onboarding/plot_intro_page.dart';
import 'package:logic_oasis/features/settings/parent_access_page.dart';
import 'package:logic_oasis/features/settings/parent_invitation_accept_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/repositories/auth_repository.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/state/app_state_scope.dart';
import 'package:logic_oasis/shared/services/parent_invitation_link_service.dart';

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
  final _parentInvitationLinks = ParentInvitationLinkService();
  StreamSubscription<ParentInvitationLink>? _parentInvitationSubscription;
  ParentInvitationLink? _pendingParentInvitation;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _listenForParentInvitationLinks();
    if (widget.loadFirebaseTopics) {
      appState.loadTopicsFromFirebase();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _parentInvitationSubscription?.cancel();
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
    if (_pendingParentInvitation != null) {
      moveTo(_EntryStage.parentInvitation);
      return;
    }
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
    appState.clearSignedInStudentRuntimeState();
    await appState.clearSavedSessionPosition();
    if (!mounted) return;
    loggedInStudentName = null;
    moveTo(_EntryStage.login);
  }

  Future<void> openParentAccess() async {
    // Firebase Auth has one current user. Clear the student runtime before a
    // parent account signs in; this prevents a previous learner from being
    // reused as a dashboard fallback during account switching.
    appState.clearSignedInStudentRuntimeState();
    await authRepository.signOutStudent();
    if (!mounted) return;
    loggedInStudentName = null;
    moveTo(_EntryStage.parentAccess);
  }

  void _listenForParentInvitationLinks() {
    _parentInvitationSubscription = _parentInvitationLinks.links.listen(
      (link) => unawaited(_openParentInvitation(link)),
      onError: (_) {},
    );
    _parentInvitationLinks.initialLink().then((link) {
      if (link != null) unawaited(_openParentInvitation(link));
    }).catchError((_) {});
  }

  Future<void> _openParentInvitation(ParentInvitationLink link) async {
    _pendingParentInvitation = link;
    await authRepository.signOutStudent();
    if (!mounted) return;
    appState.clearSignedInStudentRuntimeState();
    loggedInStudentName = null;
    moveTo(_EntryStage.parentInvitation);
  }

  Future<void> _finishParentDashboard() async {
    await authRepository.signOutStudent();
    _pendingParentInvitation = null;
    if (!mounted) return;
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
            builder: (context, child) {
              final mediaQuery = MediaQuery.of(context);
              return MediaQuery(
                data: mediaQuery.copyWith(
                  textScaler: state.accessibilityMode
                      ? const TextScaler.linear(1.08)
                      : mediaQuery.textScaler,
                ),
                child: child ?? const SizedBox.shrink(),
              );
            },
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
                  onParentAccess: openParentAccess,
                ),
                _EntryStage.parentAccess => ParentAccessPage(
                  key: const ValueKey('parent-access'),
                  state: appState,
                  onReturnToStudentLogin: () {
                    appState.clearSignedInStudentRuntimeState();
                    moveTo(_EntryStage.login);
                  },
                ),
                _EntryStage.parentInvitation => ParentInvitationAcceptPage(
                  key: const ValueKey('parent-invitation'),
                  invitationId: _pendingParentInvitation!.invitationId,
                  verifier: _pendingParentInvitation!.verifier,
                  emailLink: _pendingParentInvitation!.emailLink,
                  onAccepted: () => moveTo(_EntryStage.parentDashboard),
                  onDeclined: _finishParentDashboard,
                ),
                _EntryStage.parentDashboard => Scaffold(
                  key: const ValueKey('parent-dashboard'),
                  appBar: AppBar(
                    title: const Text('Parent Dashboard'),
                    actions: [
                      IconButton(
                        tooltip: 'Sign out',
                        icon: const Icon(Icons.logout),
                        onPressed: _finishParentDashboard,
                      ),
                    ],
                  ),
                  body: SafeArea(child: ParentDashboardPage(state: appState)),
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

enum _EntryStage {
  opening,
  login,
  parentAccess,
  parentInvitation,
  parentDashboard,
  intro,
  home,
}
