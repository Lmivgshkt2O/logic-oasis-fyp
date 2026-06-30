import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_page.dart';
import 'package:logic_oasis/features/settings/parent_password_reset_page.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/repositories/auth_repository.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

class ParentAuthPage extends StatefulWidget {
  const ParentAuthPage({
    super.key,
    required this.state,
    required this.parentAccount,
    this.authRepository,
  });

  final AppState state;
  final LinkedParentAccount parentAccount;
  final AuthRepository? authRepository;

  @override
  State<ParentAuthPage> createState() => _ParentAuthPageState();
}

class _ParentAuthPageState extends State<ParentAuthPage> {
  final passwordController = TextEditingController();
  late final AuthRepository authRepository;
  bool obscurePassword = true;
  bool isLoading = false;
  String? errorText;

  @override
  void initState() {
    super.initState();
    authRepository = widget.authRepository ?? AuthRepository();
  }

  @override
  void dispose() {
    passwordController.dispose();
    super.dispose();
  }

  Future<void> authenticate() async {
    if (isLoading) return;

    final l10n = AppLocalizations.of(context)!;
    final password = passwordController.text.trim();
    if (password.isEmpty) {
      setState(() {
        errorText = l10n.enterLinkedParentPassword;
      });
      return;
    }

    setState(() {
      isLoading = true;
      errorText = null;
    });

    try {
      await authRepository.authenticateLinkedParent(
        parent: widget.parentAccount,
        password: password,
      );
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (routeContext) => Scaffold(
            appBar: AppBar(
              title: Text(
                AppLocalizations.of(routeContext)!.parentDashboard,
              ),
            ),
            body: SafeArea(child: ParentDashboardPage(state: widget.state)),
          ),
        ),
      );
    } on AuthFailure catch (error) {
      if (!mounted) return;
      setState(() {
        errorText = error.message;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        errorText = l10n.parentAccountUnavailable;
      });
    } finally {
      if (mounted) {
        setState(() {
          isLoading = false;
        });
      }
    }
  }

  Future<void> openResetPassword() async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ParentPasswordResetPage(
          parentAccount: widget.parentAccount,
          authRepository: authRepository,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.parentAuthentication),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
          children: [
            Container(
              width: 70,
              height: 70,
              decoration: BoxDecoration(
                color: LogicOasisTheme.mint,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: LogicOasisTheme.line),
              ),
              child: const Icon(
                Icons.verified_user_outlined,
                color: LogicOasisTheme.leaf,
                size: 34,
              ),
            ),
            const SizedBox(height: 20),
            Text(
              l10n.parentAccessRequired,
              style: theme.textTheme.headlineLarge,
            ),
            const SizedBox(height: 8),
            Text(
              l10n.parentAuthInstruction,
              style: theme.textTheme.bodyLarge,
            ),
            const SizedBox(height: 18),
            _LinkedEmailBox(email: widget.parentAccount.email, state: widget.state),
            const SizedBox(height: 18),
            TextField(
              controller: passwordController,
              obscureText: obscurePassword,
              decoration: InputDecoration(
                labelText: l10n.parentPassword,
                prefixIcon: const Icon(Icons.lock_outline),
                suffixIcon: IconButton(
                  tooltip: obscurePassword
                      ? l10n.showPassword
                      : l10n.hidePassword,
                  onPressed: () {
                    setState(() {
                      obscurePassword = !obscurePassword;
                    });
                  },
                  icon: Icon(
                    obscurePassword
                        ? Icons.visibility_outlined
                        : Icons.visibility_off_outlined,
                  ),
                ),
                border: const OutlineInputBorder(),
              ),
              onSubmitted: (_) => authenticate(),
            ),
            if (errorText != null) ...[
              const SizedBox(height: 12),
              Text(
                errorText!,
                style: const TextStyle(
                  color: Color(0xFFB3261E),
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: isLoading ? null : openResetPassword,
                icon: const Icon(Icons.help_outline),
                label: Text(l10n.forgotPassword),
              ),
            ),
            const SizedBox(height: 8),
            FilledButton.icon(
              onPressed: isLoading ? null : authenticate,
              icon: isLoading
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2.2),
                    )
                  : const Icon(Icons.lock_open_outlined),
              label: Text(
                isLoading
                    ? l10n.checkingPassword
                    : l10n.unlockDashboard,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LinkedEmailBox extends StatelessWidget {
  const _LinkedEmailBox({required this.email, required this.state});

  final String email;
  final AppState state;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: const Color(0xFFE8F4EE),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFCFE3D7)),
      ),
      child: Row(
        children: [
          const Icon(Icons.mail_outline, color: LogicOasisTheme.leaf),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  AppLocalizations.of(context)!.linkedParentEmail,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 2),
                Text(
                  email,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFF315C48),
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
