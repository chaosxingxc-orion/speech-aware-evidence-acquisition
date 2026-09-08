# WAVE W4: the four config tables, and the null arm that makes an ablation one key (2026-09-08, v1)

Owner Decision 11-B, item **#6** of the openJiuwen implementation assessment's ordered change list
(`docs/readiness/2026-09-08-openjiuwen-implementation-assessment-v1.md` section 7). Built model-free,
at zero model contacts, on no GPU, in the `wt/ojw-w4` worktree, on master after merge wave 6 (W1's
`JUDGES` registry and `rails/phase_review.py`, W2's `rails/observe.py` and the relaxed observation
invariant, W3's `rails/tools.py` and `configs/toolkit/`).

## 1. The problem, restated in one sentence

The design note's admission gate (`docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md`
section 8) requires that a module's admission contrast be **module ON versus module OFF in the same
harness on the same roster — one config key, never a second code path**. The assessment measured how
far that was from true: of the seven harness modules, **one** was cleanly one key (the silence tail),
**one** was nearly so (the slot schema, whose OFF arm still changed the program id and the contact
count), and the other five needed a `policy` change, a `scorers` change or a policy subclass to turn
off. An OFF arm on a different code path is not a twin of its ON arm, so five of the seven modules
could not be admitted at all under the gate as written.

## 2. What this wave built

`src/speech_aware_evidence_acquisition/rails/config_tables.py` — one module, four tables, no second
validator and no second registry.

