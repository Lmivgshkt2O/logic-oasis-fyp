import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/shared/repositories/auth_repository.dart';
import 'package:logic_oasis/shared/widgets/recommendation_box.dart';

class RegisterPage extends StatefulWidget {
  const RegisterPage({super.key, this.authRepository});

  final AuthRepository? authRepository;

  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final formKey = GlobalKey<FormState>();
  final nameController = TextEditingController();
  final emailController = TextEditingController();
  final passwordController = TextEditingController();
  int selectedYear = 4;
  bool rememberProfile = true;
  bool obscurePassword = true;
  bool isLoading = false;
  String? errorText;

  @override
  void dispose() {
    nameController.dispose();
    emailController.dispose();
    passwordController.dispose();
    super.dispose();
  }

  Future<void> register() async {
    if (isLoading || formKey.currentState?.validate() != true) return;

    setState(() {
      isLoading = true;
      errorText = null;
    });

    final authRepository = widget.authRepository ?? AuthRepository();
    try {
      await authRepository.registerStudent(
        displayName: nameController.text.trim(),
        yearLevel: selectedYear,
        email: emailController.text.trim(),
        password: passwordController.text,
        rememberProfile: rememberProfile,
      );
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (context) {
          return AlertDialog(
            title: const Text('Successfully created account'),
            content: const Text('Please log in with your new student account.'),
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
      appBar: AppBar(title: const Text('Create student profile')),
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
                width: 68,
                height: 68,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: LogicOasisTheme.mint,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: LogicOasisTheme.line),
                ),
                child: const Icon(
                  Icons.person_add_alt_1_outlined,
                  color: LogicOasisTheme.leaf,
                  size: 34,
                ),
              ),
              const SizedBox(height: 20),
              Text('New student account', style: theme.textTheme.headlineLarge),
              const SizedBox(height: 8),
              Text(
                'Create a safe profile before restoring the oasis.',
                style: theme.textTheme.bodyLarge,
              ),
              const SizedBox(height: 22),
              TextFormField(
                controller: nameController,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(
                  labelText: 'Student name',
                  prefixIcon: Icon(Icons.badge_outlined),
                  border: OutlineInputBorder(),
                ),
                validator: (value) {
                  if (value == null || value.trim().length < 2) {
                    return 'Enter the student name.';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: emailController,
                keyboardType: TextInputType.emailAddress,
                textInputAction: TextInputAction.next,
                decoration: const InputDecoration(
                  labelText: 'Email',
                  prefixIcon: Icon(Icons.mail_outline),
                  border: OutlineInputBorder(),
                ),
                validator: _emailValidator,
              ),
              const SizedBox(height: 14),
              TextFormField(
                controller: passwordController,
                obscureText: obscurePassword,
                decoration: InputDecoration(
                  labelText: 'Password',
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
                validator: (value) {
                  if (value == null || value.length < 6) {
                    return 'Use at least 6 characters.';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 16),
              Text('Year level', style: theme.textTheme.titleMedium),
              const SizedBox(height: 8),
              SegmentedButton<int>(
                segments: const [
                  ButtonSegment(value: 4, label: Text('Year 4')),
                  ButtonSegment(value: 5, label: Text('Year 5')),
                  ButtonSegment(value: 6, label: Text('Year 6')),
                ],
                selected: {selectedYear},
                onSelectionChanged: (selection) {
                  setState(() {
                    selectedYear = selection.first;
                  });
                },
              ),
              const SizedBox(height: 10),
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: rememberProfile,
                onChanged: (value) {
                  setState(() {
                    rememberProfile = value ?? true;
                  });
                },
                title: const Text('Remember this student profile'),
                subtitle: const Text(
                  'Stores profile/email only, not password.',
                ),
                controlAffinity: ListTileControlAffinity.leading,
              ),
              if (errorText != null) ...[
                const SizedBox(height: 10),
                _ErrorBox(message: errorText!),
              ],
              const SizedBox(height: 14),
              FilledButton.icon(
                onPressed: isLoading ? null : register,
                icon: isLoading
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2.2),
                      )
                    : const Icon(Icons.check_circle_outline),
                label: Text(
                  isLoading ? 'Creating profile...' : 'Create Profile',
                ),
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                onPressed: isLoading ? null : () => Navigator.of(context).pop(),
                icon: const Icon(Icons.arrow_back),
                label: const Text('Back to Login'),
              ),
              const SizedBox(height: 16),
              const RecommendationBox(
                text:
                    'For safety, the password is handled by Firebase Auth and is not stored inside Firestore.',
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
      return 'Enter a valid email address.';
    }
    return null;
  }
}

class _ErrorBox extends StatelessWidget {
  const _ErrorBox({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFFEDEA),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE2A39B)),
        boxShadow: LogicOasisDesign.softShadow,
      ),
      child: Text(
        message,
        style: const TextStyle(
          color: Color(0xFF9A2F24),
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}
