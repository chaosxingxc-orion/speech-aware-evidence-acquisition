# Cell CELL-3: the coverage-gated `stage3-deltas-v2` store on DEV-2000-ADDED: preregistration

Registered **before contact**, 2026-09-24, from worktree `/home/chao/saea-worktrees/fable-cell3reg`
(branch `fable/cell3reg`, base `master` `060d822c`). Every cell in this package is `held`. Nothing
was flown, flipped, scored, minted or claimed to produce it: zero model, tokenizer, encoder, scorer,
server, GPU and network contacts.

Package: `docs/readiness/2026-09-24-slurp-stage3-delta-cell-r03-gate-v1/`. Mechanism design note:
`docs/readiness/2026-09-24-slurp-stage3-scenario-gate-design-v1.md`. Governing decisions: owner 83,
99, 101, 106, **110 (PENDING)**, plus 17, 25, 28, 29, 58, 75, 79 and 86.

## 1. Why this cell exists

`docs/results/2026-09-24-slurp-stage3-delta-cell-r02-verdict.md` read CELL-2 on TRAIN Fold A as
NEUTRAL by width: official pooled SLU-F1 +0.64 pp (CI95 [−0.76, +1.92]) and intent −0.09 pp (CI95
[−1.22, +0.96]), with non-inferiority on intent unproven by 0.23 pp. Underneath that flat number the
per-scenario table is not flat at all: the arm gains on `audio` (+14.5), `weather` (+9.7) and
`email` (+3.5) and loses on `general` (−10.6), `alarm` (−3.6), `music` (−3.4), `social` (−3.1),
`iot` (−0.9), `play` (−0.6) and `news` (−0.5).

`docs/results/2026-09-24-slurp-general-scenario-diagnostic.md` then established the shape of the
loss: on the 60 `general` rows the **derangement twin loses more than the arm** (intent −11.67 pp
twin versus −6.67 CELL-2 and −10.00 CELL-1), and **0 of the 200 values declare a `general` target**.
A loss the twin reproduces is a FORM cost of *carrying* a supply, not the content of any delta. And
where the store does have reach, CELL-2's arm-minus-twin column is positive: news +7.4, alarm +4.2,
qa +4.2, weather +4.1 pp SLU.

So the iteration-3 lever is neither a better statement nor a better ranking. It is **application**:
do not carry the supply into a row where the store cannot pay for its own form cost.

The amount at stake is small and stated up front — 10.00 pp intent and 11.16 pp pooled SLU-F1 on the
60 `general` rows, i.e. 0.56 pp and 0.24 pp at Fold A grain — which is exactly why the mechanism
must cost nothing where it does not fire.

## 2. The factor and the arms

One factor on cell B6's plan arm (`configs/baseline/slurp-native-default-plan-dev2000-added-baseline-v1.json`),
which is the locked v2.0 default plan as it flew on DEV-2000-ADDED:

