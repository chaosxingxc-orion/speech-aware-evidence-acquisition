# WAVE R7 of the openJiuwen convergence: rails standardization (2026-09-08, v1)

**Status: LANDED, model-free, zero model contacts, no GPU.** Branch `wt/ojw-r7`, from master
`5e4a6cf8` (merge wave 6). Authority: owner Decision 12-F, item **#7** of the ordered change list
in `docs/readiness/2026-09-08-openjiuwen-implementation-assessment-v1.md` section 5.2, whose three
parts are registration (Group C), the two out-of-base controllers (Group A) and the launcher tier
(Group B). Nothing here is a preregistration, an admission or a flight; no cell is flyable on the
strength of this note.

The assessment's own framing was that the standardization debt is **disposal and registration, not
rewrite**. That held. No renderer was rebuilt, no sealed byte was rewritten, and the one class that
disappeared was replaced by a phase program whose wire bytes are proved identical against the
flight that produced it.

---

## 1. The ratchet, before and after

`scripts/checks/engineering_base_baseline.json`, captured at `bd366feb`, measured the engineering
base's own violations in five rules. This wave moves three of them and leaves two for their own
waves. The baseline moves **down only**; `python scripts/checks/engineering_base_check.py` PASSes
on the new one.

| rule | before | after | what moved |
|---|---:|---:|---|
| `unregistered_config_values` | 36 | **0** | all 36 resolve as frozen-historical entries (section 2) |
| `launcher_dirs` | 45 | **42** | 3 orphan directories archived (section 4) |
| `controller_classes_outside_controllers` | 33 | **30** | `HardValidityRepairController` folded away; 2 launcher copies archived |
| `adapter_subclasses_outside_adapters` | 8 | 8 | untouched; belongs to the per-carrier probe waves |
| `probe_modules` | 36 | 36 | untouched; see section 6 |
| **total** | **158** | **116** | |

Two other gates move with it: `scripts/checks/tool_catalog_check.py` now reports **26 tools**
(W3's eight plus this wave's eighteen) and still PASSes, and every one of the eighteen is placed in
`configs/toolkit/task-toolkits-v1.json`'s `tool-call` rows, because that check refuses a registered
tool no toolkit names.

---

## 2. Group C: the 36 unregistered config values

### 2.1 What the scan found

The assessment expected each of these names to be "resolved by its own probe module's constant
instead", and proposed registering them by pointing a `POLICIES`/`EVIDENCE_SOURCES` entry at the
probe function that implements it. A full-tree scan of the 31 distinct ids says otherwise:

* **28 of 31 appear nowhere in `src/` at all.** They are declarative labels inside their own
  baseline fragment, read by nothing: the probe launcher that flew each cell hard-codes the
  behaviour and never resolves the config value.
* **3 appear in `src/`** — the G4, G5 and G6 `CONTROLLER_POLICY_ID` constants — and each only as a
  receipt label inside its own `rails/probes/*` module, registered nowhere and resolved by nothing.
* **No id names a callable with its registry's protocol.** An `EVIDENCE_SOURCES` entry is
  `(sample, carrier_lock_key, values) -> EvidenceItem` reading ConEC/E22 material off disk; the
  Audio2Tool "evidence sources" are handbook renderers of an entirely different shape. Binding one
  of these names to a renderer would claim a protocol the sealed flight never used.

The second half of the finding decides the disposition. **Every one of the 19 fragments carrying
these ids is cited by a sealed receipt directory under `docs/checks/`, and 15 of them by
`docs/exposure-ledger.md`.** A sealed row's fragment is immutable: it may not be archived, and it
may not be edited to say something the flight did not say. So no fragment moved.

### 2.2 What was built instead

`core.base.FrozenHistoricalComponent` — the third answer between "live registration" and "delete":

* it **RESOLVES**, so the value is a name the base accounts for and
  `engineering_base_check.py` reads it out of the canonical registration sites like every other
  component id;
* it **carries the provenance** — the fragment that declares it and the sealed receipt directory
  that consumed it;
* it **REFUSES** every call and every component-like attribute read, naming both. Registering an
  id here is bookkeeping, never rehabilitation.

The table is `src/speech_aware_evidence_acquisition/core/frozen_historical.py`; the registrations
are string literals at the call in `core/policies.py` (17 `policy` ids), `core/evidence.py`
(14 `evidence_source` ids) and `rails/controllers.py` (the two `controller_policy_id` values an
experiment fragment declares), because the gate reads those files' source without importing the
package.

