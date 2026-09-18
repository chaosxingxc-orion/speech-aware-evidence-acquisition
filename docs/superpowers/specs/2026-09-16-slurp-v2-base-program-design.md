# SLURP v2 base program: design

Author: Fable 5.1, root coordinator. Date: 2026-09-16 (owner approval), recorded 2026-09-17 UTC.
Authority: `docs/superpowers/plans/experiment-handoff/OWNER-FABLE-TAKEOVER-2026-09-16.md` and
`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`. This spec admits no model
contact; each cell registers its own ExecutionPlan, exposure row and readiness before contact.

## 1. Goal and acceptance bar

Raise the SLURP agent from the retained dual-store base (official pooled SLU-F1 48.53 / intent
77.96 on TRAIN A; 50.30 / 75.6 on DEV1000) to an acceptable base: **SLU-F1 >= 64 and intent
>= 78, replicated on the same roster** (owner decision 1). Lock that system as "SLURP base v2"
and only then open Stage 3 (training-free optimisation of its exposed decisions).

## 2. Diagnosis the design answers

| Fact (sealed evidence) | Consequence |
| --- | --- |
| Reviewer x2 + Planner = 60 % of contacts, 0 intent saves, 1 harm per 1,000 rows; Planner ACCEPTs 1,075/1,080 | The review loop is removed unless the ablation shows harm; its budget is re-spent |
| Entity loss: FN 31.5 % (date omission 84/138), FP 28.8 % (184/414 empty-gold rows emit entities), filler distance 35 % (time representation), type swap 4.7 %; recall ceiling 78 | Slots need convention transfer (exemplars), FP suppression (aggregation, support filter) and two contract fixes |
| Coverage 86.8 %, driven by own-card retrieval; Perception over all 60 cards also 87.7 %; `general` scenario coverage 43 %, intent 36.7 % | Coverage needs a supplement that preserves the model's hypotheses (neighbour intents) and a fallback for `general_quirky` |
| Far-field beats headset; fixed Whisper null; owner no-transcript rule | No ASR or re-listen tools |
| Byte-identical greedy prompts flip 28 % of outputs and 5 % of intents | Sampling plus deterministic aggregation has headroom and yields same-state trajectory groups |

## 3. Modules (each one config key, admitted one at a time)

| Id | Module | Axis | Config switch (harness-admission class) | Twin / control |
| --- | --- | --- | --- | --- |
| M0 | Review-off native episode | USE | `run`: `native_episode.max_revisions 0` + reviewer/planner `max_iterations 0` (policy `phase-native-candidates-solve-v1`) | sealed anchor |
| M1 | Exemplar-grounded Solver | SUPPLY | `knowledge_views`: `phase_supply.solver` = annotated TRAIN exemplars keyed by sealed speech vectors | within-scenario derangement of the speech vectors (token-matched) |
| M2 | Sample-and-aggregate commit | USE | `judges`: `roles.solver.samples N` + `decoding_overrides` + commit policy `saea-commit-plurality-support-v1` | N greedy repeats aggregated identically |
| M3 | USE projection v3 (label rule R_action then legal-label v2; filler normalisation P2: case, whitespace, punctuation, meridiem, numeric words; NO support filter, rejected by A1) | USE | scorer `slurp-slu-official-projected-v3[-train]` and the runtime judge of the same rule | unprojected; official, symmetric-normalised and rung numbers always reported together |
| M4a | `general_quirky` fallback candidate + qa/general contrast card | ORG | `knowledge_views`: Perception fill `fallback_candidate` + store version | base without it |
| M4b | Date/time slot-contract revision | ORG | `knowledge_views`: slot store version pin | base store |
| M5 | Node Context Policy, L1 `structured` (E8a, 2026-09-17) and L2 `cleaned` (E8b, 2026-09-17) | USE | `episode`: `native_episode.context_policy` (OFF = absent / `"raw"` / raw at every boundary) | the anchor; L1 derangement twin only on a positive CI95; L2's comparator is B7a's sealed bytes |

