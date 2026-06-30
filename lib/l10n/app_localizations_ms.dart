// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Malay (`ms`).
class AppLocalizationsMs extends AppLocalizations {
  AppLocalizationsMs([String locale = 'ms']) : super(locale);

  @override
  String get appTitle => 'Logic Oasis';

  @override
  String get home => 'Laman';

  @override
  String get forge => 'Latihan';

  @override
  String get settings => 'Tetapan';

  @override
  String get studentProfile => 'Profil Murid';

  @override
  String get manageProfilePreferences => 'Urus profil dan tetapan aplikasi.';

  @override
  String get viewEditProfile => 'Lihat dan edit profil';

  @override
  String get language => 'Bahasa';

  @override
  String get missionReminders => 'Peringatan Misi';

  @override
  String get on => 'Aktif';

  @override
  String get off => 'Tidak aktif';

  @override
  String get eyeComfort => 'Selesa Mata';

  @override
  String get logout => 'Log keluar';

  @override
  String get returnLogin => 'Kembali ke halaman log masuk';

  @override
  String get confirmLogout => 'Sahkan log keluar?';

  @override
  String get logoutConfirmBody => 'Anda akan kembali ke halaman log masuk.';

  @override
  String get cancel => 'Batal';

  @override
  String get studentProfileUpdated => 'Profil murid dikemas kini';

  @override
  String languageSet(Object language) {
    return 'Bahasa ditukar kepada $language';
  }

  @override
  String get enterStudentName => 'Masukkan nama murid.';

  @override
  String get updateStudentProfileFailed =>
      'Tidak dapat mengemas kini profil murid. Sila cuba lagi.';

  @override
  String get editStudentProfile => 'Edit profil murid';

  @override
  String get studentName => 'Nama murid';

  @override
  String get year4 => 'Tahun 4';

  @override
  String get year5 => 'Tahun 5';

  @override
  String get year6 => 'Tahun 6';

  @override
  String get saving => 'Menyimpan...';

  @override
  String get saveProfile => 'Simpan Profil';

  @override
  String get parentDashboard => 'Papan Pemuka Ibu Bapa';

  @override
  String get locked => 'Dikunci';

  @override
  String get unlockAccess => 'Buka Akses';

  @override
  String get unlockProgressWeakTopics =>
      'Buka untuk melihat kemajuan dan topik lemah';

  @override
  String get parentAccessRequired => 'Akses ibu bapa diperlukan';

  @override
  String get enterLinkedParentPassword =>
      'Masukkan kata laluan ibu bapa yang dipautkan.';

  @override
  String get parentAccountUnavailable =>
      'Akaun ibu bapa tidak tersedia. Sila cuba lagi.';

  @override
  String get parentAccountNotLinked => 'Akaun ibu bapa belum dipautkan';

  @override
  String get parentAccountNotLinkedBody =>
      'Cipta akaun demo ibu bapa sebelum membuka papan pemuka terlindung.';

  @override
  String get createParentAccount => 'Cipta akaun';

  @override
  String get parentAuthentication => 'Pengesahan Ibu Bapa';

  @override
  String get parentAuthInstruction =>
      'Masukkan kata laluan ibu bapa yang dipautkan untuk membuka maklumat pembelajaran.';

  @override
  String get parentPassword => 'Kata laluan ibu bapa';

  @override
  String get showPassword => 'Tunjuk kata laluan';

  @override
  String get hidePassword => 'Sembunyi kata laluan';

  @override
  String get forgotPassword => 'Lupa kata laluan?';

  @override
  String get checkingPassword => 'Menyemak kata laluan...';

  @override
  String get unlockDashboard => 'Buka Papan Pemuka';

  @override
  String get linkedParentEmail => 'E-mel ibu bapa dipautkan';

  @override
  String get formulaForge => 'Latihan Formula';

  @override
  String get forgeSubtitle => 'Pilih topik dan berlatih dengan tenang.';

  @override
  String get loadingFirebaseQuestionBank => 'Memuat bank soalan Firebase...';

  @override
  String get topicLockedQuestionBank =>
      'Bank soalan untuk topik ini belum sedia.';

  @override
  String get missionRemindersOn => 'Peringatan misi diaktifkan';

  @override
  String get missionRemindersOff => 'Peringatan misi dimatikan';

  @override
  String missionRewardClaimed(Object crystals) {
    return 'Ganjaran misi dituntut: +$crystals kristal';
  }

  @override
  String get missionRewardAlreadyClaimed => 'Ganjaran misi sudah dituntut';

  @override
  String get recommendedMission => 'Misi dicadangkan';

  @override
  String get done => 'Selesai';

  @override
  String rewardClaimedKeepPractising(Object topic) {
    return 'Ganjaran dituntut. Teruskan latihan $topic.';
  }