`knowledge_stores.stage3-deltas` — the released `stage3-deltas-v2` store (200 values, the
owner-decision-83 retention of v1r's 379), supplied per node through `context_supply`:

| node | cap | provider | gated |
| --- | ---: | --- | --- |
| solver | 8 | `stage3-delta-candidate-bound-v1` | yes |
| reviewer | 4 | `stage3-delta-candidate-bound-v1` | yes |
| planner | 4 | `stage3-delta-candidate-bound-v1` | yes |
| perception | — | **route REMOVED** | — |

The gate, on each of the three candidate-bound routes:

```json
"scenario_gate": {
  "policy": "majority-candidate-scenario-not-in-v1",
  "scenarios": ["general", "alarm", "music", "social", "iot", "play", "news"]
}
```

It reads the SAME projected Perception candidate list the route already reads — after the bounded
first-occurrence projection at three candidates, before any store lookup — and nothing else. Only
the sealed Perception state of the same episode: no gold, no reference, no scorer, no future turn,
no other row. The scenario of an intent is the part before the first underscore
(`rails.stage3_delta_supply.scenario_of_intent`); the majority is most-frequent, not
strictly-more-than-half, with ties broken by earliest first occurrence. CLOSED exactly when the
candidate list is non-empty and the majority scenario is one the gate names; a closed gate returns
`None`, so the node takes no supply step at all. An open gate changes nothing —
`tests/unit/test_stage3_scenario_gate.py::test_an_open_gate_is_byte_identical_to_the_ungated_route`.

**Perception is not gated, it is removed.** It is the node that produces the candidate list, so at
the moment it is served there is nothing to gate on, and the unconditional route's validator keyset
is an equality, so a `scenario_gate` there is refused by construction. A cell that wants the
Perception deltas withheld omits the route, which is what this one does.

**That is a SECOND change against CELL-2 beside the gate, and it is declared here as such**: 80 of
the 200 values are perception-targeted and are therefore unreachable in CELL-3 by construction. The
read must not attribute the whole CELL-3-minus-CELL-2 difference to gating.

Twin arm: the same cell with the store pinned to `stage3-deltas-twin-v2` (seed 20260922, 200
statements, authored token count 3,001 held, 13 arithmetic fixed points) and **the same gate**. It
isolates what the gated supply's form costs and pays on exactly the rows the gate leaves open. It
decides attribution, never admission.

### 2a. The algorithm label

`tfgrpo-semantic-advantage-v1`, operators `update` + `context_application`. The store was produced
by that algorithm's UPDATE operator over the sealed ROLL-1 advantage outputs; iteration 3 changes
the CONTEXT_APPLICATION operator and nothing else. Both are registered for this algorithm in
`core.base.STAGE3_ALGORITHMS`, so unlike the GEPA record there is no operator this cell must decline
to declare.

## 3. The venue, and why it is the point

**This is the FIRST out-of-fold read of the Stage-3 delta line.** CELL-1, CELL-2 and CELL-1-GEPA
were all read on TRAIN Fold A — the roster whose own read chose what the store retains and, in this
cell, which seven strata the gate names. DEV-2000-ADDED is a roster the delta line has never
touched (1,000 devel recordings, 913 distinct utterances, flown exactly twice by cell B6's direct
and plan arms and never re-flown). Owner decision 99 names a fresh roster as the replicate venue,
and CELL-2's own verdict names it as the precondition of any effectiveness claim.

**Stated plainly as a limitation, not hidden:** the gated set was chosen on TRAIN Fold A by reading
CELL-2's per-scenario table there. It is a judgement made on one roster and read on another. Two of
the seven gated scenarios — `alarm` and `music` — carry ZERO gold rows on DEV-2000-ADDED, yet the
model-free projection gates 21 and 42 rows on those PREDICTED labels; the gate reads a predicted
label the roster's gold does not carry at all. Also, `qa` (−0.893) and `lists` (−0.288) lost on Fold
A and are NOT gated: the seven are the set the general-scenario diagnostic named, reproduced here
rather than re-derived from a threshold.

And what it does not buy: DEV-2000-ADDED is a **development** roster (owner decisions 28, 86). No
test claim, no superiority claim, no generalisation claim, no paper-scale claim. Owner decision 29
allows one test read, after Stage 3, and it is not this one.

## 4. Decision rule (fixed here)

Delta = CELL-3 minus the sealed DEV-2000-ADDED PLAN arm
(`SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1`, official 65.40 SLU / 76.6 intent, flight commit
`54f569c6`), in percentage points. Nothing of the comparator is re-flown or re-scored.

- **ADMITTED** — the CI95 lower bound of the paired **official pooled SLU-F1** delta is **above
  zero** AND the CI95 lower bound of the paired **intent** delta exceeds **−h_intent**. A gain is
  proven, not merely non-inferior.
- **NEUTRAL** — both guards non-inferior at the roster's own null (SLU lower bound above −h_SLU,
  intent lower bound above −h_intent) without a proven SLU gain.
