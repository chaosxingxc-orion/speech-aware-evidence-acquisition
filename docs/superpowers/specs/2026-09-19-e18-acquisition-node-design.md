# E18: the Acquisition node -- `acquire(action -> typed evidence)`

Author: Claude Opus 5, engineering. Date: 2026-09-19. Tree: `fable/e18` from `6851acdc`.
Status: **BUILT. No cell is registered, nothing is admitted, no number is claimed.**

Authority: **owner decisions 43 and 44 of 2026-09-19**
(`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, section "Owner decisions
42-44"): every carrier instantiates all six nodes of the agent base, and Acquisition is a component
of **everyday inference** -- SUPPLY governs the *timing* of evidence, and today the Planner's
`ACQUIRE` action reaches no node at all (E15 turns it into a retained row) -- so it is built now.

Design frame: `docs/superpowers/specs/2026-09-19-agent-base-lock-v2-draft.md` (section 3.6 the node,
section 4 edges E17/E18, section 5.6 primitive `AC-1`, the only primitive MISSING on every carrier).
Context-policy frame: `docs/superpowers/specs/2026-09-17-node-context-policy-design.md` sections 3-5,
9, 17 (E15) and 18 (E16).

Zero contacts: no model, tool, scorer, tokenizer, encoder, server or network was reached while this
item was built; nothing under `SPEECHRL_DATA_DIR` was read or written. Every proof runs the real
parser, the real OpenJiuwen role graph and the real `rails.runner` over the shared fake transport.

---

## 1. The primitive

Stated once, carrier-neutrally, over the task abstraction `T = (U, C, K, A, S)`:

```
acquire(acquire_action, trajectory state) -> typed evidence bound into the successor state
```

One acquisition **visit** reads the episode's own state, executes exactly one registered
`rails.acquisition.AcquisitionPolicy`, and returns exactly one `rails.acquisition.AcquiredEvidence`
record. The record shape is the same for every kind, so a consumer, a receipt and a later cell all
read one object:

| Field | Meaning |
| --- | --- |
| `kind`, `policy_id` | what was run |
| `provenance_ids` | the ids of what was brought in (value ids, a re-observation contact id, registry row ids) |
| `content` | the ONE rendered typed block the next Solver revision reads |
| `contacts_used`, `cost`, `cost_unit` | what the visit spent |
| `inputs_sha256` | the digest of the QUESTION: policy, kind, row, visit, route, state restriction, dedupe set, scope, budget |
| `evidence_sha256`, `evidence_chars` | the digest and size of the ANSWER |

`inputs_sha256` is callback-free by construction (a callback is a live object and would not be
re-derivable), and the receipt never carries the acquired **text**: on a speech carrier acquired
content can quote the row's own material, and a receipt is not a place for it. The two digests are
what bind it.

**Signature, side effects, receipts, cost.** Inputs: the Planner's acquire action, the trajectory's
state and the bound acquisition callbacks. Output: one `AcquiredEvidence`. Side effect: exactly one
`AgentStateArtifact` of kind `phase:<acquisition phase>` enters the trajectory. Receipts: one
`role_visits` entry of stage `acquisition` plus one row of the episode receipt's `acquisition` block.
Cost unit: per kind (below).

## 2. The three kinds

Each is a registered policy in `core.base.ACQUISITION_POLICIES`, populated from `rails/acquisition.py`
-- the one canonical registration site, the same discipline `COMMIT_POLICIES` and
`DELIVERY_NORMALISERS` follow.

| Kind | Policy id | Contacts | Cost unit | Status |
| --- | --- | --- | --- | --- |
| `knowledge-requery` | `saea-acquire-knowledge-requery-v1` | **0** | `supply-calls` | **BUILT and armed end to end on SLURP** |
| `speech-reobserve` | `saea-acquire-speech-reobserve-v1` | **1** | `model-contacts` | **BUILT** as the primitive; SLURP instance wired through the existing Perception role |
| `tool-acquire` | `saea-acquire-tool-registry-v1` | 0 | `registry-lookups` | **STUB, fails closed** (Audio2Tool first instance) |

### (a) `knowledge-requery` -- model-free

Re-runs the phase supply **for the Solver** against the row's already sealed SPEECH key, restricted
by STATE, and returns typed content the Solver has not yet been supplied.

* **The state restriction** is `rails.acquisition.derive_state_filters`: lowercase word tokens of the
  latest Reviewer finding and the Planner's own action token, deduplicated in first-occurrence order,
  bounded by `MAX_STATE_FILTERS` (8). Zero contacts, no parser that can fail a row.
* **Why this is legal.** The tokens RESTRICT a speech-keyed ranking; they are never themselves a
  retrieval key. The owner ruling of 2026-09-06 -- *retrieval queries are speech or speech plus
  state, never text alone* -- is exactly what forbids the other reading, and the callback the
  restriction is handed to is the one that owns the row's sealed speech vector.
* **Dedupe** is the policy's own job, not the callback's: the acquisition drops any item whose
  `evidence_id` is already in the trajectory's `retrieved_value_ids`, so a callback that forgets the
  exclusion cannot re-supply what the Solver already holds.
* **The seam.** `NativeEpisodeRunBinding.acquisition_requery`, flight-owned exactly as
  `material_for_phase`, `supply_for_phase`, `review_for_phase` and `tools_for_phase` are. The runner
  never reaches for a store of its own, and an episode that arms this kind without binding the
  callback is refused by name.

### (b) `speech-reobserve` -- one Perception contact

Re-runs Perception on a re-scoped observation unit and returns the new candidate hypotheses as typed
content. **E18 introduces no prompt text anywhere**: the re-observation seat is an ordinary
`NativeRoleNode` of `role_kind` `perception`, placed at the acquisition phase, whose instruction is
that phase's own `phase_material` -- the never-varied Perception template v3 plus the config's
`fill_params` (the candidate cap, or a declared re-listen variant). Decision 40's template freeze is
untouched.

Carrier instantiations of the re-scope, stated for the record and not armed here: SLURP -- the same
recording with a different candidate cap; contextual ASR -- the neighbouring window; Audio2Tool --
the same request with the domain-grouped registry.

The contact is made through the same `metered` path, the same slot, the same budget/FIT gate, the
same trace and cost accounting as every other contact of the row. Its sealed state is a **view** of
the re-observation -- the typed block as content, the model's own bytes as
`source_response_sha256` -- through the same `seal_phase_response_state` seam a grouped Solver visit
already uses.

### (c) `tool-acquire` -- registered, armed nowhere

A registry lookup by domain group; the Audio2Tool first instance. It is registered on every carrier
and armed on none, because only Audio2Tool has a registry (`core.base.TOOL_CATALOG` plus the
`rails/a2t_*` grounds) and SLURP has none. **It fails closed with a named refusal rather than
returning an empty acquisition**: an acquisition that found nothing and an acquisition that could
never have found anything must not look alike. Its carrier implementation lands with that carrier's
own cell, not with E18.

## 3. The boundary

The record's `content` is rendered through the committed, hash-pinned template
`configs/probes/ncp_acquired_evidence_solver_v1.txt` (renderer key `acquired-evidence`), declared in
`rails/node_context_policy.py`:

| Constant | Value |
| --- | --- |
| `ACQUIRED_EVIDENCE_BOUNDARY` | `("solver", "acquired-evidence")` |
| `ACQUIRED_EVIDENCE_BOUNDARY_ID` | `B-ACQ-SOL` |
| `ACQUIRED_EVIDENCE_TEMPLATE` | `probes/ncp_acquired_evidence_solver_v1.txt` |
| `ACQUIRED_EVIDENCE_RENDERER` | `acquired-evidence` |
| new semantic class | `acquired-evidence`, added to `SEMANTIC_CLASSES` |
| new provenance | `PROVENANCE_ACQUIRED` (`"acquired-evidence"`) |

Two deliberate choices.

* **`acquired-evidence` is a semantic class of its own**, not a second spelling of supplied evidence:
  the consumer must be able to tell pre-contact SUPPLY (chosen before the row's first contact, by the
  supply policy) from evidence acquired ON DEMAND mid-episode, by a node, after a draft was reviewed.
  Those are different SUPPLY decisions and a cell that moves one must stay distinguishable from a
  cell that moves the other.
* **The boundary is declared beside `SLURP_BOUNDARY_IDS`, not inside it.** Every pair in that mapping
  gets a resolved entry in *every* policy object `build_slurp_node_context_policy` composes; an
  unarmed episode has no acquisition node at all, so a thirteenth always-resolved entry would put a
  boundary into every policy that no state can ever reach. The Acquisition node renders its own block
  instead -- exactly as the E12 audit and the E14 hints render theirs -- and
  `SlurpNodeContextPolicy.compile` classifies the resulting state as `acquired-evidence` for any
  consumer whose `phase_ids` carries the OPTIONAL `"acquisition"` entry. `ROLE_KINDS` is unchanged,
  because it is the set of CONSUMER kinds and the Acquisition node is a producer only.

## 4. Configuration

Two keys, present together or absent together; the loader refuses every half-armed shape.

```jsonc
"native_episode": {
  "roles": {
    "perception": {...}, "solver": {...}, "reviewer": {...}, "planner": {...},
    "acquisition": {                       // E18: the OPTIONAL fifth role
      "phase_id": "acquisition",
      "max_iterations": 0,                 // == the policy's contacts per acquisition
      "kinds": ["knowledge-requery"]       // what this node may execute
    }
  },
  "acquisition": {                         // E18: the episode-class switch key
    "policy": "saea-acquire-knowledge-requery-v1",
    "budget": {"max_acquisitions_per_row": 1, "contact_budget": 0}
  }
}
```

Refusals, all before any contact: the two keys declared apart; a kind not in
`ACQUISITION_KINDS`; an unregistered policy; a policy whose kind the role does not admit;
`max_iterations` that is not the policy's own `contacts_per_acquisition`; a `contact_budget` that is
not `max_acquisitions_per_row x max_iterations`; a `max_acquisitions_per_row` outside
`1 .. max_revisions`; `phase_tools` on the acquisition seat; and `candidate_refresh` composed with
acquisition (two back-edges into one revision allowance, walked by two different receipt validators
-- a question for the cell that needs it, not a default).

`native_episode.acquisition` is admitted to the closed `episode` switch-key allowlist
(`rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS`) as its **ninth** member and the first that adds a
NODE rather than a mode of an existing one. Its OFF arm is the key's absence.

## 5. The contact ceiling

Documented in `load_native_episode_config`'s own docstring and checked exactly:

```
ceiling = perception.max_iterations
        + (max_revisions + 1) * per_revision
        + max_candidate_refreshes * perception.max_iterations
        + max_acquisitions_per_row * acquisition.max_iterations        <- E18

per_revision = solver.max_iterations * solver.samples
             + reviewer.max_iterations
             + planner.max_iterations
             + cleaning contacts per revision
```

Only kind (b) costs contacts, so the new term is `0` for `knowledge-requery` and `tool-acquire`, and
`0` for every config that declares no acquisition at all -- which reduces the formula to exactly its
pre-E18 self. `program.max_contacts` must equal it; `native_contact_fit` and the fit gate read
`config.max_contacts`, so both see the new maximum without any further change.

Worked examples from the proofs: `max_revisions 1` + kind (a) -> ceiling **7** (1 + 2x3 + 0);
`max_revisions 1` + kind (b) with `max_acquisitions_per_row 1` -> ceiling **8**.

## 6. Routing, budget and refusal

* The graph builds an acquisition branch for `revision < max_acquisitions`; `ACQUIRE` at revision
  `max_revisions` already takes the existing terminal path (`_TerminalDelivery` under
  `deliver-latest-solver`, else `_Exhausted`).
* Past the declared allowance the branch is `_Exhausted("episode acquisition budget is exhausted")`
  -- defence in depth, the same shape E15 left for the unwired case. It is unreachable in practice:
  the runner stops advertising `ACQUIRE` in `available_planner_actions` the moment the allowance is
  spent, and under `json-action-v1` the Planner's own response schema cannot spell it.
* On an **unarmed** episode nothing changes: `NativeEpisodeWorkflow._planner_actions` holds no
  `ACQUIRE`, `_ApplyRole` classifies the token as an illegal Planner output and the E8c path retains
  the row. That is E15, untouched, and it is proved again here.

## 7. Receipts

Per visit, a `role_visits` entry of stage `acquisition` carrying `acquisition_receipt`
(`saea-native-acquisition-v1`: kind, policy id, provenance ids, item count, contacts used, cost,
cost unit, `inputs_sha256`, `evidence_sha256`, `evidence_chars`, visit index, revision count, the
Planner route index and action that triggered it, and the state filters). A contact-spending kind
additionally carries `execution_receipt`, normalised through the same `_execution_receipt` every role
visit's receipt takes; a zero-contact kind carrying one is refused.

Per row, the episode receipt gains an `acquisition` block naming the node's phase, its registered
policy and kind, the kinds the node may execute, the budget, the ordered per-visit records and the
contacts used. `planner_action_illegal` no longer counts `ACQUIRE` on an armed episode, because the
token now names a registered action there; on an unarmed episode it counts exactly as it did.

`validate_native_episode_finite_path` gained optional `acquire_action` / `max_acquisitions`
parameters and consumes one `acquisition` visit per `ACQUIRE` continuation; omitted, the walker is
byte-identically its pre-E18 self.

## 8. What is proved, with the fake model

`tests/unit/test_e18_acquisition_node.py`, 25 tests, all through the real parser, the real role
graph, the real runner and the shared fake transport:

* the loader: the null arm, both armed forms, the checked ceiling and nine fail-closed refusals;
* the three registered kinds and their declared cost; the boundary constants; the block's rendering
  including its closed empty phrase; the tool kind's named refusal; the state restriction's
  boundedness and determinism;
* **E15 unchanged**: an `ACQUIRE` on an unarmed episode is still the retained row, with the same
  `planner_action_illegal` mark;
* **unarmed request bytes pinned**: the four rendered requests of a four-contact unarmed row are
  pinned by sha256, the same falsifier shape E17 uses;
* **armed kind (a)**: the Planner routes `ACQUIRE`, the node runs, the visit and the receipt block
  are sealed, the row still costs 7 contacts, and the Solver's revision carries the typed block whose
  sha256 is the one the receipt bound;
* **one factor**: two `ACQUIRE` rows whose acquisitions differ only in what they brought back render
  second-Solver requests that are byte-identical outside that one agent state's content;
* **kind (b)**: exactly one extra contact, at the acquisition seat, the eighth of an eight-contact
  row, bound to its own traced contact, and the state the Solver reads is the typed block rather than
  the raw re-observation;
* **budget refusal**: an `ACQUIRE` past the declared allowance reaches the graph's own `_Exhausted`.

## 9. What is NOT claimed

No cell is registered. No number is produced, compared or admitted. No config fragment under
`configs/` is armed with this key, no harness-admission entry is written, no `contracts.ExecutionPlan`
is composed, and nothing here is evidence that acquisition helps any carrier.

The **first admission cell** will be a one-factor SLURP cell, **B9a: acquisition on demand, kind
(a)**, on the best not-HARMFUL base, with its own preregistration, its own request-bytes falsifier
(the OFF arm is the key's absence) and its own margins from that configuration's own
request-identical replicate (owner decision 38). It is not registered by E18 and is not authorised
here.

Kind (b) stays PARTIAL until a carrier declares its re-scope and flies it; kind (c) stays a STUB
until Audio2Tool's registry is bound. Both are named as such in the base-lock v2 draft's node and
primitive tables.
