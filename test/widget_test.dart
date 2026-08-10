import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_core_platform_interface/test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logic_oasis/app/logic_oasis_app.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setupFirebaseCoreMocks();

  setUpAll(Firebase.initializeApp);

  testWidgets('starts with Logic Oasis opening screen', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const LogicOasisApp(loadFirebaseTopics: false));

    expect(find.text('Logic Oasis'), findsOneWidget);
    expect(find.text('Learn. Restore. Grow together.'), findsOneWidget);
  });
}
