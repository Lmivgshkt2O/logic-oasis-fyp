import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:cloud_functions/cloud_functions.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:logic_oasis/firebase_options.dart';

/// Isolated Firebase client used only for an authenticated parent session.
///
/// Firebase Auth keeps one identity per Firebase app.  The learner remains on
/// the default app while a parent signs in through this named app, so leaving
/// the parent dashboard cannot silently discard the student's signed-in
/// session.  The matching Functions and Firestore clients inherit the named
/// app's parent token and therefore remain subject to the parent Rules.
class ParentFirebaseSession {
  ParentFirebaseSession._();

  static const _appName = 'logic_oasis_parent_session';
  static Future<FirebaseApp>? _appFuture;

  static Future<FirebaseApp> app() {
    return _appFuture ??= _loadApp();
  }

  static Future<FirebaseApp> _loadApp() async {
    try {
      return Firebase.app(_appName);
    } on FirebaseException {
      return Firebase.initializeApp(
        name: _appName,
        options: DefaultFirebaseOptions.currentPlatform,
      );
    }
  }

  static Future<FirebaseAuth> auth() async {
    return FirebaseAuth.instanceFor(app: await app());
  }

  static Future<FirebaseFunctions> functions() async {
    return FirebaseFunctions.instanceFor(
      app: await app(),
      region: 'asia-southeast1',
    );
  }

  static Future<FirebaseFirestore> firestore() async {
    return FirebaseFirestore.instanceFor(app: await app());
  }

  static Future<void> signOut() async {
    await (await auth()).signOut();
  }
}
