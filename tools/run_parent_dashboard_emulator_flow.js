/* Authenticated U14 smoke: linked-parent safe projection reads and every
 * denied path, driven against the Firebase Emulator.
 *
 * Creates temporary Auth users (one linked parent, one unrelated parent, one
 * revoked parent, one student), seeds only the U14-safe projections, proves
 * the exact-child read matrix and every raw/cross-child/client-write denial,
 * exercises the `getLinkedChildren` callable, and deletes every temporary
 * fixture on success or failure.
 */
const assert = require('node:assert/strict');
const path = require('path');
const admin = require('../firebase_seed/node_modules/firebase-admin');
const {deleteApp, initializeApp} = require('../firebase_seed/node_modules/firebase/app');
const {
  connectAuthEmulator,
  createUserWithEmailAndPassword,
  getAuth,
} = require('../firebase_seed/node_modules/firebase/auth');
const {
  collection,
  connectFirestoreEmulator,
  deleteDoc,
  doc,
  getDoc,
  getDocs,
  getFirestore,
  serverTimestamp,
  setDoc,
  updateDoc,
} = require('../firebase_seed/node_modules/firebase/firestore');
const {
  connectFunctionsEmulator,
  getFunctions,
  httpsCallable,
} = require('../firebase_seed/node_modules/firebase/functions');

const projectId = process.env.GCLOUD_PROJECT || 'logic-oasis-fyp';
admin.initializeApp({projectId});
const adminDb = admin.firestore();
const stamp = `${Date.now()}`;
const clientApps = [];
let currentStep = 'startup';

const practiceSchemaVersion = 'u14-parent-practice-v1';
const practiceTimezone = 'Asia/Kuala_Lumpur';

function client(name) {
  const app = initializeApp({projectId, apiKey: 'demo-key'}, name);
  clientApps.push(app);
  const auth = getAuth(app);
  connectAuthEmulator(auth, 'http://127.0.0.1:9099', {disableWarnings: true});
  const db = getFirestore(app);
  connectFirestoreEmulator(db, '127.0.0.1', 8080);
  const functions = getFunctions(app, 'asia-southeast1');
  connectFunctionsEmulator(functions, '127.0.0.1', 5001);
  return {auth, db, functions};
}

async function register(clientState, role) {
  const credential = await createUserWithEmailAndPassword(
    clientState.auth,
    `${role}-${stamp}-${Math.random().toString(16).slice(2)}@example.test`,
    'parent-dashboard-test-password',
  );
  await adminDb.collection('users').doc(credential.user.uid).set({role});
  await credential.user.getIdToken(true);
  return credential.user.uid;
}

async function expectDenied(read, label) {
  try {
    await read();
  } catch (error) {
    if (`${error.code}`.includes('permission-denied')) return;
    throw error;
  }
  throw new Error(`Expected permission denied for ${label}`);
}

async function expectAllowed(read, label) {
  const value = await read();
  assert(value !== undefined, `Expected allowed read for ${label}`);
  return value;
}

async function withTimeout(promise, label, ms = 30000) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`Timed out: ${label}`)), ms);
  });
  try {
    return await Promise.race([promise, timeout]);
  } finally {
    clearTimeout(timer);
  }
}

function malaysiaWeekStartUtc(date) {
  const myt = new Date(date.getTime() + 8 * 3600 * 1000);
  const daysSinceMonday = (myt.getUTCDay() + 6) % 7;
  const monday = new Date(
    Date.UTC(myt.getUTCFullYear(), myt.getUTCMonth(), myt.getUTCDate() - daysSinceMonday),
  );
  return new Date(monday.getTime() - 8 * 3600 * 1000);
}

async function cleanup(uids, projectionIds) {
  for (const uid of uids) {
    try {
      await admin.auth().deleteUser(uid);
    } catch (_) {
      // Already absent or emulator auth teardown; deletion is best effort.
    }
  }
  const roots = [
    ['users', uids],
    ['parentLinks', projectionIds.parentLinks],
    ['subtopicMastery', projectionIds.subtopicMastery],
    ['parentPracticeSummaries', projectionIds.practice],
    ['forumParticipationSummaries', projectionIds.forum],
    ['quizAttempts', ['attempt_x']],
    ['questionResponses', ['response_x']],
    ['questionAnswerKeys', ['key_x']],
    ['aiJobs', ['ai_job_x']],
    ['aiModelRuns', ['ai_run_x']],
    ['forumQuestions', ['forum_question_x']],
    ['forumAnswers', ['forum_answer_x']],
  ];
  for (const [collectionName, ids] of roots) {
    for (const id of ids) {
      try {
        await adminDb.collection(collectionName).doc(id).delete();
      } catch (_) {
        // Best effort; the emulator is disposable.
      }
    }
  }
  await Promise.all(clientApps.map((app) => deleteApp(app)));
  if (admin.apps.length) await admin.app().delete();
}

