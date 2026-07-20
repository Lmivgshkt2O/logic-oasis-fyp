import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('repair resource icons use bundled SVG assets', () async {
    final componentSource = File(
      'lib/shared/widgets/logic_oasis_figma_components.dart',
    ).readAsStringSync();

    expect(componentSource, contains("? 'stat_crystal'"));
    expect(componentSource, contains(": 'stat_energy'"));
    expect(File('assets/icons/stat_crystal.svg').existsSync(), isTrue);
    expect(File('assets/icons/stat_energy.svg').existsSync(), isTrue);
    expect(
      (await rootBundle.load('assets/icons/stat_crystal.svg')).lengthInBytes,
      greaterThan(0),
    );
    expect(
      (await rootBundle.load('assets/icons/stat_energy.svg')).lengthInBytes,
      greaterThan(0),
    );
  });
}
