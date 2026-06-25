import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:logic_oasis/app/logic_oasis_app.dart';

import 'firebase_options.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  runApp(const LogicOasisApp());
}