- **HARMFUL** — a **measured** loss on either guard (owner decision 25, Method B: a CI95 upper bound
  below zero, or a point estimate beyond the margin). Width alone is NEUTRAL, never HARMFUL.
- **TWIN = attribution, never admission.** A gain the twin reproduces within the roster's own null
  is FORM — the gated supply's shape and token volume on the rows the gate leaves open — not
  content, and the verdict says so and claims no content effect. A gain the twin does not reproduce
  is attributed to the deltas' content, with the twin delta reported beside it.
- **Replication** — an ADMITTED result is replicated on the SAME roster before any Fold B or test
  read. No such read is authorised by this package.

### 4a. The margins are NOT known at registration, and that is deliberate

`h_SLU` and `h_intent` are **not typed anywhere in this package**. They are the half-widths the
roster's own null produces: cell **PLANr-DEV2000**
(`SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-V1`), the request-identical second pass of
cell B6's plan arm registered here and flown FIRST, read as
`SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-OWN-NULL-V1` with the same paired estimator, the same
utterance-id clustering, the same seed and the same draws as the arm contrast.

The TRAIN Fold A numbers **h_SLU 1.2485 / h_intent 0.9943 are context only and are explicitly NOT
this cell's bar**: they were measured on a different roster, against a different gold split (TRAIN
versus devel), with a different scorer sibling (`slurp-slu-official-train` versus
`slurp-slu-official`) and a different clustering (whole speaker versus utterance id).

**The ORDER is part of the registration.** The own-null read completes and its margin table seals
BEFORE the arm's contrast stage is read, and the margins are never adjusted after the arm's numbers
are seen. A replicate that fails its stop stage produces no margin and the family halts.

Greedy decoding at temperature 0 is not bit-reproducible across batch compositions (the 2026-09-04
finding), which is why the second pass is flown rather than assumed.

### 4b. Primary deliverables, reported whatever the verdict

1. the paired official read of the arm against the sealed comparator at the roster's own null;
2. the margin table from PLANr-DEV2000, printed first;
3. **the GATE table**: open/closed decisions per node over the 1,000 rows, the realised gated-row
   share, the realised majority-scenario histogram, and the share of rows on which all three nodes
   closed together (the gate reads one candidate list, so they should agree on every row; a
   disagreement is a defect to report) — all beside the model-free projection of **355 closed / 645
   open**;
4. the per-node delta-consumption table split by gate outcome (item S3-4s), value ids and counts
   only;
5. the twin contrast;
6. the frontier row per **1,000** rows (owner decision 75) — a Fold A frontier row uses 1,080 and is
   not comparable digit for digit, so it is rescaled or labelled, never silently placed beside.

### 4c. What the per-stratum table can and cannot be on this roster

A **gold** per-scenario table is NOT derivable model-free here: the roster receipt withholds the
per-item stratum (`stratum_withheld_per_item: true`) and the official per-sample record carries no
scenario field, so deriving one needs gold, which is refused. Cell B6's own read
(`docs/results/2026-09-22-slurp-b6-dev2000-added-direct-vs-plan-read.md`, section 1) records the
same and names it an open registration item.

What IS reported, in both the natural-mixture and the equal-stratum weighting, is the table over the
**predicted majority candidate scenario** — exactly what the gate reads, model-free by construction
— plus the two-cell gate-closed / gate-open stratification and the per-channel table (540
far-field, 460 headset). The absence of the gold table is stated in the verdict, never omitted.
Likewise the projection-v3 and symmetric-normalised companions: those scorer siblings are TRAIN-gold
and are not reported against devel gold.

## 5. Prompt fit

NOT MEASURED IN THIS REGISTRATION. `core.flight.cli check`'s `_assess_prompt_budget` is the
measurement and it runs in the coordinator's clean-tree cycle against the minted receipt; `check`
was deliberately not run here.

