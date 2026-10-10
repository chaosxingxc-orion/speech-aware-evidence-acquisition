# Decision 243 cleanup v1 (2026-10-10)

Owner decision 243 (2026-10-10): "Clean it up." Engineering agent (Sonnet) in worktree
`fable/decision-243-cleanup`, cut from `master` at `9ba3c72d7`. Model-free throughout: zero model,
tokenizer, encoder, scorer, server, GPU and network contacts; no utterance text or gold was read or
printed; no roster, flown-cell fragment, receipt, ledger row of a flown cell or sealed output was edited.
`git status --porcelain` on the master checkout was empty at the start.

## 1. Tree-mode `flight_registration_check.py`

Before (master at start): `FAIL (979 cell(s) in scope (tree mode), 585 clean, 10 blocking, 384 advisory; blocking from 2026-09-26 in tree mode)`.
After: `PASS (969 cell(s) in scope (tree mode), 585 clean, 0 blocking, 384 advisory; blocking from 2026-09-26 in tree mode)`.

The 2026-10-09 residue was 12 blocking cells. PSV4 (`psv4-fold-b-v1`, `psv4-fold-b-smoke-4-v1`) flew on
2026-10-09, its rows are consumed, and it no longer appears. The ten remaining blockers were all ready,
unflown ChatGPT-era drafts. Each was retired with the 2026-09-19 ledger-hygiene convention:
`readiness.state` becomes `superseded` with one appended English sentence naming decision 243 and
2026-10-10, and every still-unconsumed exposure row of the cell is closed (`consumed` no to yes, one
appended sentence). Evidence for "never flown, zero contacts": no `runs/` or `attempts/` entry exists for
any of the run ids on the data root; the only artifact is a model-free
`prepared/<run id>/phase-supply-v1.json` (plus producer lock) for nine of them; the tenth has nothing.

| cells retired | why they could not launch | ledger rows closed |
| --- | --- | --- |
| k4 recovery1 remaining-b2: `branch-13`, `branch-14`, `branch-15`, `branch-16`, `seed`, `seed-aa` | DRAFT rows never countersigned, no decision receipt | 12 (generation + FIT each) plus 1 family READ row |
| simple-consumption N100 `review-off`, `solver-lookup` | open defect: N20 prepared implementation source differs | 2 each (generation + FIT) |
| simple-consumption N100 `seed-aa` | registered cumulative speech-audio budget 1500 is below the legal bound 3820 | 2 (generation + FIT) |
| simple-consumption N100 `seed-n100-audio-recovery1` | no ledger row, no readiness package | none exist |

Total: 10 cells, 19 ledger rows. The owner line is closed by owner decisions 230 and 234 (2026-10-09: the
joint N100 composition is not flown, no new N20/N100 GPU family). The unconsumed `DESCRIPTIVE-READ` rows of
the simple-consumption N100 family and the K4 observe-boundary b2 rows were left alone: they belong to flown
or non-blocking cells and are not decision-243 scope.

Tests that used the retired cells as real archetypes (18 cases) were repaired, not loosened. The first full
suite after the retirement listed 20 failures (19 from the retirement plus the AST residue); campaign loading
refuses a superseded cell by design, so: `test_architecture_audio_budget.py` reads the registered fragment JSON
directly for the budget arithmetic (its authoring-prewrite case for `seed-aa` now expects the earlier
"explicit scientific readiness" refusal, `seed` still expects the audio-budget refusal);
`test_batch_campaign_inspection.py` builds the member cells in memory with readiness forced to `ready`;
`test_manual_architecture_identity_map.py` marks its fixture COPY of the three fragments ready. Nothing in the
real repository was changed for these tests.

## 2. Fold B filler family: known cumulative exposure

`docs/receipts/rosters/slurp-stage3-filler-fold-b-v1.json` (1,080 rows, the whole of TRAIN Fold B,
`slurp-evo-fold-b-v2`) is hash-pinned by the filler configs; it was not altered, so its embedded
`disjointness_proof` still reads zero. The known overlaps are recorded beside it in
`docs/receipts/filler-family-known-overlaps-2026-10-10.json` (the sha256 of the family roster and of both
overlapping rosters are pinned in that record):

| roster | cohort | size | shared sample ids | shared utterances |
| --- | --- | ---: | ---: | ---: |
| `slurp-system-text-selection-400-analysis-v1` (`SLURP-SYSTEM-TEXT-SELECTION-400-V1`) | TRAIN Fold B positions 401-800 | 400 | 400 | 400 |
| `slurp-system-text-update-3-400-analysis-v1` (`SLURP-SYSTEM-TEXT-UPDATE-3-400-V1`) | TRAIN Fold B positions 1-400 | 400 | 400 | 400 |

The two are mutually disjoint, so 800 of the 1,080 filler rows carry the exposure and 280 do not. The sibling
rosters `update-1-400` and `update-2-400` are drawn from TRAIN Fold A and overlap nothing in the family.
They were created by the ChatGPT-era commit `84c22d759` (2026-10-02), which projected the already frozen
owner214 optimization/selection lists (protocol-control v3 under owner217) into analysis rosters; it was
metadata only, with no new contact.

Meaning: Fold B rows in these two rosters carry registered system-text-search exposure (selection and
update-3 feedback). The family is NOT independent of that search. NX reads on Fold B are development numbers
already by decision 28; this adds a named exposure source and no new restriction.

