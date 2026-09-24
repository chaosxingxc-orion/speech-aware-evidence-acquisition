# Readiness package: SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-V1 (cell CELL-3)

Status: **HELD**. This package registers the engineering for **iteration 3 of the Stage-3 delta
line** — the locked v2.0 plan plus the released `stage3-deltas-v2` store applied under a COVERAGE
GATE — on the **fresh DEV-2000-ADDED roster**, together with the roster's own null. It authorises
no flight, no readiness flip and no admission entry. Every cell in it is `held`.

Source specs: `docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md` sections S3-6
and S3-4s, and the mechanism's own design note
`docs/readiness/2026-09-24-slurp-stage3-scenario-gate-design-v1.md`. Governing decisions: owner 101
(the training-free RL families), 83 (the retention that produced the 200 values), 99 (the lock and
the replicate venue), 106 (the per-node routes), 110 (**PENDING** — iteration 3 itself), plus 17,
25, 28, 29, 58, 75, 79 and 86. The registration note is
`docs/readiness/2026-09-24-slurp-stage3-delta-cell-r03-gate-v1-preregistration.md`.

Stage-3 algorithm (owner decision 101): **`tfgrpo-semantic-advantage-v1`**, operators `update` +
`context_application`. The gate IS the `context_application` policy of iteration 3; both operators
are registered for that algorithm in `core.base.STAGE3_ALGORITHMS`. Declared as `stage3_algorithm`
in all three experiment fragments and checked by `scripts/checks/stage3_algorithm_label_check.py`.

## What this cell is

Cell B6's plan arm — the locked v2.0 default plan as it flew on DEV-2000-ADDED — with
`knowledge_stores.stage3-deltas` added and **nothing else moved**. The store is the same released
`stage3-deltas-v2` CELL-2 flew: same release, same snapshot, same 200 values, same caps, same
ranking. What iteration 3 changes is the **application**:

- the Solver (cap 8), Reviewer (cap 4) and Planner (cap 4) candidate-bound routes each declare
  `scenario_gate` `majority-candidate-scenario-not-in-v1` over **general, alarm, music, social,
  iot, play, news**, and a row whose projected Perception candidates have a majority scenario in
  that set takes **no supply step at that node at all**;
- CELL-2's **Perception unconditional route is REMOVED**, not gated — the Perception node produces
  the candidate list, so there is nothing to gate on when it is served, and the unconditional
  validator's key set is an equality, so a gate there is refused by construction.

On a row the gate leaves open the supply is byte-identical to the ungated route's. On a row it
closes the node takes no supply step and the wave seals as an ordinary `organize` step.

### Why a gate and not a better delta

`docs/results/2026-09-24-slurp-general-scenario-diagnostic.md`: on the strata the store has no reach
into, the arm loses **and the derangement twin loses as much or more** (`general` intent −11.67 pp
twin versus −6.67 CELL-2 and −10.00 CELL-1 on 60 rows), and 0 of the 200 values declare a `general`
target. A loss the twin reproduces is a FORM cost of *carrying* a supply, not the content of any
delta. Where the store does have reach, CELL-2's arm-minus-twin column is positive (news +7.4,
alarm +4.2, qa +4.2, weather +4.1 pp SLU). So the lever is not a better statement and not a better
ranking: it is a narrower application.

## The venue: the first out-of-fold read of the Stage-3 delta line

CELL-1, CELL-2 and CELL-1-GEPA were all read on **TRAIN Fold A** — the roster whose own read chose
what the store retains and which strata this gate names. **DEV-2000-ADDED is a roster the delta line
has never touched.** The seven gated scenarios were chosen on Fold A and are read here out of fold.

That is what this cell is worth, and it is also its limit: DEV-2000-ADDED is a **development**
roster (owner decisions 28, 86). No test claim, no superiority claim, no generalisation claim. Owner
decision 29 allows one test read, and it is not this one.

## The roster's own null flies first

