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

    console.log("PASS: student can read safe questions but cannot access answer keys or U3-R sequence state.");
  } finally {
    await testEnv.cleanup();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
