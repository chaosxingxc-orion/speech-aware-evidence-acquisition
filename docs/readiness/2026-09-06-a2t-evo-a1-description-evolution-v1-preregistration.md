# EVO-A1: description evolution on Audio2Tool — preregistration (DRAFT)

**Status: DRAFT.** This document is complete but unregistered. The coordinator closes it by (1)
naming `A_0` with its sha256 -- KC-A1 is VOID rather than pending, so unless the +40-token cap is
re-priced the answer is the released compact registry (section 3), (2) ratifying the STRICT or the
RELAXED target set, (3) naming the curve roster, and (4) writing the exposure rows. Track E3c, the
proposer runner, is no longer among them: it is landed (section 15 item 8), and the four
registration facts it surfaced are open point 8. Nothing here authorizes a contact.

Cell EVO-A1 of `docs/readiness/2026-09-05-three-dimension-experiment-program.md` (section 4c, loop
constants section 5). Model-free prerequisites already closed:

| prerequisite | receipt |
|---|---|
| MF-1, the query-cue audit and the TARGET list | `docs/readiness/2026-09-05-a2t-query-cue-audit-v1.md` |
| construction capacity, `SAEA-A2T-MF-EVO-CONSTRUCTION-CAPACITY-V1` | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-construction-capacity/` |
| the three loop rosters, `SAEA-SN-MF-A2T-EVO-FOLD-ROSTERS-V1` | `docs/receipts/rosters/a2t-evo-fold-{a,b}-v1.json`, `a2t-evo-exemplars-v1.json` |

---

## 1. Hypothesis

**H1.** A frozen speech-capable core, shown only its own registry rows and block-disjoint
construction exemplars with their gold calls, can write tool descriptions that separate a confusable
pair better than the released ones, and a best-of-K selection over four rounds — scored by the
official scorer on held-out construction rows and never on evaluation data — produces a registry
whose gain survives one read on the sealed 4,000.

**H2 (the control that decides what H1 means).** The deterministic control, which appends only the
registry's own `domain` and `category`, is the floor: a round whose proposer does not beat it has
learned nothing the registry already carried. The round-1 length-matched placebo is the second
floor: if it is indistinguishable from the proposer candidate, the effect is form, not content.

**The ceiling is stated before takeoff and it is small.** The capacity census puts **67 of MF-1's
235 addressable misses** inside targets the loop can actually be rewarded on — an arithmetic
maximum of **+1.68 pp** on the 4,000 if every addressable row were recovered, against a 61.40 %
pooled baseline. Under the RELAXED reading it is 90 rows and +2.25 pp. EVO-A1 is therefore a test of
whether the loop mechanism works at all, on the mass the corpus can supply; it is not a bid for the
lighting cluster, which the corpus cannot support (section 2).

## 2. Targets

`configs/knowledge/a2t-kc-a1/targets-v1.json` names MF-1's five disjoint targets over 23 tools. The
census applied section 5's own row requirement — `quota_A = quota_B = min(20, floor((units - 8) / 2))`,
dropped below 6, lowered to what a whole-block split can deliver — and four tools cannot supply
reward rows at all: `setAmbientLighting` (9 construction units), `calibrateCameras` (7),
`setBrightness` (18, quota 4 after block indivisibility) and `setRomanceMode` (10).

| target | tools | dominant pair | mass | intact? | addressable |
|---|---:|---|---:|---|---:|
| lighting | 8 | `setColor+setColorTemperature+setLighting` / `setAmbientLighting` | 88 | **no** | 18 |
| **activateRoutine** | 5 | `activateScene` / `activateRoutine` | 15 | yes | **44** |
| **getBiometricData** | 4 (3 alive) | `getBiometricData` / `getHRV` | 13 | yes | **18** |
| calibrateCameras | 4 | `calibrateCameras` / `updateFirmware` | 6 | **no** | 5 |
| **castContent** | 2 | `castContent` / `playMedia` | 5 | yes | **5** |

**STRICT (proposed): three targets, ten tools, 67 rows.**

* `activateRoutine` — `activateRoutine`, `activateScene`, `setApplianceMode`, `setSecurityMode`,
  `startCleaning`
* `getBiometricData` — `getBiometricData`, `getHRV`, `setHapticStrength` (`setRomanceMode` dropped)
* `castContent` — `castContent`, `playMedia`

**RELAXED (open point 3): five targets, nineteen tools, 90 rows** — adds lighting reduced to
`getLightState`, `resetFilterStatus`, `setColor`, `setColorTemperature`, `setGroupLightState`,
`setLighting` (its one intact pair `setGroupLightState` / `setLighting`, 18 rows) and
calibrateCameras reduced to `rebootDevice`, `streamCamera`, `updateFirmware` (5 rows). **No fresh
draw is needed either way**: both folds already carry all eighteen fold-capable tools.

`getLightState` has fold quota 0 — not from the census (which gave it 9) but from block contention:
its three shared blocks went to the block-poorer `playMedia`. It sits in no intact pair under either
reading, so no addressable mass is lost. A RELAXED lighting target therefore flies with five
reward-bearing tools and `getLightState` as a description-only member.

## 3. State, and `A_0`

`A_r` is a mapping from a **targeted** tool name to a replacement `description`, and nothing else.
Rendering is always `data.audio2tool_tools.render_registry_compact(description_overrides=...)`
through the registered `evolved-artifact-v1` fill: the same 152 lines, the same
`- {signature}: {description}` shape, the same plain `tool_name` sort, no headers, ASCII only.

| candidate | artifact | rendered block |
|---|---|---|
| **A_0-compact** — the released compact registry, byte-identical to the sealed official baseline | the empty override mapping `{}` | 15,854 characters, 152 lines, sha256 `752dd381a02028dc7345a6ac826109bdcc879d82547a9029a43d559d0de8a605` |
| **A_0-kca1** — KC-A1's contrast artifact | `configs/knowledge/a2t-kc-a1/contrast-notes-v1.json`, sha256 `dcf84c2a5a371b658e234d0f42c1f03a7c36c5a2c090790d44e383999647cd21` | **unavailable as things stand** — see below |

**KC-A1 never flew, so there is no KC-A1 verdict and A_0 is A_0-compact.** On 2026-09-06 (master
`35193cb1`) the KC-A1 prompt fit measured its artifact at **3,625 text tokens against the sealed
compact registry's 3,581** — **+44 over a binding +40 cap** — and the cell's own void clause fired:
no wire check, no flight row, no smoke, no flight, and KC-A1c was never reached. Program section
4a's routing is unchanged in effect (EVO-A1 starts from the official baseline) but arrives by a
different road: not a NULL result, an unflown cell. A_0-kca1 becomes admissible only if the
coordinator re-prices the cap, or KC-A1 is rebuilt to fit, flown and admitted.

**The token cap is the binding constraint, and the estimator that priced it was wrong.** The
measured facts, from the pinned tokenizer rather than from ORG-1's ratio:

* the sealed compact block is **15,854 characters and 3,581 text tokens** — 4.427 chars/token, not
  the 3.989 ORG-1 measured on its own grouped block;
* short appended English phrases tokenize **denser** than that, at **3.659 chars/token**, which is
  how KC-A1's 161 added characters were priced at +40 and cost +44;
* the +40-token headroom `rails.proposer.TOKEN_HEADROOM` enforces is therefore worth about **+146
  characters of new phrasing over the whole block** — roughly +14 characters per tool across ten
  targeted tools, +7 across nineteen.

**This cuts differently for EVO-A1 than for KC-A1, and it is the one structural advantage this cell
has.** KC-A1's family could only APPEND: every note was a pure addition to a description that
stayed. The loop's candidates REWRITE the whole description, so a proposer may spend the characters
an original description was wasting and land inside the cap while saying something different —
and `render_proposer_instruction` already tells it to "keep each description close in length to the
current one". The +146-character budget is headroom over a rewrite, not over an append.

**Never price a candidate with an estimator.** `validate_candidate_artifact` takes an **injected**
`token_counter` precisely so the serving geometry's own tokenizer is the authority; KC-A1 passed its
builder's gate and was refused under that authority by four tokens. Every EVO-A1 candidate is
counted through the resident server's `/tokenize` route at prompt fit, and a chars-per-token ratio
never admits one.

## 4. Action space per target and round

`K` candidates per target, all the same `rails.proposer.CandidateArtifact` dataclass, assembled
across targets into one portfolio per slot `k` (`rails.evolution.assemble_portfolio`), so a round
flies the incumbent plus `K` portfolios rather than `K x targets` arms.

| family | k | rounds | contacts | what it is |
|---|---:|---|---:|---|
| **F1 proposer** | 1, 2, 3 | every round | 1 text contact per target per k | `render_proposer_instruction`: this target's registry rows, `M = 8` block-disjoint construction exemplars per tool with their gold calls, the incumbent descriptions. Returns strict JSON `{"cue": ..., "descriptions": {...}}` |
| **F2 deterministic** | 4 | every round | none | `deterministic_candidate`: append the registry's own `domain` and `category`. Zero model contact, so it is the floor a proposer must clear |
| **F3 placebo** | 5 | round 1 only | 1 text contact per target | `render_placebo_instruction`: a length-matched rewrite explicitly told to carry no distinguishing cue |

So **`K_1 = 5` and `K_r = 4` for r >= 2**; the program's "K = 4" is the steady-state value and the
round-1 placebo is the extra slot, not a replacement for a proposer draw.

**The exemplar draw is a seeded ORDERED sample, and this matters.** `A2T-EVO-EXEMPLARS-V1` holds
exactly `M = 8` units for twelve of the twenty-three tools, because the quota rule spends everything
else on the folds. Three draws over an 8-unit pool cannot differ in membership, and the frozen core
decodes greedily, so three prompts differing only in a `# target t | round r | variant k` header
would return three near-identical rewrites and `K` would be decorative. The draw is therefore
preregistered as: **seed `(round, target_id, k)` selects the 8 exemplars where more than 8 exist,
and in every case fixes their ORDER**, which `render_proposer_instruction` preserves within a
tool's group. Exemplars never come from either fold; they may overlap across `k`.

