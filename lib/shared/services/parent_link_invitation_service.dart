import 'package:cloud_functions/cloud_functions.dart';
import 'package:logic_oasis/shared/services/parent_firebase_session.dart';

class ParentLinkInvitationException implements Exception {
  const ParentLinkInvitationException(this.message);

  final String message;

  @override
  String toString() => message;
}

class ParentInvitationStatus {
  const ParentInvitationStatus({required this.status, this.expiresAt});

  final String status;
  final DateTime? expiresAt;
}

/// Callable-only bridge for U12. Flutter never reads or writes invitation,
/// link, audit, email-HMAC, or verifier documents directly.
abstract class ParentLinkInvitationGateway {
  Future<ParentInvitationStatus> createInvitation({
    required String recipientEmail,
  });
  Future<void> accept({required String invitationId, required String verifier});
  Future<void> decline({
    required String invitationId,
    required String verifier,
  });
  Future<void> unlinkOwnParentLink({required String studentId});
}

class ParentLinkInvitationService implements ParentLinkInvitationGateway {
  ParentLinkInvitationService({FirebaseFunctions? functions})
    : _functions = functions,
      _functionsProvider = null;

  /// Parent acceptance and unlinking must carry the named parent Auth token,
  /// not the student's default-app token.
  ParentLinkInvitationService.parentSession({FirebaseFunctions? functions})
    : _functions = functions,
      _functionsProvider = ParentFirebaseSession.functions;

  final FirebaseFunctions? _functions;
  final Future<FirebaseFunctions> Function()? _functionsProvider;

  Future<FirebaseFunctions> _resolvedFunctions() async {
    final functions = _functions;
    if (functions != null) return functions;
    final provider = _functionsProvider;
    if (provider != null) return provider();
    return FirebaseFunctions.instanceFor(region: 'asia-southeast1');
  }

  Future<ParentInvitationStatus> createInvitation({
    required String recipientEmail,
  }) async {
    final result = await _call('createParentLinkInvitation', {
      'recipientEmail': recipientEmail.trim(),
    });
    final expiresAt = result['expiresAt'];
    return ParentInvitationStatus(
      status: result['status'] as String? ?? 'pending',
      expiresAt: expiresAt is String ? DateTime.tryParse(expiresAt) : null,
    );
  }

  Future<void> accept({
    required String invitationId,
    required String verifier,
  }) async {
    await _call('acceptParentLinkInvitation', {
      'invitationId': invitationId,
      'verifier': verifier,
    });
  }

  Future<void> decline({
    required String invitationId,
    required String verifier,
  }) async {
    await _call('declineParentLinkInvitation', {
      'invitationId': invitationId,
      'verifier': verifier,
    });
  }

  Future<void> unlinkOwnParentLink({required String studentId}) async {
    await _call('unlinkOwnParentLink', {'studentId': studentId});
  }

  Future<Map<String, dynamic>> _call(
    String name,
    Map<String, dynamic> payload,
  ) async {
    try {
      final result = await (await _resolvedFunctions())
          .httpsCallable(name)
          .call(payload);
      final data = result.data;
      if (data is! Map) {
        throw const ParentLinkInvitationException(
          'Secure parent request returned an invalid response.',
        );
      }
      return Map<String, dynamic>.from(data);
    } on FirebaseFunctionsException catch (_) {
      throw const ParentLinkInvitationException(
        'Unable to complete the secure parent request. Please try again.',
      );
    }
  }
}
