import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/services/parent_invitation_link_service.dart';

void main() {
  test(
    'parses Firebase Hosting email link and keeps it for email-link sign-in',
    () {
      final action = Uri.parse(
        'https://logic-oasis-fyp.firebaseapp.com/__/auth/action?apiKey=test-key&mode=signIn&'
        'oobCode=test-code&continueUrl=https%3A%2F%2Flogic-oasis-fyp.web.app%2Fparent-invitation%3F'
        'invitationId%3Dinvite-1%26verifier%3Dopaque-value',
      );
      final outer = Uri.https(
        'logic-oasis-fyp.firebaseapp.com',
        '/__/auth/links',
        {'link': action.toString()},
      );

      final link = ParentInvitationLink.parse(outer);

      expect(link?.invitationId, 'invite-1');
      expect(link?.verifier, 'opaque-value');
      expect(link?.emailLink, outer.toString());
    },
  );
}