**Candidate id** = `rails.proposer.candidate_id_for` — sha256 over the canonical JSON of `text`,
`proposer_prompt_sha256`, `exemplar_ids`, `round`, `target`, `k`, `family`. All seven fields are
inside the hash, so a candidate cannot be relabelled into another slot without changing its id. Each
portfolio is pinned by a committed baseline fragment written by
`rails.evolution.write_candidate_fragments`, which emits
`configs/knowledge/a2t-evo-a1/evolved-registry-<sha16>.json` (the override mapping alone) and
`configs/baseline/a2t-evo-a1/evolved-artifact-<sha16>.json` (a copy of the base fragment with
`task_instruction_fill = evolved-artifact-v1` and the artifact's relpath, sha256, portfolio sha256,
round and k). The sha256 is over the artifact bytes as written, so a fragment can never fly against
an artifact edited afterwards.

### The proposer instruction, verbatim in shape

Rendered by `rails.proposer.render_proposer_instruction`; the exact bytes are reproducible from the
committed registry and the exemplar ids, and `prompt_sha256` pins them. Its blocks, in order:

```
# target {target_id} | round {r} | variant {k}

You are rewriting the catalogue descriptions of tools that a speech assistant confuses with
one another.

There are {n} tools below. They are selected from the same catalogue by the same request text,
and today a reader cannot reliably tell them apart from their descriptions alone.

## Tools
### {tool}
signature: ... / domain: ... / category: ... / argument constraints: ... /
argument defaults: ... / current description: ...          (name-sorted, one block per tool)

## Example requests and their correct calls
### {tool}
1. spoken request: {construction query text}
   gold call: {rendered gold call}                          (grouped by the gold call's tool)

## Task
First decide the single cue that separates these tools -- the thing in a spoken request that
should send a reader to one rather than another.
Then rewrite each description so that cue is unmistakable in it.

## Output
Reply with ONE JSON object and nothing else -- no prose before or after it, no code fence,
no explanation:
{"cue": "...", "descriptions": {"toolA": "...", ...}}
Rules:
- the descriptions object has exactly these keys: {tools}
- each description is at most 200 ASCII characters, on one line
- describe what the tool does and when to choose it, never an example value
- never copy a sample identifier, a numeric id, or a gold call string
- keep each description close in length to the current one
```