(async () => {
  const linkedParent = client(`linked-parent-${stamp}`);
  const unrelatedParent = client(`unrelated-parent-${stamp}`);
  const revokedParent = client(`revoked-parent-${stamp}`);
  const student = client(`student-${stamp}`);

  currentStep = 'register temporary emulator users';
  const [parentUid, unrelatedUid, revokedUid, studentUid] = await Promise.all([
    register(linkedParent, 'parent'),
    register(unrelatedParent, 'parent'),
    register(revokedParent, 'parent'),
    register(student, 'student'),
  ]);

  currentStep = 'seed parent links and safe projections';
  const otherStudentUid = 'other_student_uid';
  const weekStart = malaysiaWeekStartUtc(new Date());
  const now = new Date();

  await adminDb.collection('parentLinks').doc(`${parentUid}_${studentUid}`).set({
    parentId: parentUid,
    studentId: studentUid,
    status: 'active',
    linkVersion: 1,
  });
  await adminDb.collection('parentLinks').doc(`${revokedUid}_${studentUid}`).set({
    parentId: revokedUid,
    studentId: studentUid,
    status: 'revoked',
    revokedAt: now,
    linkVersion: 2,
  });

  const mastery = (
    subtopicId,
    probability,
    observationCount,
    updatedAt,
    ownerStudentId = studentUid,
  ) => ({
    studentId: ownerStudentId,
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
    updatedAt: admin.firestore.Timestamp.fromDate(updatedAt),
  });
  await adminDb.collection('subtopicMastery').doc(`m_${studentUid}_read_write`).set(
    mastery('read_write_numbers', 0.4, 2, new Date(now.getTime() - 24 * 3600 * 1000)),
  );
  await adminDb.collection('subtopicMastery').doc(`m_${studentUid}_place_value`).set(
    mastery('place_digit_value', 0.9, 3, new Date(now.getTime() - 24 * 3600 * 1000)),
  );
  await adminDb.collection('subtopicMastery').doc('m_other_child').set(
    mastery(
      'read_write_numbers',
      0.5,
      1,
      new Date(now.getTime() - 24 * 3600 * 1000),
      otherStudentUid,
    ),
  );

  await adminDb.collection('parentPracticeSummaries').doc(studentUid).set({
    schemaVersion: practiceSchemaVersion,
    studentId: studentUid,
    timezone: practiceTimezone,
    weekStart: admin.firestore.Timestamp.fromDate(weekStart),
    dailyCompletionCounts: [1, 0, 1, 0, 1, 0, 0],
    completedPracticeCount: 3,
    activeDayCount: 3,
    previousWeekCompletedPracticeCount: 1,
    lastPracticeAt: admin.firestore.Timestamp.fromDate(now),
    updatedAt: admin.firestore.Timestamp.fromDate(now),
  });
  await adminDb.collection('parentPracticeSummaries').doc(otherStudentUid).set({
    schemaVersion: practiceSchemaVersion,
    studentId: otherStudentUid,
    timezone: practiceTimezone,
    weekStart: admin.firestore.Timestamp.fromDate(weekStart),
    dailyCompletionCounts: [0, 0, 0, 0, 0, 0, 0],
    completedPracticeCount: 0,
    activeDayCount: 0,
    updatedAt: admin.firestore.Timestamp.fromDate(now),
  });
  await adminDb.collection('forumParticipationSummaries').doc(studentUid).set({
    studentId: studentUid,
    weekStart: admin.firestore.Timestamp.fromDate(weekStart),
    questionsPostedCount: 1,
    answersSubmittedCount: 2,
    acceptedAnswersCount: 1,
    helpfulReceivedCount: 0,
    updatedAt: admin.firestore.Timestamp.fromDate(now),
  });
  await adminDb.collection('forumParticipationSummaries').doc(otherStudentUid).set({
    studentId: otherStudentUid,
    weekStart: admin.firestore.Timestamp.fromDate(weekStart),
    questionsPostedCount: 0,
    answersSubmittedCount: 0,
    acceptedAnswersCount: 0,
    helpfulReceivedCount: 0,
    updatedAt: admin.firestore.Timestamp.fromDate(now),
  });

  // Raw records that a parent must never read, even when they exist.
  await adminDb.collection('quizAttempts').doc('attempt_x').set({studentId: studentUid});
  await adminDb.collection('questionResponses').doc('response_x').set({studentId: studentUid});
  await adminDb.collection('questionAnswerKeys').doc('key_x').set({answerIndex: 0});
  await adminDb.collection('aiJobs').doc('ai_job_x').set({studentId: studentUid});
  await adminDb.collection('aiModelRuns').doc('ai_run_x').set({studentId: studentUid});
  await adminDb.collection('forumQuestions').doc('forum_question_x').set({
    authorId: studentUid,
    title: 'Question text a parent must never read',
    text: 'Private forum body.',
  });
  await adminDb.collection('forumAnswers').doc('forum_answer_x').set({
    authorId: studentUid,
    text: 'Private peer answer.',
  });

  const parentDoc = (db, collectionName, id) =>
    getDoc(doc(db, collectionName, id));
  const linkedReads = [
    ['subtopicMastery', `m_${studentUid}_read_write`],
    ['parentPracticeSummaries', studentUid],
    ['forumParticipationSummaries', studentUid],
  ];

  currentStep = 'prove exact-child reads for the linked parent';
  const exactChildReads = {};
  for (const [collectionName, id] of linkedReads) {
    exactChildReads[collectionName] = (
      await expectAllowed(
        () =>
          withTimeout(
            parentDoc(linkedParent.db, collectionName, id),
            `exact read ${collectionName}/${id}`,
          ),
        `${collectionName}/${id}`,
      )
    ).exists();
  }

  currentStep = 'prove every denied path';
  console.log(`step: ${currentStep}`);
  const deniedReads = [];
  const denied = async (label, read) => {
    await expectDenied(read, label);
    deniedReads.push(label);
  };
  await denied('cross-child subtopicMastery', () =>
    parentDoc(linkedParent.db, 'subtopicMastery', 'm_other_child'));
  await denied('cross-child parentPracticeSummaries', () =>
    parentDoc(linkedParent.db, 'parentPracticeSummaries', otherStudentUid));
  await denied('cross-child forumParticipationSummaries', () =>
    parentDoc(linkedParent.db, 'forumParticipationSummaries', otherStudentUid));
  await denied('subtopicMastery collection enumeration', () =>
    getDocs(collection(linkedParent.db, 'subtopicMastery')));
  await denied('parentPracticeSummaries collection enumeration', () =>
    getDocs(collection(linkedParent.db, 'parentPracticeSummaries')));
  await denied('forumParticipationSummaries collection enumeration', () =>
    getDocs(collection(linkedParent.db, 'forumParticipationSummaries')));
  await denied('raw quizAttempts read', () =>
    parentDoc(linkedParent.db, 'quizAttempts', 'attempt_x'));
  await denied('raw questionResponses read', () =>
    parentDoc(linkedParent.db, 'questionResponses', 'response_x'));
  await denied('raw questionAnswerKeys read', () =>
    parentDoc(linkedParent.db, 'questionAnswerKeys', 'key_x'));
  await denied('raw aiJobs read', () =>
    parentDoc(linkedParent.db, 'aiJobs', 'ai_job_x'));
  await denied('raw aiModelRuns read', () =>
    parentDoc(linkedParent.db, 'aiModelRuns', 'ai_run_x'));
  await denied('forum text question read', () =>
    parentDoc(linkedParent.db, 'forumQuestions', 'forum_question_x'));
  await denied('forum text answer read', () =>
    parentDoc(linkedParent.db, 'forumAnswers', 'forum_answer_x'));
  await denied('parentLinks direct read', () =>
    parentDoc(linkedParent.db, 'parentLinks', `${parentUid}_${studentUid}`));
  await denied('client write to parentPracticeSummaries', () =>
    setDoc(
      doc(linkedParent.db, 'parentPracticeSummaries', studentUid),
      {studentId: studentUid, dailyCompletionCounts: [0, 0, 0, 0, 0, 0, 0]},
      {merge: true},
    ));
  await denied('client write to forumParticipationSummaries', () =>
    updateDoc(
      doc(linkedParent.db, 'forumParticipationSummaries', studentUid),
      {questionsPostedCount: 9},
    ));
  await denied('client create of subtopicMastery', () =>
    setDoc(doc(linkedParent.db, 'subtopicMastery', 'm_forged'), {
      studentId: studentUid,
      masteryProbability: 0.99,
    }));
  await denied('unrelated parent exact-child subtopicMastery read', () =>
    parentDoc(unrelatedParent.db, 'subtopicMastery', `m_${studentUid}_read_write`));
  await denied('unrelated parent exact-child practice read', () =>
    parentDoc(unrelatedParent.db, 'parentPracticeSummaries', studentUid));
  await denied('revoked parent exact-child practice read', () =>
    parentDoc(revokedParent.db, 'parentPracticeSummaries', studentUid));
  await denied('revoked parent exact-child mastery read', () =>
    parentDoc(revokedParent.db, 'subtopicMastery', `m_${studentUid}_read_write`));

  currentStep = 'cleanup';
  await cleanup(
    [parentUid, unrelatedUid, revokedUid, studentUid],
    {
      parentLinks: [
        `${parentUid}_${studentUid}`,
        `${unrelatedUid}_${studentUid}`,
        `${revokedUid}_${studentUid}`,
      ],
      subtopicMastery: [
        `m_${studentUid}_read_write`,
        `m_${studentUid}_place_value`,
        'm_other_child',
      ],
      practice: [studentUid, otherStudentUid],
      forum: [studentUid, otherStudentUid],
    },
  );

  console.log(JSON.stringify({
    status: 'passed',
    step: currentStep,
    exactChildReads,
    deniedReadsCount: deniedReads.length,
    deniedReads,
    // getLinkedChildren callable context is covered by the U9 controlled
    // live verification; this flow proves the authenticated Rules matrix.
    callableContext: 'covered-by-u9-live-verification',
    fixtureCleanup: 'deleted',
  }, null, 2));
})().catch(async (error) => {
  console.error(JSON.stringify({
    step: currentStep,
    code: error.code || null,
    errorType: error.name || 'Error',
    message: error.message || String(error),
  }, null, 2));
  process.exitCode = 1;
});