The registered EXPECTATION is **ALLOW on every phase**. CELL-2's measured bound on TRAIN Fold A put
the Solver at `COMPACT_REQUIRED` by 317 tokens (required window 21,821 against a 24,576-token slot
with a 3,072-token reserve) with the Perception block present and the Solver block on every row.
CELL-3 removes the Perception block entirely and withholds the Solver block on a projected 35.5 % of
rows, so its worst case is CELL-2's minus the Perception contribution. A `COMPACT_REQUIRED` here
would be a surprise worth reporting, and a non-zero compacted-row count is a caveat on the frontier
row's token basis. An abstention caused by compaction is a failure, not a caveat.

## 6. Budgets

| | arm / twin / PLANr | four-row smoke |
| --- | ---: | ---: |
| generation calls cap | 11,000 | 44 |
| fit endpoint calls cap | 44,000 | 176 |
| repeated speech seconds cap | 32,819 | 102 |
| GPU hours (fit inclusive) | 12.0 | 1.0 |
| native task-contract calls cap | 6,000 | 24 |
| official complete scoring jobs | 1 | 0 |

11,000 = 1,000 rows × 11, the locked plan's own per-row contact ceiling (role graph perception 1 /
solver 1 / reviewer 3 / planner 1 with `max_revisions` 1, i.e. 1 + 2 × (3 + 1 + 1)) — the exact
program maximum, not a safety bound. 44,000 = 11,000 × (1 speech packet + 3 endpoints). 32,819 s =
the roster's 2,983.527 s × 11. The smoke's 102 s = 9.215312 s × 11, rounded up.

Cell B6's plan arm realised 4,071 contacts (4.071 per row) and 1.655 GPU hours per 1,000 rows on
this exact roster. CELL-2 cost +1.3 % contacts and +0.6 % GPU-h against its own base on Fold A;
CELL-3 should cost less than that, because it removes the Perception block and withholds the rest on
a projected 35.5 % of rows. **An estimate, never a target. Ceilings are bounds; unused budget is not
attempt authority; the plan budget is run-cumulative across every attempt of a run id.**

## 7. Boundary

- No gold label, reference transcript, delivered answer or future turn enters runtime. The gate in
  particular reads only the sealed Perception state of the same episode.
- The store's `source_sample_ids` are 136 R01C construction utterances, all TRAIN; none is a
  DEV-2000-ADDED recording.
- TRAIN Fold A, TRAIN Fold B, DEV-1000 and the test split stay untouched and unread.
- No new speech identity is opened and no packet is promoted: DEV-2000-ADDED's packets are the ones
  cell B6 already flew.
- Attach only to the resident session `serving-slurp-native-candidate-five-train-a-np4-v1`; never
  spawn, stop or reconfigure it. A geometry change would end the request-identity of the comparator.
- No native tool authority on any role; `tools` is absent on every request and the realised native
  task-contract call count is expected 0 against the 6,000 ceiling.

## 8. Registered hashes

Composed config and protocol hashes, computed offline by `core.config.compose` and
`core.config.protocol_hash` from the committed fragments:

