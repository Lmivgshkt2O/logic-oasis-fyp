import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/repositories/auth_repository.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/logic_oasis_figma_components.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({
    super.key,
    required this.state,
    required this.onLogout,
    this.authRepository,
  });

  final AppState state;
  final VoidCallback onLogout;
  final AuthRepository? authRepository;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return LogicOasisScaffold(
      children: [
        LogicHeader(
          title: l10n.settings,
          subtitle: state.t(
            'Personalise your oasis.',
            l10n.manageProfilePreferences,
          ),
          trailing: const SoftIconButton(icon: 'nav_settings'),
        ),
        const SizedBox(height: 18),
        _FigmaProfileCard(
          name: state.studentName,
          level:
              '${state.t('Level 7 Gardener', 'Tukang Kebun Tahap 7')} - ${state.t('Year', 'Tahun')} ${state.yearLevel}',
          email: state.currentStudentEmail ?? 'amirah@logicoasis.edu.my',
          crystals: state.crystals,
          energy: state.mutualAidEnergy,
          streak: state.currentYearAttempts.length,
          onTap: () => _showProfileSheet(context),
        ),
        const SizedBox(height: 20),
        _SettingsSection(
          title: 'LEARNING',
          children: [
            SettingsRow(
              icon: 'volume_up',
              iconColor: LogicOasisDesign.leaf,
              label: state.t('Sound', 'Bunyi'),
              value: state.soundEnabled
                  ? state.t('On', 'Hidup')
                  : state.t('Off', 'Mati'),
              trailingSwitch: state.soundEnabled,
              onTap: () {
                state.updateSoundEnabled(!state.soundEnabled);
                _showMessage(
                  context,
                  state.soundEnabled
                      ? state.t('Sound turned on.', 'Bunyi dihidupkan.')
                      : state.t('Sound turned off.', 'Bunyi dimatikan.'),
                );
              },
            ),
            SettingsRow(
              icon: 'language',
              iconColor: LogicOasisDesign.forest,
              label: state.t('Language', 'Bahasa'),
              value: state.language,
              onTap: () => _showLanguageSheet(context),
            ),
            SettingsRow(
              icon: 'accessibility',
              iconColor: const Color(0xFF42A6E2),
              label: state.t('Accessibility', 'Aksesibiliti'),
              value: state.accessibilityMode
                  ? state.t('Larger text', 'Teks besar')
                  : state.t('Standard', 'Standard'),
              trailingSwitch: state.accessibilityMode,
              onTap: () {
                state.updateAccessibilityMode(!state.accessibilityMode);
                _showMessage(
                  context,
                  state.accessibilityMode
                      ? state.t(
                          'Larger text is on.',
                          'Teks lebih besar dihidupkan.',
                        )
                      : state.t(
                          'Standard text size restored.',
                          'Saiz teks standard dipulihkan.',
                        ),
                );
              },
            ),
            SettingsRow(
              icon: state.missionReminders
                  ? 'notifications_active'
                  : 'notifications_off',
              iconColor: const Color(0xFFE6A124),
              label: state.t('Notification', 'Notifikasi'),
              value: state.missionReminders
                  ? state.t('Mission reminders', 'Peringatan misi')
                  : state.t('Off', 'Mati'),
              trailingSwitch: state.missionReminders,
              onTap: () {
                state.updateMissionReminders(!state.missionReminders);
                _showMessage(
                  context,
                  state.missionReminders
                      ? state.t(
                          'Mission reminders turned on.',
                          'Peringatan misi dihidupkan.',
                        )
                      : state.t(
                          'Mission reminders turned off.',
                          'Peringatan misi dimatikan.',
                        ),
                );
              },
            ),
            SettingsRow(
              icon: 'visibility',
              iconColor: state.eyeComfortMode
                  ? const Color(0xFF8A6B2C)
                  : const Color(0xFF6C8BD8),
              label: state.t('Eye protecting mode', 'Mod lindung mata'),
              value: state.eyeComfortMode
                  ? state.t('On', 'Hidup')
                  : state.t('Off', 'Mati'),
              trailingSwitch: state.eyeComfortMode,
              onTap: () {
                state.updateEyeComfortMode(!state.eyeComfortMode);
                _showMessage(
                  context,
                  state.eyeComfortMode
                      ? state.t(
                          'Eye protecting mode is on.',
                          'Mod lindung mata dihidupkan.',
                        )
                      : state.t(
                          'Eye protecting mode is off.',
                          'Mod lindung mata dimatikan.',
                        ),
                );
              },
            ),
            _EyeProtectingStatusCard(state: state),
            SettingsRow(
              icon: 'screen_time',
              iconColor: const Color(0xFFFFB532),
              label: state.t('Screen Time', 'Masa Skrin'),
              value: state.t(
                '${state.screenTimeLimitMinutes} min/day',
                '${state.screenTimeLimitMinutes} min/hari',
              ),
              progress: state.screenTimeProgress,
              showDivider: false,
              onTap: () => _showScreenTimeSheet(context),
            ),
          ],
        ),
        const SizedBox(height: 20),
        _SettingsSection(
          title: 'PARENT & SAFETY',
          children: [
            _ParentDashboardCard(
              title: l10n.parentDashboard,
              summary: l10n.parentDashboardSummary(state.studentName),
              restoration: l10n.oasisRestoredSummary(
                (state.restorationProgress * 100).round(),
              ),
              onTap: () => _openParentAccess(context),
            ),
            SettingsRow(
              icon: 'privacy',
              iconColor: const Color(0xFF4FBF87),
              label: state.t('Privacy & Safety', 'Privasi & Keselamatan'),
              showDivider: false,
              onTap: () => _showPrivacySafetySheet(context),
            ),
          ],
        ),
        const SizedBox(height: 18),
        _LogoutButton(title: l10n.logout, onTap: () => _confirmLogout(context)),
      ],
    );
  }

  Future<void> _confirmLogout(BuildContext context) async {
    final l10n = AppLocalizations.of(context)!;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(l10n.confirmLogout),
          content: Text(l10n.logoutConfirmBody),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: Text(l10n.cancel),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: Text(l10n.logout),
            ),
          ],
        );
      },
    );

    if (confirmed != true || !context.mounted) return;
    onLogout();
  }

  Future<void> _showProfileSheet(BuildContext context) async {
    final settingsContext = context;
    final saved = await showModalBottomSheet<bool>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) {
        return _StudentProfileSheet(
          state: state,
          authRepository: authRepository ?? AuthRepository(),
        );
      },
    );

    if (saved != true || !settingsContext.mounted) return;
    ScaffoldMessenger.of(settingsContext)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(settingsContext)!.studentProfileUpdated),
        ),
      );
  }

  Future<void> _showLanguageSheet(BuildContext context) async {
    final selected = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ListTile(
                  leading: const AppSvgIcon(
                    'language',
                    color: LogicOasisDesign.forest,
                    size: 22,
                  ),
                  title: const Text('English'),
                  trailing: state.language == 'English'
                      ? const AppSvgIcon(
                          'check',
                          color: LogicOasisDesign.leaf,
                          size: 22,
                        )
                      : null,
                  onTap: () => Navigator.of(context).pop('English'),
                ),
                ListTile(
                  leading: const AppSvgIcon(
                    'language',
                    color: Color(0xFF42A6E2),
                    size: 22,
                  ),
                  title: const Text('Bahasa Melayu'),
                  trailing: state.language == 'Bahasa Melayu'
                      ? const AppSvgIcon(
                          'check',
                          color: LogicOasisDesign.leaf,
                          size: 22,
                        )
                      : null,
                  onTap: () => Navigator.of(context).pop('Bahasa Melayu'),
                ),
              ],
            ),
          ),
        );
      },
    );

    if (selected == null) return;
    state.updateLanguage(selected);
    if (!context.mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(content: Text(AppLocalizations.of(context)!.languageSet(selected))),
      );
  }

  Future<void> _showScreenTimeSheet(BuildContext context) async {
    final selected = await showModalBottomSheet<int>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        final limits = [15, 30, 45, 60];
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  state.t('Screen Time', 'Masa Skrin'),
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 6),
                Text(
                  state.t(
                    'Choose a gentle daily practice target. The progress bar estimates time from completed quiz activity.',
                    'Pilih sasaran latihan harian yang ringan. Bar kemajuan menganggar masa daripada aktiviti kuiz lengkap.',
                  ),
                ),
                const SizedBox(height: 12),
                for (final minutes in limits)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const AppSvgIcon(
                      'screen_time',
                      color: Color(0xFFFFB532),
                      size: 22,
                    ),
                    title: Text(
                      state.t(
                        '$minutes minutes per day',
                        '$minutes minit sehari',
                      ),
                    ),
                    trailing: state.screenTimeLimitMinutes == minutes
                        ? const AppSvgIcon(
                            'check',
                            color: LogicOasisDesign.leaf,
                            size: 22,
                          )
                        : null,
                    onTap: () => Navigator.of(context).pop(minutes),
                  ),
              ],
            ),
          ),
        );
      },
    );

    if (selected == null) return;
    state.updateScreenTimeLimit(selected);
    if (!context.mounted) return;
    _showMessage(
      context,
      state.t(
        'Screen time target set to $selected minutes.',
        'Sasaran masa skrin ditetapkan kepada $selected minit.',
      ),
    );
  }

  Future<void> _showPrivacySafetySheet(BuildContext context) async {
    final settingsContext = context;
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (sheetContext) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  state.t('Privacy & Safety', 'Privasi & Keselamatan'),
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 12),
                _SafetyTile(
                  icon: 'lock_outline',
                  title: state.t('Protected parent access', 'Akses ibu bapa dilindungi'),
                  body: state.t(
                    'Parent dashboard opens through a linked parent account and password gate.',
                    'Papan pemuka ibu bapa dibuka melalui akaun ibu bapa terpaut dan laluan kata laluan.',
                  ),
                ),
                _SafetyTile(
                  icon: 'cloud_sync',
                  title: state.t('Learning data', 'Data pembelajaran'),
                  body: state.t(
                    'Quiz attempts, mastery, oasis progress, and settings are saved locally and synced to Firebase when available.',
                    'Cubaan kuiz, penguasaan, kemajuan oasis dan tetapan disimpan setempat serta disegerakkan ke Firebase apabila tersedia.',
                  ),
                ),
                _SafetyTile(
                  icon: 'psychology_alt',
                  title: state.t('AI explanation', 'Penjelasan AI'),
                  body: state.t(
                    'FYP1 AI evidence is explainable and parent-facing: BKT mastery, weakness risk, confidence, and SHAP-style reasons.',
                    'Bukti AI FYP1 boleh diterangkan kepada ibu bapa: penguasaan BKT, risiko kelemahan, keyakinan dan sebab gaya SHAP.',
                  ),
                ),
                _SafetyTile(
                  icon: 'shield',
                  title: state.t('Child-safe scope', 'Skop selamat kanak-kanak'),
                  body: state.t(
                    'The app avoids open chat and keeps student-facing navigation limited to Home, Forge, and Settings.',
                    'Aplikasi mengelakkan sembang terbuka dan mengehadkan navigasi murid kepada Home, Forge dan Settings.',
                  ),
                ),
                const SizedBox(height: 10),
                FilledButton.icon(
                  onPressed: () {
                    Navigator.of(sheetContext).pop();
                    if (settingsContext.mounted) {
                      _openParentAccess(settingsContext);
                    }
                  },
                  icon: const AppSvgIcon(
                    'supervisor_account',
                    color: Colors.white,
                    size: 20,
                  ),
                  label: Text(state.t('Open parent access', 'Buka akses ibu bapa')),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _openParentAccess(BuildContext context) async {
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Parent access is protected'),
        content: const Text(
          'A supervisor-approved administrator must link a parent Firebase account to this student. '
          'Students cannot create, choose, or reactivate parent links in the app. '
          'The parent then signs in with their own Firebase account to view safe learning updates.',
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _showMessage(BuildContext context, String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }
}

class _SafetyTile extends StatelessWidget {
  const _SafetyTile({
    required this.icon,
    required this.title,
    required this.body,
  });

  final String icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AppSvgIcon(icon, color: LogicOasisDesign.forest, size: 22),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: theme.textTheme.titleMedium),
                const SizedBox(height: 3),
                Text(body),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _EyeProtectingStatusCard extends StatelessWidget {
  const _EyeProtectingStatusCard({required this.state});

  final AppState state;

  @override
  Widget build(BuildContext context) {
    final enabled = state.eyeComfortMode;
    final background = enabled
        ? const Color(0xFFFFE7AA)
        : const Color(0xFFF2F5FF);
    final borderColor = enabled
        ? const Color(0xFFD99A2B)
        : const Color(0xFFD8E0FF);
    final iconColor = enabled
        ? const Color(0xFF8A5A00)
        : const Color(0xFF6372A6);

    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 0, 14, 10),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: borderColor),
        ),
        child: Row(
          children: [
            AppSvgIcon(
              enabled ? 'visibility' : 'visibility_off',
              color: iconColor,
              size: 22,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                enabled
                    ? state.t(
                        'Warm low-glare palette is active.',
                        'Palet hangat kurang silau sedang aktif.',
                      )
                    : state.t(
                        'Default bright palette is active.',
                        'Palet cerah asal sedang aktif.',
                      ),
                style: const TextStyle(
                  color: LogicOasisDesign.ink,
                  fontSize: 12.5,
                  fontWeight: FontWeight.w800,
                  height: 1.18,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ParentDashboardCard extends StatelessWidget {
  const _ParentDashboardCard({
    required this.title,
    required this.summary,
    required this.restoration,
    required this.onTap,
  });

  final String title;
  final String summary;
  final String restoration;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: LogicOasisDesign.purple.withValues(alpha: .16),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.supervisor_account_rounded,
                      color: LogicOasisDesign.purple,
                      size: 24,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: LogicOasisDesign.ink,
                            fontSize: 15,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: 5),
                        Text(
                          summary,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: LogicOasisDesign.body,
                            fontSize: 12.5,
                            fontWeight: FontWeight.w700,
                            height: 1.18,
                          ),
                        ),
                        const SizedBox(height: 7),
                        Row(
                          children: [
                            const Icon(
                              Icons.eco_rounded,
                              color: LogicOasisDesign.leaf,
                              size: 14,
                            ),
                            const SizedBox(width: 4),
                            Expanded(
                              child: Text(
                                restoration,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  color: LogicOasisDesign.forest,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Icon(
                    Icons.chevron_right_rounded,
                    color: Color(0xFF8C7A61),
                    size: 24,
                  ),
                ],
              ),
            ),
          ),
        ),
        const Padding(
          padding: EdgeInsets.only(left: 62, right: 14),
          child: Divider(height: 1, color: Color(0xFFEDE3D0)),
        ),
      ],
    );
  }
}