  @override
  String get missionCompleteClaimReward =>
      'Misi selesai. Ketik untuk tuntut ganjaran.';

  @override
  String completeTopicDrills(Object count, Object topic) {
    return 'Lengkapkan $count latihan $topic';
  }

  @override
  String get available => 'Tersedia';

  @override
  String get repairCost => 'Kos baik pulih';

  @override
  String get fullyRestored => 'Dipulihkan Sepenuhnya';

  @override
  String repairWithResource(Object resource) {
    return 'Baiki dengan $resource';
  }

  @override
  String needMoreResource(Object resource) {
    return 'Perlu lebih $resource';
  }

  @override
  String restoredPercent(Object percent) {
    return '$percent% dipulihkan';
  }

  @override
  String areaRepaired(Object area) {
    return '$area dibaiki +25%';
  }

  @override
  String notEnoughResource(Object resource) {
    return '$resource tidak mencukupi';
  }

  @override
  String areaFullyRestored(Object area) {
    return '$area telah dipulihkan sepenuhnya';
  }

  @override
  String get mathCrystals => 'Kristal Matematik';

  @override
  String get mutualAid => 'Bantuan Bersama';

  @override
  String get quizResult => 'Keputusan Kuiz';

  @override
  String topicRestored(Object topic) {
    return '$topic dipulihkan';
  }

  @override
  String quizCorrectSummary(Object correct, Object total) {
    return 'Anda menjawab $correct daripada $total dengan betul.';
  }

  @override
  String get score => 'Markah';

  @override
  String get crystals => 'Kristal';

  @override
  String get repairReady => 'Sedia Baiki';

  @override
  String masteryResultMessage(
    Object encouragement,
    Object next,
    Object previous,
  ) {
    return '$encouragement Penguasaan: $previous -> $next. Gunakan kristal di Laman untuk memilih kawasan yang ingin dibaiki.';
  }

  @override
  String get backToForge => 'Kembali ke Latihan';

  @override
  String questionProgress(Object current, Object total) {
    return 'Soalan $current daripada $total';
  }

  @override
  String get finishQuiz => 'Selesai Kuiz';

  @override
  String get nextQuestion => 'Soalan Seterusnya';

  @override
  String parentDashboardSummary(Object name) {
    return 'Ringkasan tenang tentang kemajuan pembelajaran $name.';
  }

  @override
  String get overallRestoration => 'Pemulihan keseluruhan';

  @override
  String oasisRestoredSummary(Object percent) {
    return '$percent% oasis telah dipulihkan.';
  }

  @override
  String get averageScore => 'Purata Markah';

  @override
  String get latestQuiz => 'Kuiz Terkini';

  @override
  String get recentActivity => 'Aktiviti terkini';

  @override
  String get predictionSummary => 'Ringkasan ramalan';

  @override
  String weakTopic(Object topic) {
    return 'Topik lemah: $topic';
  }

  @override
  String suggestedAction(Object action) {
    return 'Cadangan tindakan: $action';
  }

  @override
  String get collaborationNote => 'Nota kerjasama';

  @override
  String get collaborationNoteBody =>
      'Ciri Bantuan Bersama disediakan untuk fasa seterusnya. Untuk FYP1, papan pemuka boleh menunjukkan skor sumbangan sementara dahulu.';

  @override
  String get greyBoxAiResult => 'Keputusan AI Grey Box';

  @override
  String aiResultSummary(
    Object confidence,
    Object label,
    Object mastery,
    Object weakness,
  ) {
    return 'Penguasaan akhir: $label - Penguasaan BKT: $mastery% - Risiko kelemahan: $weakness% - Keyakinan: $confidence%';
  }

  @override
  String shapReasons(Object reasons) {
    return 'Sebab SHAP: $reasons';
  }

  @override
  String get prototypeOtpNotice =>
      'Aliran tetapan semula prototaip: gunakan OTP 246810 untuk ujian sahaja. Gantikan dengan penghantaran OTP e-mel sebelum ujian pengguna sebenar.';

  @override
  String get loadingParentDashboard =>
      'Memuat papan pemuka ibu bapa daripada Firebase...';

  @override
  String attemptSummary(
    Object correct,
    Object crystals,
    Object score,
    Object total,
  ) {
    return '$score% markah - $correct/$total betul - +$crystals kristal';
  }

  @override
  String get justNow => 'Baru sahaja';

  @override
  String minutesAgo(Object minutes) {
    return '$minutes minit lalu';
  }

  @override
  String hoursAgo(Object hours) {
    return '$hours jam lalu';
  }

  @override
  String daysAgo(Object days) {
    return '$days hari lalu';
  }
}
