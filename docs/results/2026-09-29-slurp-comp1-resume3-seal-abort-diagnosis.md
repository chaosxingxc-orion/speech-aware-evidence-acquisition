# COMP-1 resume attempt 3: seal abort diagnosis (2026-09-29)

Run `SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1`, attempt
`attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3` (flight commit 8fd87fca,
`resume_from` the original attempt, trace `029a2dbb...`). Model-free diagnosis; ids are given as
sha256 prefixes of the sample id; no text content is recorded here.

## 1. Where the check lives

`src/speech_aware_evidence_acquisition/core/flight/runtime.py:10098-10104` inside
`FlightRuntime._canonical_output_rows` (the E11 branch starting at `:10075`). It compares the
episode receipt's `deliver_normaliser.output_sha256` (recorded at capture by `rails/runner.py:4375-4391`,
which replaces the delivered text with the normaliser output) with
`sha256(sources[0].final_response_text)` -- the delivered text of the phase result handed to the seal.
It does not re-run the normaliser; the bundle's I7n (`core/bundle/outputs.py:495`) does.

Traceback path: `queue.run -> seal (runtime.py:10537) -> _merged_canonical_rows (:10401) ->
_canonical_output_rows(output_rows=replayed_rows, ...)`. The live rows (`:10390`) are rendered
first and passed; the refusal comes from the KEPT rows.

## 2. Which row tripped it

The first kept row in predecessor trace order, sample hash `548ea85ca8a3` -- one of the 471 KEPT rows,
not a flown row. Its receipt: keys `accepted_solver_receipt, context_fit, deliver_normaliser,
planner_routes, role_visits, solver_citations`; normaliser `saea-deliver-cited-answer-normalise-v3-v1`
version 1, applied, changed, labels_changed 1; Planner route `ACCEPT` (no Reviewer revision); no
`seal_refusal`; no `duplicate_citation_ids_dropped`. It is not special: all 471 kept rows carry a
changing `deliver_normaliser` block and all 471 fail identically (kept-row route shapes: 458 ACCEPT,
10 REVISE->ACCEPT, 3 empty).

Offline reproduction: `scripts/analysis/replay_seal_consistency.py` under the pre-fix code
(`resume.py` sha256 `325aeae0...`) raises exactly
`FlightRuntimeError: native delivery normalisation output differs from the delivered text` on
471/471 kept rows and, when attempt 3's own trace is replayed the same way, 609/609 flown rows.

## 3. Root cause and fix

`core/flight/resume.py::_classify` built `ReplayedEpisodeResult.final_response_text` from the
delivered contact's RAW recorded response. The live runner delivers the E11 normaliser's OUTPUT, and
the seal binds the delivered text to `output_sha256`. For every normalised row the replayed text was
the normaliser INPUT (`sha256` equals `input_sha256` on 471/471), so the seal refused. The earlier
fixes (a451f942, 06a05488, 49f88ce6) are not involved; 49f88ce6's byte-identity proof compared
citation records, not delivered text, and its unit harness carries no normaliser.

Fix (`core/flight/resume.py`, new `_replay_delivery_normalisation`): when the receipt carries a
`deliver_normaliser` block, the replay re-applies the registered rule named by the block to the
recorded response, requires `input_sha256` to be that response and the output to reproduce
`output_sha256`, and delivers the output. A row whose rule does not reproduce is INCOMPLETE and
re-flown, never kept with approximate text. Tests:
`tests/unit/test_flight_resume_recovery.py::test_a_normalised_row_replays_the_normaliser_output_not_the_raw_response`
(drives the real `_canonical_output_rows` over the replayed rows) and
`::test_a_normalised_row_whose_rule_does_not_reproduce_is_re_flown`; both fail before the fix and pass
after. 135 resume/normaliser tests pass.

Identity: the fix touches only `core/flight/resume.py`. The `_phase_seed_inputs` implementation set
(`runtime.py:7702-7719`: kb_policy, knowledge_provider, phase_supply, runtime.py, and the
knowledge-store / candidate-proposal modules) does not include it, so no prepared-artifact identity
changes. The flight commit itself does change.

## 4. Offline seal replay checker

`scripts/analysis/replay_seal_consistency.py` composes the cell's fragments, renders every complete
row of each named attempt one at a time through the real `_canonical_output_rows` (all seal-time
checks, per row), then re-runs I7 (text hash, carrier/arm), I7n
(`_verify_delivery_normalisation` against the recorded response bytes) and I7g where applicable,
and refuses a sample sealed by two attempts. Zero model contacts.

| Code | Original attempt (kept) | Attempt 3 (flown) | Union |
|---|---|---|---|
| pre-fix | 471 checked / 471 failing | 609 checked / 609 failing | 1,080 / 1,080 failing |
| fixed | 471 checked / 0 failing | 609 checked / 0 failing | 1,080 / 0 failing, 0 sealed twice |

The original trace has 472 started samples: 471 COMPLETE, 1 INCOMPLETE ("the episode emitted no
terminal receipt"). Attempt 3's trace (`87be5cef...`) has 609 started, 609 COMPLETE, 0 INCOMPLETE; one
of them carries `duplicate_citation_ids_dropped`. Every row of both traces carries a
`deliver_normaliser` block and the current rule reproduces its recorded output on all 1,080 rows.

## 5. What a fourth attempt needs

- Attempt 3 flew all 609 to-fly rows to completion; the abort was at seal, after every contact.
- `resume_from` takes ONE predecessor (`ResumeDeclaration`, `runtime.py:1480`; I7r in
  `core/bundle/outputs.py:1053` binds kept rows to one predecessor trace). Attempt 3's trace holds only
  its 609 flown samples (the 471 kept rows' contacts live in the original trace). Therefore:
  - resume from the ORIGINAL attempt (supported now, with the fix): keeps 471, re-flies 609
    (about 2,476 contacts, about 74 minutes);
  - resume from ATTEMPT 3 (supported now): keeps 609, re-flies 471 (about 1,900 contacts).
- There is no seal-only or finalise entry: the CLI modes are `check, wire-check, prepare-*,
  prompt-fit, coordinate-fit, worker, campaign`. Sealing all 1,080 rows with zero contacts needs a
  multi-predecessor resume: `resume_from` as an ordered list of pinned (attempt id, trace sha256)
  declarations with disjoint COMPLETE sets; `_merged_canonical_rows` taking the union with an empty
  flown set; the manifest `predecessor_attempt` block listing every predecessor; I7r generalised so
  each kept row binds to exactly one of N predecessor traces; and a campaign path that seals without
  opening a serving session when the flown roster is empty. This checker is the offline
  witness that such a seal would pass: 0 of 1,080 rows fail.

Nothing was registered, flown or re-pinned.
