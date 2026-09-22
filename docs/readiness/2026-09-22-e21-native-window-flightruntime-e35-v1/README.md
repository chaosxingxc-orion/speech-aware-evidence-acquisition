# E21 native-window FlightRuntime registration (item E35)

Owner decision 89 (2026-09-21): make the Earnings21+ConEC carrier
(`earnings21-original`, the contextual-ASR instance of base lock v3) able to
fly the SAME native six-node episode SLURP flies (Perception -> Solver ->
Reviewer x3 -> Planner -> Acquisition -> Delivery normaliser) through the
shared harness (`rails.controllers.EvidenceAgentController`,
`core.flight.FlightRuntime`, the OpenJiuwen executor, the flight checks), as
a four-row smoke registration plus one small paired direct-versus-system
read registration.

**Question this package answers:** does the Earnings21+ConEC carrier compose
and load the same six-node native episode program through the same shared
harness SLURP already flies it through? **It does not** ask, and this
package makes **no claim**, about whether the system arm is more accurate
than the direct arm, or about any effectiveness, comparison, decision, or
generalization question. Both cells below are engineering proofs.

Work performed under item E35 is scoped strictly to **registered-before-
contact configuration, code, and tests**: NO optimisation, NO new mechanism,
NO flight. All work happened in the git worktree
`/home/chao/saea-worktrees/fable-e35` (branch `fable/e35`, base `b03ee619`).

## What this package registers

1. `data.carriers.EARNINGS21_ORIGINAL` gains a `TaskLayout`
   (`task_kind="contextual-asr"`, `official_scorer_id="asr-wer-whisper"`,
   `knowledge_layer="conec-contexts"`, `stratum_key="file_id"`).
2. A new delivery normaliser, `saea-deliver-earnings-text-v1`
   (`rails.delivery_normalisers.EarningsTextDeliveryNormaliser`),
   `carrier_lock_key="earnings21-original"`: deterministic text hygiene only
   (strip a leading role/label wrapper, one XML-ish tag pair, one Markdown
   fence pair, collapse whitespace); refuses (E13 abstain) rather than
   deliver blank text.
3. A carrier-neutral six-node phase program,
   `phase-native-review-revise-acquire-v1`
   (`configs/policy/phase-native-review-revise-acquire-v1.json`): the SAME
   five phases, ceiling (11), and stop rule as SLURP's
   `phase-native-candidates-review-revise-acquire-v1`, but with the
   Perception phase's `response_format_id` null instead of
   `slurp-intent-hypotheses-v1`.
4. Two dataset fragments, four baseline fragments (direct + system, at two
   scales), and two paired experiment fragments (listed below).
5. A reusable, model-free builder script,
   `scripts/build_e21_native_window_unit_subset.py`, and the two derived
   execution-unit artifacts it can materialize (NOT materialized by this
   item -- see "What remains for root").

## Cells

| Cell | Dataset | Baseline | Policy | Rows | Contacts (ceiling) |
| --- | --- | --- | --- | --- | --- |
| `e21-native-window-direct-four-row-v1` | `e21-native-window-four-row-v1` | `e21-native-window-direct-four-row-v1` | `phase-direct-only-v1` | 4 | 4 |
| `e21-native-window-system-four-row-v1` | `e21-native-window-four-row-v1` | `e21-native-window-system-four-row-v1` | `phase-native-review-revise-acquire-v1` | 4 | 44 |
| `e21-native-window-direct-sub10-v1` | `e21-native-window-sub10-v1` | `e21-native-window-direct-sub10-v1` | `phase-direct-only-v1` | 342 | 342 |
| `e21-native-window-system-sub10-v1` | `e21-native-window-sub10-v1` | `e21-native-window-system-sub10-v1` | `phase-native-review-revise-acquire-v1` | 342 | 3,762 |

The four-row roster is the SAME already-authorized one-call construction
subset (`docs/receipts/probe-samples/e21-current-executor-four-row-proof-v1.json`,
call `4320211`) the OBS-path current-executor four-row proof used, re-bound
to the native-window execution-unit mechanism (see decision 2 below). The
sub10 roster is the SAME already-authorized seeded 10-of-44 discovery subset
(`docs/receipts/probe-samples/r4-e21-sub10-sample.json`, probe
`R4-context-dose`, seed `20260807`); n=342 rows is below CLAUDE.md's n>=400
effectiveness bar by construction, so the sub10 pairing supports no
effectiveness claim -- it is sized to exercise the review/revise/acquisition
graph repeatedly rather than only once.

