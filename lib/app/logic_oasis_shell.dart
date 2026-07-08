import 'dart:async';

import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/formula_forge/formula_forge_page.dart';
import 'package:logic_oasis/features/home/home_page.dart';
import 'package:logic_oasis/features/settings/settings_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/state/app_state_scope.dart';
import 'package:logic_oasis/shared/widgets/logic_oasis_figma_components.dart';

class LogicOasisShell extends StatefulWidget {
  const LogicOasisShell({
    super.key,
    required this.onLogout,
    this.welcomeStudentName,
  });

  final VoidCallback onLogout;
  final String? welcomeStudentName;

  @override
  State<LogicOasisShell> createState() => _LogicOasisShellState();
}

class _LogicOasisShellState extends State<LogicOasisShell> {
  Timer? welcomeTimer;
  bool showWelcome = false;

  @override
  void initState() {
    super.initState();
    showWelcomeMessage();
  }

  @override
  void didUpdateWidget(covariant LogicOasisShell oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.welcomeStudentName != widget.welcomeStudentName) {
      showWelcomeMessage();
    }
  }

  @override
  void dispose() {
    welcomeTimer?.cancel();
    super.dispose();
  }

  void showWelcomeMessage() {
    welcomeTimer?.cancel();
    if (widget.welcomeStudentName == null ||
        widget.welcomeStudentName!.trim().isEmpty) {
      if (mounted) {
        setState(() {
          showWelcome = false;
        });
      } else {
        showWelcome = false;
      }
      return;
    }

    if (mounted) {
      setState(() {
        showWelcome = true;
      });
    } else {
      showWelcome = true;
    }
    welcomeTimer = Timer(const Duration(seconds: 3), () {
      if (!mounted) return;
      setState(() {
        showWelcome = false;
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = AppStateScope.watch(context);
    final l10n = AppLocalizations.of(context)!;
    final pages = [
      HomePage(state: state),
      FormulaForgePage(state: state),
      SettingsPage(state: state, onLogout: widget.onLogout),
    ];

    return Theme(
      data: state.eyeComfortMode
          ? LogicOasisTheme.eyeComfort()
          : LogicOasisTheme.light(),
      child: Scaffold(
        backgroundColor: state.eyeComfortMode
            ? const Color(0xFFFFF1CE)
            : LogicOasisDesign.page,
        body: Stack(
          children: [
            pages[state.selectedTab],
            if (showWelcome && state.selectedTab == 0)
              Positioned(
                top: 18,
                right: 78,
                child: _WelcomeToast(
                  studentName: widget.welcomeStudentName!.trim(),
                ),
              ),
          ],
        ),
        bottomNavigationBar: DecoratedBox(
          decoration: const BoxDecoration(color: Colors.transparent),
          child: BottomNavBar(
            selectedIndex: state.selectedTab,
            onSelected: state.changeTab,
            items: [
              BottomNavItemData(
                icon: Icons.home_rounded,
                label: l10n.home,
              ),
              BottomNavItemData(
                icon: Icons.handyman_rounded,
                label: l10n.forge,
              ),
              BottomNavItemData(
                icon: Icons.settings_rounded,
                label: l10n.settings,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _WelcomeToast extends StatelessWidget {
  const _WelcomeToast({required this.studentName});

  final String studentName;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Material(
      color: Colors.transparent,
      child: AnimatedOpacity(
        opacity: 1,
        duration: const Duration(milliseconds: 180),
        child: Container(
          constraints: const BoxConstraints(maxWidth: 220),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
          decoration: BoxDecoration(
            color: LogicOasisDesign.card,
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: LogicOasisDesign.line),
            boxShadow: LogicOasisDesign.softShadow,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.waving_hand_outlined,
                color: LogicOasisDesign.leaf,
                size: 20,
              ),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  'Welcome back, $studentName',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.titleMedium?.copyWith(fontSize: 13.5),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
