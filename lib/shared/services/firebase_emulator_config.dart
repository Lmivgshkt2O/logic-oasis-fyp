import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:cloud_functions/cloud_functions.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';

class FirebaseEmulatorConfig {
  static const enabled = bool.fromEnvironment('USE_FIREBASE_EMULATORS');
  static Future<void> connect({FirebaseApp? app}) async {
    if (!enabled) return;
    final host = kIsWeb || defaultTargetPlatform != TargetPlatform.android
        ? 'localhost'
        : '10.0.2.2';
    final targetApp = app ?? Firebase.app();
    final auth = FirebaseAuth.instanceFor(app: targetApp);
    final firestore = FirebaseFirestore.instanceFor(app: targetApp);
    final functions = FirebaseFunctions.instanceFor(app: targetApp);
    final regionalFunctions = FirebaseFunctions.instanceFor(
      app: targetApp,
      region: 'asia-southeast1',
    );
    await auth.useAuthEmulator(host, 9099);
    firestore.useFirestoreEmulator(host, 8080);
    functions.useFunctionsEmulator(host, 5001);
    regionalFunctions.useFunctionsEmulator(host, 5001);
  }
}