`tests/unit/test_filler_family.py::test_disjointness_proof_is_complete_and_zero` keeps every zero assertion
(embedded proof, governed splits, required receipts, every other roster and probe sample) and exempts only the
two named rosters, which it asserts at exactly 400 shared ids with their sha256 pinned to the record. Any
third overlap, or a changed roster, fails it.

## 3. `test_actual_reviewed_full_runtime_ast`: review package (left failing)

The oracle (`rails/natural_source_compatibility.exact_runtime_delta`) proves that
`core/flight/runtime.py` equals the historical natural runtime (`d4ba0ec70`) plus exactly one hunk, the
audio-guard insertion in `FlightRuntime.preflight`. Master's `runtime.py` has sha256
`343fc59074d8223661322d54eb29f0c03fd9a707bc2de018ebb4901c0134143b`; `git diff d4ba0ec70 HEAD` shows 213
insertions and 3 deletions in 8 hunks, from four commits. Hunks (listed by function; H5 and H6 are adjacent in the same call):

| # | commit | hunk | what it does | cells affected | touches the natural-source path? |
| --- | --- | --- | --- | --- | --- |
| H1 | `f5617bcd9` | `_supply_variant_binding`, +5 near line 3441 | early `return None` when the supply-variant group `is_template` | NX R1 template cells (4 baseline fragments) only | no; unreachable without `roles.solver.template_variants` |
| H2 | `856d3206a` | new `_perception_branch_solver_supply_binding`, +50 near 3497 | level-2 Perception-branch Solver supply resolver; returns `None` unless a level-2 `roles.perception.branches` group is declared | P-SV level-2 branch cells | no; new method, `None` for every other cell |
| H3 | `f5617bcd9` | new `_template_variant_materials`, +77 near 3497 | reads the pinned arm templates, refuses a missing or misdigested file, renders and returns per-arm material builders, folds `template_variants` into the phase-material receipt | NX R1 template cells only | no; new method, `None` unless a template group is declared |
| H4 | `98f34cab3` | `preflight`, +8 near 4642 | the audio-adequacy guard | cells with a manual architecture audio budget | this IS the reviewed delta, the only hunk the oracle allows |
| H5 | `f5617bcd9` | native-episode construction, +6 near 7698 | passes `template_variant_materials=` (value of H3) | evaluated for every native cell; `None` unless a template group | on the shared native path; behaviour-neutral by inspection |
| H6 | `856d3206a` | native-episode construction, +7 near 7732 | passes `perception_branch_solver_supply=` (value of H2) | evaluated for every native cell; `None` unless level-2 | on the shared native path; behaviour-neutral by inspection |
| H7 | `f5617bcd9` | `_default_phase_program_binding` return dict, +14 near 10405 | adds keys `phase_specs`, `protected_material`, `material_with_static_text` (a closure over `build_material_for_phase`) | read only by H3 | shared path; keys unread by non-template cells |
| H8 | `6633c9251` | supply-variant delivery validator, +36/-3 near 11348 | declared-kind check: a template block (`template_variants`, v4 receipt) versus a supply block (`supply_variants`); refuses a Solver role declaring both or a receipt of the other kind; fixes `arm_visits` for template blocks | cells with sealed supply or template variant delivery | inside the supply-variant delivery branch only; non-variant cells never enter it |

Assessment: by inspection no hunk changes the behaviour of a cell that declares neither `template_variants`
nor a level-2 branch group, so the natural-source preflight (H4, the guarded hunk) is untouched, and every
other hunk is None-gated or confined to a variant-delivery branch. That is an inspection, not a proof:
H5, H6 and H7 edit the shared native path (extra call arguments and dict keys), and the AST oracle can only be
satisfied by equality, so it must be re-reviewed, not relaxed.

Re-pin decision: NOT re-pinned; the test stays failing and nothing was edited. Reasons: (1) the compatibility
record is a root-approved data-root artifact (`ROOT APPROVED SOURCE COMPATIBILITY`, scope
`precontact-audio-adequacy-only`) whose bytes are pinned by decision receipts and registered plans; it
carries no `runtime.py` sha that a repository edit could update, and rewriting it is a root act; (2) the only
in-repo pin is the oracle itself (the old commit `d4ba0ec70` plus the single `GUARD` hunk), and changing it to
admit H1-H3 and H5-H8 means redefining what was reviewed.

What the root reviewer must decide: whether H1-H3 and H5-H8 (all None-gated by inspection) are accepted as
additional reviewed deltas, and if so how the oracle expresses them (an explicit allow-list of hunks, or a new
reference commit with a new compatibility record and re-pinned plans). Until then the AST test is a live
reminder that the natural-source compatibility claim predates NX.

## 4. Verification

The verbatim suite and check summary lines are in the engineer report that accompanies this branch.

## 5. Residue

* `test_actual_reviewed_full_runtime_ast`: open for the root reviewer (section 3).
* Four checks need arguments and cannot run standalone: `experiment_population_config_check.py`,
  `openjiuwen_native_reuse_check.py`, `resume_prelaunch_gate_check.py`, `system_text_proposer_capacity_check.py`.
* 384 advisory tree-mode findings (historical flown cells and stale-ready drafts registered before
  2026-09-26) remain by design: the gate reports and never rewrites sealed bytes.
