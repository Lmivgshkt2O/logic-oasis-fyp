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

      return StudentAuthProfile(
        uid: user.uid,
        email: user.email ?? profileData['email'] as String? ?? '',
        displayName:
            profileData['displayName'] as String? ?? user.displayName,
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

  Future<LinkedParentAccount?> fetchLinkedParentAccount({
    required String studentId,
  }) async {
    final studentDoc = await _firestore
        .collection('users')
        .doc(studentId)
        .get();
    final studentData = studentDoc.data();
    if (studentData == null) return null;

    final linkedParentId = studentData['linkedParentAccountId'] as String?;
    final linkedParentEmail = studentData['linkedParentEmail'] as String?;

    if (linkedParentId != null && linkedParentEmail != null) {
      return LinkedParentAccount(id: linkedParentId, email: linkedParentEmail);
    }

    final parentIds = studentData['parentIds'];
    if (parentIds is List && parentIds.isNotEmpty) {
      final parentId = parentIds.first.toString();
      final parentDoc = await _firestore
          .collection('parentAccounts')
          .doc(parentId)
          .get();
      final parentData = parentDoc.data();
      final email = parentData?['email'] as String? ?? linkedParentEmail;
      if (email != null) {
        return LinkedParentAccount(id: parentId, email: email);
      }
    }

    return null;
  }

  Future<LinkedParentAccount> registerLinkedParentAccount({
    required String studentId,
    required String email,
    required String password,
  }) async {
    final normalizedEmail = email.trim().toLowerCase();
    final parentId = 'parent_${_stableKey(normalizedEmail)}';
    final parentRef = _firestore.collection('parentAccounts').doc(parentId);

    await parentRef.set({
      'email': normalizedEmail,
      'passwordKey': _passwordKey(parentId, password),
      'studentIds': FieldValue.arrayUnion([studentId]),
      'createdAt': FieldValue.serverTimestamp(),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    await _firestore.collection('users').doc(studentId).set({
      'linkedParentAccountId': parentId,
      'linkedParentEmail': normalizedEmail,
      'parentIds': FieldValue.arrayUnion([parentId]),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));

    return LinkedParentAccount(id: parentId, email: normalizedEmail);
  }

  Future<void> authenticateLinkedParent({
    required LinkedParentAccount parent,
    required String password,
  }) async {
    final parentDoc = await _firestore
        .collection('parentAccounts')
        .doc(parent.id)
        .get();
    final parentData = parentDoc.data();

    if (parentData == null ||
        parentData['passwordKey'] != _passwordKey(parent.id, password)) {
      throw const AuthFailure('Parent password is incorrect.');
    }
  }

  Future<void> sendParentResetOtp({required LinkedParentAccount parent}) async {
    await _firestore.collection('parentAccounts').doc(parent.id).set({
      'resetOtp': '246810',
      'resetOtpCreatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  Future<void> resetLinkedParentPassword({
    required LinkedParentAccount parent,
    required String otp,
    required String newPassword,
  }) async {
    final parentRef = _firestore.collection('parentAccounts').doc(parent.id);
    final parentDoc = await parentRef.get();
    final parentData = parentDoc.data();

    if (parentData == null || parentData['resetOtp'] != otp.trim()) {
      throw const AuthFailure('Enter the correct OTP to reset password.');
    }

    await parentRef.set({
      'passwordKey': _passwordKey(parent.id, newPassword),
      'resetOtp': FieldValue.delete(),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
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

  String _passwordKey(String parentId, String password) {
    return _stableKey('$parentId:${password.trim()}');
  }

  String _stableKey(String value) {
    var hash = 2166136261;
    for (final unit in value.codeUnits) {
      hash ^= unit;
      hash = (hash * 16777619) & 0xFFFFFFFF;
    }
    return hash.toRadixString(16).padLeft(8, '0');
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

class LinkedParentAccount {
  const LinkedParentAccount({required this.id, required this.email});

  final String id;
  final String email;
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
