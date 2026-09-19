# Cell B7a v2 on the sealed anchor: the Node Context Policy at level L1, preregistration

Status: **PREREGISTERED BEFORE CONTACT.** Author: the B7a v2 registration agent, worktree
`/home/chao/saea-worktrees/fable-b7a2`, branch `fable/b7a2`, base commit `25a7f325`.

This document is the **second registration** of cell B7a. It exists because the v1 flight closed on
its second failure; the closure record is
[`docs/results/2026-09-19-slurp-b7a-v1-closure.md`](../results/2026-09-19-slurp-b7a-v1-closure.md).
Everything the v1 preregistration
[`2026-09-17-slurp-b7a-ncp-l1-anchor-v1-preregistration.md`](2026-09-17-slurp-b7a-ncp-l1-anchor-v1-preregistration.md)
says about the **question, the arms, the one moved factor, the metrics, the resampling, the decision
rule, the prompt fit and what is not claimed stands unchanged**, and is not restated here except
where this document must quote it. Those bytes are pinned by the sealed root decision
`slurp-b7a-ncp-l1-anchor-admission-v1` and are **not edited**.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried; no run directory, attempt or
lock was modified; the sealed v1 recovery smoke trace was read only in the sense that this
registration *declares* it as the four-row smoke's reference, not that any byte of it was consumed
here.

## 1. Why there is a v2 at all

| | first failure | second failure |
| --- | --- | --- |
| run id | `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V1` | `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1` |
| when | 2026-09-17, about 21:00Z | 2026-09-19, about 03:35Z |
| reason | `NativeEpisodeError: Planner output names no registered action` | `NativeEpisodeError: native episode node failed: [100054] component 'reviewer_1_role' execute 'invoke' error, reason='metered completion is non-authoritative because finish_reason is 'length''` |
| spend | 3,278 calls, 8,973.150063 speech seconds, 618 rows contacted | 1,451 calls, 1,451 request-fit receipts, 3,830.12 speech seconds, roughly 290 complete rows |
| fix | item E8c (illegal Planner action becomes a row disposition), smoke passed 2026-09-18 | this registration |

Section 8 of the v1 recovery note and the owner iteration rule of the study `CLAUDE.md` -- *at most
one recovery re-registration per flight; a second failure stops the flight and the fix is proven on a
4-row dry run before another mechanism is admitted* -- close the v1 flight. **No third registration
under v1, no replay, no row filtering.** This is a new registration with its own run ids, its own
four-row dry run and its own single recovery allowance.

## 2. Root cause, and the one key that moves

Exactly one contact in the aborted recovery trace reached **512** completion tokens, the `max512`
cap of the serving geometry; every other contact stayed below 400. The SLURP native baselines -- the
sealed anchor `configs/baseline/slurp-native-dual-store-train-fold-a-anchor-v1.json` and every B cell
derived from it -- omit `native_episode.finite_completion_policy`, and
`rails/native_episode_config.py` defaults it to `"raise"`
(`raw.get("finite_completion_policy", "raise")`). One truncated completion therefore propagates out
of the episode and kills the campaign.

The alternative is already implemented and tested and needs **no new code**:
`reproduction/ojw/native_episode.py`'s `_finite_terminal_outcome`,
`rails/native_episode_receipt.py`, `rails/runner.py` (around lines 2660-2720) and
`core/flight/runtime.py` (around line 7993). With
`finite_completion_policy: "deliver-latest-or-abstain"` the row is **retained** with
`terminal_disposition.reason == "finite_completion"`, the truncated contact is recorded under
`interrupted_role`, and the latest delivery-eligible Solver draft is delivered -- or the row abstains
with empty output when no Solver had completed. The A2T and E21 native baselines set the key
explicitly, and cell B8b's fragments already carry it.

**It is a harness-robustness key, not a factor.** It renders no request byte, it is consumed only by
`rails.runner`'s `NativeEpisodeSpec`, and it only decides whether a finite completion aborts the
flight or retains the row. `tests/unit/test_config_table_module_switches.py::
test_the_two_b8b_fragments_arm_the_block_and_nothing_else` already sets it aside by name for exactly
that reason. The **factor under test is unchanged**: `native_episode.context_policy` at level
`structured` on exactly the eight model-output boundaries, `on_parse_failure` `raw` everywhere except
`solver:plan-action` (`refuse`), the four tool-observation boundaries declared `raw`, and no producer
response format.

