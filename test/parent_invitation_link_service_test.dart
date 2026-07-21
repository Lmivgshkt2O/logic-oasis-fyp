import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/services/parent_invitation_link_service.dart';

void main() {
  test('parses Firebase outer action URL and keeps it for email-link sign-in', () {
    final outer = Uri.parse(
      'https://logic-oasis-fyp.web.app/__/auth/action?mode=signIn&continueUrl='
      'https%3A%2F%2Flogic-oasis-fyp.web.app%2Fparent-invitation%3FinvitationId%3Dinvite-1%26verifier%3Dopaque-value',
    );

    final link = ParentInvitationLink.parse(outer);

    expect(link?.invitationId, 'invite-1');
    expect(link?.verifier, 'opaque-value');
    expect(link?.emailLink, outer.toString());
  });
}