Boundary for M1: exemplar text and gold annotations come only from the construction pool
(TRAIN minus every utterance with a recording in TRAIN A, TRAIN B or DEV-1000, the 2026-09-13
exclusion), reach the model only as typed content blocks, and never as instruction text. The
exact-text-neighbour rate is reported as a sensitivity subset; no gold-derived runtime mask.

Boundary for M2 (item E2c, 2026-09-17): **the committed answer is the reviewed draft; raw samples in
custody.** One grouped Solver visit takes ONE step and registers exactly ONE `phase:<solver>` agent
state, holding the commit policy's aggregated answer in the same wire form a samples-1 (anchor)
Solver state has, so the Reviewer and the Planner read one draft exactly as they do on the anchor and
the cell stays one-factor. The N raw samples stay in custody — each its own contact, trace and cost
record, all N in the visit's one `action_alternatives` wave, and their seeds, decoding parameters,
parse status and parsed answers in the sealed `solver_group` receipt that
`analysis.native_commit_replay` re-aggregates offline. A Planner `REVISE` re-samples the whole group
and re-commits; the contact-ceiling formula is unchanged.

E2d (2026-09-17): **a grouped row's delivered text is custody, re-derived at seal.** Cell B2 v3's
four-row smoke generated every contact and then failed AT THE SEAL. The delivered `text` of a grouped
Solver row is the commit policy's aggregate over the N raw sample texts and equals none of them,
while the bundle's I7 invariant reads a row's `response_text_sha256` as "the delivered text IS one
recorded model response's bytes" — and the pre-E2d runner bound that field to the LAST RAW sample's
text hash. Two changes close it, both confined to grouped rows. (1) The runner:
`reproduction.ojw.native_group_solver` now records `solver_group.commit_params`, the exact parameters
the policy was applied with, beside its already-recorded id; and
`core.flight.runtime._canonical_output_rows` binds a grouped row's `response_text_sha256` to the
DELIVERED bytes. Nothing is lost — the raw transport envelope hash stays in `response_sha256`, and
every raw sample's own request/response hashes stay in `solver_group.samples[i].contacts[j]`. A
samples-1 row is byte-identical to before (pinned in
`tests/unit/test_native_episode_runner_grouped_solver.py`). (2) The verifier: `core.bundle.outputs`
adds invariant **I7g** for a row carrying a `solver_group` receipt — every sample's recorded
`response_text_sha256` must be the trace's own MODEL_RESPONSE bytes for that contact, the named
commit policy must resolve in `core.base.COMMIT_POLICIES` and reproduce itself, re-running it over
the row's own recorded samples through `analysis.native_commit_replay` (the same code the offline
sensitivity table runs) must reproduce the delivered bytes byte for byte, and the row's
request/response identity must be that group's LAST sample contact. I7 itself is untouched and still
binds every row's `text` to its own `response_text_sha256`, grouped rows included; a grouped row
whose delivered text differs from the recomputation is refused naming I7g and the first differing
character offset, never the text. A grouped receipt recording no `commit_params` is refused: a bundle
carries no composed configuration, so without them the delivered text cannot be re-derived from the
bundle alone. That is also why the smoke's own sealed bytes, written by the pre-E2d runner, do not
verify — their samples bind to the trace and their commit recomputation reproduces all four delivered
texts exactly, but the row form is the old one, so cell B2 v3 re-flies its four-row smoke under the
fixed runner rather than any sealed byte being edited.

E8a (2026-09-17, owner directive of 2026-09-17 on node context): **M5, the Node Context Policy**, one
declared handling policy per node boundary, where a boundary is the pair
`(consumer_role_kind, semantic_class)`. Axis USE. Config switch: `episode` class, third and last key
of the closed allowlist, `native_episode.context_policy`. OFF arm: level L0 — the key absent, the
literal `"raw"`, or an object that is `raw` at every boundary — which renders request bytes identical
to the pre-key baseline (pinned in `tests/unit/test_node_context_policy_runner.py`). ON arm: level L1
`structured`, a deterministic zero-contact parse → declared malformed rule → committed hash-pinned
template under `configs/probes/ncp_slurp_*.txt`. Twin: the L1 derangement control of the design's
section 10, which flies only if the cell shows a positive CI95. Level L2 (`cleaned`, one extra
context-cleaning contact) is E8b and is refused at load time until it lands. The existing optional
`native_episode.role_context` block is folded under the new key — its `policy_id`/`params` pair IS
the structured level's implementation — and a fragment carrying both is refused. Design and cells
(B7a, B7b): `docs/superpowers/specs/2026-09-17-node-context-policy-design.md`; evidence base:
`docs/results/2026-09-17-slurp-node-context-audit-v1.md`. E8a is the engineering only: no cell, no
config commit, no exposure row and no model contact are authorised by it.

