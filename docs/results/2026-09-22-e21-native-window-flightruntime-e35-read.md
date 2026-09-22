# E35 read: the Earnings21 + ConEC carrier on FlightRuntime (owner decisions 89, 91, 92, 98)

Read 2026-09-22 by the coordinator (Fable 5.1) with `scripts/flights/batch/e35_read.py` (model-free; output
`$SPEECHRL_DATA_DIR/analysis/SAEA-E21-NATIVE-WINDOW-FLIGHTRUNTIME-E35-READ-V1/e35-read.json`, sha256
`ca0d9ee9d0a4ea4c3d77670dfead56327cd1149c788cf742e021793fdcc4cd7d`) and the diagnosis appendix
`docs/results/2026-09-22-e21-native-window-e35-sub10-diagnosis.md` (copied from
`$SPEECHRL_DATA_DIR/analysis/SAEA-E21-NATIVE-WINDOW-E35-SUB10-DIAG-V1/diag.md`, sha256
`354bc9c4c33fa12c957b1ebbbc1e0b9b3c1a32b9773b7f96bb49c8bb76817e1e`; `diag.json` sha256
`012bd7260451dea5ca1f9fdbb238ebb90e23e5fb5f096164c4207ce643a6612c`). Zero contacts of any kind in the read. Development
numbers (decisions 28, 86); n = 10 calls, below the n >= 400 rule: **no effectiveness claim of any kind**.

## 1. Verdict

| item | result |
| --- | --- |
| structural (decision 89: Earnings joins FlightRuntime) | **PASS**: both arms flew through `core.flight.FlightRuntime` and the OpenJiuwen executor on the E21 geometry; the system arm walked all six nodes (Perception -> Solver -> Reviewer -> Planner -> revision -> Delivery normaliser), 1,597 contacts on 342 windows, per-window receipts under the trace records (`use_native_episode`) joined to `execution_unit_delivery.sources[*]` 342 / 342 and 1,597 / 1,597 |
| descriptive contrast (sub10, 10 calls, 342 windows) | the system form **as flown is far worse than the bare core** on every metric and on 10 of 10 calls: corpus WER 7.24 % -> 28.63 %, numeric-value accuracy 92.39 % -> 71.06 %, high-impact error rate 0.02 % -> 0.13 % |
| root cause (diagnosis, model-free) | **one harness defect, not the carrier and not the core**: E13 `finite_completion_policy = deliver-latest-or-abstain` is scoped to the whole episode, so a `length`-truncated PERCEPTION contact (75 windows; Perception completions median 324 / p95 821 tokens against the 1,024-token cap) ends the episode before the Solver runs and delivers the empty string; 76 empty windows hold 22.9 % of the reference words and 95.6 % of the extra error mass. Had they scored like the direct arm the system corpus WER would read 7.78 % (direct 7.24 %); on the 234 windows that reached a Planner ACCEPT, direct 7.07 % vs system 7.22 % (WER-neutral) |
| disposition | the carrier is ON the base (structural pass); the six-node form is **NOT admitted for Earnings** until item E39 (E13 scoped to the answering node, per-role completion caps, tool-free Reviewer template) is proven on a four-row dry run; base lock v3 records the defect (section 5 of that record) |

## 2. The sealed arms

| arm | run / attempt | flight commit | contacts | speech s (repeated) | rows | manifest |
| --- | --- | --- | ---: | ---: | ---: | --- |
| four-row direct | SAEA-E21-NATIVE-WINDOW-DIRECT-FOUR-ROW-V1 / attempt-e21-native-window-direct-four-row-v1 | 825ee769 | 4 | 360 | 1 call (4 windows) | COMPLETED |
| four-row system | SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-V1 / attempt-e21-native-window-system-four-row-recovery-v4 (fit SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-V1-FIT-RECOVERY-V3) | 1a9c78d2 | 13 | 1,170 | 1 call (4 windows) | COMPLETED |
| sub10 direct | SAEA-E21-NATIVE-WINDOW-DIRECT-SUB10-V1 / attempt-e21-native-window-direct-sub10-v1 | 1a9c78d2 | 342 | 30,407 | 10 calls (342 windows) | COMPLETED |
| sub10 system | SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-V1 / attempt-e21-native-window-system-sub10-v1 (fit SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-V1-FIT) | 1a9c78d2 | 1,597 | 142,418 | 10 calls (342 windows) | COMPLETED |

The four-row pair is structural only (4 windows of one call scored against the whole call's reference: deletions
dominate by construction, direct WER 89.66 %, system 92.18 %). The batch driver chain SAEA-Batch-Chain-E35 sealed the
three queued steps 15:46 / 16:10 / 19:16 UTC (driver-done 19:16:31 UTC); the four-row direct arm had sealed on the
first launch. Serving: `serving-e21-native-window-flightruntime-np4-max1024-v1` (np4, 24,576-token slots, 1,024
completion tokens), stopped 19:21 UTC after the seal.

