import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:logic_oasis/app/logic_oasis_app.dart';
import 'package:logic_oasis/shared/services/firebase_emulator_config.dart';

import 'firebase_options.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  await FirebaseEmulatorConfig.connect();

  // Fredoka and Nunito are bundled as release assets; never fetch fonts from
  // the network at runtime so first render is stable even offline.
  GoogleFonts.config.allowRuntimeFetching = false;

  runApp(const LogicOasisApp());
}