**No sample id ever reaches the rendered instruction** — exemplar ids are used only to group, to
order and to seed the candidate id — and no evaluation row, evaluation gold or score enters it. The
gold calls that do appear are construction gold, the legality class the 2026-09-05 owner decision
opened for this arm alone.

### Form caps, all enforced by `validate_candidate_artifact` before a candidate flies

ASCII only in every description and in the cue; no newline inside a description; at most 200
characters per description; exactly 152 rendered lines in plain `tool_name` order; the whole
rendered block within `compact_baseline_tokens + 40` tokens under the injected counter; no
Audio2Tool sample identifier and no bare six-digit id anywhere in a description.

## 5. The rounds

Per round `r`, in order:

1. **Propose.** One text contact per target per proposer slot on the `construction-proposer-text`
   arm, whose plan's split identity is `A2T-EVO-EXEMPLARS-V1`. Build F2 with no contact. Validate
   every candidate; a candidate that fails a form or decontamination gate is dropped and its slot
   flies the incumbent's descriptions for that target.
2. **Assemble.** `assemble_portfolio` merges candidate `k` of every target into one registry state;
   `write_candidate_fragments` emits the artifact and the baseline fragment.
3. **Fold A.** Fly the incumbent plus the `K_r` portfolios over all 404 rows of
   `A2T-EVO-FOLD-A-V1`, one contact per row, greedy, the official protocol otherwise unchanged.
   Score once per complete manifest with `a2t-toolcall-official` through `core.scoring_batch`.
4. **Stage one, per target** (`select_per_target`, gates `saves >= 4, harms <= 1, net >= 3`):
   slice each arm to that target's own rows and count against the incumbent. Winner = largest net,
   ties by fewer harms, then fewer override bytes, then lowest `k`. A count rule, not an interval:
   at 6 to 20 rows per tool a bootstrap says nothing, and a reviewer can recount this by hand.
5. **Assemble the winners** into one candidate state.
6. **Stage two, fold B** (`confirm_assembly`): fly the incumbent and the assembly over all 404 rows
   of `A2T-EVO-FOLD-B-V1`. Accept the assembly **whole** iff the targeted pooled CI90 lower bound is
   strictly above 0 **and** the background CI90 lower bound is at or above **-1.0 pp**. Never
   partially. 10,000 replicates, stratified by tier, seed 20260903, `analysis.paired.paired_contrast`.
7. **Curve.** Read the round's incumbent (post-decision) once on the 400-row curve roster. Curve
   only: it decides nothing.
8. **Stop rule** (`should_stop`): `R_max = 4`; stop after two consecutive rejects, or after an
   accepted round whose gain is under 0.5 pp.
