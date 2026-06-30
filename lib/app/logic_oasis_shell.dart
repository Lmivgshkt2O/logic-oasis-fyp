import 'dart:async';

import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/formula_forge/formula_forge_page.dart';
import 'package:logic_oasis/features/home/home_page.dart';
import 'package:logic_oasis/features/settings/settings_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/state/app_state_scope.dart';

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
        body: SafeArea(
          child: Stack(
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
        ),
        bottomNavigationBar: _LogicOasisBottomNav(
          selectedIndex: state.selectedTab,
          onSelected: state.changeTab,
          items: [
            _NavItem(
              icon: Icons.home_outlined,
              selectedIcon: Icons.home,
              label: l10n.home,
            ),
            _NavItem(
              icon: Icons.calculate_outlined,
              selectedIcon: Icons.calculate,
              label: l10n.forge,
            ),
            _NavItem(
              icon: Icons.settings_outlined,
              selectedIcon: Icons.settings,
              label: l10n.settings,
            ),
          ],
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
            color: Colors.white.withValues(alpha: 0.94),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFFE7EDE8)),
            boxShadow: const [
              BoxShadow(
                color: Color(0x1A5C8069),
                blurRadius: 18,
                offset: Offset(0, 6),
              ),
            ],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.waving_hand_outlined,
                color: LogicOasisTheme.leaf,
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

class _LogicOasisBottomNav extends StatelessWidget {
  const _LogicOasisBottomNav({
    required this.selectedIndex,
    required this.onSelected,
    required this.items,
  });

  final int selectedIndex;
  final ValueChanged<int> onSelected;
  final List<_NavItem> items;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Container(
        height: 82,
        margin: const EdgeInsets.fromLTRB(12, 0, 12, 8),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 9),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.96),
          borderRadius: BorderRadius.circular(17),
          border: Border.all(color: const Color(0xFFE7EDE8)),
          boxShadow: const [
            BoxShadow(
              color: Color(0x1A5C8069),
              blurRadius: 18,
              offset: Offset(0, -4),
            ),
          ],
        ),
        child: Row(
          children: [
            for (var i = 0; i < items.length; i++)
              Expanded(
                child: _BottomNavButton(
                  item: items[i],
                  selected: selectedIndex == i,
                  onTap: () => onSelected(i),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _BottomNavButton extends StatelessWidget {
  const _BottomNavButton({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final _NavItem item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = selected ? LogicOasisTheme.deepLeaf : const Color(0xFF7C837F);

    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: onTap,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            width: selected ? 44 : 34,
            height: 28,
            decoration: BoxDecoration(
              color: selected ? LogicOasisTheme.mint : Colors.transparent,
              borderRadius: BorderRadius.circular(99),
            ),
            child: Icon(
              selected ? item.selectedIcon : item.icon,
              color: color,
              size: 22,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            item.label,
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
              height: 1,
            ),
          ),
        ],
      ),
    );
  }
}

class _NavItem {
  const _NavItem({
    required this.icon,
    required this.selectedIcon,
    required this.label,
  });

  final IconData icon;
  final IconData selectedIcon;
  final String label;
}
