# Successor 2: read qualification procedure (pre-registered; nothing has been read)

Pre-registered 2026-10-10 in the form of successor 1's `read-qualification-v1.md`
(`docs/readiness/2026-10-01-slurp-milestone-successor1-v1/read-qualification-v1.md`). Root qualifies the composed run BEFORE reading any scientific output:

1. The composed attempt is FINALIZED at 3,010 rows with a verified seal and exactly one successful official `slurp-slu-official-test` score; no failed jobs.
2. Fresh streamed hashes revalidate the final manifest and every referenced output, trace, trace manifest, score, serving receipt, generation manifest, phase summary and score-ledger artifact. Hashing does not interpret task content.
3. The two SEALED successor-1 columns (`SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-COMP1B-V1`, `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-PLAN-V1`) are revalidated against `docs/receipts/continuation/2026-10-01-milestone-successor1-pair-complete.json`; they are NOT re-flown, re-scored or re-read.
4. The shared reader's delivery check compares the arm's flown boundary sets with its own prepared supply (aggregate row equality and mismatch counts only; a mismatch is an engineering defect, never permission to rerun).
5. Root countersigns the READ row `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-PAIRED-ANALYSIS-V1` only for the registered comparison; the driver `scripts/flights/nx/milestone_successor2_read.sh` refuses before any score is opened otherwise.

No test evidence may enter the system-text optimizer, proposer inputs, candidate selection or tuning. No allowance or scientific threshold changes.