## 3. Descriptive contrast on the sub10 pair (scored once per manifest, Whisper-normalised)

| scorer | metric | direct | system | note |
| --- | --- | ---: | ---: | --- |
| asr-wer-whisper | corpus WER (75,751 reference words) | 0.0724 | 0.2863 | system: deletions 18,426 / substitutions 1,889 / insertions 1,375; direct: 1,107 / 2,403 / 1,975 |
| asr-wer-whisper | per-call mean WER (n = 10) | 0.0774 | 0.2927 | 0 calls improved, 10 worse |
| numeric-value-accuracy-v1 | accuracy (2,246 expected numeric words) | 0.9239 | 0.7106 | hypothesis numeric words 2,276 -> 1,713; spurious 201 -> 117; 544 of the 565 missing numerics sit in the empty windows |
| semantic-high-impact-error-rate-v1 | rate | 0.0002 | 0.0013 | high-impact insertions 7 -> 3 |
| conec-entity-wer-official | -- | -- | -- | **not measured**: `official_tool_run = false` in both arms (the mirror reports the corpus WER only); the ConEC entity read needs the official tool run registered separately |

Delivered words: direct 76,619, system 58,700 (0.77 x). Deletions carry 85 % of the system arm's errors while its
substitutions and insertions both fell against the direct arm.

## 4. Diagnosis (appendix; counts only)

- **Where the text went.** 76 of 342 windows (22.2 %) delivered the empty string (`delivery_text_sha256 = e3b0c442...`,
  request id `.../delivery/native-abstention-v1`); 75 carry `terminal_disposition = {finite_completion, role_id:
  perception, finish_reason: length}`. Every one of the 266 non-empty windows delivered the LAST Solver draft; no
  Reviewer or Perception text ever reached the transcript. The failure is no text, not a wrong node's text.
- **Concentration.** 59 windows (17.3 %) carry 80 % of the extra error mass and 58 of them are abstentions;
  per-window delta-WER median +0.004, p90 +0.93. Abstention is spread over all 10 calls (2 to 14 windows each).
- **Cap firing.** Completion cap 1,024 (the 24,576-token slot is not binding: largest prompt 5,585). Perception 75 /
  342 contacts at the cap, Reviewer 30 / 428, Solver 1 / 429, direct 1 / 342. E13 fired 106 times (75 Perception, 30
  Reviewer, 1 Solver); 76 produced an empty delivery, 30 delivered the latest Solver draft. E22 never fired.
- **Contacts.** 4.67 per window against the planned 11: every role visit used 1 contact (Reviewer `max_iterations 3`
  never drawn), acquisition armed at `contact_budget 0`, 106 episodes cut short. 162 windows took REVISE -> ACCEPT; in
  105 of them the second Solver draft was byte-identical to the first (315 contacts for nothing). The Reviewer template
  orders a task-contract tool call the tool-free cell cannot serve (`tool_calls = 0`): a wiring defect that costs
  reviewer caps (30 / 428), not WER.
- **Ranked hypotheses.** H1 E13 episode-wide scope (about 96 % of the extra error mass); H2 the 1,024 cap sized for a
  transcript, not for free-text auxiliary nodes, with no node-local cap; H3 the Reviewer template's tool sentence.
  Confirming fields are named in the appendix, section 6.

## 5. What follows (engineering, Stage-2 base repair; not a Stage-3 cell)

Item **E39** (branch fable/e39): `native_episode.finite_completion_scope = answering-node` (a truncated non-answering
node keeps its truncated note and the episode continues; only a truncated Solver, or no Solver draft at the end,
triggers E13), per-role `max_completion_tokens` composed at request time like the E2 decoding overrides, a tool-free
Reviewer template v2 for E21, and a HELD four-row dry-run cell on the E21 geometry (2 abstained + 2 REVISE/ACCEPT
windows; receipts only, no score). Default values keep every sealed configuration byte-identical; the SLURP locked
plan (cap 512, Perception candidate lists short) is not re-flown. The dry run needs the E21 serving geometry again
and is queued after the SLURP main line of decision 100 unless the GPU is otherwise idle. The Earnings
full-discovery calibration (n >= 400 calls) stays after the Stage-3 SLURP main line (decision 98).

## 6. Ledger and records

Seven exposure-ledger rows closed (consumed = yes) with this note as their read: the four generation rows, the
four-row fit and its recovery-v3 fit, the sub10 system fit. The R4 sub10 sample roster
`docs/receipts/probe-samples/r4-e21-sub10-sample.json` is unchanged. Base lock v3
(`docs/results/2026-09-22-base-lock-v3.md`) section 4 carries the Earnings row in the decision-98 wording.
