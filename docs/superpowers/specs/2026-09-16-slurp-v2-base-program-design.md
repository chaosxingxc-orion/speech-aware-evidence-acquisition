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
| M3 | USE projection v3 (support filter + surface normalisation) | USE | scorer `slurp-slu-official-projected-v3[-train]` and the runtime judge of the same rule | unprojected |
| M4a | `general_quirky` fallback candidate + qa/general contrast card | ORG | `knowledge_views`: Perception fill `fallback_candidate` + store version | base without it |
| M4b | Date/time slot-contract revision | ORG | `knowledge_views`: slot store version pin | base store |

Boundary for M1: exemplar text and gold annotations come only from the construction pool
(TRAIN minus every utterance with a recording in TRAIN A, TRAIN B or DEV-1000, the 2026-09-13
exclusion), reach the model only as typed content blocks, and never as instruction text. The
exact-text-neighbour rate is reported as a sensitivity subset; no gold-derived runtime mask.

## 4. Phases

**Phase 0 (done or in progress, zero contacts):** takeover receipt, owner decision record,
coordination phase `fable_directed_execution`, owner-decisions note, this spec, TRAIN A
direct-anchor release (`docs/results/2026-09-17-slurp-train-a-direct-anchor-release.md`).

**Phase A (CPU, zero model contacts; parallel agents):**

- A1 USE projection audit on the sealed TRAIN A anchor and DEV1000 replication outputs:
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
  - E4: `score_slurp_outputs_official_projected_v3[_train]` mirroring v2, plus the runtime judge
    form; a test proving scorer and judge agree byte-for-byte on sealed rows.
  - E5: Perception fill option `fallback_candidate: general_quirky` (appended when absent, never
    displacing model candidates) and a qa_factoid/general_quirky contrast card; date and time
    slot-contract revisions from construction data only, as a new pinned slot store version.

**Phase B (GPU, one cell in flight, TRAIN A 1,080):**

| Cell | Module | Base | Control | Contacts/row | GPU-h |
| --- | --- | --- | --- | ---: | ---: |
| B0 | M0 | anchor minus review loop | sealed anchor | 2 | ~1.4 |
| B1 | M1, plain top-20 speech-keyed exemplars | B0 (anchor if B0 harmful) | derangement twin + B0 | 2 | ~2 |
| B2 | M2, N=5, T=0.7 | B0 | 5 greedy repeats aggregated identically + B0 | 6 | ~4 |
| B3 | M3 | scorer-side | unprojected | 0 | 0 |
| B4a | M4a | best admitted base | that base | 2 | ~1.4 |
| B4b | M4b | best admitted base | that base | 2 | ~1.4 |
| B5 | admitted set ("v2 candidate") | -- | anchor, released direct | 6-7 | ~4-5 |
| B5r | replication of B5 | -- | B5 | 6-7 | ~4-5 |
| B6 | DEV1000 confirmation | -- | sealed DEV1000 direct 35.68 / agent 50.30 | 6-7 | ~4 |

Order: B0 -> B3 (any time) -> B1 -> B2 -> B4a -> B4b -> B5 -> B5r -> B6.

Decision rules, fixed before each flight and copied into its preregistration:

- B0 NEUTRAL if SLU and intent are non-inferior within the null margins (intent 0.92, SLU micro
  1.18); then the loop leaves the default plan. If HARMFUL, later cells build on the anchor.
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
`core.scoring_batch`; paired whole-speaker bootstrap, 10,000 draws, seed 20260915, CI95 for
advancement, CI90 for diagnostics, natural-mixture and equal-scenario tables; comparators are
sealed bytes, never re-flown controls; preregistration + ledger row + ExecutionPlan
(`bounded-discovery-probe`, discovery role) before the first contact; contact-free wire check and
a 4-row smoke for each new module form; first failure stops a cell, one recovery
re-registration at most; harness-admission entry per module; default plan = admitted or neutral
modules only; no transcript tokens, no second answering model, no gold in runtime.

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
