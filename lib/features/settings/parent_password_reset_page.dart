import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/l10n/app_localizations.dart';
import 'package:logic_oasis/shared/repositories/auth_repository.dart';
import 'package:logic_oasis/shared/widgets/recommendation_box.dart';

class ParentPasswordResetPage extends StatefulWidget {
  const ParentPasswordResetPage({
    super.key,
    required this.parentAccount,
    this.authRepository,
  });

  final LinkedParentAccount parentAccount;
  final AuthRepository? authRepository;

  @override
  State<ParentPasswordResetPage> createState() =>
      _ParentPasswordResetPageState();
}

class _ParentPasswordResetPageState extends State<ParentPasswordResetPage> {
  final formKey = GlobalKey<FormState>();
  final otpController = TextEditingController();
  final passwordController = TextEditingController();
  final confirmPasswordController = TextEditingController();
  late final AuthRepository authRepository;
  bool obscurePassword = true;
  bool isSendingOtp = true;
  bool isSaving = false;
  String? errorText;

  @override
  void initState() {
    super.initState();
    authRepository = widget.authRepository ?? AuthRepository();
    sendOtp();
  }

  @override
  void dispose() {
    otpController.dispose();
    passwordController.dispose();
    confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> sendOtp() async {
    setState(() {
      isSendingOtp = true;
      errorText = null;
    });

    try {
      await authRepository.sendParentResetOtp(parent: widget.parentAccount);
    } catch (_) {
      if (!mounted) return;
      setState(() {
        errorText = 'Unable to send OTP. Please try again.';
      });
    } finally {
      if (mounted) {
        setState(() {
          isSendingOtp = false;
        });
      }
    }
  }

  Future<void> resetPassword() async {
    if (isSaving || formKey.currentState?.validate() != true) return;

    setState(() {
      isSaving = true;
      errorText = null;
    });

    try {
      await authRepository.resetLinkedParentPassword(
        parent: widget.parentAccount,
        otp: otpController.text,
        newPassword: passwordController.text,
      );
      if (!mounted) return;

      await showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (context) {
          return AlertDialog(
            title: const Text('Password successfully changes'),
            content: const Text(
              'Please log in again with the new parent password.',
            ),
            actions: [
              FilledButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('OK'),
              ),
            ],
          );
        },
      );

      if (!mounted) return;
      Navigator.of(context).pop();
    } on AuthFailure catch (error) {
      setState(() {
        errorText = error.message;
      });
    } catch (_) {
      setState(() {
        errorText = 'Unable to change parent password.';
      });
    } finally {
      if (mounted) {
        setState(() {
          isSaving = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Setting new password')),
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [LogicOasisDesign.page, LogicOasisDesign.pageWarm],
          ),
        ),
        child: SafeArea(
          child: Form(
            key: formKey,
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
                  Icons.lock_reset_outlined,
                  color: LogicOasisTheme.leaf,
                  size: 34,
                ),
              ),
              const SizedBox(height: 20),
              Text(
                'Setting new password',
                style: theme.textTheme.headlineLarge,
              ),
              const SizedBox(height: 8),
              Text(
                'Enter the OTP received by ${widget.parentAccount.email}, then set a new password.',
                style: theme.textTheme.bodyLarge,
              ),
              const SizedBox(height: 18),
              TextFormField(
                controller: otpController,
                keyboardType: TextInputType.number,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(
                  labelText: 'OTP',
                  prefixIcon: Icon(Icons.pin_outlined),
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.trim().length < 4) {
                    return 'Enter the OTP received.';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: passwordController,
                obscureText: obscurePassword,
                textInputAction: TextInputAction.next,
                decoration: InputDecoration(
                  labelText: 'New password',
                  prefixIcon: const Icon(Icons.lock_outline),
                  suffixIcon: IconButton(
                    tooltip: obscurePassword
                        ? 'Show password'
                        : 'Hide password',
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
                validator: _passwordValidator,
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: confirmPasswordController,
                obscureText: obscurePassword,
                decoration: const InputDecoration(
                  labelText: 'Confirm new password',
                  prefixIcon: Icon(Icons.lock_reset_outlined),
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value != passwordController.text) {
                    return 'Passwords do not match.';
                  }
                  return null;
                },
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
              const SizedBox(height: 18),
              FilledButton.icon(
                onPressed: isSaving || isSendingOtp ? null : resetPassword,
                icon: isSaving
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2.2),
                      )
                    : const Icon(Icons.check_circle_outline),
                label: Text(
                  isSaving ? 'Changing password...' : 'Change Password',
                ),
              ),
              const SizedBox(height: 10),
              TextButton.icon(
                onPressed: isSaving || isSendingOtp ? null : sendOtp,
                icon: const Icon(Icons.refresh),
                label: Text(isSendingOtp ? 'Sending OTP...' : 'Resend OTP'),
              ),
              const SizedBox(height: 16),
              RecommendationBox(
                text: AppLocalizations.of(context)!.prototypeOtpNotice,
              ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String? _passwordValidator(String? value) {
    if (value == null || value.length < 6) {
      return 'Use at least 6 characters.';
    }
    return null;
  }
}
