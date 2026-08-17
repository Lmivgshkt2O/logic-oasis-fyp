import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:cloud_functions/cloud_functions.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';

class FirebaseEmulatorConfig {
  static const enabled = bool.fromEnvironment('USE_FIREBASE_EMULATORS');
  static const _hostOverride = String.fromEnvironment('FIREBASE_EMULATOR_HOST');

  /// Android Virtual Device default; every other platform reaches the host via
  /// `localhost`. Release builds never enable emulators unless the developer
  /// explicitly passes `--dart-define=USE_FIREBASE_EMULATORS=true`.
  static String get defaultHost =>
      kIsWeb || defaultTargetPlatform != TargetPlatform.android
          ? 'localhost'
          : '10.0.2.2';

  /// One validated build-time host override shared by every emulator client.
  /// A physical device uses either its LAN host/IP, or `localhost` with
  /// `adb reverse tcp:9099 tcp:9099` (and the other emulator ports).
  static String? get hostOverride => resolveOverride(_hostOverride);

  @visibleForTesting
  static String? resolveOverride(String raw) {
    final override = raw.trim();
    if (override.isEmpty) return null;
    validateEmulatorHost(override);
    return override;
  }

  static String resolveHost() => hostOverride ?? defaultHost;

  static void validateEmulatorHost(String host) {
    if (host.isEmpty) {
      throw ArgumentError.value(
        host,
        'host',
        'Emulator host override must not be empty.',
      );
    }
    if (host != host.trim()) {
      throw ArgumentError.value(
        host,
        'host',
        'Emulator host override must not contain surrounding whitespace.',
      );
    }
    if (RegExp(r'\s').hasMatch(host)) {
      throw ArgumentError.value(
        host,
        'host',
        'Emulator host override must not contain whitespace.',
      );
    }
    if (host.contains('://') || host.contains('/')) {
      throw ArgumentError.value(
        host,
        'host',
        'Emulator host override must be a bare host, without a scheme or path.',
      );
    }
    if (host.contains(':')) {
      throw ArgumentError.value(
        host,
        'host',
        'Emulator ports are configured centrally; the override must not include a port.',
      );
    }
    // `localhost` is the documented `adb reverse` tunnel alias for a physical
    // device. Numeric loopback addresses point at the device itself and are
    // rejected so a LAN override cannot silently target the wrong machine.
    if (host == '127.0.0.1' || host == '::1') {
      throw ArgumentError.value(
        host,
        'host',
        'Numeric loopback points at the device itself; use localhost with adb reverse or a LAN host.',
      );
    }
  }

  static Future<void> connect({FirebaseApp? app}) async {
    if (!enabled) return;
    final host = resolveHost();
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
