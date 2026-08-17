/* U14 live rehearsal seed: persistent linked parent + four-state fixtures for
 * the manual emulator rehearsal and live screenshots.
 *
 * Requires the Firebase Emulator Suite to be running (Auth 9099, Firestore
 * 8080). It creates (idempotently) a linked parent, a student profile, an
 * active parentLinks document, and the approved projections, then mutates
 * them between captures. `--cleanup` deletes every seeded identity and
 * document; `--verify` prints the current fixture state.
 */
const admin = require('../firebase_seed/node_modules/firebase-admin');

process.env.GCLOUD_PROJECT ||= 'logic-oasis-fyp';
process.env.FIREBASE_AUTH_EMULATOR_HOST ||= '127.0.0.1:9099';
process.env.FIRESTORE_EMULATOR_HOST ||= '127.0.0.1:8080';

const projectId = process.env.GCLOUD_PROJECT;
admin.initializeApp({projectId});
const adminDb = admin.firestore();
const adminAuth = admin.auth();

const PARENT_EMAIL = 'parent-live@example.test';
const PARENT_PASSWORD = 'parent-dashboard-test-password';
const PARENT_UID = 'live_parent';
const STUDENT_UID = 'live_student';

const practiceSchemaVersion = 'u14-parent-practice-v1';
const practiceTimezone = 'Asia/Kuala_Lumpur';

const masteryRefs = [
  ['read_write_numbers', 0.4, 2],
  ['place_digit_value', 0.9, 3],
].map(([subtopicId, probability, observationCount]) => ({
  ref: adminDb.collection('subtopicMastery').doc(`m_${STUDENT_UID}_${subtopicId}`),
  subtopicId,
  probability,
  observationCount,
}));

const practiceRef = adminDb
  .collection('parentPracticeSummaries')
  .doc(STUDENT_UID);
const forumRef = adminDb
  .collection('forumParticipationSummaries')
  .doc(STUDENT_UID);
const linkRef = adminDb
  .collection('parentLinks')
  .doc(`${PARENT_UID}_${STUDENT_UID}`);

function malaysiaWeekStartUtc(now) {
  const myt = new Date(now.getTime() + 8 * 3600 * 1000);
  const monday = new Date(
    Date.UTC(
      myt.getUTCFullYear(),
      myt.getUTCMonth(),
      myt.getUTCDate() - ((myt.getUTCDay() + 6) % 7),
    ),
  );
  return new Date(monday.getTime() - 8 * 3600 * 1000);
}

function masteryData(subtopicId, probability, observationCount, now) {
  return {
    studentId: STUDENT_UID,
    yearLevel: 4,
    topicId: 'whole_numbers_y4',
    subtopicId,
    completed: true,
    masteryLevel: 'Moderate',
    bestCorrectRate: 0.6,
    attempted: true,
    accessUnlocked: true,
    masteryProbability: probability,
    evidenceLevel: 'established',
    observationCount,
    updatedAt: admin.firestore.Timestamp.fromDate(
      new Date(now.getTime() - 24 * 3600 * 1000),
    ),
  };
}

function practiceData(now, {zero = false, previousWeek = 1} = {}) {
  const daily = zero
    ? [0, 0, 0, 0, 0, 0, 0]
    : [1, 0, 1, 0, 1, 0, 0];
  const data = {
    schemaVersion: practiceSchemaVersion,
    studentId: STUDENT_UID,
    timezone: practiceTimezone,
    weekStart: admin.firestore.Timestamp.fromDate(
      malaysiaWeekStartUtc(now),
    ),
    dailyCompletionCounts: daily,
    completedPracticeCount: daily.reduce((sum, value) => sum + value, 0),
    activeDayCount: daily.filter((value) => value > 0).length,
    updatedAt: admin.firestore.Timestamp.fromDate(now),
  };
  if (!zero) {
    data.lastPracticeAt = admin.firestore.Timestamp.fromDate(now);
  }
  if (previousWeek !== null) {
    data.previousWeekCompletedPracticeCount = previousWeek;
  }
  return data;
}

function forumData(now, {zero = false} = {}) {
  return {
    studentId: STUDENT_UID,
    weekStart: admin.firestore.Timestamp.fromDate(
      malaysiaWeekStartUtc(now),
    ),
    questionsPostedCount: zero ? 0 : 1,
    answersSubmittedCount: zero ? 0 : 2,
    acceptedAnswersCount: zero ? 0 : 1,
    helpfulReceivedCount: 0,
    updatedAt: admin.firestore.Timestamp.fromDate(now),
  };
}

async function ensureUsers() {
  const created = [];
  for (const [uid, email, password, role, displayName, yearLevel] of [
    [PARENT_UID, PARENT_EMAIL, PARENT_PASSWORD, 'parent', 'Live Parent', null],
    [STUDENT_UID, 'student-live@example.test', PARENT_PASSWORD, 'student', 'Aiman', 4],
  ]) {
    let exists = true;
    try {
      await adminAuth.getUser(uid);
    } catch (_) {
      exists = false;
    }
    if (!exists) {
      await adminAuth.createUser({uid, email, password, displayName});
      created.push(uid);
    }
    const profile = {role, email, createdAt: new Date()};
    if (displayName) profile.displayName = displayName;
    if (yearLevel !== null) profile.yearLevel = yearLevel;
    await adminDb.collection('users').doc(uid).set(profile);
  }
  return created;
}

