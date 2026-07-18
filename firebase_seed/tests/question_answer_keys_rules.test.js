const fs = require("node:fs");
const path = require("node:path");
const {
  assertFails,
  assertSucceeds,
  initializeTestEnvironment,
} = require("@firebase/rules-unit-testing");
const { collection, doc, getDoc, getDocs, setDoc } = require("firebase/firestore");

async function main() {
  const testEnv = await initializeTestEnvironment({
    projectId: "logic-oasis-fyp",
    firestore: {
      rules: fs.readFileSync(
        path.resolve(__dirname, "../../firestore.rules"),
        "utf8",
      ),
    },
  });

  try {
    await testEnv.withSecurityRulesDisabled(async (context) => {
      const adminDb = context.firestore();

      await setDoc(doc(adminDb, "questions", "safe_q1"), {
        questionId: "safe_q1",
        questionText: "Which option is correct?",
        options: ["A", "B", "C", "D"],
        isActive: true,
      });

      await setDoc(doc(adminDb, "questionAnswerKeys", "safe_q1"), {
        questionId: "safe_q1",
        answerIndex: 1,
        explanation: "Protected server-only explanation.",
      });

      await setDoc(
        doc(
          adminDb,
          "studentSubtopicSequenceStates",
          "student_aiman_y4",
          "subtopics",
          "read_write_numbers",
        ),
        { lastAllocatedSequence: 2 },
      );

      await setDoc(doc(adminDb, "studentAiStatuses", "attempt_safe"), {
        attemptId: "attempt_safe", studentId: "student_aiman_y4",
        analysisState: "completed", displayCode: "analysis_completed",
      });
      await setDoc(doc(adminDb, "adaptiveAssignments", "student_aiman_y4_read_write_numbers"), {
        studentId: "student_aiman_y4", subtopicId: "read_write_numbers", bankId: "bank_2",
      });
      await setDoc(doc(adminDb, "aiJobs", "attempt_safe"), {
        studentId: "student_aiman_y4", errorCode: "model_load_failed",
      });
      await setDoc(doc(adminDb, "aiModelRuns", "attempt_safe"), {
        studentId: "student_aiman_y4", shapValues: { correct_rate: -0.2 },
      });
      await setDoc(doc(adminDb, "modelRegistry", "xgboost_v1"), {
        artifactPath: "models/private.joblib", artifactSha256: "private",
      });
    });

    const studentDb = testEnv.authenticatedContext("student_aiman_y4").firestore();
    const anonymousDb = testEnv.unauthenticatedContext().firestore();

    await assertSucceeds(getDoc(doc(studentDb, "questions", "safe_q1")));
    await assertFails(getDoc(doc(anonymousDb, "questions", "safe_q1")));
    await assertFails(getDoc(doc(studentDb, "questionAnswerKeys", "safe_q1")));
    await assertFails(getDocs(collection(studentDb, "questionAnswerKeys")));
    await assertFails(
      setDoc(doc(studentDb, "questionAnswerKeys", "safe_q1"), {
        answerIndex: 0,
      }),
    );
    await assertFails(
      getDoc(
        doc(
          studentDb,
          "studentSubtopicSequenceStates",
          "student_aiman_y4",
          "subtopics",
          "read_write_numbers",
        ),
      ),
    );
    await assertFails(
      setDoc(
        doc(
          studentDb,
          "studentSubtopicSequenceStates",
          "student_aiman_y4",
          "subtopics",
          "read_write_numbers",
        ),
        { lastAllocatedSequence: 99 },
      ),
    );
    await assertSucceeds(getDoc(doc(studentDb, "studentAiStatuses", "attempt_safe")));
    await assertSucceeds(getDoc(doc(studentDb, "adaptiveAssignments", "student_aiman_y4_read_write_numbers")));
    await assertFails(getDoc(doc(studentDb, "aiJobs", "attempt_safe")));
    await assertFails(getDoc(doc(studentDb, "aiModelRuns", "attempt_safe")));
    await assertFails(getDoc(doc(studentDb, "modelRegistry", "xgboost_v1")));

    console.log("PASS: student can read safe questions/projections but cannot access answer keys, U3-R state, or U8 raw AI data.");
  } finally {
    await testEnv.cleanup();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
