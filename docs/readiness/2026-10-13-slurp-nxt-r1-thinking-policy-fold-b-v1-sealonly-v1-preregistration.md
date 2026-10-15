# NX-T R1: SEAL-ONLY completion of the stopped column (preregistration note)

Status: **REGISTERED_BEFORE_CONTACT_SEAL_ONLY_PENDING_OWNER_DECISION_320** (owner decision 320 A (coordinator's proposal of 2026-10-15, PENDING the owner's answer): seal-only the complete rows of the stopped NX-T R1 column, read at the complete-row n, report the failing row and the never-started rows by count, close the cell). Written with zero model, tokenizer, encoder, scorer, server and GPU contacts. No utterance text, transcript, gold label, column value or
model output is printed or persisted: ids, counts and hashes only.

This note addends the NX-T R1 registration [`2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1/`](2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1/) and its preregistration, which are **not edited**. Everything they fix stands unchanged:
the question (which nodes of the locked Thinking system need thinking), the five arms, the node words against the in-flight twin offset, the floors, the claim ceiling `nominated`
and the prohibitions -- except the roster: n is the number of complete rows.

1. **What stopped.** The rec1 column attempt completed 1,029 of 1,080 rows and stopped on a non-delivering arm's finite completion
   (RailsRunnerError: perception branch 'both-off' sealed no level-2 Solver column). Root cause and fix: the package README.
2. **The completion.** A new attempt `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-sealonly-v1` under the same run id, resume_from the stopped attempt by trace sha256 `3238cd8aedb50c8a142b15e321070ffc7cf2cd055088fdcb0aee83d8a0895835`; the roster is the 1,029 complete rows;
   zero new model contacts; run-cumulative spend unchanged.
3. **Reading.** The paired contrasts run at n = 1,029 (the complete rows). The READ reports by count: the failing row (1), the
   50 never-started rows, and the absent Solver columns per arm (an arm's delivery failure, scored as the canonical empty answer).
   Development numbers only (owner decisions 28 and 86); never a test claim; `claims_benefit` false.
4. **Closing.** The cell closes at the seal and the read; there is no further registration.
