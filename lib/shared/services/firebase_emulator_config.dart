import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:cloud_functions/cloud_functions.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';

class FirebaseEmulatorConfig {
  static const enabled = bool.fromEnvironment('USE_FIREBASE_EMULATORS');
  static Future<void> connect() async {
    if (!enabled) return;
    final host = kIsWeb || defaultTargetPlatform != TargetPlatform.android ? 'localhost' : '10.0.2.2';
    await FirebaseAuth.instance.useAuthEmulator(host, 9099);
    FirebaseFirestore.instance.useFirestoreEmulator(host, 8080);
    FirebaseFunctions.instance.useFunctionsEmulator(host, 5001);
  }
}
