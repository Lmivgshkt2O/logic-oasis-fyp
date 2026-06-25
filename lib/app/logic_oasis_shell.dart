import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/formula_forge/formula_forge_page.dart';
import 'package:logic_oasis/features/home/home_page.dart';
import 'package:logic_oasis/features/settings/settings_page.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

class LogicOasisShell extends StatefulWidget {
  const LogicOasisShell({
    super.key,
    required this.state,
    required this.onLogout,
  });

  final AppState state;
  final VoidCallback onLogout;

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
          SettingsPage(state: widget.state, onLogout: widget.onLogout),
        ];

        return Theme(
          data: widget.state.eyeComfortMode
              ? LogicOasisTheme.eyeComfort()
              : LogicOasisTheme.light(),
          child: Scaffold(
            body: SafeArea(child: pages[widget.state.selectedTab]),
            bottomNavigationBar: _LogicOasisBottomNav(
              selectedIndex: widget.state.selectedTab,
              onSelected: widget.state.changeTab,
              items: [
                _NavItem(
                  icon: Icons.home_outlined,
                  selectedIcon: Icons.home,
                  label: widget.state.t('Home', 'Laman'),
                ),
                _NavItem(
                  icon: Icons.calculate_outlined,
                  selectedIcon: Icons.calculate,
                  label: widget.state.t('Forge', 'Latihan'),
                ),
                _NavItem(
                  icon: Icons.settings_outlined,
                  selectedIcon: Icons.settings,
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
        height: 78,
        margin: const EdgeInsets.fromLTRB(14, 0, 14, 8),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 9),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.96),
          borderRadius: BorderRadius.circular(18),
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
            width: selected ? 42 : 34,
            height: 26,
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
              fontSize: 11.5,
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