`tests/unit/test_frozen_historical_registrations.py` pins all of it: the 36 baseline entries
written out verbatim (so shrinking the baseline cannot shrink the test), every id resolving, every
resolved object being frozen-historical, every receipt directory and fragment existing on disk,
every fragment really declaring the id it is credited with, the refusal message naming both, and
the fact that no frozen-historical id shadows a live registration.

---

## 3. Group A: the two out-of-base controllers

### 3.1 `HardValidityRepairController` — folded away, and proved on the sealed flight

The class is **gone**. Its sequencing is `configs/policy/phase-hard-validity-repair-v1.json`
(`draft`, then `repair` only when the draft is hard-invalid, `stop_rule:
"stop-policy-optional-early-exit"`) walked by `rails.controllers.EvidenceAgentController`, built by
`rails.controllers.make_hard_validity_phase_controller`. Three registered seams carry what the
class used to carry privately:

| what the class did privately | what carries it now |
|---|---|
| two hard-coded instruction constants | `material_for_phase`, rendering the same two constants `rails.a2t_hard_validity` still owns |
| sealed a DERIVED bounded validity report as its state | `state_view_for_phase`, resolving `core.base.PHASE_STATE_VIEWS["a2t-hard-validity-repair-report-v1"]` |
| branched on `QueryState.loop_step == 0 / == 1` | the phase index — **W2's caveat is closed** |
| stopped early on a valid draft | the base's own `stop_policy` seam |
| its findings, visible to nobody | `core.base.JUDGES["a2t-hard-validity-flag-v1"]`, the seventh judge |

**The equivalence proof.** `tests/unit/test_a2t_hard_validity_fold.py` replays the sealed
`SAEA-A2T-G3-PLAIN-ENGLISH-V1` matched arm — 40 rows, 45 contacts, five of which spent a repair —
through the folded program, using the flight's own sealed response bytes. The flight is **not
re-run** and no model is contacted. Per row it asserts: the same number of contacts in the same
order with the same `contact_id`; the same CONTROL-turn instruction bytes; the same AGENT_STATE
content bytes (the bounded validity report, which is what the repair contact actually reads); the
same declared arm identity (`key_representation_id`, `matcher_policy_id`); the same
final-response contact. It also asserts that exactly five rows repaired, so a fold that repaired
none or all could not pass by vacuous equality.

**Three declared identity deltas, pinned rather than waved at.** The sealed state's `state_id`
(`state:hard-validity:<sample>:<hash12>` → `draft:<sample>`), its `state_kind`
(`hard-validity-report` → `phase:draft`) and its `producer_policy_id` (`hard_validity_v1` →
`phase-hard-validity-repair-v1`), plus their one consequence: the repair contact's
`query_state_sha256` moves with the state id. These are receipt identity, not request content, and
they must change — a receipt still claiming `hard_validity_v1` would name a controller this
repository no longer has. The test asserts the new values and asserts they differ from the old.

`rails/probes/a2t_g3_plain_english_flight.py` now builds the folded factory, so the retired class
has no callers anywhere.

### 3.2 `KbAlphaBlendController` — one decision body, two shapes

`kb_policy.py` is the migration source the owner rule keeps "until disposal", and its class is not
in the ratchet. What blocked its disposal was that the whole acquire decision lived inside
`_advance_after_direct`, unreachable from the base. That is now
`rails.kb_policy.compute_alpha_blend_decision`, a module-level function over the same frozen organs
(`multidim_recall`, the registered ranker and fuser, `_fused_label_scores`, `_blend_scores`,
`_argmax_labels`) returning an `AlphaBlendDecision` that names which of the four retain-primary
cases fired. **The controller and the fold call the same body**, so they cannot drift; there is one
implementation, not two.

`make_kb_alpha_blend_phase_controller_factory` expresses it on
`phase-direct-evidence-alpha-blend-v1` through the base's own seams: `stop_policy` is the
retain-primary shortcut, `supply_for_phase` is the acquire returning the same
`RankResult`/`FusionDecision` pair. `tests/unit/test_kb_alpha_blend_fold.py` runs both shapes over
the same fixtures at alpha 0.0 / 0.5 / 1.0 and with no vectors, and asserts the same branch, the
same contact ids and instructions, the same selected value ids and the same rank-result hash.

**One declared behavioural delta**, and it is the standardization rather than a side effect: the
base SEALS the direct answer as an `AgentStateArtifact` and carries it on the successor
`QueryState`, so the evidence contact sees it as an agent-state turn; the retired controller sealed
nothing. Every other phase program in this repository traces its own intermediate answers that way,
and a cell that wants the old shape is asking for an untraced intermediate answer. The test pins
the delta.