## 3. The new clause (the only one this registration adds)

> **Rows whose `terminal_disposition.reason` is `finite_completion` are RETAINED and scored as
> delivered -- the latest delivery-eligible Solver draft, or an abstention with empty output when no
> Solver completed -- and are never filtered out of the paired read. Their count, their sample ids and
> the by-role / by-stage / by-finish-reason breakdown that
> `analysis.native_episode_diagnostics` emits as its `finite_stops` block are a MANDATORY diagnostic
> in the verdict, beside the node-context receipt table. A high count is a finding about the role's
> output length on this base; it is reported, not repaired inside this cell -- repairing it would be a
> new registration.**

The v1 recovery's own mandatory diagnostic -- the flight's `planner_action_illegal` count and the
sample ids that carry it, those rows likewise retained and never dropped -- is **inherited unchanged**.

## 4. What does not change

- **No roster or split change.** The same 1,080-row TRAIN Fold A roster, `SLURP-EVO-FOLD-A-V2`, split
  identity `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, same ordered ids. The
  whole roster flies from row one; no row of either aborted attempt is reused or filtered out.
- **No context-policy, prompt, role-graph, knowledge, retrieval, cap, geometry or session change.**
  Reviewer 3 / planner 1 / solver 1 / perception 1, `max_revisions` 1, policy
  `phase-native-candidates-review-revise-v1`, program ceiling 11 contacts, both stores at v1, the
  resident session `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, 24,576-token
  slot, four slots.
- **No decision-rule change.** Primary pooled official SLU micro F1 against the sealed dual-store
  anchor with a CI95 lower bound > 0; intent non-inferior within **1.0051 pp** (the TRAIN A own-null
  half-width from cell B0r, `h_SLU` 1.1218); the scenario null band; projection v3 agreeing in sign;
  and the rule that a NEUTRAL L1 still enters the SLURP default plan.
- **No estimator change.** Paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**,
  CI95 for advancement and CI90 for diagnostics; sensitivity is the paired scenario-stratified row
  bootstrap at the same draws and seed; every verdict carries the per-scenario table over all 18
  scenarios in both the natural-mixture and the equal-scenario weighting.
- **Comparators are sealed bytes, never re-flown or re-scored.** Primary
  `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` (scores SHA-256
  `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47`); secondary, for the
  system-versus-direct column only, `SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1`
  (scores SHA-256 `7840a959fe4f43928fda0e0cacfe8c0ee4200116bfcd269bfe3451b59da29c38`).

What *does* change is bookkeeping: new run and attempt ids, this package's own `native_contact_fit`
identity, its own two speech-feature identity ids (trace provenance only), and the prepared-supply
pin the coordinator's re-pin cycle rebuilds.

## 5. The wire check: the only configuration difference is the episode key

`core.flight.cli wire-check` remains **unavailable** for any native-episode cell, for the reason both
v1 packages record: `FlightRuntime._dispatch_phase_program` refuses a native episode whose transport
is not the real shared speech renderer. What stands in its place:

1. **The only configuration difference from the closed v1 recovery is the episode key.** Composed end
   to end, the v2 and v1-recovery configurations differ in `native_episode` (exactly the added
   `finite_completion_policy`), `native_contact_fit`, `what_this_is`, both
   `speech_feature_*_id`, and the experiment fragment's own `cells`, `date`, `experiment_id`,
   `fragment_kind`, `failure_policy`, `purpose` and `generation_budget` definition. Every
   model-facing key -- `policy`, the rest of `native_episode` including the whole `context_policy`
   block, `phase_material`, `phase_tools`, `knowledge_stores`, `task_instruction_template`,
   `task_instruction_fill`, `task_instruction_template_active`, `serving_slot_tokens`,
   `serving_slots`, `arm`, `evidence_source`, `evidence_mismatch`, `scorers`, `population`,
   `populations`, `split_id`, `service_session` and both speech-packet promotion keys -- is
   **byte-identical**. `tests/unit/test_b7a_v2_config.py` pins this.
