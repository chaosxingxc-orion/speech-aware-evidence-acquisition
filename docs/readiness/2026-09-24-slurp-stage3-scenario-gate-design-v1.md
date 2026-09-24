# Iteration 3: the scenario gate on the stage3-deltas context supply

Design note for the model-free mechanism landed on branch `fable/gate`. It is a WIRING note:
nothing here is flown, registered, pre-registered or claimed. No exposure row is opened, no
roster is chosen, no decision id is minted, and no effectiveness statement is made or
possible from what is written below.

## 1. Why a gate, and not a better delta

`docs/results/2026-09-24-slurp-general-scenario-diagnostic.md` and
`docs/results/2026-09-24-slurp-stage3-delta-cell-r02-verdict.md` establish the shape of the
CELL-2 result on TRAIN Fold A:

- where the store has reach, the CONTENT gain is positive against the derangement twin
  (arm minus twin: news +7.4, alarm +4.2, qa +4.2, weather +4.1 pp SLU);
- on `general` -- and on alarm, music, social, iot, play and news as strata -- the arm loses,
  and **the derangement twin loses as much** (intent -11.67 pp twin versus -6.67 CELL-2 and
  -10.00 CELL-1 on the 60 `general` rows). A loss the twin reproduces is a FORM cost of
  CARRYING a supply, not the content of any delta;
- no delta content exists for `general` at all: 0 of 200 v2 values declare a `general` target.

So the iteration-3 lever is not a better statement and not a better ranking. It is
APPLICATION: do not carry the supply into a row where the store cannot pay for its own form
cost. The whole recoverable amount on `general` is small (0.56 pp intent and 0.24 pp SLU at
Fold A grain), which is exactly why the mechanism must cost nothing where it does not fire.

## 2. Semantics

A candidate-bound route (`provider: stage3-delta-candidate-bound-v1`) may declare ONE
optional key:

```json
"scenario_gate": {
  "policy": "majority-candidate-scenario-not-in-v1",
  "scenarios": ["general", "alarm", "music", "social", "iot", "play", "news"]
}
```

- **What it reads.** The SAME projected Perception candidate list the route already reads --
  after the bounded first-occurrence projection (`_delta_candidate_read`), before any store
  lookup -- and nothing else. Only the sealed Perception state of the same episode. No gold,
  no reference transcript, no scorer, no future turn, no other row.
- **Scenario of an intent.** The part before the first `_`, the SLURP catalog's own
  composition rule (`general_quirky -> general`, `iot_hue_lightoff -> iot`). Implemented once,
  as `rails.stage3_delta_supply.scenario_of_intent`; there was no existing helper on the
  supply path (the four analysis scripts that spell the same split read sealed outputs).
- **Majority.** Most-frequent, not strictly-more-than-half. Ties are broken by the
  first-listed candidate.
- **Closed** exactly when the candidate list is non-empty AND the majority scenario is one the
  gate names. A closed gate returns `None` -- no supply step at all for that node on that row,
  the same disposition the existing "introduces nothing new" branch takes, so the wave seals as
  an ordinary `organize` step rather than an empty acquisition.
- **Open** changes nothing. Control falls through to the identical selection; the supply is
  byte-identical to the ungated route's (same selected ids, same `RankResult` hash, same
  `FusionDecision` hash, same `action_target_ref`). Proved by
  `tests/unit/test_stage3_scenario_gate.py::test_an_open_gate_is_byte_identical_to_the_ungated_route`.
- **Perception is not gated.** The unconditional route (`stage3-delta-unconditional-v1`) is the
  node that PRODUCES the candidate list, so at the moment it is served there is nothing to gate
  on. Its validator's key set is an EQUALITY, so a `scenario_gate` there is refused by
  construction. A cell that wants the Perception deltas withheld omits the route, which is what
  the derived fragment does.

### Receipts

| receipt | key | contents |
| --- | --- | --- |
| skip | `route.receipt["delta_supply"]` | the existing per-row skip audit, with `reason = "scenario-gate-closed"` and a new `majority_scenario` label. The label is declared LAST and omitted when absent, so every ungated cell's skip receipt is byte-identical to its pre-iteration-3 self. |
| decision | `route.receipt["delta_scenario_gate"]` | EVERY decision, open and closed: node, phase, sample id, store id, policy id, gated scenarios, majority scenario, candidate count, `closed`. Published only when some route declares a gate. |

Both are labels, identities and counts only. No utterance, transcript, gold label, candidate
text or statement is ever written. Open decisions are recorded because "the gate closed here"
is only readable against "and was open there": a receipt carrying closures alone cannot say
what share of rows a gate actually withheld.

## 3. Registration and gates

The policy id resolves in a `core.base` registry like every other component id a config
declares. A new registry `core.base.STAGE3_SUPPLY_GATE_POLICIES` holds it, populated from
`rails/knowledge_provider.py` -- one of the check's canonical registration files, and the file
the delta provider ids already register from. `rails.knowledge_provider.resolve_scenario_gate`
is the seam, shaped exactly like `resolve_provider`.

`scripts/checks/engineering_base_check.py` resolves `scenario_gate.policy` by PATH, not by bare
key name, for the reason its own `decoding_params.max_tokens.policy` rule is matched by path:
the key inside the gate object is spelled `policy`, which at top level already means an arm
program's `POLICIES`/`AGENT_CONTROLLERS` id. The container key `scenario_gate` is unambiguous
and is found at any depth, because the gate lives under
`knowledge_stores.<store>.context_supply.<node>`, whose middle segments are names.

