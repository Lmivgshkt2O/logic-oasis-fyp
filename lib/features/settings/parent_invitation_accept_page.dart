import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:logic_oasis/shared/services/parent_link_invitation_service.dart';
import 'package:logic_oasis/shared/services/parent_firebase_session.dart';

/// Neutral parent-only confirmation surface reached after email-link sign-in.
/// The surrounding root/deep-link handler supplies opaque values; this page
/// never renders or persists them.
class ParentInvitationAcceptPage extends StatefulWidget {
  const ParentInvitationAcceptPage({
    super.key,
    required this.invitationId,
    required this.verifier,
    required this.emailLink,
    this.service,
    this.onAccepted,
    this.onDeclined,
  });

  final String invitationId;
  final String verifier;
  final String emailLink;
  final ParentLinkInvitationGateway? service;
  final VoidCallback? onAccepted;
  final VoidCallback? onDeclined;

  @override
  State<ParentInvitationAcceptPage> createState() =>
      _ParentInvitationAcceptPageState();
}

class _ParentInvitationAcceptPageState
    extends State<ParentInvitationAcceptPage> {
  late final ParentLinkInvitationGateway _service;
  final _emailController = TextEditingController();
  bool _working = false;
  bool _accepted = false;
  bool _obscurePassword = true;
  String? _error;
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _service = widget.service ?? ParentLinkInvitationService.parentSession();
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _complete({required bool accepted}) async {
    if (_working) return;
    setState(() {
      _working = true;
      _error = null;
    });
    try {
      final email = _emailController.text.trim();
      if (email.isEmpty || !email.contains('@')) {
        setState(
          () =>
              _error = 'Enter the email address that received the invitation.',
        );
        return;
      }
      final auth = await ParentFirebaseSession.auth();
      if (!auth.isSignInWithEmailLink(widget.emailLink)) {
        setState(
          () => _error = 'This parent invitation link is invalid or expired.',
        );
        return;
      }
      await auth.signInWithEmailLink(email: email, emailLink: widget.emailLink);
      await auth.currentUser?.getIdToken(true);
      if (accepted) {
        await _service.accept(
          invitationId: widget.invitationId,
          verifier: widget.verifier,
        );
      } else {
        await _service.decline(
          invitationId: widget.invitationId,
          verifier: widget.verifier,
        );
      }
      if (!mounted) return;
      if (accepted) {
        setState(() => _accepted = true);
      } else {
        widget.onDeclined?.call();
      }
    } on FirebaseAuthException catch (_) {
      // Firebase does not expose a safe, user-actionable distinction between
      // an address mismatch and an expired/replayed email link. Keep the
      // response generic while telling the parent how to recover.
      if (mounted) {
        setState(
          () => _error =
              'Use the exact email address that received the newest invitation, then try again.',
        );
      }
    } on ParentLinkInvitationException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _working = false);
    }
  }

  Future<void> _setPasswordAndContinue() async {
    final password = _passwordController.text;
    if (password.length < 6) {
      setState(() => _error = 'Use at least 6 characters for the password.');
      return;
    }
    if (password != _confirmPasswordController.text) {
      setState(() => _error = 'The password confirmation does not match.');
      return;
    }
    setState(() {
      _working = true;
      _error = null;
    });
    try {
      final parent = (await ParentFirebaseSession.auth()).currentUser;
      if (parent == null)
        throw const ParentLinkInvitationException(
          'Your secure sign-in has expired. Open the invitation email again.',
        );
      await parent.updatePassword(password);
      if (mounted) widget.onAccepted?.call();
    } on FirebaseAuthException catch (_) {
      if (mounted)
        setState(
          () => _error =
              'Unable to set the password now. Use Forgot password from parent sign in instead.',
        );
    } finally {
      if (mounted) setState(() => _working = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_accepted) {
      return Scaffold(
        appBar: AppBar(title: const Text('Secure your parent account')),
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Text(
                'Set a password',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 12),
              const Text(
                'Your consent is recorded. Set a password now so you can use the secure parent sign-in later.',
              ),
              const SizedBox(height: 20),
              TextField(
                controller: _passwordController,
                obscureText: _obscurePassword,
                decoration: InputDecoration(
                  labelText: 'New password',
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
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _confirmPasswordController,
                obscureText: _obscurePassword,
                decoration: const InputDecoration(
                  labelText: 'Confirm password',
                  prefixIcon: Icon(Icons.lock_outline),
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: const TextStyle(color: Colors.red)),
              ],
              const SizedBox(height: 20),
              FilledButton(
                onPressed: _working ? null : _setPasswordAndContinue,
                child: Text(
                  _working ? 'Saving password...' : 'Open parent dashboard',
                ),
              ),
              TextButton(
                onPressed: _working ? null : widget.onAccepted,
                child: const Text('Skip for now — use Forgot password later'),
              ),
            ],
          ),
        ),
      );
    }
    return Scaffold(
      appBar: AppBar(title: const Text('Confirm parent invitation')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Connect to safe learning updates',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 12),
              const Text(
                'You are about to connect your parent account. You will only see safe learning summaries for the linked learner.',
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _emailController,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(
                  labelText: 'Email that received the invitation',
                  prefixIcon: Icon(Icons.mail_outline),
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 16),
                Text(_error!, style: const TextStyle(color: Colors.red)),
              ],
              const Spacer(),
              FilledButton(
                onPressed: _working ? null : () => _complete(accepted: true),
                child: Text(
                  _working ? 'Checking invitation...' : 'Accept invitation',
                ),
              ),
              const SizedBox(height: 10),
              OutlinedButton(
                onPressed: _working ? null : () => _complete(accepted: false),
                child: const Text('Decline'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
