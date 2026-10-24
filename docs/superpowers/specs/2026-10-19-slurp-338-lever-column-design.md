# Decision-338 lever column: false-fill suppression (L1) and Perception candidate union (L2) on the Thinking core, TRAIN Fold B

Model-free design, 2026-10-18 (Opus, on the coordinator's brief). Read-only on the study repo (master `23c7033f4`) and the data root.
It made no model, server or GPU contact and opened no test row. Authority: owner rulings 335 B and 338
(`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`). Evidence: `docs/results/2026-10-19-slurp-v3-gap-to-finetuned-sota-decomposition.md`.
Offline bounds: `l338_bounds.py` writes `l338-bounds.json` (this folder). Development numbers only (decisions 28 and 86); nothing here is a claim.

## 1. Column at a glance

Roster `SLURP-EVO-FOLD-B-V2` (n = 1,080); the v3.0 Thinking lock (268-B cell, P3.1 form, thinking 3,072 / cap 4,096); resident session
`think-budget-np4`, no new fragment; flies after the NX-T R4 chain exits rc 0 (carriers stay deferred). One same-flight level-2
Perception-branch group (each branch its own Perception and first-visit Solver visit, as NX-T R1 / R2b); twin, then delivering arm LAST.

| branch | role | Perception contacts | Solver contacts | what differs from the lock |
| --- | --- | ---: | ---: | --- |
| `l1-support` | candidate | 1 (greedy) | 5: sample 0 greedy; samples 1-4 at T 0.6 / top_p 0.95 / top_k 20 | delivered entities = first-first support filter + N1-gated empty decision over its own 5 Solver samples |
| `l2-union` | candidate | 4: sample 0 greedy; samples 1-3 at T 0.6 / top_p 0.95 / top_k 20 | 1 (greedy) | Solver shortlist = ordered union of the 4 notes' candidates, cap 3 |
| `aa` | twin (replicate_of lock) | 1 | 1 | none |
| `lock` | delivering | 1 | 1 | none (v3.0 lock, v4g delivery) |

Total per row: 7 Perception + 8 Solver = 15 contacts, 0 tool calls. Composed L1+L2 goes to the 335 B Fold A column (section 7).

## 2. L1: false-fill suppression on the Thinking core

### Mechanism (reused, fixed before contact)

Reused unchanged: the VER-1 composer (`scripts/analysis/slurp_ver1_offline.py` `row_supports` / `render_rule`), the aggregation read's
`support_of_entity`, the registered similarity (`character_level_f1` over `normalize_text_v1`), the R6 N1 statistic. Three steps:
1. **Support filter, first-first, n = 5, s = 2.** Sample 0 (greedy) gives labels and base entities; a base entity is kept iff >= 2 of the 5
   samples (sample 0 counts) carry the same type with normalised-filler char F1 >= 0.8. Malformed sample 0 -> lowest valid. Intent never moves.
2. **Gated empty decision.** Empty the row iff N1 >= 0.2 (entity-free share of the 20 supplied exemplars) AND >= 3 of the 4 sampled
   contacts answered no entity: the VER-1 / R6 `c3verdict x N1` gate with the samples as verdict (no contact, no R3 template axis).
3. **v4g** after the rule, as the lock delivers.

Secondary forms (s = 3, filter alone, gate alone, `saea-commit-plurality-support-v1`) are zero-GPU compositions of the same custody.
n5-s2 (+gate) is the only form with CI-LB > 0 on every Instruct 5-sample pool.

Earlier Instruct-core reads (all DESCRIPTIVE):

| read | SLU delta | note |
| --- | --- | --- |
| VER-1a Fold B, n5-s2 + gate | +1.29 / +1.43 | |
| ROLL-2 Fold A, n5-s2 | +1.03 | |
| ROLL-3 DEV, n5-s2 | +0.76 | |
| VER-1 fixed rule n3-s2 + gate, Fold A | **+0.56 [-0.40, +1.51], NOT CONFIRMED** | the loss sat on non-empty-gold rows (-0.87) |
| R6 N1-gated verdict | +0.75 / +0.98 | |

### Offline bound on the Thinking core (`L1_support_filter_vs_base`)

Base: R2b delivering arm `budget-3072` (SLU 72.74; 81 of 392 empty-gold rows false-filled). Pool: sealed lock-like R1 rec2 / R2b decodes,
v4g re-applied (idempotent on 1,079 / 1,080); greedy, heterogeneous, one note per decode: a proxy, not the flown form. Cluster bootstrap 2,000.

| form (pool) | SLU delta vs base [CI95] | false fills removed | non-empty exact lost / gained | dropped entities that were wrong |
| --- | --- | ---: | --- | ---: |
| P5 n5-s2 | +0.83 [+0.32, +1.33] | 12 | 2 / 4 | 0.92 |
| **P5 n5-s2 + gate (primary form)** | **+1.09 [+0.53, +1.63]** | 21 | 3 / 4 | 0.91 |
| P5 n5-s3 (the gate adds nothing) | +1.77 [+0.94, +2.56] | 27 | 6 / 7 | 0.89 |
| P3 n3-s2 | +1.46 [+0.63, +2.24] | 27 | 5 / 7 | 0.87 |
| P5 gate alone (>= 3 of 4 empty) | +0.42 [+0.11, +0.74] | | | |

A/A reference: the in-flight R1 twin minus both-on reads -0.12 [-1.49, +1.11].
Drop precision 87-92 %, but only 11-25 % of the base's wrong entities are reached. s = 3 wins here only because greedy decodes are
correlated; with T 0.6 samples support thins and s = 3 loses true entities (VER-1a n5-s3: 23 false fills removed, 11 / 7 non-empty exact
lost / gained). s = 2 stays primary.

**Contacts and expected effect.** 1 Perception + 5 Solver = 6 per row (3.08 lock-row eq.). Vs the lock: SLU **+0.8 to +1.8** (central
about +1.1; reaches the 1.49 floor only at the high end); intent 0. The secondary pure-filter delta (rule minus its own sample 0) carries
no twin noise (Instruct analogue +0.85 [+0.35, +1.36]) and should resolve even when the vs-lock delta does not.

## 3. L2: Perception multi-sample candidate union (new shape, never flown)

### Mechanism

1. k = 4 Perception contacts over the same packet, evidence and template: sample 0 greedy at the lock seed; samples 1-3 at T 0.6 /
   top_p 0.95 / top_k 20, seeds = lock seed + offsets 1..3.
2. **Ordering rule:** sample 0's list verbatim first; then the candidates it lacks by (samples listing it desc, best rank asc, intent id
   asc); **truncated to 3** (the Solver's own `candidate_supply.max_candidates`: no supply knob, no context-fit change). Rank 1 is never
   displaced; other note fields come from sample 0 plus the appended candidates' own entries.
3. The merged note feeds the branch's ONE greedy Solver contact (the level-2 render re-resolves the candidate supply from it).

An m = 2 variant (append only when >= 2 samples list it) changes the Solver input, so it is reported only as an offline bound.

### Offline bounds (`L2_*` keys)

Delivering-list recall **88.15 %**; base conversion by gold position: sole 99.2 %, rank 1 of several 88.8 %, rank 2-3 58.8 %, absent 7.8 %.
Recall of the union over k sealed decodes:

| decodes | k = 1 | 2 | 3 | 4 | 5 | 7 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| thinking-on greedy Perception | 88.15 | 89.00 | 89.41 | 89.68 | 89.91 | n/a |
| all 7 (adds the 2 no-think notes) | 88.15 | 90.60 | 92.16 | 93.25 | 93.96 | 94.44 |

- **Thinking-on union, cap 3:** recall 89.81 %. Gold is newly listed on 18 rows and lost on 0. The m = 2 variant reads 88.98.
- Two greedy notes of the same form differ on 15-20 % of rows (both-on vs twin: 167 rows). That is the only diversity this union saw; T 0.6 samples add more.
- **Natural experiment, R1 `perception-off`:** no-think Perception lists 3 candidates on 83 % of rows, recall **91.48 % (+3.3)**, yet
  intent **-0.09** vs the base: rank 2-3 gold converts at 43.8 %, rank 1 of a 3-list still at 97.2 %.
- **Intent:** no-dilution upper bound (newly listed x rank 2-3 conversion) +1.0 pp (greedy-like diversity) to +1.5 / +2.0 (no-think-like);
  realised analogue about 0; class-rate estimate (thinking-on 5, cap 3) 85.54 (+0.17), charging diluted sole-gold rows at 88.8 %.

**Contacts and expected effect.** 4 Perception + 1 Solver = 5 per row (2.44 lock-row eq.). Intent **0 to +1.0** (central about +0.4,
below the 0.65 floor); SLU 0 to -0.8 (longer lists raise the Solver forced-close share, R2b 38 / 45 / 65 % at 1 / 2 / 3 candidates, and
forced rows false-fill). Likely word NEUTRAL; flown as ruled, the only untried attack on the 75-78 % off-list intent mass.

## 4. Instruments: what exists, what is new (one-base rule)

What exists, and why it cannot carry the column alone:
- **R4 `roles.solver.decoding_variants`** (receipt v6) cannot carry L1: it refuses `seed` by name and two arms with the same override (no
  n same-sampler draws), and any Solver fan-out is refused beside a Perception branch group (one fan-out per episode,
  `rails/native_episode_config.py` lines 1456-1500, 1740-1830).
- **The level-2 `PerceptionBranchGroup`** (what the template / Perception-template / thinking-variant groups compile into) is the base extended.
- **The grouped Solver visit** (`roles.solver.samples` + `decoding_overrides {temperature, seed_offset, greedy_first}` + `commit`, VER-1a;
  `reproduction/ojw/native_group_solver.py`, replay `analysis/native_commit_replay.py`) carries L1, but today it is episode-wide, admits
  temperature only (no top_p / top_k), and the loader refuses a `deliver_normaliser` beside it.

New code, all inside the existing bases (no `rails/probes/` module, no adapter or controller subclass):

1. `rails/supply_variants.py`: `parse_perception_sampling_variants`, a sibling of `parse_perception_thinking_variants`, compiling into the same `PerceptionBranchGroup`.
   - Two new optional branch axes: `perception_samples {k 2..4, decoding from the closed DECODING_VARIANT_KNOBS, seed_offsets, merge_policy, cap}` and `solver_samples {n 2..8, decoding, greedy_first, seed_offsets, commit_policy, commit params}`.
   - Exactly one axis per non-A, non-twin branch.
   - Seeds are fixed and recorded per contact (fragment seed + offset, the VER-1a convention).
2. `rails/native_episode_config.py`: row field `roles.perception.sampling_variants` (same one-fan-out refusals); ceiling term = sum of
   per-branch contacts; the `deliver_normaliser` refusal scoped to the DELIVERING branch only.
3. Branch runtime (level-2 runner, beside the thinking-variant path): `perception_samples` = k contacts -> merge -> branch Solver render;
   `solver_samples` = the grouped Solver visit scoped to the branch. Contact-to-sample mapping by invocation index (as E2b).
4. `rails/native_episode_receipt.py`: perception-branch receipt schema +1 (per sample: request / response sha256, seed, override, parse
   status; merged candidate ids; commit outcome).
5. `rails/commit_policies.py`: `saea-commit-first-support-v1` (optional gate `{n1_min, empty_votes_min}`) in `core.base.COMMIT_POLICIES`;
   new registry `core.base.PERCEPTION_MERGE_POLICIES` with `saea-perception-candidate-union-v1`. The engineering-base check resolves both.
6. `scripts/checks/stage3_effect_floor_check.py`: admit `variant_kind` `perception-sampling` / `solver-sampling`.
7. Reader `scripts/analysis/slurp_l338_column_read.py`: official per-arm scoring (`stage3_rollout_score --mode supply-variants`); L1 forms
   from custody via the commit replay + v4g; N1 via the R6 helpers.
8. Flight family `scripts/flights/nx/l338_*` (arms, derive, write, launch spec, flip, chain, read), cloned from `nxt_r4_*`.
9. Tests: parser refusals, merge ordering and cap, commit-replay identity, request-level proof that every sample carries the lock's
   thinking fields, receipt round-trip; plus a 4-row smoke.

Lean alternative (coordinator's call, not recommended): L1's samples 1-4 on the twin branch, the twin delivering its sample 0. It saves
1 Perception + 1 Solver per row (60.2 GPU-h expected), but `aa` stops being the pure twin the effect-floor gate needs.

## 5. Cost (R2b delivering pass, the `nxt_r4_cost_inputs.json` numbers)

- Inputs: Perception 59.00 s, Solver 64.07 s per contact at 4 slots; lock row 123.07 s; 1.95 rows/min; 9.23 GPU-h per lock pass. Per row: 7 x 59.00 + 8 x 64.07 = 925.6 s = **7.52 lock-row equivalents**. By branch: lock 1.00, aa 1.00, l1 3.08, l2 2.44.
- **Expected 69.4 GPU-h** (l1 about 28.4, l2 about 22.5). **Ceiling 90.3 GPU-h** = ceil_0.1(69.4 x 1.3).
- Smoke: 4 rows, 60 contacts, at most 0.6 GPU-h. Program 16,200 contacts; plan ceiling 32,400 calls (2x, the R4 convention); repeated
  speech audio about 47,322 s (15 x 3,154.8).
- An estimate, not an envelope: T 0.6 samples may reason longer or shorter than greedy (R4's d1 measures it first) and L2's Solver sees
  longer lists. The machine sign-off refuses a smoke mix beyond 1.3x the registered one.

## 6. Read rule and registered words (fixed in the package before the countersign)

Each arm minus `lock`, paired per row, utterance-cluster bootstrap 10,000 draws, official `slurp-slu-official-train` once per complete
column. Twin offsets o_SLU / o_int = `aa` minus `lock`; the l1 branch's sample 0 is a second A/A (reported, used in no word). Floors
(decision 190, n = 1,080): 1.49 SLU / 0.65 intent. `stage3_measurement`: `same-flight-node-column`, `claims_benefit false`,
`expected_effect_pp 0.0`, claim `nominated` (as R3 / R4).

Both candidate arms cost more than the lock (l1: 5 Solver samples; l2: 4 Perception samples), so NO-RESOLVED-LOSS (reserved for a
cheaper arm that loses nothing, as in R1/R2) applies to neither. The vocabulary is exactly NOMINATED / HARM / NEUTRAL, judged against
the floors; the twin `aa` is the noise bar, reported beside the words and used in no word.

**L1** (SLU primary, intent guard):

  | word | condition |
  | --- | --- |
  | NOMINATED | SLU CI-LB >= 1.49 and intent CI-UB >= -0.65 (no resolved intent loss) |
  | HARM | SLU CI-UB < -1.49, or intent CI-UB < -0.65 |
  | NEUTRAL | otherwise |

**L2** (intent primary, SLU guard):

  | word | condition |
  | --- | --- |
  | NOMINATED | intent CI-LB >= 0.65 and SLU CI-UB >= -1.49 (no resolved SLU loss) |
  | HARM | intent CI-UB < -0.65, or SLU CI-UB < -1.49 |
  | NEUTRAL | otherwise |

Secondaries: L1 pure-filter delta, s = 3 / filter-only / gate-only forms, false fills removed, non-empty exact lost / gained; L2 merged-list
recall vs sample 0's, newly listed / lost gold, conversion by position, forced-close share by list size; all arms: discordance of every
sampled stream vs the twin's, per-scenario tables (natural and equal weighting), seconds per contact.

**Determinism.** Greedy decoding at np4 is not bitwise reproducible across batch shapes. Each sampled contact has a fixed, recorded seed
(lock seed + offset) but is still one draw under the same batch nondeterminism, so no arm is read as an expectation; the discordance
table shows how much of each delta is draw noise.

## 7. Composition and sequencing

**L1+L2 composed belongs in the 335 B Fold A column, not here.** Ruling 335 B puts the composed arm beside the nominated single arms, a
twin and the lock. Composing here adds 4 Perception + 5 Solver contacts (+3.8 lock-row eq., about +35 GPU-h) on the selection roster
before either arm nominates. The interaction is real (L2's longer lists raise forced-close false fills, which L1 removes) and is measured
where the decision is made. One branch may carry both new axes (refused in this registration, admitted in 335 B): no further code.

Zero-GPU pre-reads before the countersign:
- **R4 seal:** the L1 rule over {lock, d1..d4} (one shared note) is the closest analogue to the flown form. Below +0.67 pp (the VER-1
  offline floor): drop L1 from the column (saves 28 GPU-h).
- **R3 seal:** if `t2-grounded-or-empty` nominates, it attacks the same false-fill mass; re-base L1 on t2 in 335 B, do not stack blindly.

Fold B is the selection roster for both rules; the 335 B Fold A column confirms.

## 8. Risks

1. **Code size.** About 9 touch points, and the first per-branch fan-out. The engineering gates and a 4-row smoke must prove form first. L1 alone could instead fly on today's episode-wide grouped visit as a second flight, but the owner did not rule a 2-flight design.
2. **Weak L2 prior.** In the perception-off natural experiment, a +3.3 recall gain converted to about 0 intent.
3. **L1 overlaps R3 t2.** The gains may not add.
4. **v4g beside a grouped visit is refused today.** An in-flight v3.x lock with L1 needs item 2's delivering-branch scoping. N1 in flight needs the commit to see the supplied exemplar ids (335 B / lock work); the column computes N1 offline.
5. **Cost.** About 7.5x a lock pass: 69.4 GPU-h, within the owner's >= 24 GPU-h preference, but it extends the SLURP lock by about 1.5 days after R4.