| cell | composed config hash | protocol hash |
| --- | --- | --- |
| `slurp-native-default-plan-dev2000-added-replicate-v1` | `7e8ef09633a8c77785d45011dfc50b6a74245a2cfd7b894e115ccf16869c7944` | `075bf598a48ea20ca90a200d925cc22efe55289b479b84170be66677439f83e3` |
| `slurp-native-default-plan-dev2000-added-replicate-fit-v1` | `83e68035…` | `c16d649e…` |
| `slurp-native-stage3-delta-cell-r03-gate-v1` | `888965b78137eec271563423daa2b081ed4391f63f55f966bd2ceccf4c9f1188` | `16b4fca4fdf2b4a2c3b33c77a46a155e1e17dd0b0fb6acd0389eb5952e161d1f` |
| `slurp-native-stage3-delta-cell-r03-gate-fit-v1` | `7c8db497…` | `abd0091c…` |
| `slurp-native-stage3-delta-cell-r03-gate-twin-v1` | `5c164ce37d4473c98b2745ed39d18547a2a2f6c964bdedc85d48830f54979673` | `27bd2f9df1bf9c3f340d32f7defbc81561fa857420f1df22a59ba2b6b0c6d956` |
| `slurp-native-stage3-delta-cell-r03-gate-twin-fit-v1` | `9790943f…` | `5c0377b9…` |
| `slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1` | `4c4adb3c42db169e9d36a9456e75f19a80b806b45c903f7e31ad208fd94f0281` | `eb238669fc8711a2972a1a6ffe91736a4224ec96ceb33a2519605cf2cd73cee3` |
| `slurp-native-stage3-delta-cell-r03-gate-smoke-4-fit-v1` | `a934df73…` | `295085a6…` |
| `slurp-native-stage3-delta-cell-r03-gate-smoke-4-twin-v1` | `351ece33900cef90300532d09b7aa8e22a3ab284009c8f36ef76dc0019a7be5a` | `4b7a4d6c4bdb48203254c9b4f4355344722e2b2abd63ab0c8ff05175d3669a36` |
| `slurp-native-stage3-delta-cell-r03-gate-smoke-4-twin-fit-v1` | `688b0e5a…` | `ecdd7b65…` |

Split identities: `ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67` (the 1,000-row
roster) and `2cca58464272bfce1ba80828f7efe9955367ad78ab0ac3d85d4d6b3fe2ed8d58` (the four smoke
rows). Both recomputed by `data.splits.split_identity_hash` over the carrier-prefixed ids; the same
call reproduces the TRAIN smoke's `4e3413fe…` as a control.

Store pins, all read off the bytes on disk by the generator: arm release
`b81df5c5175e45e68933d4875c110fd46bea933283631d2c428187c480fc31f0`, arm snapshot CONTENT hash
`44a804184cf83a08e85831d40bae942af1e71ed4365b485d833f9a03807ef150`; twin release
`b18b141f67dae4b413391d22dd787a3b85480d2b4fab24db0848e547e7aa1a9a`, twin snapshot CONTENT hash
`131809122d23ccdaac86c9a9426c5e045a9544fc3059c1b46f80a3365151d614`. The snapshot pin is always the
CONTENT hash, never the `snapshot.json` file digest.

Protocol document `docs/readiness/2026-09-24-slurp-stage3-delta-cell-r03-gate-v1/protocol-registered-v1.json`,
sha256 `5d998917ec02d124023c86b93b17ecfae4eddfcba68b8cbc941cf6f6bfe16d7a`, pinned by all ten plan
documents.

## 9. What is registered, and what this registration does NOT authorise

Registered: five baseline fragments, three experiment fragments, three campaign plans, ten plan
documents, the protocol document, the registered facts, the analysis recipe, the dry-run record,
this note, thirteen unconsumed DRAFT exposure rows, and the runbooks
`cell3_repin_{planr,smoke,twin_smoke,arm,twin}.sh`, `cell3_flip_all.sh`, `batch_chain_cell3.sh`,
`cell3_read.sh` and `cell3_dry_run.py`.

NOT authorised by this registration:

- no readiness flip — all ten flight cells stay `held` until the coordinator mints the root decision
  receipt and runs `scripts/flights/repin_cell.py --set-ready`;
