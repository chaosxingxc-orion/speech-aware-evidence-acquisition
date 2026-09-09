# `SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1` — the logprob-as-judge probe

**NOT ADMITTED.**

The cell of `docs/readiness/2026-09-08-slurp-logprob-judge-probe-v1-preregistration.md`: the sealed
DEV-1000 closed-list direct comparator's configuration with exactly two declared decoding keys
added — `logprobs: true`, `top_logprobs: 5` — so the frozen core's own per-token distribution is
recorded beside every answer instead of discarded. It asks one falsifiable question: does that
confidence predict the core's own errors well enough to be a Reviewer signal? The reasoning is
`docs/readiness/2026-09-09-slurp-logprob-judge-probe-v1-verdict.md`.

| | |
|---|---|
| study commit | `7489a15d` (registration) — the flight binds it, `study_repo_dirt` empty |
| smoke | `SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-SMOKE-4-V1`, attempt `attempt-20260909T051251Z-1f2c58`, **PASS on 4 of 4** |
| flight | attempt `attempt-20260909T052142Z-07ca9c`, 1,000 rows, one attempt, no recovery re-registration |
| identity | config `15670eaa…711e587`, protocol `bf6e602d…83c68`, split `8580d199…1e3c84` (the comparator's), instruction `4073f79e…0d37db` (the comparator's) |
| wire check | `docs/checks/speech-aware-evidence-acquisition/2026-09-08-slurp-logprob-judge-probe-wire-check/` predicted `config_hash` `15670eaa` before the flight; preflight derived it |
| paper-facing scorer | `slurp-slu-official-projected-v2`; secondary `slurp-slu-f1-normalized-v1` |
| serving | attached to the coordinator's resident session `slurp-np8-logprob-c65536-20260909`; no server started, none stopped |
| cost | 1,000 calls of 1,050; 2,884.7937 metered speech seconds of 3,000; **0.0690 GPU-h** of 0.5; paid API spend 0 |

## The headline

| | value |
|---|---:|
| **rule arm A** — `min_token_logprob` AUROC, intent error | **0.6935** [0.6660, 0.7202] against ≥ 0.75 / LB ≥ 0.70 |
| **rule arm B** — precision at 86 flags, intent error | **51.16 %** [42.53, 59.09] against > 72.09 % |
| **verdict** | **NOT ADMITTED** |
| the signal that IS there — `intent_mean_token_logprob` AUROC | 0.8497 [0.8262, 0.8729] — **not the primary, admits nothing here** |
| rows whose least-confident token is JSON punctuation | **491 of 1,000** (420 of 735 correct, 71 of 265 errors) |
| the cost of `n_probs > 0`, measured for the first time | **+5.30 % per request, +8.33 % wall, +8.35 % GPU-h** |

## Layout

| path | what |
|---|---|
| `smoke/smoke-acceptance.json` | the four-row hard precondition, all four clauses, per row |
| `smoke/acceptance.py` | the archived checker. It uses the STUDY's own accessors — `core.model.adapter._logprobs_sha256` and the read script's `logprobs_by_request` / `token_entries` / `row_confidence` — because a checker that reimplements what it checks proves only that two guesses agree |
| `flight-1000/flight-receipt.json` | preflight, preprocess, serve (attached), `run_phases`, seal, score |
| `flight-1000/monitor-contact-window.json` | the monitor summary over the flight's own contact window |
| `verdict/read.json` | the full registered read, including the three 1,000-point precision-recall curves |
| `verdict/companion-read.json` | the per-scenario table and the minimum-token diagnostic |
| `verdict/result-summary.json` | the machine form of the verdict |
| `verdict/auroc-table.md` | all five statistics against both targets, with CI90 |
| `verdict/operating-point-table.md` | the 86-flag point for all three targets, the two recomputed judges, both unions, and the rule's arm B |
| `verdict/per-scenario-table.md` | all 18 gold scenarios, and where the row minimum actually lands |
| `verdict/deterministic-pair.json` | schema OR legality ON THEIR OWN, the one union the registered read does not compute, so the verdict's claim about the flag's effect on the free judges is measured rather than inferred |
| `verdict/score-provenance.json` | sealed manifest, derived manifest, the one verified scoring job |
| `verdict/read-inputs-provenance.json` | the clusters and label inventory the read consumed, with their sources and hashes |
| `verdict/official-aggregate.json` | this arm's own official aggregate — labels for the read, never a comparator |
| `build_read_inputs.py`, `score_once.py`, `companion-read.py`, `build_result_summary.py`, `deterministic_pair.py` | archived copies of the five zero-contact steps beside the registered read |

## The five things this receipt exists to pin

1. **The precondition was a gate, and it was checked before 1,000 rows were spent.** Four rows, four
   `choices[0].logprobs` objects on the SPEECH-FEATURE PACKET route, exactly five alternatives on
   every one of 162 generated tokens, the first alternative equal to the sampled token throughout,
   four `MODEL_LOGPROBS` records whose `logprobs_sha256` recomputes, and the reconstruction equal to
   the sealed text on 4 of 4. Section 3.6's source reading — logprobs are computed downstream of the
   prompt/generation boundary, so the packet and mmproj routes behave identically — is now measured
   rather than argued.
2. **The request side did not move.** `prompt_tokens_total` **2,190,161**, identical to the digit to
   both the sealed comparator's and the greedy replicate null's, on the same 2,884.7936875 metered
   speech seconds and the same 7,583-character instruction. The parameter bought a trace record, not
   a different prompt.
3. **The verdict was applied mechanically by code written before the flight.** `admission_verdict`
   in `scripts/slurp_logprob_judge_read.py`, unit-tested on eight cases including both boundaries,
   over a read whose 40 tests ran on synthetic traces before any real number existed.
4. **The read failed closed where it could have fudged.** 1,000 of 1,000 speakers resolved into 124
   clusters (an unresolvable speaker stops the read rather than becoming a singleton), and 0 of
   1,000 token streams failed to rebuild their sealed text, so every span statistic is aligned to
   the string it claims to be.
5. **The honesty clause fired.** 72.09 % at 86 flags is KC-S1b's number on the two-stage slot arm.
   Recomputed on THIS arm under the same definition, the schema judge flags **13 rows at 30.77 %**.
   Both readings are in `verdict/operating-point-table.md` and neither replaces the other.

## Two things this receipt records rather than tidies away

* **The statistic that would have passed is in here, labelled unquotable.**
  `verdict/result-summary.json` carries `successor_diagnostic_NOT_PREREGISTERED`: at 86 flags
  `intent_mean_token_logprob` reaches 75.58 % precision and `intent_min_token_logprob` reaches
  **72.093 %** — the 72.09 bar to three decimals. Neither is the preregistered primary, both were
  computed after the numbers existed, and the rule exists precisely to make them unquotable as this
  probe's result. They are recorded so a successor preregistration can name its primary in advance
  with a price already attached.
* **The per-scenario table is not admissible on its own.** The primary spans 0.5023 (`general`) to
  0.9866 (`weather`) across 18 strata of 30 to 61 rows, and `SAEA-SLURP-DEV1000-NULL-REPLICATE-V1`
  moved intent by −5.13 to +5.41 pp across these same strata with nothing changed. The table is kept
  with that warning attached rather than dropped or read as a finding.