9. **Receipt.** `write_round_receipt` under
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-a1/`, carrying the selection
   record, the confirmation record and the decontamination record; `replay_selection` must
   reproduce every stage-one decision from the sealed per-sample score files alone.

**Fold-B power is stated, not hidden.** Under STRICT the targeted slice of fold B is 145 rows (215
under RELAXED) against 120 background rows. That is below the owner's `n >= 400` rule, and it is why
fold B is an internal selection gate and never a claim: the claim-bearing read is the 4,000.

## 6. The reads

| read | population | when | what it produces |
|---|---|---|---|
| fold A | `A2T-EVO-FOLD-A-V1`, 404 rows, 256 blocks, identity `d96bc099…3c27de3fa` | every round, `K_r + 1` arms | per-target saves/harms/net |
| fold B | `A2T-EVO-FOLD-B-V1`, 404 rows, 292 blocks, identity `2cc816cd…cca5394bd` | every round, 2 arms | targeted and background CI90 |
| curve | the 400-row curve roster (section 7) | every round, incumbent only | the evolution curve |
| **final** | the union 4,000, `A2T-ORG1-UNION-4000` | **once**, at the end | the claim |

The final read pairs `A*` row for row against the **sealed** official-protocol outputs of the same
4,000 ids (`SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1` attempt `…t1officialpop500`,
`SAEA-A2T-TIER258-…` attempt `…t258officialpop1500`, `SAEA-A2T-TIER3467-…` attempt
`…t3467officialpop2000`; pooled 61.40 %, equal-domain 68.11 %). Nothing is re-flown on the baseline
side: greedy decoding is not bitwise reproducible across batch shapes on this runtime.

**Headline evidence**, in this order: (1) the curve — round versus fold-A gain, fold-B gain and
frozen-curve gain; (2) the evaluation delta on the 4,000 with the per-tier table and the
arXiv:2604.22821 Table 3 column beside every tier; (3) the generalization gap
`G = delta_foldB - delta_4000`; (4) the transfer ratio `delta_4000 / delta_foldB`; (5) both
weightings, natural-mixture and equal-stratum.

**Decision** (program section 4c): **ADMITTED** if the 4,000 CI90 lower bound is above 0 **and**
`G <= 0.5 * delta_foldB`. **NULL** if the curve rose but the 4,000 CI includes 0 — reported as
overfitting with the selection rule named — or if the curve never rose.

## 7. The curve roster — an open decision, both options priced

The program says "the frozen 400 per round (curve only)". Two rosters answer to that name and they
are not the same population. **The tier-1 official 500 is neither of them and is not proposed.**

**Option A (proposed): `A2T-EVO-CURVE-400-V1`** — a 400-row, tier-stratified (50 per tier)
sub-roster of the union 4,000, drawn **once** by `freeze_roster` with seed 20260906,
`split_role = "discovery"`, `roster_role = "evaluation"`, strata = tier. Every one of its rows is
**already consumed**: contacted on 2026-09-04 under the official protocol and again on 2026-09-05
under ORG-1, each carrying a sealed official-protocol output the curve read is paired against. Its
virtue is that the curve is a strict subset of the final read, so the curve and the evaluation
delta are measured on one distribution and the gap is not confounded by a population change. Its
cost is a new probe-sample-free subset receipt and its own D1 media supplement.

**Option B: `A2T-CALIBRATION-400`** — the study's original frozen 400 (identity
`e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c`, 2,159.688 s), which already
carries a sealed official-protocol read (`SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1`, cell
`R-official-raw`) and needs **no** D1 media supplement at all because its ids sit inside the base
`docs/receipts/artifacts/d1-identity.json`. Its cost is that only 68 of its 400 rows are in the
union 4,000, so the curve and the final read sit on different draws.

Budget numbers below assume Option A at an estimated 2,342 s per pass (the union's 23,418.083 s
scaled to 400 rows); Option B measures 2,159.688 s.

## 8. Decontamination, per candidate, under its own model-free row

Register **`SAEA-A2T-MF-EVO-DECONTAMINATION-V1`** (`model-free-check`, zero contacts) before the
first candidate is validated. Under it, `validate_candidate_artifact` is called with:

* `evaluation_query_texts` = the query text of all 4,000 union rows. **This is the only step in the
  whole cell that opens evaluation query text**, it opens it inside the gate alone, and it never
  renders, logs or echoes it. Refuse any candidate sharing a **word 6-gram** with an evaluation
  query unless that 6-gram already occurs in the released registry text.
* `registry_text` = the released compact registry, the legal source of shared phrasing.
* `exemplar_texts` = the construction rows the proposer was shown. Overlap here is **measured and
  reported, never gated** — construction rows are legally visible to the proposer, so the count is
  the memorization signal a reviewer reads beside the round's gain.
* the sample-identifier and bare-six-digit refusals, always on.

Per candidate the round receipt records: `candidate_id`, family, round, target, k, the exemplar ids
shown, the six-gram overlap verdict, the exemplar overlap count, the rendered token count and the
per-description character counts.

## 9. Preregistered kill results (verbatim from program section 5)

The loop is declared to have failed, and is stopped and reported as such, if any of these holds:

1. no target is admitted in rounds 1 and 2;
2. a construction gain of at least 2 pp whose 4,000 CI90 includes 0, or a transfer ratio below 0.25;
3. the deterministic control lands within 0.5 pp of the proposer;
4. the placebo is indistinguishable from the proposer candidate;
5. every candidate fails the background tolerance.

## 10. Budget

Per-round arithmetic (`rails.evolution.ledger_budget` reproduces the speech terms). Fold A carries
1,913.527 s of audio per pass, fold B 1,877.630 s, the curve roster about 2,342 s, the 4,000
23,418.083 s. Generation is costed at 0.80 s per call, the rate the sealed Audio2Tool cells showed
at two slots; these folds are shorter-audio than the union, so this is conservative.

| round | fold A | fold B | curve | proposer | calls | speech s |
|---|---:|---:|---:|---:|---:|---:|
| 1 (`K_1 = 5`, 6 arms) | 2,424 | 808 | 400 | 12 | 3,644 | 17,578 |
| 2–4 each (`K_r = 4`, 5 arms) | 2,020 | 808 | 400 | 9 | 3,237 | 15,665 |
| loop total (R_max 4) | 8,484 | 3,232 | 1,600 | 39 | 13,355 | 64,573 |
| final read on the 4,000 | | | | | 4,008 | 23,419 |
| **whole cell** | | | | | **17,363** | **87,992** (24.44 h) |

Registered **ceilings are `R_max` x the per-round budget**, per run id, because plan budgets are
cumulative across every attempt of a run id:

| run id | roster | attempts | calls ceiling | speech s ceiling | profile |
|---|---|---|---:|---:|---|
| `SAEA-A2T-EVO-A1-FOLD-A-V1` | `A2T-EVO-FOLD-A-V1` | `attempt-r{r}-i`, `attempt-r{r}-c{k}` | 9,696 | 45,925 | `baseline-reproduction` |
| `SAEA-A2T-EVO-A1-FOLD-B-V1` | `A2T-EVO-FOLD-B-V1` | `attempt-r{r}-i`, `attempt-r{r}-a` | 3,232 | 15,021 | `baseline-reproduction` |
| `SAEA-A2T-EVO-A1-CURVE-400-V1` | the curve roster | `attempt-r{r}-curve` | 1,600 | 9,368 | `baseline-reproduction` |
| `SAEA-A2T-EVO-A1-PROPOSER-V1` | `A2T-EVO-EXEMPLARS-V1` | `attempt-r{r}-p{target}-k{k}` | 48 | **0** | `bounded-discovery-probe` |
| `SAEA-A2T-EVO-A1-FINAL-4000-V1` | `A2T-ORG1-UNION-4000` | `attempt-<stamp>-evofinal` | 4,008 | 23,419 | `baseline-reproduction` |
| **total** | | | **18,584** | **93,733** | |

GPU hours: 18,584 calls x 0.80 s = 4.13 h; planned **5.0**, ceiling **6.5**. Paid API spend 0.
Proposer contacts are counted in `calls` and never in `speech_seconds`: the arm is text-only and
sends no audio part at all. Every row is written `consumed = no` and stays so until the loop closes.

## 11. Configuration

Round 1's reward fragment is `configs/experiment/a2t-evo-a1-description-evolution-v1.json`; every
later round's fragments are RE-EMITTED by the driver (below). Model fragment
`q4km-featcache-a2t-official-np2-04ccc72a`; the composed config is `model + dataset + baseline +
experiment` through the same `core.flight.FlightRuntime` and the same OpenJiuwen executor every
Audio2Tool direct cell has flown.

**Two profiles need two fragments, and this is a finding rather than a preference.** A composed
experiment fragment declares exactly one `execution_plan` object
(`FlightRuntime._build_execution_plan` reads `values["execution_plan"]`), and that object carries
the single `execution_profile` `contracts.assert_execution_scope` validates. The reward flights
(`baseline-reproduction`) and the proposer contacts (`bounded-discovery-probe`) therefore cannot
share one fragment.

**Committed, and hand-written once:**

| fragment | what it is |
|---|---|
| `configs/knowledge/a2t-evo-a1/loop-v1.json` | the loop AS DATA: targets, run ids, fragment names, metric, scorer, slots, gates, seed, `R_max`. `rails.evolution.LoopConfig.from_json` reads it and refuses an unknown key or an overlapping target set. The driver carries no cell knowledge of its own |
| `configs/baseline/a2t-evo-a1-base.json` | the official-protocol cell byte for byte with `task_instruction_fill` REMOVED. `write_candidate_fragments` owns `task_instruction_fill`/`task_instruction_fill_params` and refuses a base that already sets either; with no fill declared this fragment is also the incumbent `A_0` arm's own baseline, because falling through renders the released compact registry, which is exactly what `A_0` is |
| `configs/baseline/a2t-evo-a1-proposer.json` | the proposer arm: `arm: construction-proposer-text`, `policy: fixed`, `scorers: ["cost"]`. It declares NO instruction — every contact's system message is its draw's own rendered instruction — and no roster, because the roster is per round |

**Emitted per round, by `scripts/run_a2t_evolution_round.py`:**

| artefact | step |
|---|---|
| `docs/receipts/rosters/a2t-evo-a1-proposer-r{NN}.json` | propose |
| `configs/experiment/a2t-evo-a1-proposer-r{NN}.json` | propose |
| `configs/experiment/a2t-evo-a1-fold-a-r{NN}.json` | candidates |
| `configs/experiment/a2t-evo-a1-fold-b-r{NN}.json` | select |
| `configs/knowledge/a2t-evo-a1/evolved-registry-<sha16>.json` and `configs/baseline/evolved-artifact-<sha16>.json`, one pair per portfolio | candidates, and once more for the assembly at select |
| `docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-a1/round-{NN}/{propose,candidates,selection,confirmation}.json` | one per step |
| `docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-a1/evolution-round-{NN}.json` | confirm (`write_round_receipt`) |

**The portfolio fragments are FLAT under `configs/baseline/`, and that is a harness constraint
rather than a taste.** `core.config._FRAGMENT_NAME_PATTERN` admits no path separator in a fragment
name, so a fragment written into a `configs/baseline/<subdir>/` tree could never be composed. Their
`configs/knowledge/a2t-evo-a1/` artifacts do live in a subdirectory: `render_evolved_registry`
resolves an artifact by relpath under `configs/`, not as a fragment name.

**The proposer arm's three config keys** — `construction_proposer_roster_receipt`,
`construction_proposer_roster_split_identity_hash` and `construction_target_tools` — are declared by
the PER-ROUND experiment fragment, never by the baseline fragment, because the roster is per round
and `core.config.compose` refuses the same key from two fragments. From round 2 the fragment also
carries `evolution_incumbent_artifact_relpath`, the artifact the last ACCEPTED round's assembly
wrote.

### The proposer roster, and why it is a roster at all

A proposer "roster" is a committed `core.roster` receipt (`saea-roster-receipt-v1`,
`roster_role = "construction"`, `split_role = "discovery"`) whose ITEMS ARE THE DRAWS — one per
`(round, target, family, k)`. Three consequences, all of them the point:

* `contracts.gate_exposure._require_construction_role_for_visible_targets` accepts a plan bound to
  it, because the scan it performs is over `docs/receipts/rosters/` for exactly this role and
  carrier. The identity a round's plan carries is therefore that round's own proposer roster, not
  `A2T-EVO-EXEMPLARS-V1`'s;
* each item's `sample_id` is the draw's ANCHOR — a real construction row of
  `A2T-EVO-EXEMPLARS-V1`, and for a proposer draw one the same contact's prompt actually shows.
  That is what makes the payload's `speech_ref`/`media_relpath`/`audio_seconds` honest on an arm
  that sends no audio at all, and it is why every draw claims a distinct anchor: the bundle
  contract seals exactly one outputs row per sample;
* each item additionally carries `exemplar_ids` (the seeded ORDERED draw), `round`, `target_id`,
  `family`, `k` and the anchor's measured media facts, so the roster is also the flight-roster view
  `scripts/flights/run_calibration_cell.py` hydrates from.

A **placebo** draw carries no exemplar id at all (an exemplar's gold call IS a distinguishing cue),
so its payload declares exactly ONE construction target, its own anchor — a row whose gold its
prompt never rendered. That over-declares exposure by one row, which is the conservative direction,
and `ProposerContact.rendered_exemplar_ids` records what the prompt actually showed.

### The proposer contact, seam by seam

`FrozenCoreClient` binds the UNION of every draw's declared targets ONCE, at construction, from the
committed roster; each request then names the ordered SUBSET its own draw showed
(`complete(..., construction_target_ids=...)`). A request can NARROW what the frozen core sees and
can never widen it — an id the bound tuple does not carry is refused — so the client's own invariant
("the gold this arm may show is a property of the client's whole life") is intact. The order is the
caller's because the draw's order is what the prompt showed.

`FlightRuntime` supplies the material through the `construction_material_resolver` seam, whose
config-driven default reads the committed roster, `tools_registry.csv`, the incumbent artifact and
the carrier's own construction rows (`data.audio2tool.load_query_rows`) and renders every
instruction at flight time. **No construction query text or gold call is ever written to a receipt
or committed to this repository**; a receipt records identity, counts and the prompt's sha256.

## 12. What the flight agent must do before the first contact

1. **Close A_0** (section 3) and record its sha256 in the fragment and in every exposure row.
2. **Ratify STRICT or RELAXED** (section 2) and write the chosen target set into
   `configs/knowledge/a2t-evo-a1/loop-v1.json`. Neither reading needs a fresh roster draw.
3. **Choose the curve roster** (section 7) and, for Option A, draw it once by seed and land its
   receipt under a model-free row.
4. **Make the folds hydratable** — three model-free artifacts per speech-bearing roster, none of
   which exists today: a probe-sample view under `docs/receipts/probe-samples/` (so
   `data.audio2tool` can resolve the ids at all), a flight-roster receipt carrying per-row media
   facts (`audio_sha256`, `audio_seconds`, `sample_rate`, `media_relpath`) of the shape
   `saea-a2t-agentloop-flight-roster-receipt-v1`, and a `d1-a2t-*` media supplement built with
   `scripts/build_a2t_semantic_agentloop_d1_supplement.py --roster ...` (one supplement per flight;
   the gate accepts exactly one supplement path per run).
5. **The exemplar roster needs none of those three; its ANCHORS need a D1 media supplement.** This
   corrects the earlier reading. `A2T-EVO-EXEMPLARS-V1` itself is never flown and needs no
   probe-sample view: the proposer's identities come from the per-round proposer roster the driver
   writes, which already carries the media facts a flight-roster receipt would. But
   `core.model.lifecycle` calls `gate.verify_media_identity` for every sample the binding names, and
   the payload names each draw's anchor, so **each round's anchors need a `d1-a2t-evo-proposer-r{NN}`
   media supplement** even though no audio part is sent. Anchors are few (twelve in round 1, nine
   thereafter) and are a strict subset of the exemplar roster, so one supplement per round is small.
6. **Write the dataset fragments** `audio2tool-evo-fold-a-404` and `audio2tool-evo-fold-b-404` on
   the `a2t_calibration_*` key contract, plus one per round for the proposer roster, so every cell
   flies through the same entry point with no new code path.
7. **Register `SAEA-A2T-MF-EVO-DECONTAMINATION-V1`** (section 8) before validating any candidate.
8. **The proposer run id cannot be registered at zero speech seconds.** `contracts.ExecutionPlan`
   refuses a non-positive `planned_speech_audio_seconds` outright, and
   `core.model.FrozenCoreAdapter` charges the payload's own `audio_seconds` against the plan even
   for a text-only request that sends no audio part. The arm still sends none — section 10's claim
   about the wire is unchanged — but `SAEA-A2T-EVO-A1-PROPOSER-V1`'s registered speech ceiling must
   cover the sum of its anchors' durations across every round, and the driver sizes each round's
   fragment accordingly. The ledger row's `speech audio seconds` cell is therefore an ACCOUNTING
   ceiling, not a claim that audio was heard.
9. **Prompt fit** under a `bounded-discovery-probe` row: `/tokenize` the A_0 block and every
   round-1 portfolio on the resident server, confirm the +40-token headroom against the sealed
   compact registry's measured **3,581** tokens, and re-derive the serving geometry. Zero generated
   tokens. A candidate that only an estimator admits is refused: KC-A1 died four tokens over a
   forty-token cap because its builder injected the ORG-1 ratio as its counter. The driver
   deliberately prices NO candidate — `run_candidates_step`'s `validator` seam is left unfilled,
   because filling it would be a contact — so this row is where `validate_candidate_artifact` runs
   with the serving tokenizer as its `token_counter`, and a candidate it refuses is appended to that
   round's refusal record.
10. **Wire check every cell, the proposer included.** Both fold cells are ordinary `policy: fixed`
    speech cells and `FlightRuntime.wire_check` applies unchanged. **The proposer arm is now
    wire-checkable too** (track E3c): the check drives `_dispatch_fixed_policy` into
    `_run_construction_proposer` against `WireCheckGate`/`WireCheckTransport` with zero contacts and
    refuses unless — one payload per draw, payload keys exactly
    `ARM_VISIBLE_FIELDS["construction-proposer-text"]`, each payload's `construction_targets` exactly
    that draw's own exemplars in the order the seeded draw fixed and carrying no key beyond
    `sample_id`/`target`, each `task_instruction` hashing to that draw's pinned `prompt_sha256`, and
    no `input_audio` / `input_speech_features` / `audio_url` anywhere in any request body. The
    receipt records the draws by identity, count and digest, never by text.
11. **The E2.4 gate now fires at preflight.** `FlightRuntime` forwards the arm to
    `assert_model_touch_allowed` at preflight and at serve, so a plan whose split identity is not a
    committed `roster_role = "construction"` roster of the carrier is refused BEFORE a server is
    started and before an attempt id is spent; a gate that cannot receive the arm refuses a
    construction-visible flight outright rather than flying it unchecked.
12. **MF-5 dry run**: four rows of fold A end to end through `run_program`, sealed and scored. The
    loop's own model-free dry run is already landed and is a test
    (`tests/unit/test_a2t_evolution_round_driver.py`): a whole round over a synthetic world, a
    hand-written sealed proposer manifest with one valid answer and one refusal, `replay_selection`
    reproducing every stage-one decision from the score files alone, and a second run that is
    byte-identical.
13. **Confirm the tree is clean** for the whole run: a COMPLETED manifest reads `study_commit` at
    finalize and refuses a dirty checkout. The driver writes into `configs/` and `docs/`, so commit
    each step's artefacts before the flight that reads them.

### The commands, per round

The driver runs one STEP per invocation and is resumable: every step reads its predecessor's sealed
receipt and refuses to redo it, so re-running the same command after an interruption re-enters at
exactly the first step that has not landed. `--plan-only` reports which step is next, and why the
others are not, without writing anything.

```
# what is next, and what it is waiting for
python scripts/run_a2t_evolution_round.py --config configs/knowledge/a2t-evo-a1/loop-v1.json \
    --round 1 --plan-only

