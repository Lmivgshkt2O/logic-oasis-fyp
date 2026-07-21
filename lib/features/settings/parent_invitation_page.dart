import 'package:flutter/material.dart';
import 'package:logic_oasis/shared/services/parent_link_invitation_service.dart';

/// Student-side request screen. It intentionally never shows an invitation
/// document, raw link, verifier, or the entered parent address after sending.
class ParentInvitationPage extends StatefulWidget {
  const ParentInvitationPage({super.key, this.service});

  final ParentLinkInvitationGateway? service;

  @override
  State<ParentInvitationPage> createState() => _ParentInvitationPageState();
}

class _ParentInvitationPageState extends State<ParentInvitationPage> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  late final ParentLinkInvitationGateway _service;
  bool _sending = false;
  ParentInvitationStatus? _status;
  String? _error;

  @override
  void initState() {
    super.initState();
    _service = widget.service ?? ParentLinkInvitationService();
  }

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    if (_sending || _formKey.currentState?.validate() != true) return;
    setState(() {
      _sending = true;
      _error = null;
    });
    try {
      final status = await _service.createInvitation(
        recipientEmail: _emailController.text,
      );
      if (mounted) setState(() => _status = status);
    } on ParentLinkInvitationException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final expiry = _status?.expiresAt;
    return Scaffold(
      appBar: AppBar(title: const Text('Invite a parent')),
      body: SafeArea(
        child: Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Text('Share safe learning updates', style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 8),
              const Text(
                'Enter a parent email. They must open the invitation on their own device, verify the email, and choose whether to connect.',
              ),
              const SizedBox(height: 20),
              TextFormField(
                controller: _emailController,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(
                  labelText: 'Parent email', prefixIcon: Icon(Icons.mail_outline),
                ),
                validator: (value) => value != null && value.contains('@')
                    ? null
                    : 'Enter a valid parent email address.',
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: const TextStyle(color: Colors.red)),
              ],
              if (_status != null) ...[
                const SizedBox(height: 16),
                const Text('Invitation pending. The parent must accept it from their own email.'),
                if (expiry != null) Text('This invitation expires at ${expiry.toLocal()}.'),
              ],
              const SizedBox(height: 20),
              FilledButton.icon(
                onPressed: _sending ? null : _send,
                icon: _sending
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.send_outlined),
                label: Text(_sending ? 'Sending invitation...' : 'Send secure invitation'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