E8b (2026-09-17): **M5 gains its level L2, `cleaned`.** A boundary declared
`{"level": "cleaned", "cleaning": {...}}` performs L1 first and then makes ONE additional contact to
the same frozen core, on the consumer contact's own pinned slot, in the same resident session and
serving geometry, composed by the same `MeteredNativeSpeechRequest` path every role contact uses — so
it is metered, budget-gated, exposure-bound, traced and costed identically and is refused past
`config.max_contacts`. Its declared phase carries `knowledge: "none"` (its request has no evidence
block and no agent-state history), its own registered `response_format_id`
(`ncp-review-issues-v1`), and an instruction that is exactly the committed, hash-pinned template
`configs/probes/ncp_slurp_cleaning_review_v1.txt` plus the L1 material — never the task, never the
answer schema, never a request for a new judgment. Its answer is validated against the design's
closed schema and against the rule that a cleaning contact may not introduce content; on ANY failure
the boundary falls back to its L1 rendering and the receipt records `validation: "rejected"` with the
reason, one attempt and no retry. At most one cleaning contact is made per consumer contact per
boundary (the LAST state of that boundary in the contact's exposed history), which is what makes the
ceiling exact: the contact ceiling gains `(max_revisions + 1) × consumer_role.max_iterations` per
cleaned boundary, taking the anchor's 11 to 13 for the one boundary cell B7b declares. Cell B7b's
whole config difference from B7a is that one boundary entry. E8b, like E8a, is engineering only.

E3c (2026-09-17, cell B1 abort): when the Planner routes REVISE the Solver is re-entered and the
prepared M1 supply returns the same twenty values, so `rails.controllers.restrict_repeat_visit_supply`
restricts a repeat visit to what the trajectory does not already hold and emits no acquire
transition when that is nothing — the values still reach the revisited request through the
accumulated `QueryState`, and every first visit is byte-identical.

E8c (2026-09-17, cell B7a abort): **harness robustness — a malformed Planner output is a retained
row, never a flight failure.** The B7a L1 arm aborted at 618 of 1,080 rows and 3,278 contacts
because one Planner response was `REJECT` and one was an 80-character sentence instead of `ACCEPT`
or `REVISE`. Every module in this section shares the one harness, so this applies to every cell: a
Planner output that names no registered action (and, under `json-action-v1`, any output the strict
single-key parse refuses) now ends its own row through the same explicit-accept seal an `ACCEPT`
takes — the committed draft delivered unchanged, no further contact, no revision spent — and is
reported as a row-level disposition, with `"legal": false` and
`"disposition": "planner_action_illegal"` on the route, the token cut to 32 characters, its sha256
beside it, and a `planner_action_illegal` count on the row's `native_episode_receipt`. The row
counts toward every budget it consumed and is scored by the standard scorer like any other row. A
cell verdict must read that count: rows sealed this way answered without a Planner decision, and a
cell whose count is not ~0 is reporting on a different population than its comparator. See
`docs/superpowers/specs/2026-09-17-node-context-policy-design.md` section 6 for the mechanism and
the proofs.

E10 (2026-09-18): **resume-recovery of an aborted attempt.** Owner decision 22 makes this a
standing program rule: every experiment registered from now on must support checkpoint resume. A
resume-recovery is a recovery re-registration (one per flight, root-diagnosed) that applies ONLY
when the code and the request bytes are unchanged — an infrastructure failure, never a harness or
config defect. Under that precondition every COMPLETE row of the aborted attempt is kept, without
selection; every partial or unstarted row is flown by the recovery attempt under the SAME run id
and its own new attempt id; the merged manifest declares the predecessor attempt (trace sha256, the
sorted kept sample ids and their hash, the kept/flown/partial counts) and scores once; and the
bundle verifies every kept row against the predecessor trace, byte for byte. It is a capability of
the shared campaign path, not of one cell: a recovery cell declares `resume_from`
(`{"attempt_id", "trace_sha256"}`) in its committed experiment fragment, `FlightRuntime.preflight`
scans that attempt's trace model-free and fixes the flown roster before any contact,
`_dispatch_phase_program` narrows the roster to the rows that are not COMPLETE, and the seal merges
the predecessor's replayed rows with this attempt's live ones through the one
`_canonical_output_rows` stage (`core.flight.resume`; `core.bundle.outputs` invariant I7r).
Completeness is decided by the episode's own terminal receipt in the trace, never by counting
contacts. Exposure accounting stays run-cumulative across attempts: the recovery plan's worst case
must cover the remaining rows plus the partial ones. The sibling note
`docs/superpowers/specs/2026-09-18-resume-modes-comparison.md` records why this mode was chosen
over incremental checkpoints, chunked sub-attempts and streaming appends (owner decision 24).

E10b (2026-09-18): the narrowing applies to what is DISPATCHED, never to what is VERIFIED — a
prepared artifact (`prepared/<run>/phase-supply-v<N>.json` and its recall twin) is produced, and
re-verified by `core.flight.repin`, over the cell's WHOLE roster, so its identity is computed
from the full-roster packet map (`FlightRuntime._identity_binding`) and the loaded selections are
restricted to the flown rows afterwards; the first resume-recovery flight aborted in `run_phases`
with zero contacts on `PreparationError("prepared artifact identity mismatch")` because the
narrowed 500-row map was compared against a 1,080-row artifact, and the audited list of every
other narrowed-binding consumer lives in that method's docstring.


## 4. Phases

**Phase 0 (done or in progress, zero contacts):** takeover receipt, owner decision record,
coordination phase `fable_directed_execution`, owner-decisions note, this spec, TRAIN A
direct-anchor release (`docs/results/2026-09-17-slurp-train-a-direct-anchor-release.md`).

**Phase A (CPU, zero model contacts; parallel agents):**

- A1 USE projection audit (DONE 2026-09-17, `docs/results/2026-09-17-slurp-a1-use-projection-audit-v1.md`: P2 +3.46 / +3.73 pp official with no scenario harm, about three quarters of it case alignment that the symmetric scorer scores at zero; support filter REJECTED; illegal-label rule R_action +1.39 pp intent) on the sealed TRAIN A anchor and DEV1000 replication outputs:
  support filter (type never under the delivered intent in the 402 TRAIN bindings; variant < 1 %
  of that intent's mentions), spoken-form normalisation for time (digits to words, am/pm),
  scored with the official scorer on projected copies; decision rule fixed: >= +1.0 pp SLU on
  TRAIN A, DEV1000 same sign, no scenario harm beyond the null margin, normalised scorer same
  sign -> M3 admitted.
- A2 exemplar-retrieval headroom (DONE 2026-09-17, `docs/results/2026-09-17-slurp-a2-exemplar-headroom-audit-v1.md`: plain k=20 union coverage 0.972, type recall 0.960, filler recall 0.566, no memorisation channel): sealed Fold A speech vectors
  (`vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl`,
  encoder identity verified against the Nemotron `query:` protocol) against the construction-pool
  subset of `vectors/slurp-kus3/facet-vectors.jsonl`; k in {5, 8, 12, 20}: gold intent among
  neighbour intents, union coverage with sealed Perception candidates, gold filler and slot-type
  recall, echo versus the sealed draft, exact-text-neighbour rate, token cost. Decision: the
  (k, c/m/top_l) maximising union coverage and filler recall under +600 Solver tokens; if
  filler+type recall < 50 % at k <= 12 and union coverage < 92 %, M1 is downgraded and reported.
- A3 coverage confusion audit (DONE 2026-09-17, `docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md`; FIX-3 illegal-id repair joins M3): pair tables for the 143 missing and 95 covered-wrong rows,
  scenario-level recall, share of the 100 persistent misses recovered by A2 neighbours.
- A4 cost pricing from the maximum-five receipts (3.46 GPU-h / 5,417 contacts).
- Engineering E1-E5 (worktrees off master, one agent per item, no installs, PYTHONPATH armour,
  `PYTHONDONTWRITEBYTECODE=1`, base check and targeted tests before merge):
  - E1: `rails/native_episode_config.py` accepts reviewer/planner `max_iterations 0` with
    `max_revisions 0` (ceiling `1 + 1*(0+0+1) = 2`); `reproduction/ojw/native_episode.py`
    delivers the initial Solver output; policy fragment `phase-native-candidates-solve-v1`;
    prompts byte-identical to the anchor; harness-admission switch registered.
  - E2: `roles.solver.samples N` and per-phase `decoding_overrides {temperature, seed_offset}`
    composed into `decoding_params` in `reproduction/ojw/native_request.py` (session identity
    unchanged); all N raw responses kept in the episode receipt; commit policy
    `saea-commit-plurality-support-v1` in `core.base` (intent plurality, greedy tie-break; entity
    pairs at support >= s of N with same-type char-F1 >= 0.8 clustering; medoid filler); an
    offline re-aggregation CLI over sealed samples; tests.
  - E3: KB view `annotated-exemplars` (utterance | intent | type=filler pairs; facet ids
    unchanged so sealed key vectors bind); `phase_supply.solver` through the E6 `acquire`
    transition, key = the sealed speech vector, plain top-k with k = 20 (A2 decision of
    2026-09-17; k = 12 if the prompt-fit receipt refuses 20); no intent diversification
    (`saea-fuse-associated-values-v1` groups per facet and equals plain top-k here);
    containment preflight with the no-example task-contract projection if needed; twin =
    derangement of the query vectors within the sealed anchor's delivered scenario (gold-free,
    token-matched by construction); prompt-fit estimate; tests.
  - E4: `score_slurp_outputs_official_projected_v3[_train]` in `core/scorers.py` mirroring v2's
    registration pattern (label rule R_action, then the v2 fallback; filler normalisation P2 with
    its four rungs; no support filter), plus the runtime commit judge form of the same function;
    tests proving scorer and judge agree byte-for-byte on sealed rows and that v3 reproduces the
    A1 numbers (TRAIN A 51.995 / 79.352, DEV1000 agent 54.031 / 76.5-76.6 as A1 records).
  - E5: Perception fill option `fallback_candidate: general_quirky` (appended when absent, never
    displacing model candidates) and a qa_factoid/general_quirky contrast card; date and time
    slot-contract revisions from construction data only, as a new pinned slot store version.

**Phase B (GPU, one cell in flight, TRAIN A 1,080):**

| Cell | Module | Base | Control | Contacts/row | GPU-h |
| --- | --- | --- | --- | ---: | ---: |
| B0 | M0 | anchor minus review loop | sealed anchor | 2 | ~1.4 |
| B1 | M1, plain top-20 speech-keyed exemplars | anchor (B0 harmful) | derangement twin + anchor | 5 | ~3.4 | ADMITTED 2026-09-18 (twin read, decision 18 branch A): SLU +12.61 [+10.54, +14.60] vs anchor, +7.83 [+5.85, +9.75] vs twin; twin alone +4.77 with nil intent; intent +2.22, v3 62.67 |
| B2 | M2, N=5, T=0.7 | anchor (B0 harmful) | 5 greedy repeats aggregated identically + anchor | 10 | ~5-6 |
| B3 | M3 (A1-decided: R_action + v2 labels, P2 fillers; +3.5 SLU official, about +0.2 symmetric, +1.4 intent) | scorer-side | unprojected | 0 | 0 |
| B4a | M4a | anchor | anchor | 5 | ~3.4 |
| B4b | M4b | anchor | anchor | 5 | ~3.4 | ADMITTED 2026-09-17: SLU +2.55 [+1.13, +3.98], intent +0.56, v3 +2.06; provisional until replicated |
| B5 | admitted set ("v2 candidate") | -- | anchor, released direct | 6-7 | ~4-5 |
| B5r | replication of B5 | -- | B5 | 6-7 | ~4-5 |
| B6 | DEV1000 confirmation | -- | sealed DEV1000 direct 35.68 / agent 50.30 | 6-7 | ~4 |

Order (owner decision 8, 2026-09-17): B0 -> B0r (own-null re-decision) -> B1 -> B2 -> B4b -> B4a -> B4c only if B4a admits -> B5 -> B5r -> B6; a twin flies only after its arm shows a positive CI95 against the base. B3 (projection v3)

Order update (owner decisions 12-17, 2026-09-17): B1 recovery -> B1 twin only on a positive arm CI95 -> B2 v3 -> B7a -> B4b replicate -> B4a -> B4c only if B4a admits -> B7r -> B7c -> B7b -> B5 -> B5r -> B6; every paired read reports net harmed rows per scenario and flags five or more; a TRAIN sibling of the symmetric scorer is registered and every sealed TRAIN A cell re-read offline.

Bar metric (owner decision 23, 2026-09-18): the bar and every final evaluation read the OFFICIAL, unprojected SLURP `evaluate.py` number (`slurp-slu-official-train`), aligned with the community-standard protocol; projection v3 and the TRAIN symmetric view are diagnostics reported beside every official number, never the number a bar or a rule reads. Gains are never assumed additive: a combination cell is read from its own measured score, and additivity (the combination's delta against the sum of the single-module deltas) is a reported diagnostic only. Owner decision 24 (2026-09-18): the serving wrapper, its monitor and every campaign run as Windows Scheduled Tasks with the battery and idle conditions disabled (they survive Claude Code restarts; a machine shutdown still kills them, which is what the resume-recovery of E10 and decision 22 cover); AC sleep and hibernate are set to never during the program.

Order update (owner decisions 18-21, 2026-09-18, bar-first): B1 twin closure -> the pending four-row smokes (B2 v3 recovery, B7a recovery) in GPU gaps -> B4b replicate -> B5e (early combination of M1 or M1p with M4b, the B5 form restricted to the modules admitted so far) -> on meeting the bar, B5er replicate -> lock "SLURP base v2.0" -> B6 DEV1000 -> B2 v3 -> B7a -> B4a -> B4c only if B4a admits -> B7r -> B7c -> B7b as "v2.1" admissions on the locked base. If B5e misses the bar, the decisions 12-17 order resumes and B5b (all admitted modules) reads against the unchanged bar before any owner re-decision. Twin contingency (decision 18): a twin that ties B1 while beating the anchor makes B1 NOT ADMITTED under the registered rule and registers the twin's sealed bytes as the arm of module M1p (delivered-scenario annotated-exemplar presence), replicated by the combination flights. Record: docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md.

Outcome 2026-09-17 (B0 and B0r flown): module M0 is HARMFUL under the TRAIN A own null (docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md); the review loop is retained and recorded NEUTRAL in the harness-admission table with the SLURP default plan configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json; cells B1, B2 and B4 re-register on the anchor as v2 packages (the review-off v1 packages are superseded before contact). Every later cell carries the anchor's nominal 5 contacts per row (B2: 10) at about 3.4 GPU hours (B2: about 5 to 6). The measured own null of this roster and geometry, half-widths pooled SLU 1.1218 pp and intent 1.0051 pp, replaces the imported DEV1000 margins in every later TRAIN A rule. B3 (projection v3) is adopted as the fixed post-processing of every official number (owner decision 7), reported beside the symmetric-normalised number.

Decision rules, fixed before each flight and copied into its preregistration:

- B0 NEUTRAL if SLU and intent are non-inferior within the null margins (intent 0.92, SLU micro
  1.18); then the loop leaves the default plan. If HARMFUL, later cells build on the anchor.
  Outcome: HARMFUL on the first pass (imported margin) and HARMFUL on the own-null re-decision;
  later cells build on the anchor.
- B1, B2, B4 ADMITTED if primary SLU CI95 lower bound > 0 against the base and (B1) the twin,
  intent non-inferior at the null margin, normalised scorer agreeing in sign, and no scenario
  losing intent beyond the null band. Otherwise NEUTRAL (enters the plan only if it lowers cost)
  or HARMFUL.
- B2 thresholds preregistered: s = 3 of 5, char-F1 >= 0.8; the sealed samples license an offline
  sensitivity table (s in {2,3,4}), reported and never used for the verdict.
- B5/B5r/B6: SLU >= 64 and intent >= 78 on TRAIN A twice and on DEV1000 -> lock v2. If B5 lands
  at 56-63, report per-module contributions and return to the owner with the three options
  (second round inside one preregistered grid, lower bar, core-swap study). No repeat-to-pass.

**Phase C (after the lock):** Stage 3 training-free optimisation: state = sealed candidates +
exemplar set + draft structure + sample agreement; actions = exemplar policy, aggregation
thresholds, candidate union; grouped rollouts from the M2 sampler; reward = per-row official SLU
proxy on TRAIN A; update = the adapted Training-Free GRPO experience operator; controls = fixed
agent and unchanged-policy grouped sampling; first read on Fold B. Own spec later.

## 5. Fixed protocol (every cell)

Shared harness (`EvidenceAgentController`, `FlightRuntime`, OpenJiuwen native episode); roster
`docs/receipts/rosters/slurp-evo-fold-a-v2.json`; resident session geometry of
`configs/model/q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1.json`
(attach, never spawn); primary `slurp-slu-official-train`, one score per complete manifest through
`core.scoring_batch`, with the symmetric-normalised sibling
`slurp-slu-f1-normalized-v1-train` (owner decision 14 of 2026-09-17; same implementation, same
TRAIN gold resolution, gold and prediction normalised alike) reported beside every official
TRAIN number as owner decision 7 requires; paired whole-speaker bootstrap, 10,000 draws, seed 20260915, CI95 for
advancement, CI90 for diagnostics, natural-mixture and equal-scenario tables; comparators are
sealed bytes, never re-flown controls; preregistration + ledger row + ExecutionPlan
(`bounded-discovery-probe`, discovery role) before the first contact; contact-free wire check and
a 4-row smoke for each new module form; first failure stops a cell, one recovery
re-registration at most; harness-admission entry per module; default plan = admitted or neutral
modules only; no transcript tokens, no second answering model, no gold in runtime.
Every new preregistration's failure rule carries the resume-recovery clause (section 3, E10; owner
decision 22): its one recovery re-registration is a `resume_from` resume when the abort was an
infrastructure failure with code and request bytes unchanged, and a full re-fly otherwise.

## 6. Verification

Gates: `scripts/checks/engineering_base_check.py`, `harness_admission_check.py`,
`results_ledger_check.py`, `tool_catalog_check.py`, `derived_media_confinement_check.py`,
`experiment_handoff_check.py`; targeted `pytest` per engineering item; WSL-marked runtime tests
where applicable. Per cell: wire-check receipt showing the request differs from the base only in
the module's channel, smoke receipt, prompt-fit receipt, hashes bound before contact, official
score once, paired analysis with the fixed seed, per-scenario tables, admission entry, ledger row.
Program: B5r inside the null band of B5 on every metric; B6 agrees in sign with B5.

## 7. Roles, cadence, budget

Fable designs, preregisters, decides and reports. Opus agents babysit flights and run the A1-A4
reads. Sonnet agents implement E1-E5 in worktrees, one item per agent. Merges land serially on
master between flights; HEAD never moves while a cell flies; CPU work runs at 8 workers during a
flight and 20 idle. Budget about 25-30 GPU-h, three to four weeks wall clock.

## 8. Out of scope

ASR or transcript states, core swap, E21/Audio2Tool flights, N/K sweeps, reuse of any ABORTED
attempt, the four-row slot-view proof, paper-scale claims, Fold B or test reads before the lock.
