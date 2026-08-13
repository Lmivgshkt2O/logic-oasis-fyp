const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const {
  assertFails,
  assertSucceeds,
  initializeTestEnvironment,
} = require("@firebase/rules-unit-testing");
const {
  collection,
  deleteDoc,
  doc,
  getDoc,
  getDocs,
  onSnapshot,
  query,
  setDoc,
  serverTimestamp,
  updateDoc,
  where,
} = require("firebase/firestore");

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

      await setDoc(doc(adminDb, "users", "student_aiman_y4"), { role: "student" });
      await setDoc(doc(adminDb, "users", "student_other"), { role: "student" });
      await setDoc(doc(adminDb, "users", "parent_active"), { role: "parent" });

      await setDoc(doc(adminDb, "questions", "safe_q1"), {
        questionId: "safe_q1",
        questionText: "Which option is correct?",
        options: ["A", "B", "C", "D"],
        isActive: true,
      });

      await setDoc(doc(adminDb, "contentSourceManifest", "en_y4"), {
        materialId: "en_y4",
        filename: "Mathematics Year 4 SK (DLP).pdf",
        sha256: "private-material-checksum",
        authorId: "content-author-supervisor",
        reviewerId: "content-reviewer-supervisor",
        approvedAt: new Date(),
        questions: {
          safe_q1: { sourceLocator: "p. 3", contentDigest: "private-digest" },
        },
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
      await setDoc(doc(adminDb, "quizAttempts", "attempt_status_pending"), {
        attemptId: "attempt_status_pending", studentId: "student_aiman_y4",
        validationStatus: "finalized",
      });
      await setDoc(doc(adminDb, "adaptiveAssignments", "student_aiman_y4_read_write_numbers"), {
        studentId: "student_aiman_y4", subtopicId: "read_write_numbers", bankId: "bank_2",
      });
      await setDoc(doc(adminDb, "subtopicMastery", "student_aiman_y4_y4_whole_numbers_read_write_numbers"), {
        studentId: "student_aiman_y4", topicId: "whole_numbers_y4", subtopicId: "read_write_numbers",
      });
      await setDoc(doc(adminDb, "forumParticipationSummaries", "student_aiman_y4"), {
        studentId: "student_aiman_y4", questionsPostedCount: 1, answersSubmittedCount: 2,
        acceptedAnswersCount: 0, helpfulReceivedCount: 1,
      });
      await setDoc(doc(adminDb, "forumQuestions", "forum_q1"), {
        authorId: "student_aiman_y4", title: "How do I check my addition?",
        text: "I added the tens first. How can I check the result?", createdAt: new Date(), updatedAt: new Date(),
      });
      await setDoc(doc(adminDb, "forumAnswers", "forum_a1"), {
        questionId: "forum_q1", authorId: "student_other", text: "Use subtraction to check the total.", revision: 1, createdAt: new Date(), updatedAt: new Date(),
      });
      await setDoc(doc(adminDb, "forumAnswers", "forum_accepted"), {
        questionId: "forum_q1", authorId: "student_other", text: "I checked each place value carefully.",
        revision: 1, acceptedAt: new Date(), acceptedBy: "student_aiman_y4",
        createdAt: new Date(), updatedAt: new Date(),
      });
      await setDoc(doc(adminDb, "forumAnswers", "forum_legacy"), {
        questionId: "forum_q1", authorId: "student_other",
        text: "This older answer predates explicit revisions.",
        aiFeedback: {
          state: "completed", label: "clear", probability: 0.9,
          modelVersion: "forum-explanation-nb-v1",
          calibrationState: "not_calibrated",
          message: "Thanks for explaining your method.", revision: 1,
          logicalInferenceId: "legacy-run", updatedAt: new Date(),
        },
        createdAt: new Date(), updatedAt: new Date(),
      });
      await setDoc(doc(adminDb, "forumQuestions", "linked_forum_q1_v1"), {
        mode: "linked", sourceQuestionId: "safe_q1", sourceContentVersion: "v1",
        promptSnapshot: {
          questionText: "Which option is correct?", options: ["A", "B", "C", "D"],
        },
        title: "Which option is correct?", text: "Which option is correct?",
        createdAt: new Date(), updatedAt: new Date(),
      });
      await setDoc(doc(adminDb, "forumAnswers", "forum_linked_a1"), {
        questionId: "linked_forum_q1_v1", authorId: "student_other", mode: "linked",
        selectedOption: 1, explanation: "I compared each option with the question.",
        revision: 1, aiPublicState: "none", createdAt: new Date(), updatedAt: new Date(),
      });
      await setDoc(doc(adminDb, "forumAiFeedback", "forum_a1"), {
        answerId: "forum_a1", state: "completed", label: "needs_reasoning",
        message: "Private author-only guidance.", probability: 0.74, revision: 1,
        logicalInferenceId: "run-private", updatedAt: new Date(),
      });
      await setDoc(doc(adminDb, "forumAiFeedback", "forum_linked_a1"), {
        answerId: "forum_linked_a1", state: "completed", label: "sufficient_reasoning",
        message: "Private linked guidance.", probability: 0.9, revision: 1,
        logicalInferenceId: "run-private-linked", updatedAt: new Date(),
      });
      await setDoc(doc(adminDb, "forumReports", "student_other_question_forum_q1"), {
        reporterId: "student_other", targetType: "question", targetId: "forum_q1",
        reason: "This needs review.", status: "active", reviewState: "pending",
        createdAt: new Date(), updatedAt: new Date(),
      });
      await setDoc(doc(adminDb, "parentLinks", "parent_active_student_aiman_y4"), {
        parentId: "parent_active", studentId: "student_aiman_y4", status: "active",
      });
      await setDoc(doc(adminDb, "parentLinks", "parent_revoked_student_aiman_y4"), {
        parentId: "parent_revoked", studentId: "student_aiman_y4", status: "revoked",
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
    const linkedParentDb = testEnv.authenticatedContext("parent_active").firestore();
    const revokedParentDb = testEnv.authenticatedContext("parent_revoked").firestore();
    const otherParentDb = testEnv.authenticatedContext("parent_other").firestore();
    const anonymousDb = testEnv.unauthenticatedContext().firestore();
    const otherStudentDb = testEnv.authenticatedContext("student_other").firestore();

    await assertSucceeds(getDoc(doc(studentDb, "questions", "safe_q1")));
    await assertFails(getDoc(doc(anonymousDb, "questions", "safe_q1")));
    await assertFails(getDoc(doc(studentDb, "questionAnswerKeys", "safe_q1")));
    await assertFails(getDocs(collection(studentDb, "questionAnswerKeys")));
    await assertFails(getDoc(doc(studentDb, "contentSourceManifest", "en_y4")));
    await assertFails(getDocs(collection(studentDb, "contentSourceManifest")));
    await assertFails(
      setDoc(doc(studentDb, "questionAnswerKeys", "safe_q1"), {
        answerIndex: 0,
      }),
    );
    await assertFails(
      setDoc(doc(studentDb, "contentSourceManifest", "en_y4"), {
        materialId: "en_y4",
        filename: "forged.pdf",
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
    await assertSucceeds(getDoc(doc(studentDb, "studentAiStatuses", "attempt_status_pending")));
    await assertSucceeds(getDoc(doc(linkedParentDb, "studentAiStatuses", "attempt_status_pending")));
    await assertFails(getDoc(doc(otherParentDb, "studentAiStatuses", "attempt_status_pending")));
    await assertFails(getDoc(doc(studentDb, "studentAiStatuses", "attempt_unknown")));
    await assertSucceeds(getDocs(query(
      collection(linkedParentDb, "studentAiStatuses"),
      where("studentId", "==", "student_aiman_y4"),
    )));

    const pendingStatusRef = doc(
      studentDb,
      "studentAiStatuses",
      "attempt_status_pending",
    );
    let resolveMissingStatus;
    let resolveCreatedStatus;
    let rejectMissingStatus;
    let rejectCreatedStatus;
    const missingStatus = new Promise((resolve, reject) => {
      resolveMissingStatus = resolve;
      rejectMissingStatus = reject;
    });
    const createdStatus = new Promise((resolve, reject) => {
      resolveCreatedStatus = resolve;
      rejectCreatedStatus = reject;
    });
    const unsubscribeStatus = onSnapshot(
      pendingStatusRef,
      (snapshot) => {
        if (snapshot.exists()) {
          resolveCreatedStatus(snapshot);
        } else {
          resolveMissingStatus(snapshot);
        }
      },
      (error) => {
        rejectMissingStatus(error);
        rejectCreatedStatus(error);
      },
    );
    assert.equal((await missingStatus).exists(), false);
    await testEnv.withSecurityRulesDisabled(async (context) => {
      await setDoc(doc(context.firestore(), "studentAiStatuses", "attempt_status_pending"), {
        attemptId: "attempt_status_pending", studentId: "student_aiman_y4",
        analysisState: "processing", displayCode: "analysis_in_progress",
      });
    });
    const createdStatusSnapshot = await createdStatus;
    unsubscribeStatus();
    assert.equal(createdStatusSnapshot.data().analysisState, "processing");
    await assertSucceeds(getDoc(doc(studentDb, "adaptiveAssignments", "student_aiman_y4_read_write_numbers")));
    await assertSucceeds(getDoc(doc(linkedParentDb, "studentAiStatuses", "attempt_safe")));
    await assertSucceeds(getDoc(doc(linkedParentDb, "adaptiveAssignments", "student_aiman_y4_read_write_numbers")));
    await assertSucceeds(getDoc(doc(linkedParentDb, "subtopicMastery", "student_aiman_y4_y4_whole_numbers_read_write_numbers")));
    await assertFails(getDoc(doc(otherStudentDb, "subtopicMastery", "student_aiman_y4_y4_whole_numbers_read_write_numbers")));
    await assertSucceeds(getDoc(doc(linkedParentDb, "forumParticipationSummaries", "student_aiman_y4")));
    await assertFails(getDoc(doc(revokedParentDb, "studentAiStatuses", "attempt_safe")));
    await assertFails(getDoc(doc(otherParentDb, "forumParticipationSummaries", "student_aiman_y4")));
    await assertFails(getDoc(doc(linkedParentDb, "aiModelRuns", "attempt_safe")));
    await assertFails(getDoc(doc(linkedParentDb, "parentLinks", "parent_active_student_aiman_y4")));
    await assertFails(setDoc(doc(studentDb, "parentLinks", "student_aiman_y4_parent_other"), {
      parentId: "student_aiman_y4", studentId: "parent_other", status: "active",
    }));
    await assertFails(getDoc(doc(studentDb, "aiJobs", "attempt_safe")));
    await assertFails(getDoc(doc(studentDb, "aiModelRuns", "attempt_safe")));
    await assertFails(getDoc(doc(studentDb, "modelRegistry", "xgboost_v1")));
    await assertSucceeds(getDoc(doc(studentDb, "forumQuestions", "forum_q1")));
    await assertSucceeds(getDoc(doc(otherStudentDb, "forumAnswers", "forum_a1")));
    await assertFails(getDoc(doc(linkedParentDb, "forumQuestions", "forum_q1")));
    await assertFails(getDoc(doc(anonymousDb, "forumQuestions", "forum_q1")));
    await assertFails(getDoc(doc(linkedParentDb, "forumAnswers", "forum_a1")));
    await assertFails(getDoc(doc(linkedParentDb, "forumReports", "student_other_question_forum_q1")));
    await assertFails(getDoc(doc(linkedParentDb, "forumBlocks", "student_other_student_aiman_y4")));
    await assertFails(getDoc(doc(studentDb, "forumAiJobs", "forum_a1")));
    await assertFails(getDoc(doc(studentDb, "forumAiFeedback", "forum_a1")));
    await assertFails(getDoc(doc(otherStudentDb, "forumAiFeedback", "forum_a1")));
    await assertFails(getDoc(doc(linkedParentDb, "forumAiFeedback", "forum_a1")));
    await assertFails(getDoc(doc(studentDb, "forumAiFeedback", "forum_linked_a1")));
    await assertFails(getDoc(doc(studentDb, "forumAiFeedback", "guessed-private-id")));
    await assertFails(getDocs(collection(studentDb, "forumAiFeedback")));
    await assertFails(setDoc(doc(studentDb, "forumAiFeedback", "forum_a1"), {
      state: "pending", revision: 2, updatedAt: serverTimestamp(),
    }));
    await assertFails(setDoc(doc(studentDb, "forumQuestions", "linked_forum_q1_v1"), {
      mode: "linked", sourceQuestionId: "safe_q1", sourceContentVersion: "v1",
      promptSnapshot: {}, title: "Forged canonical thread", text: "Forged thread",
      createdAt: serverTimestamp(), updatedAt: serverTimestamp(),
    }));
    await assertFails(updateDoc(doc(studentDb, "forumQuestions", "linked_forum_q1_v1"), {
      title: "Changed canonical title", updatedAt: serverTimestamp(),
    }));
    await assertFails(setDoc(doc(studentDb, "forumAnswers", "forum_linked_a2"), {
      questionId: "linked_forum_q1_v1", authorId: "student_aiman_y4", mode: "linked",
      selectedOption: 0, explanation: "A forged structured answer.", revision: 1,
      createdAt: serverTimestamp(), updatedAt: serverTimestamp(),
    }));
    await assertFails(updateDoc(doc(studentDb, "forumAnswers", "forum_linked_a1"), {
      text: "A direct linked edit must fail.", revision: 2,
      aiFeedback: { state: "pending", label: "uncertain", message: "Pending.", revision: 2 },
      updatedAt: serverTimestamp(),
    }));
    await assertFails(updateDoc(doc(studentDb, "forumAnswers", "forum_linked_a1"), {
      selectedOption: 2, explanation: "A forged structured edit.",
      revision: 2, updatedAt: serverTimestamp(),
    }));
    await assertSucceeds(getDoc(doc(studentDb, "forumAnswers", "forum_linked_a1")));
    await assertSucceeds(getDoc(doc(otherStudentDb, "forumAnswers", "forum_linked_a1")));
    await assertSucceeds(setDoc(doc(studentDb, "forumQuestions", "forum_q2"), {
      authorId: "student_aiman_y4", title: "How can I check this answer?",
      text: "I tried grouping the numbers and need help checking it.",
      createdAt: serverTimestamp(), updatedAt: serverTimestamp(),
    }));
    await assertFails(setDoc(doc(otherStudentDb, "forumQuestions", "forum_q1"), {
      authorId: "student_other", title: "Changed question title", text: "This should not replace another learner question.", updatedAt: new Date(),
    }, { merge: true }));
    await assertSucceeds(setDoc(doc(studentDb, "forumAnswers", "forum_a2"), {
      questionId: "forum_q1", authorId: "student_aiman_y4",
      text: "I regrouped the ones and then checked the tens.", revision: 1,
      createdAt: serverTimestamp(), updatedAt: serverTimestamp(),
    }));
    await assertSucceeds(setDoc(doc(studentDb, "forumAnswers", "forum_legacy_create"), {
      questionId: "forum_q1", authorId: "student_aiman_y4",
      text: "This older client does not send an explicit revision field.",
      createdAt: serverTimestamp(), updatedAt: serverTimestamp(),
    }));
    await assertSucceeds(updateDoc(doc(studentDb, "forumAnswers", "forum_a2"), {
      text: "I regrouped the ones, checked the tens, and verified by subtraction.",
      revision: 2,
      aiFeedback: { state: "pending", label: "uncertain", message: "Your revised answer is being reviewed.", revision: 2 },
      updatedAt: serverTimestamp(),
    }));
    await assertFails(updateDoc(doc(studentDb, "forumAnswers", "forum_a1"), {
      text: "A foreign edit should be rejected.", revision: 2,
      aiFeedback: { state: "pending", label: "uncertain", message: "Pending.", revision: 2 },
      updatedAt: serverTimestamp(),
    }));
    await assertFails(updateDoc(doc(otherStudentDb, "forumAnswers", "forum_accepted"), {
      text: "Accepted answers cannot be changed.", revision: 2,
      aiFeedback: { state: "pending", label: "uncertain", message: "Pending.", revision: 2 },
      updatedAt: serverTimestamp(),
    }));
    await assertFails(updateDoc(doc(studentDb, "forumAnswers", "forum_a2"), {
      text: "This revision must not inject an arbitrary feedback payload.", revision: 3,
      aiFeedback: { state: "pending", label: "uncertain", message: { nested: "invalid" }, revision: 3 },
      updatedAt: serverTimestamp(),
    }));
    await assertFails(updateDoc(doc(otherStudentDb, "forumReports", "student_other_question_forum_q1"), {
      reason: "Duplicate reports converge here.", updatedAt: serverTimestamp(),
    }));
    await assertFails(updateDoc(doc(otherStudentDb, "forumReports", "student_other_question_forum_q1"), {
      reviewState: "resolved", updatedAt: serverTimestamp(),
    }));
    await assertFails(setDoc(doc(otherStudentDb, "forumReports", "student_other_answer_forum_a2"), {
      reporterId: "student_other", targetType: "answer", targetId: "forum_a2",
      reason: "Client-side reports are not trusted.", status: "active",
      createdAt: serverTimestamp(), updatedAt: serverTimestamp(),
    }));
    await assertSucceeds(updateDoc(doc(otherStudentDb, "forumAnswers", "forum_legacy"), {
      text: "This older answer can enter revision two safely.", revision: 2,
      aiFeedback: { state: "pending", label: "uncertain", message: "Your revised answer is being reviewed.", revision: 2 },
      updatedAt: serverTimestamp(),
    }));
    await assertSucceeds(setDoc(doc(studentDb, "forumBlocks", "student_aiman_y4_student_other"), {
      studentId: "student_aiman_y4", blockedStudentId: "student_other", createdAt: serverTimestamp(),
    }));
    await assertSucceeds(getDoc(doc(studentDb, "forumBlocks", "student_aiman_y4_student_other")));
    await assertFails(getDoc(doc(otherStudentDb, "forumBlocks", "student_aiman_y4_student_other")));
    await assertSucceeds(deleteDoc(doc(studentDb, "forumBlocks", "student_aiman_y4_student_other")));
    await assertFails(setDoc(doc(studentDb, "forumBlocks", "student_aiman_y4_student_aiman_y4"), {
      studentId: "student_aiman_y4", blockedStudentId: "student_aiman_y4", createdAt: serverTimestamp(),
    }));

    console.log("PASS: student can read safe questions/projections but cannot access answer keys, U3-R state, or U8 raw AI data.");
  } finally {
    await testEnv.cleanup();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
