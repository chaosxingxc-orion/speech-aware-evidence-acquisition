# Continuation status after max256 preparation

Date: 2026-09-09. Coordinator: Codex. WSL Ubuntu-24.04 only.

## Accepted decisions

- Retain the original KC-S1b examples and test incremental retrieval.
- Keep the completed original 64-token repeat and the bounded four-case comparison unchanged.
- Use 256 tokens for KU-S3a, its form twin and one new matched no-retrieval control, each on the same frozen 1,000-row roster.
- Do not enable a reasoning prompt or switch frozen weights. The four-case evidence shows two resolved truncations, not an accuracy or reasoning improvement.
- No owner question is currently pending. Capacity checks and source verification are implementation work within this approval.

## Completed since STATUS-009

All three max256 configurations are merged. Their six final fit/generation attempt IDs are fixed. Separate complete-roster fit plans admit 3,001 tokenizer endpoints per arm, with zero generation; the old unconsumed max64 KU-S3 plans are preserved and are not reused.

The two final retrieval artifacts each cover 1,000 rows. Their ordered selected values and actual shared-runner supply bytes are identical to the original prepared artifacts. Current runtime consumption succeeds with selection computation replaced by a failure sentinel: warm consumption invokes no producer. The provisional max256 artifacts remain immutable; final artifacts bind the assigned attempt identities.

A shared batch capacity entry prepares all actual requests before the first model attachment. It keeps those requests immutable in memory and revalidates configuration, source, roster and run identity before fitting. Each arm still uses the existing exclusive lease, registered execution gate, tokenizer path and persistent fit receipt. Failure stops dispatch without automatic restart or replay. Validation: 59 focused tests, Ruff and engineering-base checks passed.

## Active work

The root capacity batch uses the frozen checkout /home/chao/saea-worktrees/g1-max256-runtime. The source commit is recorded in state.json. The planned new resident session is slurp-g1-max256-np4-20260909-root, with four slots and 65,536 total context tokens. All three groups retain a 256-token completion reserve.

Read current state from speechrl-data/coordination/ku-s3-max256-fit-batch-v1.json.events.jsonl and the session receipts. The initial state at this update is CPU request materialization; this document does not claim a capacity pass or generation start. Root keeps service ownership; experiment workers only attach.

## Next execution order

1. Complete all three full-roster actual-request fits. If any request fails, stop and diagnose the named capacity issue; do not shrink the output ceiling or change only one comparison arm.
2. Bind passing fit receipts and register generation separately. Advance the frozen checkout only at the fit-to-generation boundary.
3. Run the matched no-retrieval control, speech arm and form twin serially on the same resident identity. Each covers all 1,000 rows. Preserve raw responses and output hashes; score each complete sealed manifest once, retaining per-sample statistics.
4. Read the registered contrasts after the trio is sealed. Use historically exposed NEW500 as primary and report OLD500/pooled results, original scenario bootstrap plus speaker sensitivity, natural and equal-stratum weighting. Treat the old 64-token KC repeat as descriptive across completion ceilings.
5. Close KU-S3 and inherited replication obligations. Continue the queued KU-S4N and twin with all 60 labels. Only a passing non-inferiority gate opens exemplar encoding and a/b/c.
6. Complete E21 current-executor and actual-window fit review, all 1,593-window/44-call constrained replay checks, and bounded controller transitions. Then execute two DR generations/four deliveries and LOOP/twin under its prospectively registered budget.
7. Verify live SLURP/E21 system state transfers and complete-system cost. Depth-2 remains last.

## Remaining limits

The new fit batch removes repeated request construction between capacity checks. It is not persistent cross-process packet validation, and generation still has separate preprocessing costs. Measure those costs rather than claiming the idle-time target is already met.

G2 through G6 have not flown. E21 and KU-S4 worktrees remain available for root review. Full live state joins, broader engineering enforcement and complete system baselines remain open. No new Audio2Tool, E22, LP-2, enhancement or Stage-3 work is admitted.