**Why the class stays for now.** Five SLURP experiment configs declare
`controller_policy_id: "saea-kb-alpha-blend-v1"`. Flipping a live cell's controller is a change to
what that cell IS and belongs to that cell's own preregistration, not to a standardization wave
(study rule: one experiment in flight). The fold is built, proved and ready; the flip is a config
decision.

### 3.3 The base seams this wave added

Three optional keywords on `EvidenceAgentController`, each defaulting to today's behaviour and each
byte-identical to it when omitted:

* `state_view_for_phase(phase_name, response_text) -> str` — what the phase SEALS. `None` seals the
  raw response. `source_response_sha256` always hashes the RAW response, so a view can never
  disguise which bytes the core returned.
* `contact_identity` — a cell's own `(key_representation_id, matcher_policy_id)`, one pair or one
  per phase. It exists because two arms of one cell can share a phase program and still be
  different arms (G3 matched vs shuffled differ in exactly the matcher id), and because a folded
  cell must keep the identity its sealed receipts carry.
* and one behavioural widening: `stop_policy` now receives the **staged** context — this phase's
  just-sealed state appended, `query_state` unchanged — which is the same context
  `supply_for_phase` and the Reviewer already receive, and a strict superset of what it saw before.
  An early exit conditioned on the answer just given needs it, and `stop_policy` had no consumer in
  `src/` before this wave.

`core.base.PHASE_STATE_VIEWS` is the registry, populated from `rails/controllers.py`.

### 3.4 The eighteen `rails/a2t_*` renderers

Group A's verdict was **"Register, do not rebuild."** Eighteen modules (the assessment says
nineteen; the tree has eighteen), one catalog entry each, all in the SYSTEM-invoked catalog W3
built:

