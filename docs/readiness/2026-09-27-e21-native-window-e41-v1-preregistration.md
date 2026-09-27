# Item E41 preregistration: the bounded Perception note -- four-row dry run, then the sub10 re-read

Registered 2026-09-27 before any contact by the E41 registration agent (Claude Opus 5.5) in the worktree
`/home/chao/saea-worktrees/fable-e41` (branch `fable/e41`, base commit `a50a0d1c`). DRAFT: root countersignature
pending. **Development receipts only.**

## 1. Why

E35 (`docs/results/2026-09-22-e21-native-window-flightruntime-e35-read.md`) root-caused the Earnings system form's
HARM to E13's episode-wide scope voiding 76 windows after a length-truncated Perception contact; E39 / E39b repaired
the scope and the Reviewer cap and both still failed R3 on the Perception node (4 / 4 at 320, 2 / 4 at 640); row 103
defined E41 and row 158 ordered it carried out as unfinished Stage-2 base.

## 2. The factor

ONE pin, `phase_material.perception.instruction_template`: `probes/e21_native_window_system_perception_v1.txt` -> `probes/e21_native_window_system_perception_v2.txt` (sha256 `dbc2e691e21f59dff33657e1691259815c1afce3f305d1bb6712bfee93b15bfa`).
Token cost: +98 prompt tokens per Perception contact; a compliant note is at most
574 tokens (digit-dense worst case) against the 640 cap.
Of 354 sealed Perception notes, 82 truncated, 0 within the bound (modes
{"ENUMERATION": 12, "LOOP": 60, "PROSE": 5, "TRANSCRIPT": 5}).

## 3. Decision rules (fixed here, before contact)

**Dry run** (`dry-run-analysis-recipe-v1.json`): R1 zero auxiliary-node abstentions; R2 4 / 4 non-empty deliveries;
R3 the Perception truncation rate at 640, reported with its count, TARGET ZERO (the Reviewer count beside it). PASS iff
R1 and R2 hold and zero Perception or Reviewer contacts truncate. A non-zero Perception count FAILS E41 with the
truncated note's structure named; at most one recovery re-registration.

**Sub10 re-read** (`sub10-analysis-recipe-v1.json`), flipped only after the dry run PASSES: a descriptive structural
read S1-S5 (voided windows, empty deliveries, Perception truncation rate, contacts and routes, note compliance) with
the carrier's standard scorer (Whisper-normalised corpus WER) and the agentic metrics (ConEC entity WER mirror with
official_tool_run false -- the official fstalign tool is not runnable here -- numeric-value accuracy) reported beside
the sealed E35 sub10 direct arm, bound per window, with the E35 diagnosis's per-window attribution. No claim.

## 4. Measurement declaration (the canonical copy is `registered-facts-v1.json`)

```json
{
  "stage3_measurement": {
    "SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1": {
      "measurement_design": "form-proof",
      "expected_effect_pp": 0.0,
      "rows": 1,
      "claims_benefit": false,
      "primary_metric": "the Perception length-truncation count on the four windows (target zero), with R1 (no auxiliary node voids its window) and R2 (4 / 4 non-empty deliveries)",
      "note": "A receipts-only STRUCTURAL dry run of one instruction pin: one call (four windows) is far under MIN_BENEFIT_ROWS, so under rule 5 it is a form proof by size; claims_benefit is false and expected_effect_pp is 0.0 because the cell registers no effect on any task metric. It is NOT an admission request: no admission mode is declared and no harm margin is claimed."
    },
    "SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-E41-V1": {
      "measurement_design": "form-proof",
      "expected_effect_pp": 0.0,
      "rows": 10,
      "claims_benefit": false,
      "primary_metric": "structural receipts at scale (windows voided by an auxiliary node, non-empty deliveries, the Perception truncation rate) beside the carrier's standard scorer (Whisper-normalised corpus WER) and the agentic metrics (ConEC entity WER mirror, numeric-value accuracy), all DESCRIPTIVE against the sealed E35 sub10 direct arm bound per window",
      "note": "A descriptive structural read: 10 calls (342 windows) sit below every power floor of the measurement instrument and under MIN_BENEFIT_ROWS, so this is a form proof by size; claims_benefit is false and expected_effect_pp is 0.0 because no effect on any metric is registered or may be claimed. The comparator is a sealed arm from another flight (a cross-flight contrast with no in-chain replicate), which is exactly why the read is descriptive and never an admission. It is NOT an admission request."
    }
  }
}
```

`stage3_algorithm` is `none` in both experiment fragments: E41 carries no training-free RL operator.

## 5. What is not claimed

No score, WER, entity, numeric or semantic-error claim from the dry run; no effectiveness, superiority, comparison or
generalization claim from either cell (n = 1 and 10 calls, below every floor; row 98 keeps the n >= 400 Earnings
calibration after the SLURP main line). No transcript, reference or delivered text is printed or persisted by any read.

## 6. Budgets and failure rule

Dry run: 44 calls / 176 fit endpoints / 3,960 repeated speech seconds / 0.5 GPU-h. Sub10: 3,762 / 15,048 / 334,477 /
12.0. Ceilings, never targets, run-cumulative per run id; zero ASR, encoder, paid-API and task-contract calls. First
failure stops and preserves; at most one separately registered recovery per cell.

## 7. Registration state

Both cells HELD. Runbook: `docs/readiness/2026-09-27-e21-native-window-e41-v1/README.md`.