Negative control run against the live tree: a fragment naming an unregistered policy is
reported as
`...::knowledge_stores.stage3-deltas.context_supply.solver.scenario_gate.policy=not-registered-v9`.

Gates run from the worktree, all PASS: `engineering_base_check`, `harness_admission_check`,
`results_ledger_check`, `tool_catalog_check`, `finite_completion_policy_check`,
`stage3_algorithm_label_check`, `derived_media_confinement_check --output <scratch>`.

## 4. The offline dry run (zero contacts)

`scripts/flights/batch/cell3_gate_dry_run.py` is `cell2_dry_run.py`'s recipe with the baseline
fragment swapped for the gated one; it imports that driver's traced candidate ids and canned
answers rather than restating them. It walks the CELL-2 cell truncated to four rows -- the
CELL-2 smoke population IS "the first four rows of TRAIN Fold A in the roster's own order", and
the driver asserts the walked roster equals the four rows the traced ids belong to. Zero model,
tool, network, GPU, gate, transport, client, attempt and serving-session contacts.

| row | candidate scenarios | majority | solver | reviewer | planner | delta items S / R / P |
| --- | --- | --- | --- | --- | --- | --- |
| `slurp:train:000007:audio--1504197557` | audio, audio, play | `audio` | open | open | open | 0 / 1 / 0 |
| `slurp:train:000009:audio-1497557594-headset` | iot, iot, iot | `iot` | CLOSED | CLOSED | CLOSED | 0 / 0 / 0 |
| `slurp:train:000015:audio-1488524781` | audio, play, audio | `audio` | open | open | open | 0 / 1 / 0 |
| `slurp:train:000023:audio-1490956038` | iot, iot, iot | `iot` | CLOSED | CLOSED | CLOSED | 0 / 0 / 0 |

Two tie walks on row 1, the same two candidates in the two orders:

| walk | candidates | majority | gates |
| --- | --- | --- | --- |
| tie | `audio_volume_up`, `iot_hue_lighton` | `audio` | all open (reviewer supplies 1) |
| tie reversed | `iot_hue_lighton`, `audio_volume_up` | `iot` | all CLOSED |

The open rows reproduce the CELL-2 package's own recorded per-node counts for those rows
(`0 / 1 / 0` on rows 1 and 3, `0 / 0 / 0` on rows 2 and 4), which is the byte-identity claim at
cell grain: the gate changed the closed rows and left the open ones exactly where they were.
Every row walks the whole graph and delivers from the Solver's sealed draft. `ok: true`.

## 5. What this does NOT decide

- **TODO-ROSTER.** No roster is chosen. The candidate venue is DEV-2000-ADDED against the
  sealed `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1`, but the derived fragment inherits
  CELL-2's TRAIN Fold A population keys (the intent-boundary and exemplar query vectors, the
  speech-feature identity ids, the promotion receipt) unchanged. Re-pointing them is the
  coordinator's registration step, not this branch's.
- No experiment or campaign fragment, no twin, no readiness package, no exposure row, no
  decision requirement and no pre-registration is created here. Owner decision 110 is PENDING.
- The seven scenarios are the seven the general-scenario diagnostic named. Whether that set is
  the right one -- and whether a gate helps at all -- is a flight, not a design note.

## 6. Semantic questions decided while implementing

1. **Tie-break when the first-listed candidate's scenario is not tied.** "Ties broken by the
   first-listed candidate's scenario" is exact when that scenario is one of the tied maxima and
   undefined when it is not (`a_x, b_y, b_z, c_p, c_q`). Decided: of the scenarios tied at the
   maximum count, the one whose FIRST OCCURRENCE in the candidate list is earliest. This
   reduces to the stated rule in the case the rule describes, and is deterministic otherwise.
2. **Which registry the policy id resolves in.** The provider ids resolve in
   `core.base.KNOWLEDGE_PROVIDERS`, but a gate is not a provider -- one answers "which values",
   the other "on which rows". Decided: a new `core.base.STAGE3_SUPPLY_GATE_POLICIES`, registered
   from the same canonical file beside the provider ids, plus a path rule in
   `engineering_base_check.py` so the nested `policy` key is actually resolved (a nested `policy`
   matched no existing rule, so registering alone would not have made the check read it).
3. **Where the gate is parsed.** At config load, in the route validator, alongside
   `_delta_candidate_read` -- not per row. A gate naming a non-catalog scenario is a config
   defect and must be refused before a contact is spent.
4. **What "catalog scenario" means.** Derived from the task adapter's authoritative legal
   candidate inventory the route already binds against, never hard-coded. That is what refuses
   both a misspelling (`generl`) and the category error (`qa_factoid`, an intent) with one rule.
5. **Recording OPEN decisions too.** Not required by the brief; added because the closed-only
   receipt cannot report the denominator. It is published only when a gate is declared, so no
   existing cell's receipt bytes move.
6. **Which cell the dry run composes.** The CELL-2 SMOKE baseline carries its own
   `-smoke-v1` speech-feature identity ids, so pairing it with a fragment derived from the
   non-smoke CELL-2 baseline would have mixed two identity families. Decided: compose the CELL-2
   cell itself with `sample_limit=4`, which is the same four rows by that experiment's own
   population definition, and assert the roster equality in the driver.
7. **An explicit `"scenario_gate": null`.** Refused rather than treated as absent: a spec that
   carries the key is asking for a gate.
