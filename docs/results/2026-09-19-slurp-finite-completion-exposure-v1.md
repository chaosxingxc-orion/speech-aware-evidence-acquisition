# NEUTRAL — no sealed SLURP native-episode contact ever met a finite completion, so `native_episode.finite_completion_policy` is byte-identical ON and OFF on every sealed row

Item E13, 2026-09-19, model-free. Across **28 sealed SLURP attempts that ran a
native role episode — 69,987 role-labelled contacts — every completion ended
`stop` (57,756) or `tool_calls` (12,231). Zero `length`, zero
`content_filter`, and zero contacts at their request's own `max_tokens`.** The
highest completion any sealed native contact ever produced is 402 tokens (the
dual-store anchor recovery's Reviewer), 110 below the 512-token cap. Arming
`native_episode.finite_completion_policy` as `"deliver-latest-or-abstain"`
therefore changes not one delivered byte of anything already sealed: the key is
consulted only where a completion has come back `length` or `content_filter`,
and no sealed native row has one. What it changes is the failure mode of a
FUTURE flight — a flight abort becomes a retained row.

That future is not hypothetical, and the positive control is the flight that
proved it: the B7a recovery arm died after 1,451 contacts on exactly one
512-token Reviewer completion.

This note reports exposure and failure modes only. It decides no task quality,
no comparator, no admission and no carrier claim.

## 1. What was measured, and what was deliberately not read

`src/speech_aware_evidence_acquisition/analysis/finite_completion_exposure_scan.py`
(`--data-dir`, `--out`) streams every sealed trace under
`$SPEECHRL_DATA_DIR/runs/` whose run id starts with `SAEA-SLURP-` and whose
attempt directory holds a `*.run-manifest.json` with status `COMPLETED`, plus
the two ABORTED B7a attempts named as positive controls. Per contact it joins
three trace channels by request id:

| field | channel | why it is needed |
| --- | --- | --- |
| `usage.completion_tokens` | `MODEL_RESPONSE` | how long the completion actually was |
| `finish_reason` | `MODEL_WIRE_RESPONSE` | `MODEL_RESPONSE` does **not** carry it; the preserved wire metadata does |
| `decoding_params.max_tokens` | `MODEL_REQUEST` | the cap is per cell (64, 256, 512), so "finite" means "reached ITS OWN request's cap" |
| `use_role_id` | `USE` `.../native-role-contact` | only the native episode runner writes this record, so it is both the role label and the witness that a native episode ran at all |

**No response text, transcript or gold label is read, printed or persisted.**
The only response fields opened are the usage counters, the finish reason and
the role id; the preserved base64 wire body is never decoded. Zero model,
tokenizer, encoder, scorer, network and GPU contacts; read-only under
`SPEECHRL_DATA_DIR`.

Receipt: `docs/receipts/slurp-finite-completion-exposure-v1.json`
(`saea-finite-completion-exposure-scan-v1`), 103 sealed attempts and 141,051
contacts scanned in total, 50 attempt directories skipped and listed there (no
trace file, or a manifest that is not `COMPLETED`).

## 2. Sealed SLURP attempts that ran a native role episode

"P / S / R / Pl" is the maximum completion tokens of the Perception, Solver,
Reviewer and Planner roles; `-` is a role that never ran (the review-off cells).

| run id | attempt id | contacts | cap | finish_reason counts | max completion tokens P / S / R / Pl | >=448 | ==512 |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: |
| `SAEA-SLURP-DIRECT-VS-NATIVE-SYSTEM-DEV1000-V1` | `attempt-slurp-direct-vs-native-system-generation-v1` | 5,020 | 256 | stop 4015, tool_calls 1005 | 211 / 111 / 234 / 3 | 0 | 0 |
| `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-SMOKE-4-V1` | `attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-smoke-4-generation-v1` | 20 | 512 | stop 16, tool_calls 4 | 149 / 26 / 86 / 2 | 0 | 0 |
| `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1` | `attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-generation-recovery-v1` | 5,415 | 512 | stop 4341, tool_calls 1074 | 166 / 58 / 245 / 3 | 0 | 0 |
| `SAEA-SLURP-NATIVE-B8A-DELIVER-NORMALISE-V3-EXEMPLARS-K20-SMOKE-4-V1` | `attempt-slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-generation-v1` | 24 | 512 | stop 19, tool_calls 5 | 149 / 26 / 121 / 3 | 0 | 0 |
| `SAEA-SLURP-NATIVE-BOUNDED-PERCEPTION-PROOF-V1` | `attempt-slurp-native-bounded-perception-proof-generation-v1` | 20 | 512 | stop 16, tool_calls 4 | 147 / 36 / 148 / 2 | 0 | 0 |
| `SAEA-SLURP-NATIVE-BROAD-FACTORED-TRAIN-FOLD-A-V1` | `attempt-slurp-native-broad-factored-train-fold-a-generation-v1` | 5,407 | 512 | stop 4326, tool_calls 1081 | 160 / 148 / 217 / 3 | 0 | 0 |
| `SAEA-SLURP-NATIVE-CANDIDATE-FIVE-TRAIN-FOLD-A-V1` | `attempt-slurp-native-candidate-five-train-fold-a-generation-v1` | 5,421 | 512 | stop 4341, tool_calls 1080 | 258 / 84 / 225 / 3 | 0 | 0 |
| `SAEA-SLURP-NATIVE-DUAL-STORE-DEV1000-BASE-REPLICATION-V1` | `attempt-slurp-native-dual-store-dev1000-generation-base-replication-v1` | 5,040 | 512 | stop 4033, tool_calls 1007 | 163 / 195 / 353 / 3 | 0 | 0 |
| `SAEA-SLURP-NATIVE-DUAL-STORE-DEV1000-REBOOT-RECOVERY-V1` | `attempt-slurp-native-dual-store-dev1000-generation-reboot-recovery-v1` | 5,046 | 512 | stop 4036, tool_calls 1010 | 167 / 111 / 187 / 3 | 0 | 0 |
| `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` | `attempt-slurp-native-dual-store-train-fold-a-anchor-generation-recovery-v1` | 5,417 | 512 | stop 4335, tool_calls 1082 | 163 / 97 / **402** / 3 | 0 | 0 |
| `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-RECOVERY-V2` | `attempt-slurp-native-exemplars-k20-anchor-smoke-4-generation-recovery-v2` | 20 | 512 | stop 16, tool_calls 4 | 147 / 26 / 78 / 2 | 0 | 0 |
| `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-V2` | `attempt-slurp-native-exemplars-k20-anchor-smoke-4-generation-v2` | 20 | 512 | stop 16, tool_calls 4 | 147 / 26 / 78 / 2 | 0 | 0 |
| `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2` | `attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-recovery-v2` | 5,425 | 512 | stop 4341, tool_calls 1084 | 166 / 60 / 251 / 3 | 0 | 0 |
| `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TWIN-TRAIN-FOLD-A-V2` | `attempt-slurp-native-exemplars-k20-anchor-twin-train-fold-a-generation-v2` | 5,429 | 512 | stop 4347, tool_calls 1082 | 158 / 71 / 152 / 3 | 0 | 0 |
| `SAEA-SLURP-NATIVE-KNOWLEDGE-FIX-DRY-RUN-V1` | `attempt-slurp-native-knowledge-fix-dry-run-generation-v1` | 20 | 256 | stop 16, tool_calls 4 | 184 / 37 / 145 / 2 | 0 | 0 |
| `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-RECOVERY-V1` | `attempt-slurp-native-ncp-l1-anchor-smoke-4-generation-recovery-v1` | 20 | 512 | stop 16, tool_calls 4 | 147 / 26 / 113 / 2 | 0 | 0 |
| `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-V1` | `attempt-slurp-native-ncp-l1-anchor-smoke-4-generation-v1` | 24 | 512 | stop 19, tool_calls 5 | 147 / 26 / 134 / 3 | 0 | 0 |
| `SAEA-SLURP-NATIVE-REVIEW-OFF-SMOKE-4-V1` | `attempt-slurp-native-review-off-smoke-4-generation-v1` | 8 | 512 | stop 8 | 149 / 26 / - / - | 0 | 0 |
| `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-REPLICATE-V1` | `attempt-slurp-native-review-off-train-fold-a-replicate-generation-v1` | 2,160 | 512 | stop 2160 | 163 / 98 / - / - | 0 | 0 |
| `SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1` | `attempt-slurp-native-review-off-train-fold-a-generation-v1` | 2,160 | 512 | stop 2160 | 163 / 116 / - / - | 0 | 0 |
| `SAEA-SLURP-NATIVE-ROLE-GPU-PROOF-V1` | `attempt-slurp-native-role-gpu-proof-generation-v1` | 20 | 256 | stop 16, tool_calls 4 | 163 / 34 / 72 / 2 | 0 | 0 |
| `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-RECOVERY-V3` | `attempt-slurp-native-samples5-anchor-smoke-4-generation-recovery-v3` | 36 | 512 | stop 32, tool_calls 4 | 147 / 36 / 128 / 2 | 0 | 0 |
| `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-SMOKE-4-V3` | `attempt-slurp-native-samples5-anchor-smoke-4-generation-v3` | 36 | 512 | stop 32, tool_calls 4 | 149 / 26 / 119 / 2 | 0 | 0 |
| `SAEA-SLURP-NATIVE-SAMPLES5-ANCHOR-TRAIN-FOLD-A-V3` | `attempt-slurp-native-samples5-anchor-train-fold-a-generation-v3` | 9,807 | 512 | stop 8717, tool_calls 1090 | 161 / 120 / 241 / 3 | 0 | 0 |
| `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-SMOKE-4-V2` | `attempt-slurp-native-slot-store-v2-anchor-smoke-4-generation-v2` | 20 | 512 | stop 16, tool_calls 4 | 147 / 26 / 87 / 2 | 0 | 0 |
| `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2` | `attempt-slurp-native-slot-store-v2-anchor-train-fold-a-replicate-generation-v2-resume2` | 2,501 | 512 | stop 2006, tool_calls 495 | 152 / 57 / 177 / 3 | 0 | 0 |
| `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V2` | `attempt-slurp-native-slot-store-v2-anchor-train-fold-a-generation-v2` | 5,407 | 512 | stop 4332, tool_calls 1075 | 163 / 70 / 177 / 3 | 0 | 0 |
| `SAEA-SLURP-NATIVE-TYPED-CONTEXT-TOOL-REJECTION-PROOF4-V1` | `attempt-slurp-native-typed-context-tool-rejection-proof4-generation-v1` | 44 | 512 | stop 28, tool_calls 16 | 149 / 27 / 125 / 3 | 0 | 0 |

**Totals: 28 attempts, 69,987 role-labelled contacts, `stop` 57,756 +
`tool_calls` 12,231, `length` 0, `content_filter` 0, at the configured cap 0,
at or above 448 tokens 0, at 512 tokens 0.** Every one of these attempts
preserved its wire responses, so the finish reason is KNOWN — not assumed — for
all 69,987.

## 3. The positive control: the two ABORTED B7a attempts

| run id | attempt id | contacts | cap | finish_reason counts | max completion tokens P / S / R / Pl | >=448 | ==512 |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: |
| `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1` | `attempt-slurp-native-ncp-l1-anchor-train-fold-a-generation-recovery-v1` | 1,451 | 512 | **length 1**, stop 1156, tool_calls 294 | 161 / 76 / **512** / 3 | 1 | 1 |
| `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1` | `attempt-slurp-native-ncp-l1-anchor-train-fold-a-generation-v1` | 3,278 | 512 | stop 2613, tool_calls 665 | 163 / 77 / 315 / 22 | 0 | 0 |

The recovery attempt shows **exactly one** 512-token contact, on the Reviewer
(`flight-1360`, 588 Reviewer contacts in that attempt), with `finish_reason`
`length`. That single contact is the whole of the September 18 abort: 1,450 of
1,451 contacts were authoritative, and the flight was lost because the parser's
default `"raise"` had never been overridden. Under
`"deliver-latest-or-abstain"` that row would have been RETAINED with a
`finite_completion` terminal disposition naming the interrupted Reviewer, and
the flight would have continued. The first B7a attempt carries no finite
completion at all — it died of a different cause — which is why the control is
read as a pair.

## 4. The three `length` completions that DO exist, and why they are not counted against the claim

Three sealed SLURP contacts across the whole record ended `length`, and none of
them is a native-episode contact:

| run id | attempt id | cap | `length` contacts | role |
| --- | --- | ---: | ---: | --- |
| `SAEA-SLURP-KU-S3A-CONTROL-G1-MAX256-RECOVERY-V1` | `attempt-20260909T233650Z-4328b7` | 256 | 1 (`flight-0469`, 256 tokens) | none — no native role record |
| `SAEA-SLURP-OUTPUT-BUDGET-ENGINEERING-MAX64-V1` | `attempt-20260909T152049Z-7e7a4d` | 64 | 2 (`flight-0001`, `flight-0003`, 64 tokens each) | none — no native role record |

These are pre-native phase-program cells at 64- and 256-token caps. Not one of
their contacts carries a `USE .../native-role-contact` record, which only the
native episode runner writes, so no native episode ran and no
`native_episode` block exists for `finite_completion_policy` to be read from:
ON and OFF are not two arms of those configs, they are the same config.

The same holds, more loosely, for the rest of the non-native record: across 75
sealed non-native attempts (71,064 contacts at 64/256/512-token caps) 127
contacts reached their configured cap, and 28,902 of those contacts have no
preserved wire response, so their finish reason is recorded as
`<no wire record>` rather than assumed. **That gap is real and is reported
rather than papered over** — but it lies entirely outside the native-episode
surface this key governs, and every one of those cells is closed.

## 5. What this licenses, and what it does not

Licensed:

* `native_episode.finite_completion_policy` is recorded NEUTRAL in
  `docs/receipts/harness-admission.json` (class `episode`), because ON and OFF
  deliver the same bytes on every sealed native row.
* Every new SLURP native cell arms the key, and
  `scripts/checks/finite_completion_policy_check.py` refuses a live, unflown
  native cell that does not.
* The SLURP default plan
  (`configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json`)
  carries the key ON.

NOT licensed:

* Any re-reading, re-scoring or re-flight of a sealed arm. Nothing here touches
  a sealed number; the point is precisely that nothing would change.
* Any claim that finite completions are IMPOSSIBLE on this carrier. One
  occurred, in 1,451 contacts, on the B7a recovery arm; the Reviewer's sealed
  maximum of 402 tokens says the margin is thin, not infinite.
* Any task-quality, comparator, admission or generalisation claim. This note
  counts finish reasons.
* Any statement about the 28,902 non-native contacts whose wire responses were
  not preserved. Their finish reasons are unknown and are reported as unknown.

## 6. Reproduce

```bash
python -m speech_aware_evidence_acquisition.analysis.finite_completion_exposure_scan \
    --data-dir "$SPEECHRL_DATA_DIR" \
    --out docs/receipts/slurp-finite-completion-exposure-v1.json
```

Model-free proof of the two arms' behaviour, against the fake model on the real
anchor baseline's `native_episode` block:
`tests/unit/test_slurp_finite_completion_row.py`.
