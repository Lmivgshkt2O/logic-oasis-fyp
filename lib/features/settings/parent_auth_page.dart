import 'package:flutter/material.dart';
import 'package:logic_oasis/app/theme.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_page.dart';
import 'package:logic_oasis/shared/state/app_state.dart';
import 'package:logic_oasis/shared/widgets/recommendation_box.dart';

class ParentAuthPage extends StatefulWidget {
  const ParentAuthPage({super.key, required this.state});

  final AppState state;

  @override
  State<ParentAuthPage> createState() => _ParentAuthPageState();
}

class _ParentAuthPageState extends State<ParentAuthPage> {
  final passwordController = TextEditingController();
  final otpController = TextEditingController();
  bool obscurePassword = true;
  String? errorText;

  @override
  void dispose() {
    passwordController.dispose();
    otpController.dispose();
    super.dispose();
  }

  void authenticate() {
    final password = passwordController.text.trim();
    final otp = otpController.text.trim();
    final validPassword = password == 'parent123';
    final validOtp = otp == '246810';

    if (!validPassword && !validOtp) {
      setState(() {
        errorText = 'Enter the demo parent password or OTP to continue.';
      });
      return;
    }

    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (_) => Scaffold(
          appBar: AppBar(title: const Text('Parent Dashboard')),
          body: SafeArea(child: ParentDashboardPage(state: widget.state)),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Parent Authentication')),
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
              'Parent access required',
              style: theme.textTheme.headlineLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'This dashboard contains learning insights and recommendations for parents.',
              style: theme.textTheme.bodyLarge,
            ),
            const SizedBox(height: 22),
            TextField(
              controller: passwordController,
              obscureText: obscurePassword,
              decoration: InputDecoration(
                labelText: 'Parent password',
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
            const SizedBox(height: 14),
            TextField(
              controller: otpController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'One-time password',
                prefixIcon: Icon(Icons.pin_outlined),
                border: OutlineInputBorder(),
              ),
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
              onPressed: authenticate,
              icon: const Icon(Icons.lock_open_outlined),
              label: const Text('Unlock Dashboard'),
            ),
            const SizedBox(height: 16),
            const RecommendationBox(
              text:
                  'Prototype access: use password parent123 or OTP 246810. Firebase Auth or real OTP can replace this later.',
            ),
          ],
        ),
      ),
    );
  }
}
