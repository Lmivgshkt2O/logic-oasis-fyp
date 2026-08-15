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
  String get forum => 'Forum S&J';

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
  String get guidedStepsTitle => 'Mari semak langkahnya';

  @override
  String get hintTitle => 'Petunjuk';

  @override
  String examplePrefix(Object example) {
    return 'Contoh: $example';
  }

  @override
  String get secureAnswerChecked =>
      'Pilihan anda telah disemak dengan selamat.';

  @override
  String get reviewTheseFirst => 'Semak dahulu';

  @override
  String get perfectScore => 'Markah penuh! Tiada apa yang perlu disemak.';

  @override
  String get nextPractice => 'Latihan seterusnya';

  @override
  String nextPracticeLevel(Object difficulty) {
    return 'Seterusnya: Latihan $difficulty';
  }

  @override
  String get practiseAgain => 'Ulang Latihan';

  @override
  String get moveOn => 'Teruskan';

  @override
  String get basedOnQuizProgress => 'Berdasarkan kemajuan kuiz anda';

  @override
  String get preparingNextPractice => 'Menyediakan latihan seterusnya…';

  @override
  String get allTopicsComplete =>
      'Anda telah melengkapkan semua topik yang tersedia!';

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

  @override
  String get discussInForum => 'Bincang dalam forum';

  @override
  String get openingDiscussion => 'Membuka perbincangan...';

  @override
  String get discussionUnavailable =>
      'Soalan ini tidak tersedia untuk perbincangan.';

  @override
  String parentDashboardCaption(String name) {
    return 'Kemas kini pembelajaran selamat untuk $name.';
  }

  @override
  String parentDashboardUpdated(String updated) {
    return 'Dikemas kini: $updated';
  }

  @override
  String get glanceFull => 'Minggu yang stabil dengan fokus yang jelas.';

  @override
  String glanceFullSupport(String focus) {
    return '$focus ialah fokus, dengan latihan dan aktiviti Saling Membantu minggu ini.';
  }

  @override
  String get glanceFocusPractice =>
      'Minggu latihan yang stabil dengan fokus yang jelas.';

  @override
  String glanceFocusPracticeSupport(String focus) {
    return '$focus ialah fokus, dengan latihan direkodkan minggu ini.';
  }

  @override
  String get glanceFocusPracticeNoMutualAidYet =>
      'Minggu latihan yang stabil dengan fokus yang jelas.';

  @override
  String glanceFocusPracticeNoMutualAidYetSupport(String focus) {
    return '$focus ialah fokus, dengan latihan direkodkan dan belum ada momen Saling Membantu.';
  }

  @override
  String get glanceFocusNoPracticeYetMutualAid =>
      'Aktiviti forum dengan fokus yang jelas.';

  @override
  String glanceFocusNoPracticeYetMutualAidSupport(String focus) {
    return '$focus ialah fokus, dengan momen Saling Membantu dan belum ada latihan direkodkan.';
  }

  @override
  String get glanceFocusNoPracticeYet => 'Fokus yang jelas sudah sedia.';

  @override
  String glanceFocusNoPracticeYetSupport(String focus) {
    return '$focus ialah fokus. Bukti latihan masih dikumpulkan.';
  }

  @override
  String get glanceFocusNoPracticeYetNoMutualAidYet =>
      'Fokus yang jelas sudah sedia.';

  @override
  String glanceFocusNoPracticeYetNoMutualAidYetSupport(String focus) {
    return '$focus ialah fokus. Aktiviti latihan dan Saling Membantu masih dikumpulkan.';
  }

  @override
  String get glanceFocusMutualAid => 'Aktiviti forum dengan fokus yang jelas.';

  @override
  String glanceFocusMutualAidSupport(String focus) {
    return '$focus ialah fokus, dengan momen Saling Membantu direkodkan minggu ini.';
  }

  @override
  String get glanceFocusNoMutualAidYet => 'Fokus yang jelas sudah sedia.';

  @override
  String glanceFocusNoMutualAidYetSupport(String focus) {
    return '$focus ialah fokus, dengan belum ada momen Saling Membantu.';
  }

  @override
  String get glanceFocusOnly => 'Fokus yang jelas sudah sedia.';

  @override
  String glanceFocusOnlySupport(String focus) {
    return '$focus ialah fokus pembelajaran semasa.';
  }

  @override
  String get glancePracticeRecorded => 'Latihan direkodkan minggu ini.';

  @override
  String get glancePracticeRecordedSupport =>
      'Latihan diteruskan sementara lebih banyak bukti Pemahaman dikumpulkan.';

  @override
  String get glanceNoPracticeYet => 'Belum ada latihan disiapkan minggu ini.';

  @override
  String get glanceNoPracticeYetSupport =>
      'Satu latihan ringkas boleh memulakan rutin mingguan.';

  @override
  String get glanceMutualAidRecorded =>
      'Aktiviti Saling Membantu direkodkan minggu ini.';

  @override
  String get glanceMutualAidRecordedSupport =>
      'Lebih banyak bukti Pemahaman dan latihan masih dikumpulkan.';

  @override
  String get glanceNoMutualAidYet =>
      'Belum ada momen Saling Membantu minggu ini.';

  @override
  String get glanceNoMutualAidYetSupport =>
      'Lebih banyak bukti Pemahaman dan latihan masih dikumpulkan.';

  @override
  String get glanceNoDataYet => 'Bukti pembelajaran masih dikumpulkan.';

  @override
  String get glanceNoDataYetSupport =>
      'Kemas kini selamat akan muncul selepas latihan seterusnya disiapkan.';

  @override
  String get understandingCardTitle => 'Pemahaman';

  @override
  String get learningSnapshotLabel => 'Ringkasan pembelajaran';

  @override
  String get practiceCardTitle => 'Usaha Latihan';

  @override
  String get mutualAidCardTitle => 'Saling Membantu';

  @override
  String get conversationStarterTitle => 'Soalan ringkas untuk ditanya';

  @override
  String get focusStatusNeedsGuidedPractice => 'Memerlukan latihan terbimbing';

  @override
  String get focusStatusGrowing => 'Sedang berkembang';

  @override
  String get focusStatusCurrentStrength => 'Kekuatan semasa';

  @override
  String focusTopic(String topic) {
    return 'Topik: $topic';
  }

  @override
  String focusSubtopic(String subtopic) {
    return 'Fokus: $subtopic';
  }

  @override
  String focusObservationSentence(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: 'Berdasarkan $count pemerhatian pembelajaran yang dipercayai.',
      one: 'Berdasarkan 1 pemerhatian pembelajaran yang dipercayai.',
    );
    return '$_temp0';
  }

  @override
  String focusStrength(String subtopic) {
    return 'Kekuatan: $subtopic';
  }

  @override
  String get understandingInsufficient =>
      'Bukti pembelajaran yang lebih terkini diperlukan sebelum fokus dapat dinamakan.';

  @override
  String get understandingUnavailable =>
      'Pemahaman tidak tersedia buat sementara waktu.';

  @override
  String get parentNextStep => 'Langkah seterusnya untuk ibu bapa';

  @override
  String actionUnderstandingFocus(String subtopic) {
    return 'Berlatih $subtopic bersama minggu ini.';
  }

  @override
  String actionMaintainStrength(String subtopic) {
    return 'Kekalkan $subtopic dengan satu latihan ringkas.';
  }

  @override
  String get actionPracticeRoutine =>
      'Satu latihan ringkas minggu ini mengekalkan rutin.';

  @override
  String get actionMutualAidInvitation =>
      'Tanya sama ada rakan sekelas menjawab soalan matematik minggu ini.';

  @override
  String get actionNeedsMoreActivity =>
      'Lebih banyak aktiviti diperlukan sebelum cadangan boleh dibuat.';

  @override
  String practiceWeekly(int total) {
    String _temp0 = intl.Intl.pluralLogic(
      total,
      locale: localeName,
      other: '$total latihan disiapkan minggu ini',
      one: '1 latihan disiapkan minggu ini',
      zero: 'Tiada latihan disiapkan minggu ini',
    );
    return '$_temp0';
  }

  @override
  String practiceActiveDays(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count hari aktif',
      one: '1 hari aktif',
    );
    return 'sepanjang $_temp0';
  }

  @override
  String get practiceUnavailable => 'Usaha latihan tidak tersedia minggu ini.';

  @override
  String practiceComparison(int previous) {
    String _temp0 = intl.Intl.pluralLogic(
      previous,
      locale: localeName,
      other: '$previous latihan',
      one: '1 latihan',
    );
    return 'Berbanding $_temp0 minggu lalu.';
  }

  @override
  String practiceImproved(int difference) {
    return 'Latihan meningkat sebanyak $difference minggu ini.';
  }

  @override
  String get dayMonday => 'Isn';

  @override
  String get dayTuesday => 'Sel';

  @override
  String get dayWednesday => 'Rab';

  @override
  String get dayThursday => 'Kha';

  @override
  String get dayFriday => 'Jum';

  @override
  String get daySaturday => 'Sab';

  @override
  String get daySunday => 'Ahd';

  @override
  String mutualAidQuestions(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count soalan ditanya',
      one: '1 soalan ditanya',
    );
    return '$_temp0';
  }

  @override
  String mutualAidReplies(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count jawapan',
      one: '1 jawapan',
    );
    return '$_temp0';
  }

  @override
  String mutualAidAccepted(int count) {
    return ' · $count diterima';
  }

  @override
  String mutualAidHelpfulMarks(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count tanda membantu',
      one: '1 tanda membantu',
    );
    return '$_temp0';
  }

  @override
  String get mutualAidZero => 'Belum ada momen Saling Membantu minggu ini.';

  @override
  String get mutualAidUnavailable =>
      'Ringkasan penyertaan tidak tersedia minggu ini.';

  @override
  String conversationUnderstandingFocus(String subtopic) {
    return 'Bahagian $subtopic mana yang patut kita lihat bersama?';
  }

  @override
  String conversationMaintainStrength(String subtopic) {
    return 'Bolehkah kamu tunjukkan cara kamu menyelesaikan $subtopic?';
  }

  @override
  String get conversationPracticeRoutine =>
      'Bolehkah kita buat satu latihan ringkas bersama minggu ini?';

  @override
  String get conversationMutualAidInvitation =>
      'Adakah sesiapa di kelas membantu menjawab soalan matematik minggu ini?';

  @override
  String get conversationNeedsMoreActivity =>
      'Apa yang kamu seronok latih minggu ini?';
}
