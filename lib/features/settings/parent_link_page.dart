import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
import 'package:logic_oasis/features/settings/parent_auth_page.dart';
import 'package:logic_oasis/shared/repositories/auth_repository.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/recommendation_box.dart';

class ParentLinkPage extends StatefulWidget {
  const ParentLinkPage({super.key, required this.state, this.authRepository});

  final AppState state;
  final AuthRepository? authRepository;

  @override
  State<ParentLinkPage> createState() => _ParentLinkPageState();
}

class _ParentLinkPageState extends State<ParentLinkPage> {
  final formKey = GlobalKey<FormState>();
  final emailController = TextEditingController();
  final passwordController = TextEditingController();
  final confirmPasswordController = TextEditingController();
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
    emailController.dispose();
    passwordController.dispose();
    confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> registerParent() async {
    if (isLoading || formKey.currentState?.validate() != true) return;

    setState(() {
      isLoading = true;
      errorText = null;
    });

    try {
      final parentAccount = await authRepository.registerLinkedParentAccount(
        studentId: widget.state.currentStudentId,
        email: emailController.text,
        password: passwordController.text,
      );
      if (!mounted) return;

      await showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (context) {
          return AlertDialog(
            title: const Text('Successfully created parent account'),
            content: const Text(
              'Please enter the parent password to unlock the dashboard.',
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
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => ParentAuthPage(
            state: widget.state,
            parentAccount: parentAccount,
            authRepository: authRepository,
          ),
        ),
      );
    } on AuthFailure catch (error) {
      setState(() {
        errorText = error.message;
      });
    } catch (_) {
      setState(() {
        errorText = 'Unable to create linked parent account.';
      });
    } finally {
      if (mounted) {
        setState(() {
          isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Link parent account')),
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
                  color: const Color(0xFFFFF6E6),
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(color: const Color(0xFFF1D7AA)),
                ),
                child: const Icon(
                  Icons.family_restroom_outlined,
                  color: Color(0xFF9B6119),
                  size: 34,
                ),
              ),
              const SizedBox(height: 20),
              Text(
                'Create parent account',
                style: theme.textTheme.headlineLarge,
              ),
              const SizedBox(height: 8),
              Text(
                'This parent account will be linked to ${widget.state.studentName}.',
                style: theme.textTheme.bodyLarge,
              ),
              const SizedBox(height: 22),
              TextFormField(
                controller: emailController,
                keyboardType: TextInputType.emailAddress,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(
                  labelText: 'Parent email',
                  prefixIcon: Icon(Icons.mail_outline),
                  border: OutlineInputBorder(),
                ),
                validator: _emailValidator,
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: passwordController,
                obscureText: obscurePassword,
                textInputAction: TextInputAction.next,
                decoration: InputDecoration(
                  labelText: 'Parent password',
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
                  labelText: 'Confirm password',
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
                onPressed: isLoading ? null : registerParent,
                icon: isLoading
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2.2),
                      )
                    : const Icon(Icons.link),
                label: Text(
                  isLoading ? 'Creating parent account...' : 'Create and Link',
                ),
              ),
              const SizedBox(height: 16),
              const RecommendationBox(
                text:
                    'Prototype safeguard: this password is only for the local FYP demo flow. Use Firebase Auth or server-side verification before real user testing.',
              ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String? _emailValidator(String? value) {
    final email = value?.trim() ?? '';
    if (email.isEmpty || !email.contains('@') || !email.contains('.')) {
      return 'Enter a valid parent email.';
    }
    return null;
  }

  String? _passwordValidator(String? value) {
    if (value == null || value.length < 6) {
      return 'Use at least 6 characters.';
    }
    return null;
  }
}