- no model, tokenizer, encoder, scorer, server, GPU or network contact of any kind;
- no `core.flight.cli check` (it needs the coordinator's clean-tree cycle) and no prompt-fit bound
  claimed as measured;
- no test read, no Fold B read, no DEV-1000 read;
- no re-fly or re-scoring of the sealed comparator;
- no new store release and no retirement of any value;
- **no change to the gated scenario set, and no adjustment of `h_SLU` or `h_intent`, after the arm's
  numbers are seen**;
- no paper-scale work of any kind.

### 9a. The run-id count is TEN, not twelve

The family is: PLANr-DEV2000 (generation + fit), the arm (generation + fit), the twin (generation +
fit), the arm smoke (generation + fit) and the twin smoke (generation + fit). **PLANr-DEV2000
carries no smoke**, following cell B6's own `why_no_smoke` rule — a request-identical replicate of a
form already sealed and flown on this exact roster raises no structural question a four-row flight
would answer. Three further ids are model-free-check READS and are never flown:
`SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-OWN-NULL-V1`,
`SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-PAIRED-ANALYSIS-V1` and
`SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-TWIN-PAIRED-ANALYSIS-V1`. The decision receipt's
`eligible_run_ids` therefore lists **ten**.

### 9b. The read driver, recorded as an open item rather than worked around

`scripts/analysis/plan_cell_read.py` — the driver every TRAIN Fold A delta cell used — **cannot read
this cell as committed**. Its `SCORER`, `V3_SCORER` and `SYM_SCORER` are module constants bound to
the TRAIN gold siblings with no override flag; its `lock` stage compares against a TRAIN-only B5e
comparator; and its per-scenario stages need a roster-metadata file carrying a per-sample speaker
and scenario that DEV-2000-ADDED does not publish. This package therefore registers
`scripts/analysis/slurp_paired_roster_read.py` — the driver cell B6 proved on this exact roster,
with this scorer (`--scorer-id slurp-slu-official`) and this clustering (`--cluster-key
utterance_id`) as its own defaults — plus `scripts/analysis/stage3_delta_consumption_read.py`
(`--scorer slurp-slu-official` MUST be passed; its module default is the TRAIN sibling) for the gate
and consumption tables. That driver always writes status `DESCRIPTIVE` and computes no verdict, so
the decision rule of section 4 is applied by the coordinator in the verdict document, showing the
arithmetic. Adapting `plan_cell_read.py` to a devel roster is a separate engineering change with its
own tests and its own review; a registration agent does not make it, and not beside a live flight.

## 10. The coordinator's sequence

0. Clear `locks/flight.lock` if an earlier campaign left one.
1. Mint `coordination/slurp-stage3-delta-cell-r03-gate-v1/root-admission-v1.json` (decision id
   `slurp-stage3-delta-cell-r03-gate-admission-v1`) with
   `scripts/flights/batch/mint_decision_receipt.py`, then rewrite its `eligible_run_ids` to the ten
   run ids of section 9a and its budget caps to section 6's. Without that rewrite
   `core.flight.campaign.declared_readiness` refuses every cell but the first
   ("run … is not eligible in decision receipt").
2. `bash scripts/flights/batch/cell3_flip_all.sh` — five re-pin cycles in order: PLANr, arm smoke,
   twin smoke, arm, twin. Each mints that cell's OWN `prepared_phase_supply` under its own run id
   (item E16) and inserts the matching `preparation` requirement. **`--allow-output-change` must
   never be passed.** PLANr-DEV2000's prepared artifact MUST reproduce cell B6's
   `36463545fa791723c2adee82db9fb8c78420c72d0ebc07d4ec179cc0ddb2e179` exactly; a different value
   means the knowledge channel moved and the replicate is not a replicate — stop and report.
3. `bash scripts/flights/batch/batch_chain_cell3.sh` — three steps through the SAEA-Batch-Driver
   scheduled task (owner decision 77): **PLANr-DEV2000 first** (no smoke), then the arm with its
   smoke, then the twin with its smoke. The chain reads the flight commit from
   `/home/chao/cell3-flight-commit.txt`.
4. `bash scripts/flights/batch/cell3_read.sh own-null` — the margin table, sealed before anything
   else is read.
5. `bash scripts/flights/batch/cell3_read.sh arm`, then the consumption read, then
   `bash scripts/flights/batch/cell3_read.sh twin`.
6. The verdict document `docs/results/<date>-slurp-stage3-delta-cell-r03-gate-verdict.md`, applying
   section 4's rule against the margins of step 4, with the gate table, the per-stratum tables in
   both weightings, the arm-minus-twin line and the frontier row.
