import 'dart:async';

import 'package:app_links/app_links.dart';

class ParentInvitationLink {
  const ParentInvitationLink({
    required this.emailLink,
    required this.invitationId,
    required this.verifier,
  });

  final String emailLink;
  final String invitationId;
  final String verifier;

  static ParentInvitationLink? parse(Uri uri) {
    final continuation = uri.queryParameters['continueUrl'];
    final embedded = continuation == null ? uri : Uri.tryParse(continuation);
    if (embedded == null || embedded.path != '/parent-invitation') return null;
    final invitationId = embedded.queryParameters['invitationId'];
    final verifier = embedded.queryParameters['verifier'];
    if (invitationId == null || invitationId.isEmpty || verifier == null || verifier.isEmpty) {
      return null;
    }
    return ParentInvitationLink(
      emailLink: uri.toString(),
      invitationId: invitationId,
      verifier: verifier,
    );
  }
}

class ParentInvitationLinkService {
  ParentInvitationLinkService({AppLinks? appLinks})
    : _appLinks = appLinks ?? AppLinks();

  final AppLinks _appLinks;

  Future<ParentInvitationLink?> initialLink() async {
    final uri = await _appLinks.getInitialLink();
    return uri == null ? null : ParentInvitationLink.parse(uri);
  }

  Stream<ParentInvitationLink> get links async* {
    await for (final uri in _appLinks.uriLinkStream) {
      final link = ParentInvitationLink.parse(uri);
      if (link != null) yield link;
    }
  }
}