2. **Request bytes are identical.** `finite_completion_policy` is read by `rails.runner` when it
   builds `NativeEpisodeSpec` and is never serialised into a payload. The v1 recovery's
   request-envelope comparison already proved, over the v1 arm's **3,278** sealed `MODEL_REQUEST`
   payloads, that no run, attempt or speech-feature identity string of either registration appears in
   any payload byte, and that each payload's own `key_representation_id` and `matcher_policy_id` are
   derived from the **policy** id rather than from the baseline. That proof is not re-derived here.
3. **The four-row smoke proves it in flight.** Every `MODEL_REQUEST` record of
   `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-V2` must carry a `request_sha256` equal to the
   corresponding record of the sealed v1 recovery smoke
   `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-RECOVERY-V1`, whose trace lives under
   `SPEECHRL_DATA_DIR/runs/SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-RECOVERY-V1/`. **Reading that
   trace is allowed; writing to it is not**, and no answer, reference or quality field of it is read.
   The comparison covers the four rows' Perception and Solver requests and every Reviewer and Planner
   request on a row that took the same trajectory; a request whose predecessor response differs is
   **reported**, never silently excused, because greedy decoding at `temperature 0` is not bitwise
   reproducible across batch compositions.

## 6. Cells, identities and registered hashes

| item | value |
| --- | --- |
| arm cell | experiment and cell `slurp-native-ncp-l1-anchor-train-fold-a-v2`, run `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-V2`, attempt `attempt-slurp-native-ncp-l1-anchor-train-fold-a-generation-v2` |
| arm FIT | `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-FIT-V2` / `attempt-slurp-native-ncp-l1-anchor-train-fold-a-fit-v2`, 47,520 endpoints |
| smoke cell | experiment and cell `slurp-native-ncp-l1-anchor-smoke-4-v2`, run `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-V2`, attempt `attempt-slurp-native-ncp-l1-anchor-smoke-4-generation-v2` |
| smoke FIT | `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-SMOKE-4-FIT-V2` / `attempt-slurp-native-ncp-l1-anchor-smoke-4-fit-v2`, 176 endpoints |
| baselines | `configs/baseline/slurp-native-anchor-ncp-l1-train-fold-a-v2.json`, `configs/baseline/slurp-native-anchor-ncp-l1-smoke-4-v2.json` |
| experiments | `configs/experiment/slurp-native-ncp-l1-anchor-train-fold-a-v2.json`, `configs/experiment/slurp-native-ncp-l1-anchor-smoke-4-v2.json` |
| campaign plan | `configs/campaign/slurp-native-ncp-l1-anchor-train-fold-a-v2.json` |
| composed / protocol (arm) | `73a817ffda56b02501002685db0cd695516425644544fa040464efb17849d494` / `f5a6733f39952cfba2fc418d233c8acf1ff3a3758f16765737de47cc2fbceb31` |
| composed / protocol (smoke) | `fbe7556e225a4f6ab53f466b09f3b8fcd1efba45404e55a566d0f081b16e8880` / `1f3bdd15ece682b449d0706301a633af09a747f5ef38fa3b93aacc65ae0e52e5` |
| plans | `docs/readiness/2026-09-19-slurp-b7a-ncp-l1-anchor-v2/` -- four prospective and four `-registered` plans, the protocol document and the analysis recipe |
| readiness | both cells `held` with the inherited `preparation` requirement; the coordinator adds the `decision` requirement, rebuilds the prepared supply and flips with `scripts/flights/repin_cell.py` |

**Registered hashes are pre-flip.** Every composed and protocol hash above is the value of the five
v2 config fragments exactly as committed: readiness `held`, the inherited preparation requirement
present, `prepared_phase_supply` inherited, and no decision requirement. Re-pin with
`scripts/flights/repin_cell.py`, never a hand edit.

