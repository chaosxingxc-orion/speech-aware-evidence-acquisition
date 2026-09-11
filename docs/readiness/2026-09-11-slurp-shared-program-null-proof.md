# SLURP shared-program null configuration proof

Date: 2026-09-11 UTC. This model-free check follows the closed G6 result and does not reopen its decision, modify historical configurations, or admit a new flight.

## Scientific interpretation

The saved paired analysis already reports nine scenario saves, ten harms and 481 ties on NEW500. OLD500 has six saves, five harms and 489 ties; DEV1000 has fifteen saves, fifteen harms and 970 ties. The NEW500 difference is therefore a net loss of one correct response among nineteen correctness changes, rather than proof of one isolated failure. Preserve the original nonnegative scenario point guard and its failed decision.

Source: DATA/analysis/SAEA-SLURP-LIVE-INTENT-SLOTS-PAIRED-ANALYSIS-V1/paired-contrasts.json, SHA-256 cbf7f3a21501cca9b19327a74af6c95d8aceae414bb00c068d8bc13a90d88cd5. The counts are saved fields under results.speech_minus_live_matched_control.<population>.official.scenario_exact.speaker_clustered. No scores or bootstrap draws were rerun.

The existing root attribution found all 1,000 first-stage rendered requests equal after normalization of the named control identifier, with 834 raw answers exactly equal. This identifies a request mismatch, not the cause of answer variability or the failed guard. The final join assigns scenario and action to the first-stage answer, so slot supply does not have direct authority to change those delivered fields. Do not label the historical configured-system contrast an isolated retrieval effect.

## Configuration proof

Both future arms can use the existing phase-direct-then-slots-supplied-v1 program. An absent or empty null-arm phase_supply parses to no supply specifications; the treatment declares supply only for slots. No change to the shared controller or renderer is needed to express that comparison.

Root loaded the two actual historical baseline fragments, changed the null program and empty supply in memory only, and passed their declared phase material through the existing parsers, material builder and request renderer. A synthetic direct packet and instruction produced identical null and treatment envelopes. The unchanged historical control program still produced a different envelope. This proof is executable in tests/unit/test_phase_supply_prompt_bound.py::test_shared_slurp_program_supports_null_arm_without_direct_prompt_id_drift.

Content-free receipt: DATA/coordination/slurp-shared-program-null-proof-v1.json, SHA-256 14544a90997902ab5aee10e08b3bf6965daee789ef496efe4bcbc61583aad0ac. The receipt binds source cede439ad6be7636f94f830daf5fdd201f6bf618 and both input fragment hashes.

## Limits and next admissible action

This is a synthetic configuration check, not full-roster actual-payload equality, capacity, service equivalence, generation reproducibility, or quality evidence. Model, tokenizer, encoder, scorer and reference contacts are all zero. No baseline fragment was written or changed.

If a later SLURP comparison is admitted for a specific decision, first use the same program in both arms and verify the complete model-visible first-stage requests. Preserve independent current-run state and all serving variability; equal request bytes do not guarantee equal generated answers. Do not alter old scores, reassign old outputs, relax the guard, or rerun until a new result passes.

The active E21 direct-to-KC-E1f comparison retains its frozen source and remains the GPU priority.

## Verification

In WSL Ubuntu-24.04, the existing prompt-bound test file and empty-supply parser check passed: eight tests, zero neural contacts. Run with explicit source selection:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /home/chao/.venvs/speechrl/bin/python -m pytest -q tests/unit/test_phase_supply_prompt_bound.py tests/unit/test_phase_supply.py::test_absent_phase_supply_yields_no_specs
```