`rails/tool_wrappers/a2t_renderers.py` holds eighteen **passthrough** wrappers — `*args, **kwargs`
forwarded unchanged, the wrapped function's own return value in `ToolResult.result`. Each manifest
declares the axis (4 ORG, 11 SUPPLY, 3 USE), scope `carrier:audio2tool`, cost class `cpu`, ledger
row (`none`, except the frozen-asset loader's `tool-contact`), and pins the sha256 of the entry
point's own source. The typed I/O spellings are the wrapped functions' **own annotations**, read
off their signatures rather than restated.

`tests/unit/test_a2t_renderer_tools.py` (64 tests) asserts: every `rails/a2t_*.py` module on disk
has exactly one entry, so a nineteenth cannot appear without a row and a pin; every pin equals the
live source hash; every wrapper is structurally a passthrough (signature and source); the wrapped
result equals the direct result field for field where the inputs are cheap to build; a wrapper
raises exactly the renderer's own exception type and message; every renderer is placed in a
toolkit; and every module names its own catalog id in its docstring, so a reader of a renderer
finds the catalog row without reading `rails/tools.py`.

The modules are **kept and marked**, not moved. The 2026-08-08 ruling is untouched: this catalog is
system-invoked, and `build_tool_entry` refuses a manifest that does not say so.

---

## 4. Group B: the launcher tier

Full inventory and disposition: `docs/archive/launchers/2026-09-08/INDEX.md`.

The rule, applied to all 45: a launcher directory is an **ORPHAN** when nothing outside it names
any of its files — not an artifact of its own receipt directory, not `docs/exposure-ledger.md`, not
a test, not another document or config. Everything else is **kept, immutable**, beside the receipt
it produced.

**3 orphans, 42 kept.** `2026-08-24-dev500-confirmatory`, `2026-09-01-a2t-factor-top1-104-v1` and
`2026-09-01-a2t-self-consistency-104-v1` moved to `docs/archive/launchers/2026-09-08/` with
`git mv`, byte for byte, sha256 and origin path recorded. Each origin receipt keeps its own sealed
artifacts; what left is a script none of those artifacts ever named.

The inventory corrected one number: the assessment says 14 launcher files are copies of one class;
measured on the tree it is **19 files across 11 directories** for `RuntimeEmbeddedBlendController`
alone — the ratchet baseline already listed all 19, and the "14" undercounts the six
`dev100-round0` attempt variants and the three `a2t-g1` blend attempts — plus `DirectAdapter` in 2
directories and `DirectDedupController` / `DirectObservabilityController` in 1 each.

**Nine of the eleven blend-controller directories are named by the exposure ledger**, so the
copy-paste tier is largely protected by its own evidence. That is the finding, not a shortfall. The
durable half is the gate: `engineering_base_check.py` runs `launcher_dirs` in ratchet mode, so a
directory not already in the baseline FAILS — **no NEW launcher directory can appear**, and the 42
are a fixed, shrinking set. The index names the next four candidates: the receipt directories whose
only content is a launcher (`a2t-g4-...-e16`, `-se16`, `a2t-g5-...-fixed16-v1`,
`a2t-g6-...-fixed16-v1`), archivable as soon as their pinning tests are re-pointed at the receipts
themselves.

`tests/unit/test_launcher_archive_index.py` pins the index: the archived bytes hash to the recorded
sha256, every origin receipt survives without its launcher directory, nothing archived has
reappeared under `docs/checks/`, the baseline's launcher set is a superset of the tree, and the
disposition table covers all 45.

---

## 5. Gates

* `ruff check` — clean on every file this wave touched. (The pre-existing findings elsewhere in
  `analysis/`, `reproduction/`, `scripts/` and other test modules are unchanged and untouched, as
  W1's note already records.)
* `python scripts/checks/engineering_base_check.py` — **PASS** on the lowered baseline.
* `python scripts/checks/tool_catalog_check.py` — **PASS** (26 tools, 1 extra pin, 11 modules clean
  of framework clients).
* Targeted suites green: `test_frozen_historical_registrations` (new, 11),
  `test_launcher_archive_index` (new, 5), `test_a2t_hard_validity_fold` (new, 7),
  `test_kb_alpha_blend_fold` (new, 10), `test_a2t_renderer_tools` (new, 64),
  `test_a2t_hard_validity`, `test_a2t_g3_plain_english_flight`, `test_rails_controllers` (56),
  `test_phase_review`, `test_phase_supply`, `test_phase_supply_cells`, `test_rails_phase_runner`,
  `test_kb_policy_v1`, `test_core_judges`, `test_judge_registry`, `test_policies`,
  `test_tool_catalog`, `test_tool_catalog_check`, `test_engineering_base_check`,
  `test_config_composition`, `test_evidence_derivation`.
* Two pre-existing failures are unchanged and are not this wave's:
  `test_build_a2t_g6_family_sweep` cannot import `scripts.build_a2t_g6_family_sweep` because
  `verl` installs a top-level regular `scripts` package into the shared venv; and the eight
  `a2t_*_preprocess` tests hard-require the literal main-checkout `PYTHONPATH`, so they cannot pass
  from any worktree.

Two existing assertions were updated because the facts they pinned changed on purpose:
`test_tool_catalog_check::test_the_real_catalog_passes` (8 → 26 tools) and
`test_rails_controllers::_EXPECTED_PROGRAM_SHAPES` (the seventh phase program).

---

## 6. What remains, and the order it should go in

| rule | left | the wave that clears it |
|---|---:|---|
| `probe_modules` | 36 | per carrier, and only after that carrier's cells are expressible as phase programs. The Audio2Tool probes are 25 of the 36 (the G3-G8 series alone is 10) and are the largest block; they are now reachable-in-principle, because their config ids resolve, their renderers are catalog tools, and `phase-hard-validity-repair-v1` shows the shape a G-series fold takes. |
| `controller_classes_outside_controllers` | 30 | **19** are launcher copies inside kept receipts and leave only when their receipts' citations are superseded; **10** are probe-module controllers and leave with their probes; **1** is `rails/runner.py::AgentController`, which is the Protocol itself and is not an offender in substance. |
| `adapter_subclasses_outside_adapters` | 8 | 6 are probe-module adapters (with their probes); 2 are launcher copies (with their launchers). |
| `launcher_dirs` | 42 | disposal-paced, four candidates named in the archive index; the gate already blocks growth. |

**The plan for the probe modules, stated so the next wave does not have to re-derive it.** Each
`rails/probes/a2t_g*.py` is one flight's sequencing plus its own renderers plus its own launcher
glue. The renderers are already catalog tools. The sequencing is a phase program plus, at most, a
`state_view_for_phase` and a `stop_policy` — which is exactly what the hard-validity fold cost
(one config fragment, one factory, one registered view, one judge). The launcher glue is the part
that genuinely disappears, because `FlightRuntime`'s E1/E6 config seams already express a
two-contact supplied cell as a config edit. Fold **one carrier per wave**, prove each against its
own sealed flight the way section 3.1 does, and take the ratchet down with it.

Three things this wave deliberately did **not** do:

* it did not flip any live cell onto a folded controller (section 3.2);
* it did not add a `state_view` config key — the seam is injected, and making it config-declared
  needs the gate's `NESTED_ID_KEYS` entry, which belongs with W4's config tables;
* it did not touch `reproduction/obs_loop.py`, `reproduction/ojw/*`, `core/driver/run.py`,
  `core/driver/speech_native.py` or `core/flight/runtime.py` — the files the parallel E21 port and
  the config-table wave own.