Both system cells are TOOL-FREE (no `phase_tools`, no `knowledge_stores`),
matching the SLURP six-node reference's own current, locked B1-notool base.
The acquisition module is armed exactly as SLURP cell B9a arms it
(`max_iterations: 0`, `contact_budget: 0`) because the runtime binding of
the kind (a) knowledge-requery (item E36) is on another branch and is NOT
implemented here.

## Decisions taken, and why

1. **Delivery normaliser registration site**: registered from
   `rails/delivery_normalisers.py` (beside the SLURP one), the module's own
   existing docstring names it the canonical registration site for
   `core.base.DELIVERY_NORMALISERS`. `scripts/checks/
   engineering_base_check.py`'s `CANONICAL_REGISTRY_FILES` list and its
   `ALL_REGISTRY_VARS` set do not name `DELIVERY_NORMALISERS`/
   `delivery_normalisers.py` at all -- this registry is not tracked by that
   check, so there is no "canonical registration site" constraint from it to
   satisfy or violate.
2. **Four-row execution units are native WINDOWS, not the OBS-path relisten
   spans**: `docs/receipts/obs/e21-current-executor-four-row-proof-v1.json`
   (the existing four-row proof) is an `obs_unit_plan`-shaped receipt
   (relisten spans inside call `4320211`, at scattered parent-window indices
   5/6/9/11). The native-window execution-unit mechanism
   (`core.preparation_windows.load_raw_execution_unit_roster`) requires each
   call's kept windows to be a CONTIGUOUS prefix starting at `w0001` (it
   refuses "duplicated, missing or out of order" units); a scattered pick is
   structurally impossible there without renumbering `request_key`s, which
   would silently break their `payload_sha256`/`encoding_key_sha256`
   binding to the wrong audio. The four-row native-window dataset therefore
   reuses the SAME authorized call (`4320211`) and takes its FIRST FOUR
   native windows from the shared inventory instead -- same authorized
   sample, native-window unit shape.
3. **A new, small execution-unit artifact per cell, not a slice of the
   shared 1,593-row inventory**: `load_raw_execution_unit_roster` requires
   `prepared_execution_units.unit_count` to equal the COMPLETE request count
   of the named batch inside the referenced file -- there is no partial-read
   seam. `scripts/build_e21_native_window_unit_subset.py` re-partitions the
   shared inventory's own already-computed, already-verified per-row
   metadata (never touching an audio byte) into a new, smaller batch under a
   new name, byte-reproducing what the real preparation pipeline would
   produce for that smaller roster.
4. **The derived artifacts are NOT materialized by this item.** The HARD
   RULE for this item forbids writing under `SPEECHRL_DATA_DIR`, and every
   `prepared_execution_units.relpath` resolves under the data root. The
   builder script's `--dry-run` mode was used to compute the exact bytes and
   SHA-256 each artifact WOULD have, WITHOUT writing them; those hashes are
   pinned into the two system/direct baseline pairs below. Root must run the
   two commands in `ledger-rows-needed.md` to materialize them before any
   flight; a mismatch there means the shared inventory or the selection
   changed since this item registered it.
5. **New, minimal, tool-free Perception/Reviewer/Planner instruction files**
   (`configs/probes/e21_native_window_system_{perception,reviewer,planner}_v1.txt`),
   rather than reusing the existing `e21_native_window_{perception,reviewer,planner}_v1.txt`
   files: those existing files belong to the context-tools-full44 baseline,
   which DOES declare `phase_tools` (the Reviewer's file explicitly
   instructs calling `saea-tool-live-speech-span-v1`); this item's system
   arm declares no `phase_tools` at all, so reusing that Reviewer text would
   instruct a tool call that is never wired. The new files follow the same
   structural pattern SLURP's own tool-free six-node instructions use
   (`configs/probes/slurp_native_role_reviewer_v1.txt`,
   `slurp_native_role_planner_v1.txt`: mention only the always-available
   task-contract tool, ask for a bare action token rather than a JSON
   object). The Solver's instruction reuses `probes/e21_native_window_direct_v1.txt`
   verbatim, per the item's own scouting note.
