import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/shared/services/firebase_emulator_config.dart';

void main() {
  tearDown(() {
    debugDefaultTargetPlatformOverride = null;
  });

  test('Android virtual device defaults to the host loopback alias', () {
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    expect(FirebaseEmulatorConfig.defaultHost, '10.0.2.2');
  });

  test('desktop and web default to localhost', () {
    debugDefaultTargetPlatformOverride = TargetPlatform.windows;
    expect(FirebaseEmulatorConfig.defaultHost, 'localhost');
    expect(
      FirebaseEmulatorConfig.resolveHost(),
      'localhost',
    );
  });

  test('a validated LAN or adb-reverse override is used consistently', () {
    expect(FirebaseEmulatorConfig.resolveOverride('192.168.1.50'), '192.168.1.50');
    expect(FirebaseEmulatorConfig.resolveOverride('oasis-device.lan'), 'oasis-device.lan');
    expect(FirebaseEmulatorConfig.resolveOverride('localhost'), 'localhost');
    expect(FirebaseEmulatorConfig.resolveOverride(''), isNull);
    expect(FirebaseEmulatorConfig.resolveOverride('   '), isNull);
  });

  test('invalid and numeric-loopback physical overrides are rejected', () {
    for (final host in <String>[
      'http://192.168.1.50',
      '192.168.1.50:8080',
      '192.168.1.50/path',
      '192 .168.1.50',
      '127.0.0.1',
      '::1',
      ' host',
    ]) {
      expect(
        () => FirebaseEmulatorConfig.validateEmulatorHost(host),
        throwsArgumentError,
        reason: host,
      );
    }
  });

  test('release builds are no-ops without the emulator flag', () async {
    expect(FirebaseEmulatorConfig.enabled, isFalse);
    // Without a Firebase app and with the flag absent, connect() returns
    // immediately instead of silently pointing any client at an emulator.
    await FirebaseEmulatorConfig.connect();
  });
}