**The prepared Perception supply is inherited and will be rebuilt.** Both baselines keep the v1
recovery's `prepared_phase_supply` pins, whose `output` blocks reproduce the sealed anchor
preparation's on **1,080 of 1,080** (`ba5e1faa...`) and **4 of 4** (`512583ec...`) rows.
`core.preparation.artifact_inputs` binds the composed values -- this cell's identity ids and the new
episode key included -- so those pins will **not** verify against the v2 digests. That is by design:
`core.flight.repin.ensure_artifact_pinned` finds the mismatch, derives a fresh artifact under
`prepared/<run id>/` and **asserts its `output` block equals the inherited artifact's** before writing
the new pin into the baseline and the readiness requirement. **Never pass `--allow-output-change`**:
part of the one-factor claim is that the Perception selection does not move.

## 7. Budgets (a fresh 1,080-row flight)

| | arm | smoke |
| --- | --- | --- |
| generation contacts | 11,880 | 44 |
| FIT endpoints | 47,520 | 176 |
| repeated speech seconds | 33,930 | 117 |
| fit-inclusive GPU hours | 12.0 | 1.0 |
| native task-contract calls | 6,480 | 24 |
| official complete scoring jobs | 1 | 0 |
| ASR / encoder / paid-API calls | 0 | 0 |

These are ceilings, not targets: 1,080 x 11 is the exact program maximum, and the anchor's own
realized cost at this geometry was 5,417 contacts (5.016 per row), 15,459.76 repeated speech seconds
and 3.388 GPU hours. The two aborted v1 attempts spent 3,278 and 1,451 contacts against their **own
closed run ids**; nothing is charged here. The cap is enforced run-cumulatively across every attempt
of this run id (`core.attempts.AttemptStore.prior_actual_usage`, invariants I3/I6), which is also
what makes the allowed resume-recovery affordable without a new ceiling.

## 8. Failure rule, and the resume-recovery this flight is allowed

Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster,
role-graph, prompt, geometry or cap change, and no silent recovery. This registration carries **one**
root-diagnosed recovery allowance, and under **owner decision 22 of 2026-09-18** that recovery takes
the **resume-recovery** form: its own experiment fragment declaring
`resume_from {attempt_id, trace_sha256}`, the **same** run id and a new attempt id, with
`core/flight/resume.py` replaying the predecessor trace model-free so COMPLETE rows are kept without
selection and only the rest are flown, and the seal merging them. No `resume_from` is declared by
this registration: v2 is a fresh flight from row one. **A second failure closes the v2 flight** on the
same terms as v1 -- no third registration, no replay, no row filtering, and the fix proven on a
four-row dry run before another mechanism is admitted. A failed four-row smoke stops v2 on the same
terms. One experiment in flight at a time.

## 9. What is NOT claimed

Everything section 11 of the v1 preregistration lists, unchanged, and in addition:

- **Nothing about task quality from either closed v1 attempt.** The 618 rows the v1 arm contacted and
  the roughly 290 rows the recovery completed were never scored and never read; no partial read is
  permitted.
- **No claim that the finite-completion policy improves anything.** It decides what happens to a
  truncated row. The cell's question is unchanged.
- **No claim about why a Reviewer completion reached the cap**, nor that v2 will meet none.
- **The four-row smoke proves form and request identity, nothing else.** A four-row roster cannot by
  itself reach the finite-completion path; that path is proved by the harness's own committed tests.
- **A structural smoke result is never a quality result.**

## 10. What this package does not authorise

No readiness flip, no model contact, no `prepare-supply` run, no re-pin, no default-plan edit and no
harness-admission entry. The admission entry for the module "node context policy L1" is written from
the sealed verdict, never from a registration.

## 11. Launch

Exactly the v1 runbook (`2026-09-17-slurp-b7a-ncp-l1-anchor-v1/README.md` sections 2-7) with the v2
names, and the package's own [`README.md`](2026-09-19-slurp-b7a-ncp-l1-anchor-v2/README.md) carries
the ordered steps. Flip the **smoke first**, fly it, compare its `MODEL_REQUEST` digests with the
sealed v1 recovery smoke's, then re-pin and flip the arm.