6. **The wire proof (deliverable 6b) uses the existing
   `_ActualEpisodeHarness` fake-transport fixture at its native 2-sample
   scale, run twice**, rather than one 4-sample invocation:
   `test_rails_frozen_core_client._World` (the fixture's own synthetic
   sample source) hard-codes exactly two fake samples per instance; every
   sample within one harness run is already independent (no cross-sample
   interaction), so two disjoint two-sample runs exercise the item's own
   four-row scale exactly as one four-sample run would, without touching a
   shared test fixture used by dozens of other test modules.
7. **The direct arm's dedicated wire proof (deliverable 6c) was not
   duplicated**: `phase-direct-only-v1` is an existing, already-tested,
   unmodified single-phase program; this item's direct-arm test asserts,
   at the config level, that each direct baseline declares exactly the one
   `direct` phase material entry it needs, and relies on that program's own
   pre-existing test coverage elsewhere in the suite for the "one request
   per unit" property.
8. **Combined direct+system experiment fragments** (`cells: [...]`, one
   entry per arm) rather than one experiment file per arm: this item's own
   scouting note names ONE experiment filename per scale
   (`e21-native-window-{four-row,sub10}-direct-vs-system-v1.json`); no
   repository-wide JSON-schema check enforces a single-cell-per-experiment
   shape, so the two arms are registered as sibling cells of one shared
   population, each carrying its own `execution_plan`.

## Model-free proofs (all pass; see the touched-area gate/test run below)

* (a) `tests/unit/test_e35_earnings_native_window_configs.py`: composes and
  loads all four new cells through `core.config.compose` /
  `rails.native_episode_config.load_native_episode_config`.
* (b) `tests/unit/test_e35_earnings_native_episode_wire.py`: the six-node
  Earnings episode through the REAL role graph and a fake transport, four
  synthetic units, asserting the role-visit sequence, the zero-contact
  acquisition module's own summary block, and that the delivered text is
  the Earnings normaliser's hygiene output of a raw Solver response, never
  the raw bytes; a second test proves the ON/OFF arms render byte-identical
  requests.
* (c) direct-arm rendering: see decision 7 above.
* (d) gates: `engineering_base_check.py`, `finite_completion_policy_check.py`,
  `derived_media_confinement_check.py`, `harness_admission_check.py`,
  `results_ledger_check.py`, `tool_catalog_check.py` -- all exit 0.
* (e) `pytest -q -p no:cacheprovider tests/unit tests/contract` from the
  worktree root (repo root prepended to `PYTHONPATH` ahead of `src`, so it
  shadows the shared venv's verl-installed `scripts` package).

## What remains for root

1. Owner decision receipt admitting this readiness package.
2. Materialize the two derived execution-unit artifacts (model-free; NOT a
   flight):

   ```
   python scripts/build_e21_native_window_unit_subset.py \
       --source <data-root>/analysis/SAEA-E21-DR-SHARED-EXACT-WINDOW-INVENTORY-V1/window-inventory.json \
       --batch-name SAEA-E21-NATIVE-WINDOW-FOUR-ROW-V1 \
       --sample-id 4320211 --per-call-limit 4 \
       --output <data-root>/analysis/SAEA-E21-NATIVE-WINDOW-FOUR-ROW-V1/window-inventory.json

   python scripts/build_e21_native_window_unit_subset.py \
       --source <data-root>/analysis/SAEA-E21-DR-SHARED-EXACT-WINDOW-INVENTORY-V1/window-inventory.json \
       --batch-name SAEA-E21-NATIVE-WINDOW-SUB10-V1 \
       --sample-id 4330115 --sample-id 4365024 --sample-id 4365948 \
       --sample-id 4366429 --sample-id 4366522 --sample-id 4384964 \
       --sample-id 4385072 --sample-id 4387383 --sample-id 4389907 \
       --sample-id 4397829 \
       --output <data-root>/analysis/SAEA-E21-NATIVE-WINDOW-SUB10-V1/window-inventory.json
   ```

   Each command must print the `file_sha256` this package's baselines pin
   (see `ledger-rows-needed.md`); a mismatch means refuse and re-check
   before flying.
3. Fresh exposure-ledger rows and re-pin (see `ledger-rows-needed.md`).
4. Enqueue through the SAEA-Batch-Driver (decision 77); this item queues
   nothing itself.
