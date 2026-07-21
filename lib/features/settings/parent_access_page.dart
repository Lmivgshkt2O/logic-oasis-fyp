import 'package:flutter/material.dart';
import 'package:logic_oasis/features/parent_dashboard/parent_dashboard_page.dart';
import 'package:logic_oasis/shared/repositories/auth_repository.dart';
import 'package:logic_oasis/shared/state/app_state.dart';

abstract class ParentAuthenticationGateway {
  Future<void> signIn({required String email, required String password});

  Future<void> signOut();
}

class FirebaseParentAuthenticationGateway
    implements ParentAuthenticationGateway {
  FirebaseParentAuthenticationGateway({AuthRepository? authRepository})
    : _authRepository = authRepository ?? AuthRepository();

  final AuthRepository _authRepository;

  @override
  Future<void> signIn({required String email, required String password}) {
    return _authRepository.signInParent(email: email, password: password);
  }

  @override
  Future<void> signOut() => _authRepository.signOutStudent();
}

/// A separate Firebase-authenticated parent session. Account provisioning and
/// the parent-child link remain supervisor-approved server operations.
class ParentAccessPage extends StatefulWidget {
  const ParentAccessPage({
    super.key,
    required this.state,
    required this.onReturnToStudentLogin,
    this.authGateway,
    this.dashboardBuilder,
  });

  final AppState state;
  final VoidCallback onReturnToStudentLogin;
  final ParentAuthenticationGateway? authGateway;
  final Widget Function(AppState state)? dashboardBuilder;

  @override
  State<ParentAccessPage> createState() => _ParentAccessPageState();
}

class _ParentAccessPageState extends State<ParentAccessPage> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  late final ParentAuthenticationGateway _authGateway;
  bool _isSigningIn = false;
  bool _parentSessionActive = false;
  bool _obscurePassword = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _authGateway = widget.authGateway ?? FirebaseParentAuthenticationGateway();
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _signIn() async {
    if (_isSigningIn || _formKey.currentState?.validate() != true) return;
    setState(() {
      _isSigningIn = true;
      _error = null;
    });
    var parentSessionStarted = false;
    var parentSessionCleared = false;
    try {
      await _authGateway.signIn(
        email: _emailController.text,
        password: _passwordController.text,
      );
      parentSessionStarted = true;
      _parentSessionActive = true;
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (context) => Scaffold(
            appBar: AppBar(title: const Text('Parent Dashboard')),
            body: SafeArea(
              child:
                  widget.dashboardBuilder?.call(widget.state) ??
                  ParentDashboardPage(state: widget.state),
            ),
          ),
        ),
      );
    } on AuthFailure catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = 'Unable to open secure parent access. Please retry.',
        );
      }
    } finally {
      if (parentSessionStarted) {
        try {
          await _authGateway.signOut();
          parentSessionCleared = true;
          _parentSessionActive = false;
        } on AuthFailure catch (error) {
          if (mounted) setState(() => _error = error.message);
        } catch (_) {
          if (mounted) {
            setState(
              () => _error = 'Unable to securely close the parent session.',
            );
          }
        }
      }
      if (parentSessionCleared && mounted) {
        widget.onReturnToStudentLogin();
      }
      if (mounted) setState(() => _isSigningIn = false);
    }
  }

  Future<void> _retrySecureSignOut() async {
    if (_isSigningIn || !_parentSessionActive) return;
    setState(() {
      _isSigningIn = true;
      _error = null;
    });
    try {
      await _authGateway.signOut();
      _parentSessionActive = false;
      if (mounted) widget.onReturnToStudentLogin();
    } on AuthFailure catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Unable to securely close the parent session.');
      }
    } finally {
      if (mounted) setState(() => _isSigningIn = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: !_parentSessionActive,
      child: Scaffold(
        appBar: AppBar(title: const Text('Parent sign in')),
        body: SafeArea(
          child: Form(
            key: _formKey,
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Text(
                  'Private parent access',
                  style: Theme.of(context).textTheme.headlineLarge,
                ),
                const SizedBox(height: 10),
                const Text(
                  'Sign in with the parent Firebase account linked to this learner. Only safe learning updates for active, approved links are shown.',
                ),
                const SizedBox(height: 20),
                TextFormField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(
                    labelText: 'Parent email',
                    prefixIcon: Icon(Icons.mail_outline),
                  ),
                  validator: (value) => value != null && value.contains('@')
                      ? null
                      : 'Enter the parent email address.',
                ),
                const SizedBox(height: 14),
                TextFormField(
                  controller: _passwordController,
                  obscureText: _obscurePassword,
                  decoration: InputDecoration(
                    labelText: 'Password',
                    prefixIcon: const Icon(Icons.lock_outline),
                    suffixIcon: IconButton(
                      onPressed: () =>
                          setState(() => _obscurePassword = !_obscurePassword),
                      icon: Icon(
                        _obscurePassword
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
                      ),
                    ),
                  ),
                  validator: (value) => value != null && value.isNotEmpty
                      ? null
                      : 'Enter the parent password.',
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!, style: const TextStyle(color: Colors.red)),
                ],
                if (_parentSessionActive) ...[
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: _isSigningIn ? null : _retrySecureSignOut,
                    icon: const Icon(Icons.logout),
                    label: const Text('Retry secure sign out'),
                  ),
                ],
                const SizedBox(height: 20),
                FilledButton.icon(
                  onPressed: _isSigningIn ? null : _signIn,
                  icon: _isSigningIn
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.verified_user_outlined),
                  label: Text(
                    _isSigningIn ? 'Signing in…' : 'Secure parent sign in',
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  'New parent accounts and links are not created from a student device. Please contact your school or supervisor to provision an approved account and link.',
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
