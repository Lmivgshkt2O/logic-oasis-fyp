import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/settings/parent_auth_page.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key, required this.state, required this.onLogout});

  final AppState state;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

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
                    state.t('Settings', 'Tetapan'),
                    style: theme.textTheme.headlineLarge,
                  ),
                  const SizedBox(height: 5),
                  Text(
                    state.t(
                      'Manage your profile and preferences.',
                      'Urus profil dan tetapan aplikasi.',
                    ),
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
          title: state.t('Student Profile', 'Profil Murid'),
          subtitle: state.t(
            'View and edit your profile',
            'Lihat dan edit profil',
          ),
          onTap: () => _showProfileSheet(context),
        ),
        const SizedBox(height: 12),
        _SettingTile(
          icon: Icons.language,
          iconColor: LogicOasisTheme.water,
          title: state.t('Language', 'Bahasa'),
          trailingText: state.language,
          onTap: () => _showLanguageSheet(context),
        ),
        const SizedBox(height: 12),
        _SettingTile(
          icon: Icons.notifications,
          iconColor: const Color(0xFFEAB948),
          title: state.t('Mission Reminders', 'Peringatan Misi'),
          trailingText: state.missionReminders
              ? state.t('On', 'Aktif')
              : state.t('Off', 'Tidak aktif'),
          onTap: () => state.updateMissionReminders(!state.missionReminders),
        ),
        const SizedBox(height: 12),
        _SettingTile(
          icon: Icons.visibility,
          iconColor: LogicOasisTheme.leaf,
          title: state.t('Eye Comfort', 'Selesa Mata'),
          trailingText: state.eyeComfortMode
              ? state.t('On', 'Aktif')
              : state.t('Off', 'Tidak aktif'),
          onTap: () => state.updateEyeComfortMode(!state.eyeComfortMode),
        ),
        const SizedBox(height: 18),
        _ParentDashboardCard(state: state),
        const SizedBox(height: 12),
        _SettingTile(
          icon: Icons.logout,
          iconColor: const Color(0xFFC65D4B),
          title: state.t('Log out', 'Log keluar'),
          subtitle: state.t(
            'Return to the login page',
            'Kembali ke halaman log masuk',
          ),
          onTap: () => _confirmLogout(context),
        ),
      ],
    );
  }

  Future<void> _confirmLogout(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text(state.t('Confirm to log out?', 'Sahkan log keluar?')),
          content: Text(
            state.t(
              'You will return to the login page.',
              'Anda akan kembali ke halaman log masuk.',
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: Text(state.t('Cancel', 'Batal')),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: Text(state.t('Log out', 'Log keluar')),
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
    final nameController = TextEditingController(text: state.studentName);
    var selectedYear = state.yearLevel;
    var saved = false;

    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
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
                      state.t('Edit student profile', 'Edit profil murid'),
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: nameController,
                      decoration: InputDecoration(
                        labelText: state.t('Student name', 'Nama murid'),
                        prefixIcon: const Icon(Icons.person_outline),
                        border: const OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 14),
                    SegmentedButton<int>(
                      segments: [
                        ButtonSegment(
                          value: 4,
                          label: Text(state.t('Year 4', 'Tahun 4')),
                        ),
                        ButtonSegment(
                          value: 5,
                          label: Text(state.t('Year 5', 'Tahun 5')),
                        ),
                        ButtonSegment(
                          value: 6,
                          label: Text(state.t('Year 6', 'Tahun 6')),
                        ),
                      ],
                      selected: {selectedYear},
                      onSelectionChanged: (selection) {
                        setSheetState(() {
                          selectedYear = selection.first;
                        });
                      },
                    ),
                    const SizedBox(height: 18),
                    FilledButton.icon(
                      onPressed: () {
                        state.updateStudentProfile(
                          name: nameController.text,
                          year: selectedYear,
                        );
                        saved = true;
                        Navigator.of(context).pop();
                      },
                      icon: const Icon(Icons.save_outlined),
                      label: Text(state.t('Save Profile', 'Simpan Profil')),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );

    nameController.dispose();

    if (saved && settingsContext.mounted) {
      ScaffoldMessenger.of(settingsContext)
        ..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            content: Text(
              state.t('Student profile updated', 'Profil murid dikemas kini'),
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

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(
            state.t(
              'Language set to $selected',
              'Bahasa ditukar kepada $selected',
            ),
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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      color: const Color(0xFFFFF6E6),
      elevation: 0.8,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => ParentAuthPage(state: state)),
          );
        },
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
                                state.t(
                                  'Parent Dashboard',
                                  'Papan Pemuka Ibu Bapa',
                                ),
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
                                state.t('Locked', 'Dikunci'),
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
                          state.t(
                            'Unlock to view progress and weak topics',
                            'Buka untuk melihat kemajuan dan topik lemah',
                          ),
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
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => ParentAuthPage(state: state),
                      ),
                    );
                  },
                  child: Text(state.t('Unlock Access', 'Buka Akses')),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
