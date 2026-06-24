import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/formula_forge/formula_forge_page.dart';
import 'package:logic_oasis/features/home/home_page.dart';
import 'package:logic_oasis/features/settings/settings_page.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

class LogicOasisShell extends StatefulWidget {
  const LogicOasisShell({super.key, required this.state});

  final AppState state;

  @override
  State<LogicOasisShell> createState() => _LogicOasisShellState();
}

class _LogicOasisShellState extends State<LogicOasisShell> {
  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.state,
      builder: (context, _) {
        final pages = [
          HomePage(state: widget.state),
          FormulaForgePage(state: widget.state),
          SettingsPage(state: widget.state),
        ];

        return Theme(
          data: widget.state.eyeComfortMode
              ? LogicOasisTheme.eyeComfort()
              : LogicOasisTheme.light(),
          child: Scaffold(
            body: SafeArea(child: pages[widget.state.selectedTab]),
            bottomNavigationBar: NavigationBar(
              selectedIndex: widget.state.selectedTab,
              onDestinationSelected: widget.state.changeTab,
              destinations: [
                NavigationDestination(
                  icon: const Icon(Icons.spa_outlined),
                  selectedIcon: const Icon(Icons.spa),
                  label: widget.state.t('Home', 'Laman'),
                ),
                NavigationDestination(
                  icon: const Icon(Icons.calculate_outlined),
                  selectedIcon: const Icon(Icons.calculate),
                  label: widget.state.t('Forge', 'Latihan'),
                ),
                NavigationDestination(
                  icon: const Icon(Icons.settings_outlined),
                  selectedIcon: const Icon(Icons.settings),
                  label: widget.state.t('Settings', 'Tetapan'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
