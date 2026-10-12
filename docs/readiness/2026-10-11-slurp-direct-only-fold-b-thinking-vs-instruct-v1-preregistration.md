# Preregistration -- cell 266-E: the bare-core read on TRAIN Fold B, Thinking versus Instruct

Registered 2026-10-11 before any contact, at study commit `a057eea1d9479a8220dfe9b44d817faa1ec2a7a8`. Owner decision 266-E. Package `docs/readiness/2026-10-11-slurp-direct-only-fold-b-thinking-vs-instruct-v1/`.

## 1. Question and design

Does the Thinking core move the official SLU-F1 on TRAIN Fold B (1,080 rows, discovery role) by more than the cross-flight bar (about 2.5 pp) over the
Instruct core, with the system held out entirely? Same form on both cores (direct-only program, closed-list instruction, same roster and order); the only
differences are the core, its own packet root, the completion cap 8192 and `--reasoning-format deepseek`. Cross-session by necessity, so the Instruct arm
flies twice in the chain and the Thinking delta is read against the mean of the two. All numbers are development numbers (owner decisions 28 and 86).

## 2. Measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-REPLICATE-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The Instruct arm and its request-identical replicate measure the same-core offset the Thinking delta is read against; expected_effect_pp is 0.0 because a request-identical pair is registered to look for no effect and claims_benefit is false because the read is a capability measurement, not an admission.",
      "primary_metric": "official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official-train, the pinned official evaluate.py), natural-mixture weighting, with intent accuracy (scenario_action) beside it",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "replicate_run_id": "SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-V1",
      "rows": 1080,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The Instruct arm and its request-identical replicate measure the same-core offset the Thinking delta is read against; expected_effect_pp is 0.0 because a request-identical pair is registered to look for no effect and claims_benefit is false because the read is a capability measurement, not an admission.",
      "primary_metric": "official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official-train, the pinned official evaluate.py), natural-mixture weighting, with intent accuracy (scenario_action) beside it",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "replicate_run_id": "SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-REPLICATE-V1",
      "rows": 1080,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "The four-row smoke seals and reports decode cost (tokens per answer, seconds per contact, GPU-hour projection) before the Thinking arm is queued; under instrument rule 5 four rows are a form proof by size and claim nothing.",
      "primary_metric": "none: a four-row decode-cost smoke reads no metric",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 2.5,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "Core capability, not a system claim: expected effect = the cross-flight bar (about 2.5 pp SLU-F1 at n = 1,080), the smallest delta the cross-session design can resolve; the Thinking core is read against the mean of the two request-identical Instruct passes of the same chain and is resolved only above that bar (owner decision 266-E: a stronger core is expected to show more than that or the line closes).",
      "primary_metric": "official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official-train, the pinned official evaluate.py), natural-mixture weighting, with intent accuracy (scenario_action) beside it",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "replicate_run_id": "SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-REPLICATE-V1",
      "rows": 1080,
      "tuning_roster": "none"
    }
  }
}
```

## 3. Read rules (fixed here, before contact)

* **Estimand.** `d` = SLU-F1(Thinking) minus the mean of SLU-F1(Instruct) and SLU-F1(Instruct replicate), each pooled micro over the resampled utterance
  clusters (official evaluate.py per-sample counts, scorer `slurp-slu-official-train`); the same on intent accuracy (`scenario_action` exact, per-row mean). The
  twin offset `o` = replicate minus Instruct, with its CI95.
* **Interval.** Utterance-cluster bootstrap, 10,000 draws, seed 20261011, CI95; saves / harms / ties on the per-row metrics.
* **Verdict words.**
  * `RESOLVED-ABOVE-BAR`: `d >= 2.5` pp AND the CI95 lower bound of `d` is greater than `|o|` AND the reasoning-leak count is 0.
  * `HARM`: `d <= -2.5` pp AND the CI95 upper bound of `d` is below `-|o|`.
  * `NOT RESOLVED`: every other outcome. A cap-hit or parse-failure explanation is reported in the tables and never adjusted away.
  If the verdict is `NOT RESOLVED` or `HARM`, the Thinking-core line closes (owner decision 266-E).
* **Tables.** Paired per-row official SLU-F1 and intent; the twin offset; the per-scenario table (18 scenarios from the roster's stratum; natural-mixture and
  equal-scenario weightings); the Thinking answer-length table (completion tokens p10/p50/p90/p99/max, cap-hit count) and parse-failure table (empty delivered
  content; no JSON object); the reasoning-leak guard count over all three arms (count only); cost (contacts per minute, seconds per contact p50/p99, GPU hours per 1,000 rows).
* **Privacy.** No utterance text, transcript, gold label, model output or reasoning text is printed or persisted.

## 4. Stop rules

A response whose delivered content carries a reasoning marker stops the flight (`reasoning_content_guard`). The Thinking arm does not open before the
smoke has sealed and `/home/chao/direct-fb-decode-signoff.marker` exists. At most one root-diagnosed recovery re-registration per run id; a second failure closes the cell.

## 5. Findings recorded before contact

The audio-encoder tensors of the two mmproj files differ: 748 of 860 tensors are not byte-identical (name-for-name comparison of the GGUF tensor tables of mmproj-Qwen3-Omni-30B-A3B-Instruct-bf16.gguf and mmproj-Qwen3-Omni-30B-A3B-Thinking-bf16.gguf; the 112 identical tensors are the non-audio ones). The Instruct speech-feature packets (/home/chao/feat-cache/slurp-q4km-packets-04ccc72a) are decoder-ready projector outputs of the Instruct encoder and are therefore NOT valid input for the Thinking decoder. The Thinking core needs its OWN packet root (/home/chao/feat-cache/slurp-q4km-packets-thinking-gpu-afdaeff6) prepared by a GPU encoder pass over TRAIN Fold B inside a serving-swap window (registered, held: ledger row SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-GPU-V1, fragment q4km-thinking-feature-preprocess-gpu-np1-v1; it supersedes the CPU sidecar run SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-V1, stopped after 50 rows at 16-19 s per row); the Thinking baselines pin its future promotion receipt with a zero sentinel the flip refuses.

Reasoning stays out of the delivered content by the server flag --reasoning-format deepseek (registered explicitly in the serving fragment's server_args). Evidence from the pinned featcache build 04ccc72a2 (read-only grep): tools/server/README.md line 220 documents the option (none leaves thoughts in message.content; deepseek puts thoughts in message.reasoning_content; deepseek-legacy keeps <think> in content AND fills reasoning_content); common/arg.cpp line 3130 defines it; common/common.h line 622 makes COMMON_REASONING_FORMAT_DEEPSEEK the build's own default; common/chat.cpp line 828 maps it. The transport (core/model/transport.py) reads ONLY choices[0].message.content (and tool_calls); it never reads reasoning_content. The cells set preserve_wire_responses false, so no raw wire bytes (which would carry reasoning_content) are persisted. Client-side guard: the fragment declares reasoning_content_guard refuse-think-marker-in-content, and the transport raises FrozenCoreError when a delivered content string carries <think>, </think>, <thinking> or </thinking> (case-insensitive), BEFORE anything is returned or persisted; the flight stops (a leak means the option is not effective). The reader counts leak markers in the sealed delivered text (count only) as a second check.

Completion cap 8192 tokens (amended from 2048 at the decode-cost sign-off of 2026-10-11, the one re-registration this finding pre-authorised). Slot budget: -c 98304 / -np 4 = 24,576 tokens per slot. The direct-only prompt is about 2,300 tokens per row (the sealed Instruct direct form measured 2,262 to 2,280 prompt tokens per contact; 3,733 on the A2T registry). 2,300 + 8,192 = 10,492 tokens, 42.7 percent of a slot, so the cap is still bound by decode cost, not by the slot. The first cap, 2048, was proposed because a SLURP answer is a short structured object, so a thinking trace that needs more than 2,048 tokens is itself the signal the read must see (a truncated answer is an abstention, counted in the cap-hit table). The four-row decode-cost smoke then measured the real distribution (run SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SMOKE-4-V1, attempt attempt-slurp-direct-only-fold-b-thinking-smoke-4-generation-v1, 2026-10-11T21:49Z, 4 calls, 9.9395 speech-seconds): completions of 363, 921 and 977 tokens delivered 99, 111 and 60 characters of content, and ONE of the four contacts spent all 2,048 completion tokens (prompt 2,285) and delivered content of length 0 (the whole budget went to reasoning, which the server routes to message.reasoning_content and the transport never reads), so 1 of 4 rows hit the cap; decode speed was 37 tokens per second per slot (58 with one slot busy) and prompt evaluation 0.9 to 1.7 ms per token. That empty content crashed the OpenJiuwen wave (the sealed state refused an empty string). The harness now seals an empty final content of a direct-only contact as the explicit empty marker and leaves a saea-empty-completion-v1 receipt (cap_hit, completion_tokens, finish_reason), so a cap hit is a row-level outcome counted in the cap-hit table, never a flight abort. A cap that truncates a quarter of the rows would make the read a read of the cap, so it is raised to 8192 for the smoke (re-flown whole under rec1) and the Thinking arm. The Thinking arm's GPU-hour ceiling moves 3.0 -> 4.5: a bound, never a target; at the smoke's mean of 1,077 completion tokens per contact and 4 slots x 37 tokens per second the 1,080-row arm is about 2.2 GPU-h, and 4.5 GPU-h admits a mean of about 2,200 tokens per contact (the all-cap-hit worst case, about 16.6 GPU-h, is not what the ceiling covers). The cap lives in the model fragment's decoding_params and the flight attaches to a resident session by fragment name and sha256, so the fragment (q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max8192-v1) and the serving session (serving-slurp-thinking-direct-fold-b-np4-max8192-v1) both carry the new cap; the flown q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max2048-v1 and serving-slurp-thinking-direct-fold-b-np4-v1 stay on disk as the record of the first smoke attempt.

No sealed Instruct direct-only Fold B column exists. The sealed direct-only (phase-direct-only-v1, slurp-direct-max512) columns are SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-V1 (Fold A), -DEV1000-V1 and -DEV2000-ADDED-V1 (devel rosters). Fold B carries only the older EVO-S1 confirmation flight of the 'fixed' closed-list arm (SAEA-SLURP-EVO-S1-FOLD-B-V2), a different form on a different code path, which is not a same-harness comparator. The Instruct arm and its replicate therefore fly in this chain: the comparison must be same-chain.

## 6. Claim boundary

No system-level, superiority, generalisation, component-causal, admission, held-out, confirmatory or paper-scale claim. The Thinking model is admitted for
this read only. Nothing here authorises a flight, a readiness flip or a serving swap.

## Recovery rec1: the four-row Thinking decode-cost smoke (the cell's single recovery re-registration)

The predecessor attempt made its four contacts on the Thinking session (completion cap 2,048): completions of 363, 921 and 977 tokens delivered 99, 111 and 60 characters of content, and ONE contact spent all 2,048 completion tokens (prompt 2,285) and delivered content of length 0, because the whole budget went to reasoning, which the server routes to message.reasoning_content and the transport never reads. That empty content raised in the OpenJiuwen wave (ExecutionError 100054, component aggregate_agent_wave: AgentStateArtifact.content must be a non-empty string), the smoke step exited 1, the driver wrote its STOP and the Thinking arm never opened. Measured decode speed: 37 tokens per second per slot (58 with one slot busy); prompt evaluation 0.9 to 1.7 ms per token. The smoke is re-flown whole under the rec1 ids with the completion cap amended to 8,192; the Thinking arm's attempt never opened and keeps its ids; the Instruct cells are untouched.

RECOVERY 2026-10-11 (the cell's single one; coordinator brief, Fable 5.1; the cap amendment is the one re-registration the package README Finding 3 pre-authorised for the decode-cost sign-off). The generation budget is run-cumulative across the attempts of the run id (core/model/adapter.py), so the rec1 plan carries the original plan plus the failed attempt's recorded spend (4 calls, 9.9395 speech-seconds): the cumulative budget is 8 calls and 20 speech-seconds. The FIT cap is structural and unchanged (1 + 3 x 4 = 13). The FIT run id and the FIT attempt id both take the rec1 marker because the cell is re-flown whole and a (run_id, attempt_id) pair is a one-time key; the generation run id is unchanged. The model fragment moves to q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max8192-v1 and the serving session to serving-slurp-thinking-direct-fold-b-np4-max8192-v1 (the flight attaches to a resident session by fragment name and sha256, and the cap lives in the fragment's decoding_params). The Thinking arm takes the same fragment and session and its GPU-hour ceiling moves 3.0 -> 4.5.

- Failed attempt: `attempt-slurp-direct-only-fold-b-thinking-smoke-4-generation-v1` (OPENED at flight commit c9edf3244 on 2026-10-11T21:49Z, 4 calls / 9.9395 speech-seconds spent, the wave raised on the cap-hit row's empty content; preserved unread.)
- Root cause: two defects: the 2,048-token completion cap is below the Thinking trace on at least 1 of 4 rows (that row delivered empty content), and the harness raised on an empty final content of a direct-only contact instead of receipting it (owner decision 199: empty is legal); corrected by the 8,192-token cap and by the saea-empty-completion-v1 receipt (cap_hit, completion_tokens, finish_reason).
- Fix: completion cap 2,048 -> 8,192 (new model fragment `q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max8192-v1`, new serving session `serving-slurp-thinking-direct-fold-b-np4-max8192-v1`; the flown `q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max2048-v1` and its session id stay on disk unedited); an empty final content of a non-native direct-only contact is sealed as the explicit empty marker and receipted (`saea-empty-completion-v1`: cap_hit, completion_tokens, finish_reason) instead of raising (`rails/controllers.py`, `rails/runner.py`); the server finish reason is forwarded only under the reasoning guard, so no other transport envelope moves.
- Re-flown whole under generation attempt `attempt-slurp-direct-only-fold-b-thinking-smoke-4-generation-rec1-v1` and FIT run `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SMOKE-4-FIT-REC1-V1` / attempt `attempt-slurp-direct-only-fold-b-thinking-smoke-4-fit-rec1-v1`; the generation run id `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SMOKE-4-V1` is unchanged; the decision receipt lists the new FIT run id `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SMOKE-4-FIT-REC1-V1` in `eligible_run_ids` and is re-minted by the coordinator (`direct_fb_mint_receipt.py`).
- Run-cumulative plan budget: 4 + 4 = 8 calls; 10 + 9.9395 = 20 speech-seconds; the FIT cap stays structural.
- Plans: `smoke-generation-plan-registered-rec1-v1.json`, `smoke-fit-plan-registered-rec1-v1.json` (the first-attempt plan files are superseded and removed from the package; the git history keeps them, and the failed attempt stays on the data root).
- Unchanged: the Instruct arm and its replicate (flying; no baseline, experiment, plan or request byte of theirs moves). One forced consequence: the shared `protocol-registered-v1.json` carries every cell's identity, so its sha256 changed with this recovery and the four Instruct plan files still pin the PREVIOUS document's sha256; they were deliberately not rewritten while the pair flies, and the coordinator re-pins them after the Instruct pair seals. The Thinking arm's attempt never opened and keeps its ids; its plans change only through the cap (model fragment, session id, composed hashes) and the GPU-hour ceiling.
- Serving: the Thinking session recorded resident is the SUPERSEDED `serving-slurp-thinking-direct-fold-b-np4-v1` (completion cap 2,048); `serving_swap.sh` refuses a resident session outside its geometry table, so stop it with `scripts/flights/direct/serving_stop_think_superseded.sh` (dry run first), then `serving_swap.sh think-np4 --start-only` starts `serving-slurp-thinking-direct-fold-b-np4-max8192-v1` (checklist step 3b).
- A second failure closes the cell; the fix is proven on a four-row dry run.

## Recovery rec1: the Thinking arm (the cell's single recovery re-registration)

The predecessor attempt aborted before any model contact: "GateClosed: execution plan claims 4.5 gpu hours but only 3.0 were pre-registered; model touch refused". The exposure gate reads the FIT-inclusive pre-registration, and the live phase-fit row SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-FIT-V1 still read 3.0 GPU hours although the plan (gpu_hours_fit_inclusive) claimed 4.5. A (run_id, attempt_id) pair is a one-time key, so the arm is re-flown whole under the rec1 ids. The smoke, the Instruct arm and its replicate are untouched.

RECOVERY 2026-10-12 (the cell's single one; coordinator brief, Fable 5.1). The generation budget is run-cumulative across the attempts of the run id (core/model/adapter.py), so the rec1 plan carries the original plan plus the failed attempt's recorded spend (0 calls, 0 speech-seconds): the cumulative budget equals the original plan (1080 calls, 3155 speech-seconds). The FIT cap is structural and unchanged (1 + 3 x rows). The GPU-hour ceiling is 4.5 on both the generation and the FIT-inclusive pre-registration. The FIT run id and the FIT attempt id both take the rec1 marker because the cell is re-flown whole and a (run_id, attempt_id) pair is a one-time key; the generation run id is unchanged.

- Failed attempt: `attempt-slurp-direct-only-fold-b-thinking-generation-v1` (ABORTED at 2026-10-12T00:25:21Z at flight commit 5daf057f8 before any model contact (GateClosed: the FIT-inclusive GPU pre-registration of the live phase-fit row still read 3.0 after the cap amendment raised the plan to 4.5), 0 calls / 0.0 speech-seconds; preserved unread. The FIT attempt was never opened.)
- Root cause: an incomplete coordinator ledger amendment: when the completion cap and the arm's GPU ceiling were amended (3.0 to 4.5), the generation row's gpu cell was set to 4.5 but the live phase-fit row stayed at 3.0; corrected by the rec1 FIT row, which carries 4.5 natively (both rows are written from the same plan caps).
- Fix: the rec1 FIT row and the rec1 generation row both carry 4.5 GPU hours (the plan's gpu_hours_fit_inclusive); `flight_registration_check.py` now blocks a live FIT row whose gpu cell is below the FIT plan's claim, and a unit test asserts it for every live 266-E cell, so this class is caught model-free before a flight.
- Re-flown whole under generation attempt `attempt-slurp-direct-only-fold-b-thinking-generation-rec1-v1` and FIT run `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-FIT-REC1-V1` / attempt `attempt-slurp-direct-only-fold-b-thinking-fit-rec1-v1`; the generation run id `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-V1` is unchanged; the decision receipt lists the new FIT run id `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-FIT-REC1-V1` in `eligible_run_ids` and is re-minted by the coordinator (`direct_fb_mint_receipt.py`).
- Run-cumulative plan budget: 1080 + 0 = 1080 calls; 3155 + 0 = 3155 speech-seconds; the FIT cap stays structural.
- Plans: `thinking-generation-plan-registered-rec1-v1.json`, `thinking-fit-plan-registered-rec1-v1.json` (the first-attempt plan files are superseded and removed from the package; the git history keeps them, and the failed attempt stays on the data root).
- Unchanged: the smoke (flown twice; its rec1 attempt opened, 4 calls) and the Instruct pair (sealed); no baseline, experiment, plan or request byte of theirs moves. The Thinking arm's model fragment, serving session and completion cap are unchanged; its plans change only through the rec1 ids and the composed identities that carry them.
- A second failure closes the cell; the fix is proven on a four-row dry run.

## Recovery rec1: the Instruct arm (the cell's single recovery re-registration)

The predecessor attempt aborted before any model contact: "RailsRunnerError: AgentLoop query samples overlap the TRAIN knowledge source roster" (raised by the runner's roster guard, rails/runner.py). The guard compares the query roster with the pinned knowledge snapshot's source roster even when the program supplies no evidence. The Instruct arm is re-flown whole under the rec1 ids; the replicate, the Thinking arm and the smoke are untouched (their attempts never opened) and only take the knowledge pin.

RECOVERY 2026-10-11 (the cell's single one; coordinator brief, Fable 5.1). The generation budget is run-cumulative across the attempts of the run id (core/model/adapter.py), so the rec1 plan carries the original plan plus the failed attempt's recorded spend (0 calls, 0 speech-seconds): the cumulative budget equals the original plan (1080 calls, 3155 speech-seconds). The FIT cap is structural and unchanged (1 + 3 x rows). The FIT run id and the FIT attempt id both take the rec1 marker because the cell is re-flown whole and a (run_id, attempt_id) pair is a one-time key; the generation run id is unchanged.

- Failed attempt: `attempt-slurp-direct-only-fold-b-instruct-generation-v1` (ABORTED at 20:07:46Z at flight commit 77b2283e9 before any model contact, 0 calls / 0.0 speech-seconds; preserved unread (reserved 1080 calls / 3155 speech-seconds). The FIT attempt was never opened.)
- Root cause: the full-TRAIN knowledge view (609854e4...; 50,628 source rows, every Fold B id inside it) was pinned on a TRAIN-fold cell; corrected to the fold-excluded view of the same family (9c64e8ec...; 37,407 source rows, 0 Fold A and 0 Fold B ids).
- Fix: every 266-E baseline fragment now pins the fold-excluded knowledge view `knowledge/slurp/saea-kb-distmodel-v1/size-full-content-slot-fillers-intent-slot-frame-tfrl-folds-v1/snapshot.json` (sha256 `9c64e8ec48a0fce4f172bd190932f99c98c7efa18bbfb14526d54c62fdf7032b`); the single source is `scripts/flights/direct/direct_fb_family.py` and `direct_fb_derive_cells.py` writes it. The direct-only program supplies no evidence, so the pin changes no request; it only has to pass the runner's roster guard.
- Re-flown whole under generation attempt `attempt-slurp-direct-only-fold-b-instruct-generation-rec1-v1` and FIT run `SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-FIT-REC1-V1` / attempt `attempt-slurp-direct-only-fold-b-instruct-fit-rec1-v1`; the generation run id `SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-V1` and the minted decision receipt are unchanged.
- Run-cumulative plan budget: 1080 + 0 = 1080 calls; 3155 + 0 = 3155 speech-seconds; the FIT cap stays structural.
- Plans: `instruct-generation-plan-registered-rec1-v1.json`, `instruct-fit-plan-registered-rec1-v1.json` (the first-attempt plan files are superseded and removed from the package; the git history keeps them, and the failed attempt stays on the data root).
- Unchanged cells (their attempts never opened; they take only the knowledge pin): `slurp-direct-only-fold-b-thinking-smoke-4-v1`, `slurp-direct-only-fold-b-thinking-v1`, `slurp-direct-only-fold-b-instruct-replicate-v1`.
- A second failure closes the cell; the fix is proven on a four-row dry run.
