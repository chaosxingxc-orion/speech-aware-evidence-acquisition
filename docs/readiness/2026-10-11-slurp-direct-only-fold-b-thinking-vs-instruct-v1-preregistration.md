# Preregistration -- cell 266-E: the bare-core read on TRAIN Fold B, Thinking versus Instruct

Registered 2026-10-11 before any contact, at study commit `a057eea1d9479a8220dfe9b44d817faa1ec2a7a8`. Owner decision 266-E. Package `docs/readiness/2026-10-11-slurp-direct-only-fold-b-thinking-vs-instruct-v1/`.

## 1. Question and design

Does the Thinking core move the official SLU-F1 on TRAIN Fold B (1,080 rows, discovery role) by more than the cross-flight bar (about 2.5 pp) over the
Instruct core, with the system held out entirely? Same form on both cores (direct-only program, closed-list instruction, same roster and order); the only
differences are the core, its own packet root, the completion cap 2048 and `--reasoning-format deepseek`. Cross-session by necessity, so the Instruct arm
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

The audio-encoder tensors of the two mmproj files differ: 748 of 860 tensors are not byte-identical (name-for-name comparison of the GGUF tensor tables of mmproj-Qwen3-Omni-30B-A3B-Instruct-bf16.gguf and mmproj-Qwen3-Omni-30B-A3B-Thinking-bf16.gguf; the 112 identical tensors are the non-audio ones). The Instruct speech-feature packets (/home/chao/feat-cache/slurp-q4km-packets-04ccc72a) are decoder-ready projector outputs of the Instruct encoder and are therefore NOT valid input for the Thinking decoder. The Thinking core needs its OWN packet root (/home/chao/feat-cache/slurp-q4km-packets-thinking-afdaeff6) prepared by an encoder pass over TRAIN Fold B (registered, held: ledger row SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-V1, fragment q4km-thinking-preprocess-featcache-cpu-sidecar-np4-v1); the Thinking baselines pin its future promotion receipt with a zero sentinel the flip refuses.

Reasoning stays out of the delivered content by the server flag --reasoning-format deepseek (registered explicitly in the serving fragment's server_args). Evidence from the pinned featcache build 04ccc72a2 (read-only grep): tools/server/README.md line 220 documents the option (none leaves thoughts in message.content; deepseek puts thoughts in message.reasoning_content; deepseek-legacy keeps <think> in content AND fills reasoning_content); common/arg.cpp line 3130 defines it; common/common.h line 622 makes COMMON_REASONING_FORMAT_DEEPSEEK the build's own default; common/chat.cpp line 828 maps it. The transport (core/model/transport.py) reads ONLY choices[0].message.content (and tool_calls); it never reads reasoning_content. The cells set preserve_wire_responses false, so no raw wire bytes (which would carry reasoning_content) are persisted. Client-side guard: the fragment declares reasoning_content_guard refuse-think-marker-in-content, and the transport raises FrozenCoreError when a delivered content string carries <think>, </think>, <thinking> or </thinking> (case-insensitive), BEFORE anything is returned or persisted; the flight stops (a leak means the option is not effective). The reader counts leak markers in the sealed delivered text (count only) as a second check.

Completion cap 2048 tokens. Slot budget: -c 98304 / -np 4 = 24,576 tokens per slot. The direct-only prompt is about 2,300 tokens per row (the sealed Instruct direct form measured 2,262 to 2,280 prompt tokens per contact; 3,733 on the A2T registry). 2,300 + 2,048 = 4,348 tokens, 17.7 percent of a slot, so the cap is bound by decode cost, not by the slot; a cap of 8,192 would still use only 42.7 percent. 2048 is proposed because a SLURP answer is a short structured object, so a thinking trace that needs more than 2,048 tokens is itself the signal the read must see (a truncated answer is an abstention, counted in the cap-hit table), and because the smoke measures the real distribution before the arm is queued. The coordinator may amend the cap at the decode-cost sign-off (one re-registration changes the fragment hash and re-pins the cells); the GPU-hour ceiling of 3.0 is the 1,080-contact worst case at ~250 aggregate tokens per second.

No sealed Instruct direct-only Fold B column exists. The sealed direct-only (phase-direct-only-v1, slurp-direct-max512) columns are SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-V1 (Fold A), -DEV1000-V1 and -DEV2000-ADDED-V1 (devel rosters). Fold B carries only the older EVO-S1 confirmation flight of the 'fixed' closed-list arm (SAEA-SLURP-EVO-S1-FOLD-B-V2), a different form on a different code path, which is not a same-harness comparator. The Instruct arm and its replicate therefore fly in this chain: the comparison must be same-chain.

## 6. Claim boundary

No system-level, superiority, generalisation, component-causal, admission, held-out, confirmatory or paper-scale claim. The Thinking model is admitted for
this read only. Nothing here authorises a flight, a readiness flip or a serving swap.
