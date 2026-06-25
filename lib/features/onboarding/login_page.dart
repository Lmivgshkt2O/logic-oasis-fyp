import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/shared/widgets/recommendation_box.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key, required this.onLogin});

  final ValueChanged<bool> onLogin;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final emailController = TextEditingController(text: 'student@test.com');
  final passwordController = TextEditingController(text: 'password123');
  bool rememberMe = true;
  bool obscurePassword = true;

  @override
  void dispose() {
    emailController.dispose();
    passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      body: SafeArea(
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
            Text('Welcome back', style: theme.textTheme.headlineLarge),
            const SizedBox(height: 8),
            Text(
              'Sign in to continue restoring your learning oasis.',
              style: theme.textTheme.bodyLarge,
            ),
            const SizedBox(height: 24),
            TextField(
              controller: emailController,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(
                labelText: 'Email',
                prefixIcon: Icon(Icons.mail_outline),
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: passwordController,
              obscureText: obscurePassword,
              decoration: InputDecoration(
                labelText: 'Password',
                prefixIcon: const Icon(Icons.lock_outline),
                suffixIcon: IconButton(
                  tooltip: obscurePassword ? 'Show password' : 'Hide password',
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
              controlAffinity: ListTileControlAffinity.leading,
            ),
            const SizedBox(height: 8),
            FilledButton.icon(
              onPressed: () => widget.onLogin(false),
              icon: const Icon(Icons.login),
              label: const Text('Continue as Student'),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: () => widget.onLogin(true),
              icon: const Icon(Icons.person_add_alt_1_outlined),
              label: const Text('Create new student profile'),
            ),
            const SizedBox(height: 18),
            const RecommendationBox(
              text:
                  'Parent Dashboard is available later inside Setting with password or OTP access.',
            ),
          ],
        ),
      ),
    );
  }
}