# (a) the proposer roster + its bounded-discovery-probe fragment + the prompt digests
python scripts/run_a2t_evolution_round.py --config configs/knowledge/a2t-evo-a1/loop-v1.json --round 1

# then FLY the proposer cells (attempt-r1-p{target}-k{k}) and copy the sealed outputs to
#   docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-a1/round-01/proposer-outputs.jsonl

# (b) candidates, portfolios, their committed fragments, the fold-A fragment
python scripts/run_a2t_evolution_round.py --config configs/knowledge/a2t-evo-a1/loop-v1.json --round 1

# then FLY fold A (attempt-r1-i, attempt-r1-c{k}), score once per complete manifest with
#   include_per_sample=True, and write .../round-01/fold-a-scores.json as
#   {"incumbent": "<path>.score.json", "1": "<path>", "4": "<path>", ...}

# (c) stage one, the assembly, the fold-B fragment
python scripts/run_a2t_evolution_round.py --config configs/knowledge/a2t-evo-a1/loop-v1.json --round 1

# then FLY fold B (attempt-r1-i, attempt-r1-a) and write .../round-01/fold-b-scores.json as
#   {"incumbent": "<path>", "assembly": "<path>"}

# (d) confirmation, the next incumbent, the stop rule, the round receipt
python scripts/run_a2t_evolution_round.py --config configs/knowledge/a2t-evo-a1/loop-v1.json --round 1
```

The driver checks `ledger_budget` against the parsed exposure rows before it emits a fragment and
refuses a run id whose registered ceiling the whole loop would exceed, or whose row is not
`consumed = no`. It never contacts the model: the three inputs it waits on — the sealed proposer
outputs and the two score indexes — are flight products, and a step whose input is missing BLOCKS
rather than guesses.

## 13. Analysis

`rails.evolution.select_per_target` (stage one), `confirm_assembly` (stage two),
`analysis.paired.paired_contrast` (every interval; 10,000 replicates, tier strata, seed 20260903,
CI90), `write_round_receipt` per round, `replay_selection` to recompute every stage-one decision
from the sealed per-sample score files, and `analysis.paired.render_markdown` for the tables.
`ledger_budget` reproduces section 10's speech arithmetic. No new analysis module is admitted for
this cell.

## 14. Claim surface

Nothing here is a superiority, generality or Stage-3 claim. The folds are construction-role
discovery rows; the 4,000 are discovery identities already exposed on 2026-09-04 and 2026-09-05; the
curve roster's rows are already consumed. Gates are set relative to the sealed baseline and never
above the published ceiling, which is reported beside every tier as a reference. No test contact, no
fresh roster, no `A2T-FRESH-800` opening, no Q8_0, no second answering model, no parameter update.
At most one recovery re-registration per run id.

## 15. Open points for the coordinator

1. **A_0** — which of the two admissible states, with its sha256, and the token-cap baseline that
   follows from it.
2. **KC-A1 is VOID, not pending** (master `35193cb1`): it never flew, so A_0 is the released
   compact registry unless the coordinator re-prices the +40-token cap. That result also retires
   the ORG-1 chars-per-token estimator for this family.
3. **STRICT or RELAXED** — 67 addressable rows on three targets, or 90 on five. RELAXED costs
   nothing in rows and adds the lighting pair MF-1 flagged as already-halved-without-gain.
4. **The curve roster** — comparability (Option A) against zero supplement work (Option B).
5. **`K_1 = 5`** — the round-1 placebo as an extra slot rather than a replaced proposer draw.
6. **The exemplar draw as a seeded ORDERED sample** — the only way `K = 3` proposer draws differ at
   all for the twelve tools whose exemplar pool is exactly `M`.
7. **Fold-B power** — 145 targeted rows under STRICT is an internal gate, not a claim; confirm that
   reading rather than raising `n`.
8. **Track E3c is landed and no longer blocks round 1.** The proposer runner exists inside the
   base -- `rails.evolution`'s draws/roster/material, the `construction_material_resolver` seam and
   `_run_construction_proposer` on `FlightRuntime`'s own `_dispatch_fixed_policy` path, the
   per-request narrowing seam on `FrozenCoreClient`, and
   `scripts/run_a2t_evolution_round.py` -- with no launcher, no probe module and no controller or
   adapter subclass. Four things it surfaced that ARE still open points, because each one changes
   what the coordinator registers rather than how the code runs:
   * the proposer run id cannot be registered at **zero speech seconds** (section 12 item 8): the
     arm sends no audio, but `ExecutionPlan` refuses a non-positive value and the adapter charges
     the payload's `audio_seconds` regardless. Section 10's `speech s` cell for
     `SAEA-A2T-EVO-A1-PROPOSER-V1` must become the anchors' summed duration, read as an accounting
     ceiling rather than as a claim that audio was heard;
   * each round's proposer **anchors need their own `d1-a2t-evo-proposer-r{NN}` media supplement**
     (section 12 item 5), because the I-4 media-identity gate re-hashes exactly what the binding
     names. This is a small, per-round, model-free artifact, not a new roster;
   * the round's plan identity is that round's **own proposer roster**, not
     `A2T-EVO-EXEMPLARS-V1`'s `cff83b48...`. The gate's construction-role scan accepts it for the
     same reason it would have accepted the exemplar roster, and the exemplar roster remains the
     pool every draw is taken from;
   * the **placebo** contact declares one construction target (its anchor) whose gold its prompt
     never renders -- an over-declaration of exactly one row, the conservative direction, recorded
     as such. Confirm that reading rather than giving the placebo a second arm.