CELL-3 is **not** read under the TRAIN Fold A margins. `h_SLU 1.2485` / `h_intent 0.9943` were
measured on a different roster, against a different gold split (TRAIN versus devel), with a
different scorer sibling (`slurp-slu-official-train` versus `slurp-slu-official`) and a different
clustering (whole speaker versus utterance id).

So this package registers **cell PLANr-DEV2000** (`SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-V1`):
the request-identical second pass of cell B6's plan arm, differing from it only by its run, attempt
and native-contact-fit identities. It flies FIRST, its margin table
(`SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-OWN-NULL-V1`) is sealed BEFORE the arm's contrast
stage is read, and the margins are never adjusted after the arm's numbers are seen. Precedent: cell
PLANr on Fold A (`docs/results/2026-09-22-slurp-planr-v2-lock-replicate-verdict.md`).

PLANr-DEV2000 registers **no smoke**, following cell B6's own `why_no_smoke` rule: a
request-identical replicate of a form already sealed and flown on this exact roster raises no
structural question a four-row flight would answer.

## The cells

| role | run id | fit run id | rows |
| --- | --- | --- | ---: |
| own null | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-V1` | `...-REPLICATE-FIT-V1` | 1000 |
| arm | `SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-V1` | `...-GATE-FIT-V1` | 1000 |
| twin | `SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-TWIN-V1` | `...-GATE-TWIN-FIT-V1` | 1000 |
| arm smoke | `SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-SMOKE-4-V1` | `...-GATE-SMOKE-4-FIT-V1` | 4 |
| twin smoke | `SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-SMOKE-4-TWIN-V1` | `...-GATE-SMOKE-4-TWIN-FIT-V1` | 4 |

**TEN flight run ids**, not twelve: PLANr-DEV2000 carries no smoke. Three further ids are
model-free-check READS and are never flown — the own-null read, the arm paired analysis and the twin
paired analysis. The coordinator's decision receipt
`coordination/slurp-stage3-delta-cell-r03-gate-v1/root-admission-v1.json` (decision id
`slurp-stage3-delta-cell-r03-gate-admission-v1`) lists the ten.

Composed and protocol hashes of all ten cells: `protocol-registered-v1.json`, `cells` and
`fit_only_cells`.

## What moved, and only what moved

Against cell CELL-2's fragments, exactly two mechanism changes (the removed Perception route, the
gate on the three candidate-bound routes) plus the **roster re-pointing cell B6 already proved on
this venue**, key for key:

1. `knowledge_stores.intent-boundaries.phase_supply.perception.query_source`
2. `knowledge_stores.train-exemplars.phase_supply.solver.query_source`
3. `preparation_source_receipts` (alias swapped; the DEV-2000-ADDED encode receipt and the roster
   receipt added)
4. `scorers` — `slurp-slu-official-train` → `slurp-slu-official`, the devel gold scorer
5. `speech_packet_promotion_receipt` and `speech_packet_promotion_receipt_sha256`
6. `native_contact_fit` (run id, attempt id, `contact_cap` 47,520 → 44,000)
7. in the experiment fragment: `dataset_fragment`, `population.count`,
   `population.split_identity_hash`, `split_id`, `split_role`

`native_episode`, `phase_material`, `policy`, the other three knowledge-store releases and
snapshots, the geometry and the E13/E22 declarations stay byte-identical to cell B6's plan arm. All
six DEV-2000-ADDED and store pins were **verified against the bytes on disk** by the generator, not
typed.

## The store, and what this cell can reach of it

| | v2 (CELL-2 and CELL-3 both pin it) |
| --- | ---: |
| values | 200 |
| perception / solver / reviewer / planner | 80 / 76 / 40 / 4 |
| distinct facets / facet entries | 26 / 219 |
| source sample ids | 136 |
| authored token count (twin holds it) | 3,001 |
| twin value fixed points | 13 of 200 |

**80 of the 200 values are unreachable in CELL-3 by construction**: they are perception-targeted and
the Perception route is removed. That is a second change against CELL-2 beside the gate; it is
registered here, and the read must not attribute the whole arm-minus-CELL-2 difference to gating.

Store pins (read off disk): release `b81df5c5…`, snapshot **content** hash `44a80418…`; twin release
`b18b141f…`, snapshot content hash `13180912…`. The snapshot pin is always the CONTENT hash, never
the `snapshot.json` file digest.

## The gate's reach on this roster, projected model-free

From the sealed comparator's own Perception candidates, projected with the route's own rule: **355
of 1,000 rows CLOSED, 645 OPEN** (35.5 %), on every gated node. Projected majority-scenario
histogram: play 164, calendar 160, qa 142, email 80, weather 63, iot 61, transport 59, lists 49,
music 42, recommendation 41, general 38, audio 30, news 23, alarm 21, datetime 16, social 6,
cooking 3, takeaway 2.

This is a **projection, not a measurement of this cell**. CELL-3's Perception request is
byte-identical to the comparator's for the same row, so it is close — but greedy decoding is not
bit-reproducible across batch compositions, so the realised share is measured by the consumption
read and never assumed. A realised share far from 355 is a finding, not a failure.

Note the asymmetry registered before contact: **`alarm` and `music` carry zero gold rows on this
roster**, yet the projection gates 21 and 42 rows on those predicted labels. The gate reads a
predicted label; the roster's gold does not carry those strata at all.

## The four-row smokes

Cell B6 registered no smoke on this roster, so this package **defines** the population rather than
inheriting one: the **first two gate-CLOSED and the first two gate-OPEN rows of DEV-2000-ADDED in
the roster's own order**, decided model-free from the sealed comparator's own Perception candidate
labels. Deterministic, zero contacts, labels only.

| row | roster position | projected majority | gate |
| --- | ---: | --- | --- |
| `slurp:devel:000017:audio-1501773854-headset` | 1 | `iot` | CLOSED |
| `slurp:devel:000024:audio-1490195864-headset` | 2 | `iot` | CLOSED |
| `slurp:devel:000099:audio-1501754782` | 8 | `weather` | OPEN |
| `slurp:devel:000217:audio-1490367363` | 14 | `weather` | OPEN |

Smoke split identity `2cca58464272bfce1ba80828f7efe9955367ad78ab0ac3d85d4d6b3fe2ed8d58`
(recomputed by `data.splits.split_identity_hash` over the carrier-prefixed ids; the same function
reproduces the TRAIN smoke's `4e3413fe…` and the full roster's `ee6c43cd…` as controls), 9.215312 s
of audio.

Offline dry run over both forms: `dry-run-v1.md`. **Both PASS**, zero defects — the two `iot` rows
close all three gates and supply nothing, the two `weather` rows open all three, and the two tie
walks disagree.

## The read

`analysis-recipe-v1.json`. The driver is **`scripts/analysis/slurp_paired_roster_read.py`** — the
one cell B6 proved on this roster, with this scorer and this clustering — plus
`scripts/analysis/stage3_delta_consumption_read.py` for the gate and consumption tables.

**`scripts/analysis/plan_cell_read.py` cannot read this cell as committed.** Its `SCORER`,
`V3_SCORER` and `SYM_SCORER` are module constants bound to the TRAIN gold siblings with no override
flag; its `lock` stage compares against a TRAIN-only B5e comparator; and its per-scenario stages
need a roster-metadata file carrying a per-sample speaker and scenario that this roster does not
publish. Adapting it is a separate engineering change with its own tests and its own review — not
something a registration agent does, and not beside a live flight. This is recorded as an open item
rather than worked around.

Two further honest limits of this venue, both registered before contact:

- **No gold per-scenario table.** The roster receipt withholds the per-item stratum
  (`stratum_withheld_per_item: true`) and the official per-sample record carries no scenario field;
  deriving one needs gold, which is refused. Cell B6's own read records the same and names it an
  open registration item. What IS reported, in both weightings, is the table over the **predicted
  majority candidate scenario** — exactly what the gate reads, and model-free by construction —
  plus the two-cell gate-closed / gate-open stratification.
- **No projection-v3 or TRAIN-symmetric companion.** Those scorer siblings are TRAIN-gold; they are
  not reported against devel gold. Their absence is stated in the verdict.

The driver always writes status `DESCRIPTIVE`; the ADMITTED / NEUTRAL / HARMFUL decision rule of
`protocol-registered-v1.json` is applied **by the coordinator** in the verdict document, against the
margins the own-null read produced, showing the arithmetic.

## The proofs on the committed tree

- Offline gates, all exit 0: `engineering_base_check.py`, `harness_admission_check.py`,
  `results_ledger_check.py`, `tool_catalog_check.py`, `experiment_handoff_check.py`,
  `finite_completion_policy_check.py`, `stage3_algorithm_label_check.py` and
  `derived_media_confinement_check.py`.
- The composed config and protocol hashes of all ten cells, computed offline by
  `core.config.compose` and `core.config.protocol_hash`: `protocol-registered-v1.json`.
- The offline four-row native-episode dry run on both forms: `dry-run-v1.md`.
- `tests/unit/test_slurp_cell3_gate_registration.py`: the five baselines equal cell B6's plan
  fragment on every key except `knowledge_stores.stage3-deltas` and the per-flight bookkeeping keys,
  and PLANr-DEV2000 equals it on every key except the fit identities and `what_this_is`.

**`core.flight.cli check` was NOT run** and no prompt-fit bound is claimed as measured. That check
needs the coordinator's clean-tree cycle against the minted receipt. What this package registers
instead is the EXPECTATION: ALLOW on every phase, because CELL-3 removes the Perception block
entirely and withholds the Solver block on a projected 35.5 % of rows, where CELL-2's measured bound
sat at `COMPACT_REQUIRED` by 317 tokens on the Solver with both present. A `COMPACT_REQUIRED` here
would be a surprise worth reporting.

## What is registered here

Ten plan documents (`{planr-,,twin-,smoke-,twin-smoke-}{generation,fit}-plan-registered-v1.json`),
`protocol-registered-v1.json`, `registered-facts-v1.json`, `analysis-recipe-v1.json` and
`dry-run-v1.md` in this directory; outside it the preregistration note, five baseline fragments,
three experiment fragments, three campaign plans, thirteen unconsumed DRAFT exposure rows and the
runbooks `cell3_repin_{planr,smoke,twin_smoke,arm,twin}.sh`, `cell3_flip_all.sh`,
`batch_chain_cell3.sh`, `cell3_read.sh` and `cell3_dry_run.py`.

## The order the coordinator flies

1. mint `coordination/slurp-stage3-delta-cell-r03-gate-v1/root-admission-v1.json`, rewrite its
   `eligible_run_ids` to the ten and its budget caps to this family's;
2. `cell3_flip_all.sh` — five re-pin cycles (PLANr, arm smoke, twin smoke, arm, twin);
3. `batch_chain_cell3.sh` — three steps: **PLANr-DEV2000 first** (no smoke), then the arm with its
   smoke, then the twin with its smoke;
4. `cell3_read.sh own-null` — the margin table, sealed before anything else is read;
5. `cell3_read.sh arm`, then the consumption read, then `cell3_read.sh twin`;
6. the verdict document, applying the registered decision rule against those margins.

## The lessons this package carries forward

1. **A recovery needs two new identities.** The fit gate binds the baseline's
   `native_contact_fit.attempt_id` and refuses an identity that already carries evidence. Every
   `failure_policy` here says a recovery re-registration needs a new generation attempt id AND a new
   fit attempt id.
2. **A sealed identity is never re-pointed.** CELL-3 is a sibling fragment set; CELL-1's, CELL-2's
   and CELL-1-GEPA's fragments are untouched.
3. **`check` does not walk the episode.** The four-row offline dry run over the real released stores,
   on the candidates the sealed comparator actually produced, is a precondition of the smoke.
4. **A margin is a property of a roster, not of a mechanism.** Importing Fold A's own null onto a
   devel roster would import a different gold split, scorer sibling and clustering. Hence
   PLANr-DEV2000.
5. **An aborted campaign leaves `locks/flight.lock`.** Clear it before the next launch.
