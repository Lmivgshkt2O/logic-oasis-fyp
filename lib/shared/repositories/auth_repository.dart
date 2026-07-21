import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AuthRepository {
  AuthRepository({FirebaseAuth? auth, FirebaseFirestore? firestore})
    : _auth = auth ?? FirebaseAuth.instance,
      _firestore = firestore ?? FirebaseFirestore.instance;

  static const _rememberedUidKey = 'remembered_student_uid';
  static const _rememberedEmailKey = 'remembered_student_email';

  final FirebaseAuth _auth;
  final FirebaseFirestore _firestore;

  Future<RememberedStudentProfile?> loadRememberedStudentProfile() async {
    final preferences = await SharedPreferences.getInstance();
    final email = preferences.getString(_rememberedEmailKey);
    final uid = preferences.getString(_rememberedUidKey);

    if (email == null || uid == null) return null;

    try {
      final doc = await _firestore
          .collection('rememberedProfiles')
          .doc(uid)
          .get();
      final data = doc.data();
      return RememberedStudentProfile(
        uid: uid,
        email: email,
        displayName: data?['displayName'] as String?,
        yearLevel: data?['yearLevel'] as int?,
      );
    } catch (_) {
      return RememberedStudentProfile(uid: uid, email: email);
    }
  }

  Future<StudentAuthProfile?> loadCurrentStudentProfile() async {
    final user = _auth.currentUser;
    if (user == null) return null;

    try {
      final profile = await _firestore.collection('users').doc(user.uid).get();
      final profileData = profile.data();
      if (!profile.exists || profileData == null) {
        await _auth.signOut();
        return null;
      }
      // The root session is a learner session only. A parent who arrives via
      // an email invitation is routed by the parent entry flow instead of
      // being silently treated as a learner because both roles use Firebase
      // Auth's single current-user slot.
      if (profileData['role'] != 'student') {
        await _auth.signOut();
        return null;
      }

      return StudentAuthProfile(
        uid: user.uid,
        email: user.email ?? profileData['email'] as String? ?? '',
        displayName: profileData['displayName'] as String? ?? user.displayName,
        yearLevel: profileData['yearLevel'] as int?,
      );
    } catch (_) {
      return null;
    }
  }

  Future<void> signOutStudent({bool clearRememberedProfile = false}) async {
    await _auth.signOut();
    if (clearRememberedProfile) {
      await clearRememberedStudentProfile();
    }
  }

  Future<StudentAuthProfile> signInStudent({
    required String email,
    required String password,
    required bool rememberProfile,
  }) async {
    try {
      final credential = await _auth.signInWithEmailAndPassword(
        email: email,
        password: password,
      );

      final user = credential.user;
      if (user == null) {
        throw const AuthFailure('Unable to sign in. Please try again.');
      }

      final profile = await _firestore.collection('users').doc(user.uid).get();
      if (!profile.exists) {
        await _auth.signOut();
        throw const AuthFailure("The account doesn't exist");
      }
      if (profile.data()?['role'] != 'student') {
        await _auth.signOut();
        throw const AuthFailure('Use the parent dashboard to sign in to this account.');
      }

      if (rememberProfile) {
        await _rememberStudentProfile(user.uid, email, profile.data());
      } else {
        await clearRememberedStudentProfile();
      }

      final profileData = profile.data();
      return StudentAuthProfile(
        uid: user.uid,
        email: email,
        displayName: profileData?['displayName'] as String?,
        yearLevel: profileData?['yearLevel'] as int?,
      );
    } on FirebaseAuthException catch (error) {
      if (error.code == 'user-not-found' ||
          error.code == 'wrong-password' ||
          error.code == 'invalid-credential') {
        throw const AuthFailure("The account doesn't exist");
      }
      throw AuthFailure(
        error.message ?? 'Unable to sign in. Please try again.',
      );
    }
  }

  /// Parent access uses Firebase Auth, then U9's active parentLinks relation
  /// decides which safe child projections are available. It intentionally does
  /// not create a parent account or inspect prototype password documents.
  Future<void> signInParent({
    required String email,
    required String password,
  }) async {
    try {
      final credential = await _auth.signInWithEmailAndPassword(
        email: email.trim(),
        password: password,
      );
      if (credential.user == null) {
        throw const AuthFailure('Unable to sign in to the parent account.');
      }
      final profile = await _firestore
          .collection('users')
          .doc(credential.user!.uid)
          .get();
      if (!profile.exists || profile.data()?['role'] != 'parent') {
        await _auth.signOut();
        throw const AuthFailure(
          'This account does not have approved parent dashboard access.',
        );
      }
    } on FirebaseAuthException catch (error) {
      if (error.code == 'user-not-found' ||
          error.code == 'wrong-password' ||
          error.code == 'invalid-credential') {
        throw const AuthFailure('The parent account details are incorrect.');
      }
      throw AuthFailure(
        error.message ?? 'Unable to sign in to the parent account.',
      );
    }
  }

  Future<void> registerStudent({
    required String displayName,
    required int yearLevel,
    required String email,
    required String password,
    required bool rememberProfile,
  }) async {
    try {
      final credential = await _auth.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );

      final user = credential.user;
      if (user == null) {
        throw const AuthFailure('Unable to create account. Please try again.');
      }

      await user.updateDisplayName(displayName);

      final profileData = {
        'displayName': displayName,
        'email': email,
        'yearLevel': yearLevel,
        'language': 'English',
        'role': 'student',
        'parentIds': <String>[],
        'createdAt': FieldValue.serverTimestamp(),
        'lastActiveAt': FieldValue.serverTimestamp(),
      };

      await _firestore.collection('users').doc(user.uid).set(profileData);

      if (rememberProfile) {
        await _rememberStudentProfile(user.uid, email, profileData);
      } else {
        await clearRememberedStudentProfile();
      }
    } on FirebaseAuthException catch (error) {
      if (error.code == 'email-already-in-use') {
        throw const AuthFailure('This email is already registered.');
      }
      if (error.code == 'weak-password') {
        throw const AuthFailure('Use at least 6 characters for the password.');
      }
      throw AuthFailure(
        error.message ?? 'Unable to create account. Please try again.',
      );
    }
  }

  Future<StudentAuthProfile> signInStudentWithGoogle({
    required bool rememberProfile,
  }) async {
    try {
      final googleUser = await GoogleSignIn().signIn();
      if (googleUser == null) {
        throw const AuthFailure('Google sign-in was cancelled.');
      }

      final googleAuth = await googleUser.authentication;
      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );

      final userCredential = await _auth.signInWithCredential(credential);
      final user = userCredential.user;
      if (user == null) {
        throw const AuthFailure('Unable to sign in with Google.');
      }

      final email = user.email ?? googleUser.email;
      final displayName =
          user.displayName ?? googleUser.displayName ?? 'Student';
      final profileRef = _firestore.collection('users').doc(user.uid);
      final profileDoc = await profileRef.get();
      final profileData = profileDoc.data();

      if (!profileDoc.exists) {
        await profileRef.set({
          'displayName': displayName,
          'email': email,
          'yearLevel': 4,
          'language': 'English',
          'role': 'student',
          'authProvider': 'google',
          'parentIds': <String>[],
          'createdAt': FieldValue.serverTimestamp(),
          'lastActiveAt': FieldValue.serverTimestamp(),
        });
      } else {
        if (profileData?['role'] != 'student') {
          await _auth.signOut();
          throw const AuthFailure('Use the parent dashboard to sign in to this account.');
        }
        await profileRef.set({
          'email': email,
          'displayName': profileData?['displayName'] ?? displayName,
          'authProvider': profileData?['authProvider'] ?? 'google',
          'lastActiveAt': FieldValue.serverTimestamp(),
        }, SetOptions(merge: true));
      }

      final latestProfile = await profileRef.get();
      final latestData = latestProfile.data();

      if (rememberProfile) {
        await _rememberStudentProfile(user.uid, email, latestData);
      } else {
        await clearRememberedStudentProfile();
      }

      return StudentAuthProfile(
        uid: user.uid,
        email: email,
        displayName: latestData?['displayName'] as String? ?? displayName,
        yearLevel: latestData?['yearLevel'] as int? ?? 4,
      );
    } on FirebaseAuthException catch (error) {
      throw AuthFailure(
        error.message ?? 'Unable to sign in with Google. Please try again.',
      );
    }
  }

  /// Firebase Auth owns reset delivery and verification. The response shown by
  /// the UI is deliberately generic so it does not reveal account existence.
  Future<void> sendParentPasswordResetEmail({required String email}) async {
    final normalizedEmail = email.trim();
    if (normalizedEmail.isEmpty || !normalizedEmail.contains('@')) {
      throw const AuthFailure('Enter a valid parent email address.');
    }
    try {
      await _auth.sendPasswordResetEmail(email: normalizedEmail);
    } on FirebaseAuthException catch (_) {
      // Keep parent-account existence private. Firebase still applies its own
      // abuse controls and may have delivered a reset message.
    }
  }

  Future<void> updateStudentProfile({
    required String uid,
    required String displayName,
    required int yearLevel,
    String? email,
  }) async {
    final trimmedName = displayName.trim();
    if (trimmedName.isEmpty) {
      throw const AuthFailure('Enter the student name.');
    }

    final normalizedYearLevel = yearLevel.clamp(4, 6);
    final currentUser = _auth.currentUser;
    if (currentUser?.uid == uid) {
      await currentUser!.updateDisplayName(trimmedName);
    }

    await _firestore.collection('users').doc(uid).set({
      'displayName': trimmedName,
      'yearLevel': normalizedYearLevel,
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    await _firestore.collection('rememberedProfiles').doc(uid).set({
      'uid': uid,
      if (email != null && email.trim().isNotEmpty) 'email': email.trim(),
      'displayName': trimmedName,
      'yearLevel': normalizedYearLevel,
      'rememberedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  Future<void> _rememberStudentProfile(
    String uid,
    String email,
    Map<String, dynamic>? profile,
  ) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(_rememberedUidKey, uid);
    await preferences.setString(_rememberedEmailKey, email);
    await _firestore.collection('rememberedProfiles').doc(uid).set({
      'uid': uid,
      'email': email,
      'displayName': profile?['displayName'],
      'yearLevel': profile?['yearLevel'],
      'rememberedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  Future<void> clearRememberedStudentProfile() async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.remove(_rememberedUidKey);
    await preferences.remove(_rememberedEmailKey);
  }

}

class StudentAuthProfile {
  const StudentAuthProfile({
    required this.uid,
    required this.email,
    this.displayName,
    this.yearLevel,
  });

  final String uid;
  final String email;
  final String? displayName;
  final int? yearLevel;
}

class RememberedStudentProfile {
  const RememberedStudentProfile({
    required this.uid,
    required this.email,
    this.displayName,
    this.yearLevel,
  });

  final String uid;
  final String email;
  final String? displayName;
  final int? yearLevel;
}

class AuthFailure implements Exception {
  const AuthFailure(this.message);

  final String message;

  @override
  String toString() => message;
}
