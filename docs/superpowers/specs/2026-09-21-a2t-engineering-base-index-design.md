# Audio2Tool engineering base: the registry index on the shared native-episode harness (design)

Author: the coordinator (Fable 5.1). Date: 2026-09-21. Status: DESIGN, owner decisions 65-71 taken 2026-09-21
(section 7). Owner mandate: decisions 36, 39, 43, 48 (the Audio2Tool instance of the index is "the
domain-grouped tool registry in the constant prefix at L0/L1 with a per-row pointer block"), 50, 59 and
63 (D6: "the Audio2Tool engineering base is built in CPU time during the SLURP flights, never on the
flight tree"). Zero model contacts are authorised by this document.

## 1. What exists today (inventory of 2026-09-21, read-only)

- Carrier plumbing is complete and carrier-neutral where it matters: descriptor
  `data/carriers.py:433-460` (`task_kind speech-tool-use`, `official_scorer_id a2t-toolcall`,
  `knowledge_layer tool-registry`, `stratum_key tier`); adapter `rails/adapters/audio2tool.py` and
  runtime adapter `rails/adapters/audio2tool_runtime.py`; scorers `a2t-toolcall`, `a2t-toolcall-v2`,
  `a2t-toolcall-official` (the pinned release's own metric code) through the neutral
  `core.scoring_batch`.
- The native episode already runs on Audio2Tool. The newest baselines
  (`configs/baseline/a2t-native-role-*.json`) declare the four-role `native_episode` with both
  failure-mode keys armed (E13 `deliver-latest-or-abstain`, E22 `continue-without-answer`), tool
  authority on Reviewer (and on Planner in the scope-tools form), two released named stores
  (`tool-activation`, `parameter-meaning` with a Solver `candidate_supply`), and `phase_material`
  per role. No A2T config declares `observe`, `judges`, `toolkits`, `tool_schema_rendering`,
  `knowledge_index`, `context_policy`, `reviewer_audit` or `solver_hints`.
- Sealed numbers (union-4000 roster, split identity `c0c1e7cc...`): direct
  `SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1` primary-call exact 18.500 / tool accuracy 62.025;
  native dual-store `SAEA-A2T-NATIVE-ROLE-DUAL-STORE-UNION4000-RECOVERY-V1` exact 22.550
  (+4.050 [2.963, 5.165]) but tool accuracy 58.425 (-3.600): NOT ADOPTED (tool guard). The
  scope-tools successors are registered and unflown (np3 refused by prompt volume; np2 is the fix).
  ORG-1 (the domain-grouped registry as a prompt fill) read HARMFUL, -3.23 pp [-4.15, -2.33], by
  re-ordering alone. KC-A1 contrast notes NULL. The carrier has NO measured own null, no
  harness-admission entry and no default plan.
- The registry is a prompt fill, not a store: `audio2tool-registry-compact` (official protocol) and
  `audio2tool-registry-grouped` (ORG-1) in `data/audio2tool_tools.py`; no `knowledge/audio2tool/semantic/`
  namespace, no `*-release-pins-*.json`.
- The index rail `rails/knowledge_index.py` is a SLURP module by construction: carrier literal
  (`:123`), pin namespace (`:249`), view ids (`:100-102`), entry kinds and sigils (`:129-141`), card
  section tables (`:155-176`), id grammar (`:310-336`), the three SLURP evidence prefixes
  (`:2337-2341`), the Perception-state reader `candidates[].intent_id` (`:2389-2431`) and the one
  ordering `taxonomy-frequency-v1` (`:1293-1336`). The loader's refusal 8 already passes for A2T
  (`knowledge_layer` non-null); the loader's carrier equality test (`native_episode_config.py:1356`)
  and refusal 7 (constant prefix requires no tool authority or `tool_schema_rendering constant`)
  are the two gates an A2T index cell hits today.

## 2. Goal and non-goals

Goal: one shared harness on which the SLURP and Audio2Tool carriers each run the same six-node
native episode with a carrier-specific, released, pinned knowledge INDEX rendered once per slot in the
constant prefix, a per-row pointer block and budgeted expansions, read on the official scorer at the
carrier's own-null margins with a derangement twin (decision 50) and the index-consumption read
(decision 64).

Non-goals: no new controller, adapter subclass, probe module or launcher (engineering base rules);
no ASR or transcript state; no core swap; no claim on the union-4000 before the form is admitted on
the paired 400-row subset; no Earnings work (decision 59).

## 3. The A2T index (the object)

Source of truth: `tools_registry.csv` (152 rows: name, signature, description, parameters,
constraints, domain) plus the two released stores (`tool-activation-scope-v1` for activation
boundaries, `parameter-meaning-v1` for argument meaning).

| level | content | rendered where |
| --- | --- | --- |
| L0 | one line per DOMAIN (3) and one line per TOOL (152): `T<domain>.<tool_name>(signature)` | constant prefix, always |
| L1 | per tool: `Activation boundary` (from tool-activation-scope-v1) and `Admissible arguments` (argument names, types, enumerations from the registry constraints) | constant prefix at the default granularity `tool L1 Activation boundary`; arguments as pointer-expanded L2 by default (owner decision 66) |
| L2 | per tool: full description, constraints, parameter meaning (parameter-meaning-v1 card); per confusable pair (`edge`): the contrast line | per-row expansion under the budget |
| pointer block | per row: the Perception state's `actions[].candidate_tools` mapped to tool ids (budget `tool 8`), their domains (`domain 3`), confusable edges among the pointed tools (`edge 4`) | per contact, after the constant index |

Entry kinds for the carrier profile: `domain`, `tool`, `edge`, `exemplar` (construction-pool
examples from `a2t-construction-800-v1`, keyed by speech vectors exactly as SLURP's
train-exemplars; OFF in the first cell). `parameter` is a SECTION of the tool card, not a kind
(decision 66, recommended): a parameter is never selected on its own, it is read with its tool.
Edges (v1) come from the registry STRUCTURE alone, gold-free: two tools of the same domain whose
signatures share argument names or whose descriptions share content tokens above a fixed threshold
(the builder's rule is pinned in the release receipt). The ORG-1 same-domain twin-miss table is an
EVALUATION-roster statistic (union-4000 gold) and must not author knowledge (the construction
exclusion of 2026-09-13); data-derived edges, if ever, come from the construction-800 roster only.

Ordering: `domain-alphabetical-v1` (ORG-1's own form: sorted domain, sorted tool name) registered in
`core.base` beside `taxonomy-frequency-v1`. Because ORG-1 lost 3.23 pp by re-ordering alone, the
derangement twin (seeded Sattolo over the L1 lines and L2 cards within each kind, header keeping the
source view id; item E24's builder flag) is mandatory for the first A2T index cell, not optional.

## 4. Engineering items (all CPU, none on a flight tree)

E27 -- carrier profile for the index rail. `rails/knowledge_index.py` keeps every SLURP constant as
the `slurp` profile of a `KnowledgeIndexCarrierProfile` table keyed by `carrier_lock_key`: view ids,
pin namespace, entry kinds and sigils, L1 section choices and hoisted sections, id grammar, evidence
prefixes, the Perception-candidate extractor (SLURP: `candidates[].intent_id`; A2T:
`actions[].candidate_tools` through `rails/a2t_perception_state.py`) and the admitted orderings.
Regression guard: the sealed IDX receipts (view sha `b279dcc0...`, 17,265 characters, one
system-message sha over 1,080 rows) and the render proof on 20 sealed B1-notool rows must reproduce
byte for byte after the refactor; the loader's carrier test becomes a lookup of the view's declared
carrier. `native_episode_config.py` refusals 7 and 8 are unchanged in meaning.

E28 -- the A2T id grammar (sigils D / T beside I / S / E / X in `parse_index_id`, `IndexEntry`
construction for `domain` / `tool` / `edge`) and the A2T view builder
`scripts/build_a2t_knowledge_index_view.py` (modelled on the SLURP builder): sources pinned by sha256, `knowledge/audio2tool/semantic/a2t-knowledge-index-v1/{snapshot,
release,completion}.json`, `--twin-seed` for `a2t-knowledge-index-twin-v1`, pins document
`docs/readiness/<date>-a2t-knowledge-index-release-pins-v1.json`, two zero-contact ledger rows.
Model-free render proof and wire check on 20 sealed rows of the A2T base (the existing scripts,
carrier-parameterised by E27).

E29 -- the A2T tool-free arm. The A2T base for the index must have a constant prefix; the cheapest
form is the SLURP precedent: withdraw the Reviewer's and Planner's `phase_tools` (both hold
`saea-tool-task-contract-v1` / `saea-tool-knowledge-target-lookup-v1`, whose observations are the
registry and the stores the prefix already carries). Items E23/E23b already accept a tool-free native
arm; the A2T recovery policy `phase-audio2tool-native-candidate-recovery-tools-v1` needs its
tool-free twin program registered in `rails/controllers.py` (same shape as the SLURP one).

E30 -- admission plumbing: an A2T default-plan fragment
`configs/baseline/a2t-native-role-default-plan-v1.json` (the sealed dual-store base plus decided
modules), the `audio2tool` carrier in `docs/receipts/harness-admission.json` default plans, entries
written only from sealed verdicts.

Registrations by script (decision 58), one cell per package: A2T-NULL (request-identical replicate
of the base on the paired 400 subset: the carrier's first own null, decision 38), A2T-NOTOOL (E29 on
the same subset, read at the A2T own null once it exists), A2T-IDX and A2T-IDXT (the index and its
twin on the tool-free base), each with the index-consumption read (decision 64) in the protocol.

## 5. Rosters, comparators, cost

- First cells on the PAIRED 400-ROW SUBSET of the sealed union-4000 (the 400 sample ids of
  `A2T-CALIBRATION-400` that lie in the union, or a stratified 400 by tier drawn once and frozen):
  the comparator rows are the sealed union-4000 outputs of the same ids, never re-flown. n = 400
  meets the paired-claim floor; the full 4,000 flies only for the admitted form.
- Serving geometry: the A2T native session (`q4km-mmproj-free-a2t-native-role-np2-max2048-v1`,
  2 slots x 49,152) is a different resident session from SLURP's np4 session; A2T cells therefore
  fly only in gaps of the SLURP queue where the geometry swap pays (one resident server per
  geometry; owner 2026-09-07 always-on rule). The index shrinks the A2T Perception prompt (34,868
  tokens today, most of it the registry) toward the np3 slot; whether np3 fits again is measured by
  the render proof before any session change (decision 60 host settings untouched).
- Cost per 400-row cell at np2: about 0.6-0.9 GPU-h (4 contacts per row, 2,048 max tokens); the
  four registrations above about 3 GPU-h; the full-4000 confirmation of an admitted form about 8.

## 6. Verification

- E27: `pytest tests/unit/test_knowledge_index*.py`, the sealed-receipt byte-identity regression
  (IDX view sha and system-message sha), `engineering_base_check`, `harness_admission_check`,
  `finite_completion_policy_check`; the SLURP IDX/IDXT registrations are pinned at their flight
  commits and are unaffected.
- E28: view completion receipt (152 tools, 3 domains, edge count, character count), twin
  permutation with zero fixed points and equal multiset and total length, render proof P1-P3 and
  wire check W1-W8 on 20 sealed A2T base rows.
- Every cell: four-row smoke with the structural acceptance (one system-message sha, index receipt
  on every contact, no tools array, all requests fit), official scorer once per complete manifest,
  paired read at the own-null margins, per-tier table (natural and equal-tier weighting), the
  index-consumption statement.

## 6a. Status after E27 and E28 (2026-09-21)

E27 merged (2385efa3): the rail is a carrier profile; SLURP renders byte for byte (released view sha
`b279dcc0...`, render proof on 20 sealed rows identical). E28 merged (0b50e98c): views
`a2t-knowledge-index-v1` (3 domain / 152 tool / 1,040 edge entries; release `a964c69c...`) and its
twin released and pinned; ledger rows SAEA-A2T-E28-KNOWLEDGE-INDEX-VIEW-V1 / -TWIN-VIEW-V1. Two
findings change the plan before any A2T cell: (1) the v1 edge rule admits 1,040 edges (67 % of the
smart_home pairs) because generic argument names (`state`, `action`, `enabled`) are shared by most
tools of a domain; (2) the rendered constant index is 73,652 characters, about 4.3x the SLURP index
and roughly 18k tokens -- too large for a constant prefix on the np2/np3 slots. Owner decision 70 (2026-09-21) settles the form: NOT a hand-tuned
threshold rule. The constant prefix carries the minimal L0 index only (3 domain lines + 152 tool
signature lines); every L1 line, L2 card and edge is per-row material entering through the pointer
block and VALUE RETRIEVAL keyed by the Perception state and the speech key, under a budget; and WHICH
material deserves the prefix or a pointer, at what granularity and budget, is the context-engineering
action space of training-free RL on this carrier (section 3a). The v1 views stay the released record;
no v2 view is hand-released.

## 3a. Index content by best discriminability (owner decision 70)

| element | value |
| --- | --- |
| state | the Perception state (`actions[].candidate_tools`), the speech key, the pointer block |
| actions | per tool: include its activation line / argument line in the constant prefix (yes/no); per pointed tool: expand L1 / L2 (level); per confusable pair: render the edge (yes/no); expansion budget; ordering |
| reward | discriminability = tool accuracy on construction-pool rollouts plus a same-domain confusion term (a wrong tool from the same domain is the failure ORG-1 amplified), minus a prefill-token cost term |
| rollouts | the construction-800 roster only (never union-4000 rows or their gold); grouped rollouts per state from the E2 sampler with pinned seeds |
| update | the adapted Training-Free GRPO experience operator (2026-09-11 audit), the same operator Stage 3 uses on SLURP |
| controls | the minimal L0 index (no learned content), the full hand-authored v1 view (E28), the derangement twin of whatever the search selects |
| first cell | flies BEFORE the search: the minimal L0 constant index with retrieval-supplied expansions at a fixed budget, read against the tool-free base at the A2T own null |

## 7. Owner decisions requested

65-69 decided 2026-09-21 (record rows 65-69); 70 (index content by discriminability, training-free RL) and 71 (tier-stratified 50-per-tier paired subset, seed 20260921) decided 2026-09-21. Retained below as the record of what was asked.

65. Base for the A2T index: the sealed dual-store union-4000 fragment made tool-free (E29,
    recommended) or the unflown scope-tools np2 form (adds candidate refresh and Planner tools; not
    yet a sealed comparator).
66. Index kinds: `parameter` as a section of the tool card (recommended) or a fourth selectable kind;
    exemplars OFF in the first cell (recommended).
67. Roster: the paired 400-row subset of the sealed union-4000 for A2T-NULL / A2T-NOTOOL / A2T-IDX /
    A2T-IDXT (recommended) or the full 4,000 from the first cell.
68. Own null first: A2T-NULL (about 0.7 GPU-h) flies before any A2T NEUTRAL reading (recommended;
    decision 38), so the index is never read against zero as ORG-1 and KC-A1 were.
69. GPU placement: A2T cells enter the queue behind IDXT and Probe G2 and ahead of the SLURP
    node-read cells only when the SLURP queue has no ready cell (recommended), or as a fixed slot
    after B9a.

Until 65-69 are decided, E27 and E28 proceed (they change no flown SLURP byte and release a view
nobody flies); E29 and the registrations wait.
