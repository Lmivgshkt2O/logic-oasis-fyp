import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_design.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/onboarding/register_page.dart';
import 'package:logic_oasis/shared/repositories/auth_repository.dart';
import 'package:logic_oasis/shared/widgets/recommendation_box.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key, required this.onLogin, this.authRepository});

  final ValueChanged<StudentAuthProfile> onLogin;
  final AuthRepository? authRepository;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final formKey = GlobalKey<FormState>();
  final emailController = TextEditingController();
  final passwordController = TextEditingController();
  late final AuthRepository authRepository;
  bool rememberMe = true;
  bool obscurePassword = true;
  _LoginAction? activeLoginAction;
  String? errorText;
  String? rememberedProfileText;

  bool get isLoading => activeLoginAction != null;

  @override
  void initState() {
    super.initState();
    authRepository = widget.authRepository ?? AuthRepository();
    loadRememberedProfile();
  }

  @override
  void dispose() {
    emailController.dispose();
    passwordController.dispose();
    super.dispose();
  }

  Future<void> loadRememberedProfile() async {
    RememberedStudentProfile? rememberedProfile;
    try {
      rememberedProfile = await authRepository.loadRememberedStudentProfile();
    } catch (_) {
      return;
    }
    if (!mounted || rememberedProfile == null) return;
    final profile = rememberedProfile;

    setState(() {
      emailController.text = profile.email;
      rememberedProfileText = profile.displayName == null
          ? 'Remembered student email loaded.'
          : 'Student profile loaded for ${profile.displayName}.';
    });
  }

  Future<void> signIn() async {
    if (isLoading || formKey.currentState?.validate() != true) return;

    setState(() {
      activeLoginAction = _LoginAction.password;
      errorText = null;
    });

    try {
      final profile = await authRepository.signInStudent(
        email: emailController.text.trim(),
        password: passwordController.text,
        rememberProfile: rememberMe,
      );
      if (!mounted) return;
      widget.onLogin(profile);
    } on AuthFailure catch (error) {
      setState(() {
        errorText = error.message;
      });
    } finally {
      if (mounted) {
        setState(() {
          activeLoginAction = null;
        });
      }
    }
  }

  Future<void> signInWithGoogle() async {
    if (isLoading) return;

    setState(() {
      activeLoginAction = _LoginAction.google;
      errorText = null;
    });

    try {
      final profile = await authRepository.signInStudentWithGoogle(
        rememberProfile: rememberMe,
      );
      if (!mounted) return;
      widget.onLogin(profile);
    } on AuthFailure catch (error) {
      setState(() {
        errorText = error.message;
      });
    } finally {
      if (mounted) {
        setState(() {
          activeLoginAction = null;
        });
      }
    }
  }

  Future<void> openRegisterPage() async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => RegisterPage(authRepository: authRepository),
      ),
    );
  }

  void showProviderSetup(String provider) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(
            '$provider sign-in needs Firebase provider setup before use.',
          ),
        ),
      );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
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
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
            children: [
              Align(
                alignment: Alignment.centerLeft,
                child: Container(
                  width: 62,
                  height: 62,
                  decoration: BoxDecoration(
                    color: LogicOasisTheme.mint,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: LogicOasisTheme.line),
                  ),
                  child: const Icon(Icons.spa, color: LogicOasisTheme.leaf),
                ),
              ),
              const SizedBox(height: 24),
              Text('Log in', style: theme.textTheme.headlineLarge),
              const SizedBox(height: 8),
              Text(
                'Sign in to continue restoring your learning oasis.',
                style: theme.textTheme.bodyLarge,
              ),
              if (rememberedProfileText != null) ...[
                const SizedBox(height: 12),
                _InfoBox(message: rememberedProfileText!),
              ],
              const SizedBox(height: 22),
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
                  if (value == null || value.isEmpty) {
                    return 'Enter your password.';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 10),
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: rememberMe,
                onChanged: (value) {
                  setState(() {
                    rememberMe = value ?? true;
                  });
                },
                title: const Text('Remember this student profile'),
                subtitle: const Text(
                  'Profile/email only. Password stays secure.',
                ),
                controlAffinity: ListTileControlAffinity.leading,
              ),
              if (errorText != null) ...[
                const SizedBox(height: 8),
                _ErrorBox(message: errorText!),
              ],
              const SizedBox(height: 10),
              FilledButton.icon(
                onPressed: isLoading ? null : signIn,
                icon: activeLoginAction == _LoginAction.password
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2.2),
                      )
                    : const Icon(Icons.login),
                label: Text(
                  activeLoginAction == _LoginAction.password
                      ? 'Checking account...'
                      : 'Log In',
                ),
              ),
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: isLoading ? null : openRegisterPage,
                icon: const Icon(Icons.person_add_alt_1_outlined),
                label: const Text('Create new student profile'),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: isLoading ? null : signInWithGoogle,
                      icon: activeLoginAction == _LoginAction.google
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.2,
                              ),
                            )
                          : const Icon(Icons.g_mobiledata),
                      label: const Text('Google'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: isLoading ? null : () => showProviderSetup('Facebook'),
                      icon: const Icon(Icons.facebook),
                      label: const Text('Facebook'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              const RecommendationBox(
                text:
                    'Parent Dashboard is available later inside Setting with password or OTP access.',
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

enum _LoginAction { password, google }

class _InfoBox extends StatelessWidget {
  const _InfoBox({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: LogicOasisDesign.mintLight,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFCFE3D7)),
        boxShadow: LogicOasisDesign.softShadow,
      ),
      child: Text(
        message,
        style: const TextStyle(
          color: Color(0xFF315C48),
          fontWeight: FontWeight.w800,
        ),
      ),
    );
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