async function ensureLink() {
  await linkRef.set({
    parentId: PARENT_UID,
    studentId: STUDENT_UID,
    status: 'active',
    linkVersion: 1,
    updatedAt: admin.firestore.Timestamp.now(),
  });
}

async function writeFullFixtures({previousWeek = 1} = {}) {
  const now = new Date();
  for (const {ref, subtopicId, probability, observationCount} of masteryRefs) {
    await ref.set(masteryData(subtopicId, probability, observationCount, now));
  }
  await practiceRef.set(practiceData(now, {previousWeek}));
  await forumRef.set(forumData(now));
}

async function applyState(state) {
  const now = new Date();
  if (state === 'full') {
    await writeFullFixtures();
  } else if (state === 'partial') {
    await writeFullFixtures({previousWeek: null});
  } else if (state === 'zero') {
    for (const {ref} of masteryRefs) await ref.delete();
    await practiceRef.set(practiceData(now, {zero: true, previousWeek: null}));
    await forumRef.set(forumData(now, {zero: true}));
  } else if (state === 'insufficient') {
    for (const {ref} of masteryRefs) await ref.delete();
    await practiceRef.delete();
    await forumRef.delete();
  } else if (state === 'card-missing') {
    await writeFullFixtures();
    await forumRef.delete();
  } else if (state === 'revoked') {
    await writeFullFixtures();
    await linkRef.update({status: 'revoked', revokedAt: admin.firestore.Timestamp.now(), updatedAt: admin.firestore.Timestamp.now(), linkVersion: 2});
  } else {
    throw new Error(`Unknown state: ${state}`);
  }
}

async function verifyState() {
  const now = new Date();
  const masterySnapshots = await Promise.all(
    masteryRefs.map(async ({ref, subtopicId}) => ({
      subtopicId,
      exists: (await ref.get()).exists,
    })),
  );
  const practice = await practiceRef.get();
  const forum = await forumRef.get();
  const link = await linkRef.get();
  const practiceDataOut = practice.exists ? practice.data() : null;
  const forumDataOut = forum.exists ? forum.data() : null;
  return {
    parentUser: (await adminAuth.getUser(PARENT_UID).catch(() => null))?.uid,
    link: link.exists ? link.data().status : null,
    mastery: masterySnapshots,
    practice: practiceDataOut
      ? {
          completedPracticeCount: practiceDataOut.completedPracticeCount,
          activeDayCount: practiceDataOut.activeDayCount,
          previousWeekCompletedPracticeCount:
            practiceDataOut.previousWeekCompletedPracticeCount ?? null,
        }
      : null,
    forum: forumDataOut
      ? {
          questionsPostedCount: forumDataOut.questionsPostedCount,
          answersSubmittedCount: forumDataOut.answersSubmittedCount,
          acceptedAnswersCount: forumDataOut.acceptedAnswersCount,
        }
      : null,
  };
}

async function cleanup() {
  const deletes = [];
  for (const uid of [PARENT_UID, STUDENT_UID]) {
    deletes.push(
      adminAuth
        .deleteUser(uid)
        .then(() => `user:${uid}`)
        .catch((error) =>
          error.code === 'auth/user-not-found'
            ? null
            : Promise.reject(error),
        ),
      adminDb
        .collection('users')
        .doc(uid)
        .delete()
        .then(() => `users:${uid}`),
    );
  }
  for (const {ref} of masteryRefs) {
    deletes.push(ref.delete().then(() => `subtopicMastery:${ref.id}`));
  }
  deletes.push(
    linkRef.delete().then(() => 'parentLinks'),
    practiceRef.delete().then(() => 'parentPracticeSummaries'),
    forumRef.delete().then(() => 'forumParticipationSummaries'),
  );
  const removed = (await Promise.all(deletes)).filter(Boolean);
  return {removed};
}

(async () => {
  const args = process.argv.slice(2);
  if (args.includes('--cleanup')) {
    const result = await cleanup();
    console.log(JSON.stringify({status: 'cleaned', ...result}, null, 2));
    return;
  }
  const stateIndex = args.indexOf('--state');
  const state = stateIndex >= 0 ? args[stateIndex + 1] : null;
  if (state) {
    const createdUsers = await ensureUsers();
    await ensureLink();
    await applyState(state);
    const verification = await verifyState();
    console.log(
      JSON.stringify(
        {
          status: 'seeded',
          state,
          createdUsers,
          parentEmail: PARENT_EMAIL,
          parentPassword: PARENT_PASSWORD,
          ...verification,
        },
        null,
        2,
      ),
    );
    return;
  }
  if (args.includes('--verify')) {
    const verification = await verifyState();
    console.log(JSON.stringify({status: 'verified', ...verification}, null, 2));
    return;
  }
  throw new Error(
    'Usage: node tools/seed_parent_dashboard_live.js --state full|partial|zero|insufficient|card-missing|revoked | --cleanup | --verify',
  );
})().catch((error) => {
  console.error(JSON.stringify({status: 'failed', message: error.message}, null, 2));
  process.exitCode = 1;
});