| table | scope | entries | null arm |
|---|---|---|---|
| `observe` | per phase | `tail_silence_seconds`, `unit_plan` (`{relpath, sha256}`), `relisten` (`judges` **or** a pinned `fixture`, plus `context_margin_seconds` / `max_relistens_per_sample` / `derivation_kind`, built through W2's own `ObserveConfig`) | absent, `null` or `{}` — today's fixed windows, byte for byte |
| `knowledge_views` | per phase | `material` (the `phase_material` entry verbatim; its `state_fill` IS the view), `supply` (the `phase_supply` entry verbatim; the retrieval provider) | absent, `null` or `{}` — falls back to the flat blocks |
| `judges` | per phase | W1's `phase_review` entry verbatim: `judges`, `on_flag`, `params` | absent, `null` or `{}` — no phase is reviewed |
| `toolkits` | per run | `task_type` (one row of W3's `configs/toolkit/task-toolkits-v1.json`), optional `roles` subset | absent, `null` or `{}` — no tool is armed |

Three properties, each enforced rather than described:

1. **Wrapping, not rewriting.** `knowledge_views` and `judges` carry the E1/E6/W1 entry objects
   unchanged and hand them to `load_phase_material_specs`, `load_phase_supply_specs` and
   `load_phase_review_specs`. Every refusal those loaders already make is the table's refusal too, and
   every id inside the tables keeps resolving in a `core.base` registry — including the any-depth
   `judges` rule `scripts/checks/engineering_base_check.py` already carries for exactly this reason
   ("so a future top-level `judges` list … without a second rule"). The check needed no change and
   still PASSes.
2. **One switch, one spelling.** A fragment declares the flat block **or** its wrapping table, never
   both; and a fragment carrying the `observe` table may not also carry the Earnings obs-loop's flat
   `obs_slice_tail_silence_seconds` / `obs_unit_plan` / `obs_unit_plan_sha256` knobs. Two spellings of
   one switch is how a cell ends up with two identities.
3. **The null arm IS the absence.** `core.config.NULL_ARM_TABLE_KEYS` + `drop_null_arms` drop a table
   key holding its null arm before hashing, and from the composed `values`. `"observe": null`,
   `"observe": {}` and no `observe` key are ONE cell identity. The rule is deliberately narrow — those
   four keys only — because an explicit `null` elsewhere in this study is a real declaration
   (`d1_media_supplement` is refused unless it and its sha256 are both present or both absent), and a
   blanket "drop every null" would erase that pairing.

**No committed fragment's hash moves.** A test scans every fragment under
`configs/{model,dataset,baseline,experiment}/` and proves not one of them carries a table key at all.

### Why `knowledge_views` and not `knowledge`

The change list's working name for the knowledge table is `knowledge`. That spelling is already taken
at the top level of a composed fragment: `configs/experiment/a2t-g3-plain-english-v1.json` declares a
`knowledge` object of card-build provenance, and `core.config.compose` refuses a top-level key defined
by two fragments. A `knowledge` table would therefore be permanently uncomposable with that cell —
fail-closed, at the worst possible moment. `knowledge_views` is the assessment's own spelling for the
same object (section 7: `knowledge_views: {slots: … | null}`).

## 3. The seven modules, each with its proof

`tests/unit/test_config_table_module_switches.py`. Every proof composes the ON arm and the OFF arm as
four real config fragments, loads BOTH through `rails.config_tables` (so the claim is about a
configuration that validates, not two JSON documents that happen to differ), and asserts the two
composed configs differ in exactly one key.

`switch_key(on, off)` is the machine form of "one config key": every leaf on which the two composed
configs differ must lie under ONE common dotted path that resolves in an arm. An object-valued entry
is therefore one switch (`observe.<phase>.unit_plan` moves both its `relpath` and its `sha256`), while
two sibling top-level keys are not — which is precisely the difference between the table entry and the
flat spelling it replaces.

| # | module | assessment verdict then | table entry now | switch |
|---|---|---|---|---|
| 1 | silence tail | **YES**, already one key | `observe` | `observe.<phase>.tail_silence_seconds` |
| 2 | speaker-turn unit plan | **NO** — two keys that must move together, and the ojw executor refuses the pair by name | `observe` | `observe.<phase>.unit_plan` (one nullable object) |
| 3 | legal-label projection | **NO** — the switch was the `scorers` list, i.e. a measurement change, not a system change | `judges` | `judges.<phase>.judges`, with `scorers` untouched |
| 4 | TRAIN slot schema per intent | **NEARLY** — one key, but OFF dropped to another program id and another contact count | `knowledge_views` | `knowledge_views.<phase>.material.state_fill` |
| 5 | substitution-only repair rule | **NO** — OFF meant switching `policy` from `obs-repair-loop` to `obs-agent-loop` | `judges` | `judges.<phase>.judges` |
| 6 | retrieval provider | **NO** — "on/off means swapping `phase-slots-given-intent-v1` ↔ `…-supplied-v1`" | `knowledge_views` | `knowledge_views.<phase>.supply`, same program id |
| 7 | window hook (per-window instruction + delivery) | **NO** — no config key at all | *(none yet)* | see §3.3 |

### 3.1 Which table the repair rule belongs in, and why

The change list left the choice open ("a `knowledge`/`observe`-side entry or a Solver-constraint
entry"). Owner **Decision 11-C** decides it: the Reviewer *scores and flags and never proposes a
revision*, and the design note names "`e21-entity-repair-substitutions-v1`'s refusal reasons" among
the frozen checks **behind the Reviewer**. The module therefore splits along the line the decision
already draws:

* its **criticism half** — the alignment rule that decides which proposed edits are legal and refuses
  the rest — is the registered judge `e21-substitution-alignment-flag-v1`, whose `JudgeVerdict`
  structurally cannot carry replacement text (`core.base.assert_criticism_only`). That is a `judges`
  entry.
* its **delivery half** — actually applying the accepted substitutions — stays a Solver-side
  constraint on the revise phase, where a rewrite belongs.

It is not an `observe` entry (it reads a response, never the audio) and not a `knowledge_views` entry
(it supplies the phase with nothing).

### 3.2 A correction the assessment owes itself: no `PhaseSpec` relaxation is needed

Section 7 asked for `PhaseSpec.knowledge: "optional"` so that supply on/off would stop requiring two
program ids. That reads the convention, not the code. `rails/controllers.py` already says
`"supplied"` means *the phase MAY have a `supply_for_phase`-sourced `SupplyPacket`*, and
`load_phase_supply_specs` returns an empty mapping for an absent block without complaint. So
`phase-slots-given-intent-supplied-v1` already carries **both** arms, and
`test_a_supplied_phase_with_no_supply_block_is_already_legal` pins it. `PHASE_KNOWLEDGE_KINDS` stays
the closed pair `{none, supplied}` and `rails/controllers.py` was not touched by this wave.

### 3.3 Why the window hook is still not a table entry

It has no config key to lift. It is a `_window_hook` override on a policy **subclass**
(`reproduction/obs_loop.py` returns `None`; `reproduction/repair_loop.py` overrides it), selected by
the `policy` value, and its switch moves three unrelated keys today — measured, not asserted, by
`test_the_window_hook_switch_moves_more_than_one_key_today` (`policy`,
`response_postprocessor`, `response_postprocessor_params.*`), which `switch_key` then refuses.

Its table form is not a new entry but the pair `judges: [...]` plus the `phase-draft-revise-v1`
program — which is the re-expression of the E21 obs path onto `FlightRuntime`, assessment changes
**#8/#9**, owned by the wave that holds `core/flight/runtime.py` and `reproduction/`. Widening the
tables here would half-wire it: the loop-back that lets one phase re-ask a flagged row is refused by
name in W1 (`on_flag: "loop"`) against two runner rails, and this wave inherits that refusal rather
than routing around it.

## 4. The admission receipt, and its gate

`docs/receipts/harness-admission.json` moves to schema **`saea-harness-admission-v2`**. Per entry it
now carries `switch: {table, key, on, off, proof}` — the one config key that switches the module —
and the receipt carries a `default_plans` list. **No verdict, number, status, evidence pin or
provisional obligation was changed**: v2 records, for a module already decided, where its one key
lives.

The single entry's switch is `judges.<phase>.judges` with `e21-substitution-alignment-flag-v1`, and a
`what_flew` field says plainly that **the sealed KC-E1f arm did not fly through that key** — it flew
the `obs-repair-loop` policy with a `response_postprocessor` whose OFF arm was a different policy id,
which is the defect this wave removes. The receipt records the module's form from now on; its
evidence stays the sealed bytes.

`default_plans` is **empty**, and that is the program's state rather than an omission. The one decided
module is ADMITTED but provisional with its replication **UNMET**, and its own verdict note fixed the
consequence before the verdict was known: *"until then NO candidate freeze, NO citation of this as an
admitted effect and NO entry into the default plan."*

`scripts/checks/harness_admission_check.py` (model-free; no model, GPU, network or
`SPEECHRL_DATA_DIR` contact) turns three of section 8's bullets into enforced rules:

1. every entry's `switch.key` resolves in one of the four tables (it must start with its table and
   name one of that table's entry keys), its `switch.off` must be that table's null arm, its
   `switch.on` must arm something, and its `switch.proof` must be a test node id whose file exists and
   whose test that file defines;
2. every ADMITTED or NEUTRAL entry with no blocking obligation appears in at least one default plan
   **for its own carrier** — an admission that reaches no plan is a receipt nobody acted on;
3. no HARMFUL entry, and no entry whose `provisional.state` is `UNMET`, is armed in any default plan.

A default plan is **declared in the receipt, never inferred**: an experimental ON arm is a config
fragment carrying a table too, and reading those as default plans would admit every module the moment
it was first tried.

Live result: `harness admission check: PASS (1 module(s), 1 barred from every default plan, 0 default
plan(s))`.

## 5. Gates

- `ruff` — clean on every file this wave touched.
- `scripts/checks/engineering_base_check.py` — **PASS**, unchanged. The tables needed no new rule:
  the `judges` any-depth rule W1 added already covers the `judges` table, and the nested
  `provider` / `rank_policy` / `fuse_policy` / `response_format_id` rules already cover the wrapped
  `knowledge_views` entries.
- `scripts/checks/tool_catalog_check.py` — **PASS**, unchanged.
- `scripts/checks/harness_admission_check.py` — **PASS** (new).
- Tests — 110 new, all green: `test_config_tables.py` 68, `test_config_table_module_switches.py` 13,
  `test_harness_admission_check.py` 29 (a negative control per rule). The composition,
  phase-material / phase-supply / phase-review, observe seam and tool-catalog / toolkit / wrapper
  suites are still green: 264 of them before this wave, 415 together with the new ones.

## 6. What this wave did not do

- **No table is consumed by a run.** The module parses, validates and hashes; turning a validated
  `ConfigTables` into an `ObserveStep`, a `review_for_phase` or an armed toolkit is the phase-program
  dispatch in `core/flight/runtime.py`, which belongs to a sibling wave. W2's four construction notes
  for `ObserveStep` still stand and are unconsumed here.
- **No config fragment was written with a table.** Committing an arm is a preregistration act, not a
  config-plumbing act; the tables' first real fragments belong to the cell that flies them.
- **No module was admitted, re-decided or promoted.** `default_plans` stays empty, the KC-E1f entry's
  replication obligation stays UNMET, and this note claims no gain of any kind.
- **`rails/controllers.py`, `core/flight/runtime.py` and `reproduction/` were not touched**, so the
  `PhaseSpec.knowledge` set, the runner and the E21 obs path are exactly as merge wave 6 left them.
