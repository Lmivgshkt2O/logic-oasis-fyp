import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/settings/parent_auth_page.dart';
import 'package:logic_oasis/features/settings/parent_link_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/repositories/auth_repository.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

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
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 18),
      children: [
        Row(
          children: [
            const _HeaderIcon(
              icon: Icons.settings,
              color: LogicOasisTheme.leaf,
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.settings,
                    style: theme.textTheme.headlineLarge,
                  ),
                  const SizedBox(height: 5),
                  Text(
                    l10n.manageProfilePreferences,
                    style: theme.textTheme.bodyLarge,
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 30),
        _SettingTile(
          icon: Icons.person,
          iconColor: LogicOasisTheme.leaf,
          title: l10n.studentProfile,
          subtitle: l10n.viewEditProfile,
          onTap: () => _showProfileSheet(context),
        ),
        const SizedBox(height: 12),
        _SettingTile(
          icon: Icons.language,
          iconColor: LogicOasisTheme.water,
          title: l10n.language,
          trailingText: state.language,
          onTap: () => _showLanguageSheet(context),
        ),
        const SizedBox(height: 12),
        _SettingTile(
          icon: Icons.notifications,
          iconColor: const Color(0xFFEAB948),
          title: l10n.missionReminders,
          trailingText: state.missionReminders ? l10n.on : l10n.off,
          onTap: () => state.updateMissionReminders(!state.missionReminders),
        ),
        const SizedBox(height: 12),
        _SettingTile(
          icon: Icons.visibility,
          iconColor: LogicOasisTheme.leaf,
          title: l10n.eyeComfort,
          trailingText: state.eyeComfortMode ? l10n.on : l10n.off,
          onTap: () => state.updateEyeComfortMode(!state.eyeComfortMode),
        ),
        const SizedBox(height: 18),
        _ParentDashboardCard(state: state),
        const SizedBox(height: 12),
        _SettingTile(
          icon: Icons.logout,
          iconColor: const Color(0xFFC65D4B),
          title: l10n.logout,
          subtitle: l10n.returnLogin,
          onTap: () => _confirmLogout(context),
        ),
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

    if (saved == true && settingsContext.mounted) {
      final l10n = AppLocalizations.of(settingsContext)!;
      ScaffoldMessenger.of(settingsContext)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            content: Text(
              l10n.studentProfileUpdated,
            ),
          ),
        );
    }
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
                  leading: const Icon(Icons.language),
                  title: const Text('English'),
                  trailing: state.language == 'English'
                      ? const Icon(Icons.check)
                      : null,
                  onTap: () => Navigator.of(context).pop('English'),
                ),
                ListTile(
                  leading: const Icon(Icons.translate),
                  title: const Text('Bahasa Melayu'),
                  trailing: state.language == 'Bahasa Melayu'
                      ? const Icon(Icons.check)
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
    final l10n = AppLocalizations.of(context)!;

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(
            l10n.languageSet(selected),
          ),
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
      final l10n = AppLocalizations.of(context)!;
      setState(() {
        errorText = l10n.enterStudentName;
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
            Text(
              l10n.editStudentProfile,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: nameController,
              focusNode: nameFocusNode,
              enabled: !isSaving,
              onTapOutside: (_) => nameFocusNode.unfocus(),
              decoration: InputDecoration(
                labelText: l10n.studentName,
                prefixIcon: const Icon(Icons.person_outline),
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 14),
            SegmentedButton<int>(
              segments: [
                ButtonSegment(
                  value: 4,
                  label: Text(l10n.year4),
                ),
                ButtonSegment(
                  value: 5,
                  label: Text(l10n.year5),
                ),
                ButtonSegment(
                  value: 6,
                  label: Text(l10n.year6),
                ),
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
              label: Text(
                isSaving
                    ? l10n.saving
                    : l10n.saveProfile,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HeaderIcon extends StatelessWidget {
  const _HeaderIcon({required this.icon, required this.color});

  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 68,
      height: 68,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.13),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Icon(icon, color: color, size: 36),
    );
  }
}

class _SettingTile extends StatelessWidget {
  const _SettingTile({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.onTap,
    this.subtitle,
    this.trailingText,
  });

  final IconData icon;
  final Color iconColor;
  final String title;
  final String? subtitle;
  final String? trailingText;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 14, 12, 14),
          child: Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: iconColor.withValues(alpha: 0.13),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(icon, color: iconColor, size: 29),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      title,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontSize: 16,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (subtitle != null) ...[
                      const SizedBox(height: 3),
                      Text(
                        subtitle!,
                        style: theme.textTheme.bodyMedium,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ],
                ),
              ),
              if (trailingText != null) ...[
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 86),
                  child: Text(
                    trailingText!,
                    style: theme.textTheme.bodyLarge?.copyWith(
                      color: LogicOasisTheme.ink,
                      fontSize: 15.5,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.right,
                  ),
                ),
                const SizedBox(width: 8),
              ],
              const Icon(
                Icons.chevron_right,
                color: Color(0xFF6D7470),
                size: 22,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ParentDashboardCard extends StatelessWidget {
  const _ParentDashboardCard({required this.state});

  final AppState state;

  Future<void> _openParentAccess(BuildContext context) async {
    final navigator = Navigator.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final authRepository = AuthRepository();

    try {
      final parentAccount = await authRepository.fetchLinkedParentAccount(
        studentId: state.currentStudentId,
      );

      if (!context.mounted) return;

      if (parentAccount == null) {
        final shouldRegister = await showDialog<bool>(
          context: context,
          builder: (context) {
            return AlertDialog(
              title: const Text('Parent account not linked'),
              content: const Text(
                "You don't have linked parent account, do you want to register a new account?",
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(false),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: () => Navigator.of(context).pop(true),
                  child: const Text('OK'),
                ),
              ],
            );
          },
        );

        if (shouldRegister != true || !context.mounted) return;
        navigator.push(
          MaterialPageRoute(
            builder: (_) =>
                ParentLinkPage(state: state, authRepository: authRepository),
          ),
        );
        return;
      }

      navigator.push(
        MaterialPageRoute(
          builder: (_) => ParentAuthPage(
            state: state,
            parentAccount: parentAccount,
            authRepository: authRepository,
          ),
        ),
      );
    } catch (_) {
      if (!context.mounted) return;
      messenger
        ..hideCurrentSnackBar()
        ..showSnackBar(
          const SnackBar(
            content: Text('Unable to check linked parent account.'),
          ),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return Card(
      color: const Color(0xFFFFF6E6),
      elevation: 0.8,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openParentAccess(context),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 17),
          child: Column(
            children: [
              Row(
                children: [
                  Container(
                    width: 62,
                    height: 62,
                    decoration: BoxDecoration(
                      color: const Color(0xFFF4C77E),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: const Icon(
                      Icons.lock,
                      color: Color(0xFF9B6119),
                      size: 30,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                l10n.parentDashboard,
                                style: theme.textTheme.titleLarge?.copyWith(
                                  fontSize: 18,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                                vertical: 6,
                              ),
                              decoration: BoxDecoration(
                                color: const Color(0xFFF7DDAF),
                                borderRadius: BorderRadius.circular(99),
                              ),
                              child: Text(
                                l10n.locked,
                                style: const TextStyle(
                                  color: Color(0xFF7B4B14),
                                  fontWeight: FontWeight.w800,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 7),
                        Text(
                          l10n.unlockProgressWeakTopics,
                          style: theme.textTheme.bodyMedium,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  style: FilledButton.styleFrom(
                    backgroundColor: const Color(0xFFF0BE70),
                    foregroundColor: const Color(0xFF6E410A),
                    minimumSize: const Size.fromHeight(44),
                  ),
                  onPressed: () => _openParentAccess(context),
                  child: Text(l10n.unlockAccess),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
