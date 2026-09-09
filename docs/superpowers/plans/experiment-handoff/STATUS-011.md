# Status 011: max256 campaign admitted; later-stage integration

The owner approved a fixed 256-token ceiling for KU-S3a, its form twin and a new matched no-retrieval control. Preserve the original KC-S1b examples, frozen predecessor, DEV-1000 roster and completed max64 repeat. There is no pending owner decision.

## Active registered comparison

All three actual 1,000-row capacity checks passed in one root-owned decoder-only session with four 16,384-token slots. After reserving 256 output tokens, minimum margins are 6,122 (control), 5,927 (speech) and 5,917 (twin). The three contact journals contain 9,003 registered tokenizer endpoints and no generation or encoding. See `docs/readiness/2026-09-09-ku-s3-max256-registration/fit-completion.json`.

The common campaign entry now reads registered cells across experiment fragments. The committed order is control, speech, twin. All three generations were separately registered before launch. The queue overlaps one complete official scoring task with the next flight and retains per-sample statistics on the first score job. Read comparative outcomes only after all three generation bundles seal.

Frozen generation checkout: `/home/chao/saea-worktrees/g1-max256-runtime`, commit `024eb00a559ff383411d4ebdc43b731806098fb9`. Root service: `slurp-g1-max256-np4-20260909-root`. The launch receipt under `SPEECHRL_DATA_DIR/coordination/ku-s3-max256-campaign-v1.launch.json` gives the actual PID and command. The fit-batch wrapper remains alive solely to preserve the WSL resident session; root must stop service and monitor explicitly at the boundary. Do not infer live status from this document.

## Accepted engineering work

- Shared fit batching materializes all three request sets before model loading. This moved approximately 17 minutes of CPU work before the new service window.
- Queue selection defers later preflights once an admissible matching candidate is found. Its plan, readiness, queue, factory and max256 configuration checks passed (41 tests), with Ruff and the engineering-base check passing.
- Canonical master merged actual E21 raw-window fitting, including configured repair hooks, live slice/source bindings and the multimodal input-token endpoint. Merge review preserved the existing phase-batch handoff and implementation hashes. Across the focused suites, 111 tests pass after repairing two old phase-only interface compatibility failures; Ruff and engineering-base checks pass.
- The E21 DR successor has two explicit OJW baseline fragments. Only policy and workflow timeout differ from their legacy baseline fields. All four fit/generation cells compose, remain held and pin actual source hashes. Two generation parents declare constrained and free deliveries in advance. Full-window fits require 1,594 endpoints per parent, separately registered from generation.
- KU-S4N successor configurations retain the full 60-label inventory, add at most eight candidate blocks, pin the aligned null thresholds, and remain held. Four configuration tests pass. The synthetic direct fixture is not full candidate-request coverage.
- Historical E21 constrained replay is complete: all 1,593 windows and 44 stitched calls match byte-for-byte, including three saturated fallbacks. It consumed no new model, tokenizer, encoder or scorer contact.

## Efficiency limits

The new service window still incurs avoidable CPU waiting. A prepared capacity receipt currently triggers full request rematerialization in generation preflight, and packet preparation/validation is process-local. Exact durations must come from the stage and monitor receipts. No throughput or idle-time success claim is made. Improve shared reuse at a later frozen-run boundary; preserve full source/config/roster checks and the common controller/executor.

## Next work order

1. Complete and seal the max256 matched trio. Finish each official score exactly once. Bind only the pending manifest/score hashes in `slurp-ku-s3-max256-analysis-v1.json`, run its prospective paired analysis, and issue the scoped KU-S3 verdict with strata, row-mean/micro distinction, costs and failures.
2. Finish the common persistent preparation path for actual KU-S4N candidate supply, verify bank/snapshot bindings, register full-roster fits, and switch to the eight-slot decoder only after G1 closure. N and twin must both seal and score before the non-inferiority decision. No automatic rerun on failure.
3. Only after N passes non-inferiority, admit the registered exemplar encoding union, skip verified existing packets and encode missing recordings once. Then run a/b/c with the registered interpretation limits.
4. Use the reviewed E21 bridge to prepare and fit all actual DR/LOOP request groups. Prove current live execution, explicitly migrate LOOP configuration, unify the family budget, choose six or four slots for each complete comparison group, and run two DR generations with four deliveries followed by LOOP/twin.
5. Complete live full-system joins and bounded controller transitions, final analysis and handoff receipts. Depth-2 remains last. G2-G6 generation has not occurred.

Preserve historical worktrees and scoring source versions. All implementation, preparation, inference and scoring remain in WSL Ubuntu-24.04, with explicit checkout paths and no editable-package reinstall.