class _FigmaProfileCard extends StatelessWidget {
  const _FigmaProfileCard({
    required this.name,
    required this.level,
    required this.email,
    required this.crystals,
    required this.energy,
    required this.streak,
    required this.onTap,
  });

  final String name;
  final String level;
  final String email;
  final int crystals;
  final int energy;
  final int streak;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SoftCard(
      onTap: onTap,
      color: const Color(0xFFE6F5E4),
      radius: 22,
      padding: const EdgeInsets.all(14),
      child: Column(
        children: [
          Row(
            children: [
              const SproutAvatar(size: 68),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: LogicOasisDesign.forest,
                        fontSize: 18,
                        fontWeight: FontWeight.w900,
                        height: 1.05,
                      ),
                    ),
                    const SizedBox(height: 7),
                    Text(
                      level,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: LogicOasisDesign.ink,
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      email,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: LogicOasisDesign.body,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              const Icon(
                Icons.chevron_right_rounded,
                color: Color(0xFF806F59),
                size: 26,
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: StatCard(
                  compact: true,
                  icon: 'stat_crystal',
                  iconColor: const Color(0xFF36BFE2),
                  value: '$crystals',
                  label: 'Crystals',
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: StatCard(
                  compact: true,
                  icon: 'stat_energy',
                  iconColor: const Color(0xFFFFB92E),
                  value: '$energy',
                  label: 'Energy',
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: StatCard(
                  compact: true,
                  icon: 'stat_streak',
                  iconColor: const Color(0xFFFF6B4A),
                  value: '$streak',
                  label: 'Day Streak',
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SettingsSection extends StatelessWidget {
  const _SettingsSection({required this.title, required this.children});

  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.eco_rounded, color: LogicOasisDesign.leaf, size: 15),
            const SizedBox(width: 5),
            Text(
              title,
              style: const TextStyle(
                color: Color(0xFF74664E),
                fontSize: 13,
                fontWeight: FontWeight.w900,
                letterSpacing: .2,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        SoftCard(
          padding: EdgeInsets.zero,
          radius: 18,
          child: Column(children: children),
        ),
      ],
    );
  }
}

class _LogoutButton extends StatelessWidget {
  const _LogoutButton({required this.title, required this.onTap});

  final String title;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return FigmaCard(
      onTap: onTap,
      color: const Color(0xFFFFF8EC),
      radius: 16,
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 17),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.logout_rounded, color: Color(0xFFB72B27), size: 22),
          const SizedBox(width: 8),
          Text(
            title,
            style: const TextStyle(
              color: Color(0xFFB72B27),
              fontSize: 16,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}

class _StudentProfileSheet extends StatefulWidget {
  const _StudentProfileSheet({
    required this.state,
    required this.authRepository,
  });

  final AppState state;
  final AuthRepository authRepository;

  @override
  State<_StudentProfileSheet> createState() => _StudentProfileSheetState();
}

class _StudentProfileSheetState extends State<_StudentProfileSheet> {
  late final TextEditingController nameController;
  late final FocusNode nameFocusNode;
  late int selectedYear;
  bool isSaving = false;
  String? errorText;

  @override
  void initState() {
    super.initState();
    nameController = TextEditingController(text: widget.state.studentName);
    nameFocusNode = FocusNode();
    selectedYear = widget.state.yearLevel;
  }

  @override
  void dispose() {
    nameFocusNode.dispose();
    nameController.dispose();
    super.dispose();
  }

  Future<void> saveProfile() async {
    if (isSaving) return;

    final trimmedName = nameController.text.trim();
    if (trimmedName.isEmpty) {
      setState(() {
        errorText = AppLocalizations.of(context)!.enterStudentName;
      });
      return;
    }

    nameFocusNode.unfocus();
    setState(() {
      isSaving = true;
      errorText = null;
    });

    try {
      await widget.authRepository.updateStudentProfile(
        uid: widget.state.currentStudentId,
        email: widget.state.currentStudentEmail,
        displayName: trimmedName,
        yearLevel: selectedYear,
      );
      widget.state.updateStudentProfile(name: trimmedName, year: selectedYear);
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on AuthFailure catch (error) {
      if (!mounted) return;
      setState(() {
        errorText = error.message;
        isSaving = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        errorText = AppLocalizations.of(context)!.updateStudentProfileFailed;
        isSaving = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          20,
          4,
          20,
          MediaQuery.of(context).viewInsets.bottom + 24,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.editStudentProfile, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 16),
            TextField(
              controller: nameController,
              focusNode: nameFocusNode,
              enabled: !isSaving,
              onTapOutside: (_) => nameFocusNode.unfocus(),
              decoration: InputDecoration(
                labelText: l10n.studentName,
                prefixIcon: const Icon(Icons.person_outline_rounded),
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 14),
            SegmentedButton<int>(
              segments: [
                ButtonSegment(value: 4, label: Text(l10n.year4)),
                ButtonSegment(value: 5, label: Text(l10n.year5)),
                ButtonSegment(value: 6, label: Text(l10n.year6)),
              ],
              selected: {selectedYear},
              showSelectedIcon: false,
              onSelectionChanged: (selection) {
                if (isSaving) return;
                setState(() {
                  selectedYear = selection.first;
                });
              },
            ),
            if (errorText != null) ...[
              const SizedBox(height: 12),
              Text(
                errorText!,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.error,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: isSaving ? null : saveProfile,
              icon: isSaving
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2.2),
                    )
                  : const Icon(Icons.save_outlined),
              label: Text(isSaving ? l10n.saving : l10n.saveProfile),
            ),
          ],
        ),
      ),
    );
  }
}
