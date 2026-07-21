import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/features/settings/parent_invitation_page.dart';
import 'package:logic_oasis/shared/services/parent_link_invitation_service.dart';

void main() {
  testWidgets('student invitation page never renders the submitted email', (tester) async {
    final gateway = _InvitationGateway();
    await tester.pumpWidget(MaterialApp(home: ParentInvitationPage(service: gateway)));

    await tester.enterText(find.byType(TextFormField), 'parent@example.com');
    await tester.tap(find.text('Send secure invitation'));
    await tester.pumpAndSettle();

    expect(gateway.createCalls, 1);
    expect(find.textContaining('Invitation pending'), findsOneWidget);
    expect(find.text('parent@example.com'), findsNothing);
  });
}

class _InvitationGateway implements ParentLinkInvitationGateway {
  int createCalls = 0;

  @override
  Future<ParentInvitationStatus> createInvitation({required String recipientEmail}) async {
    createCalls += 1;
    return const ParentInvitationStatus(status: 'pending');
  }

  @override
  Future<void> accept({required String invitationId, required String verifier}) async {}

  @override
  Future<void> decline({required String invitationId, required String verifier}) async {}

  @override
  Future<void> unlinkOwnParentLink({required String studentId}) async {}
}
