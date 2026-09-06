# EVO-A1: description evolution on Audio2Tool — preregistration (REGISTERED)

**Status: REGISTERED, 2026-09-06.** All three of the coordinator's closing conditions are met.
(1) **`A_0` is `A_0-compact`**, the released compact registry, sha256
`752dd381a02028dc7345a6ac826109bdcc879d82547a9029a43d559d0de8a605` over 15,854 characters and 152
lines, measured at 3,581 text tokens (section 3). (2) **The curve roster is
`A2T-EVO-CURVE-400-V1`**, Option A, frozen and hash-pinned (section 7). (3) **All five loop exposure
rows are written**, plus `SAEA-A2T-MF-EVO-DECONTAMINATION-V1`, `SAEA-SN-MF-A2T-EVO-CURVE-ROSTER-V1`
and `SAEA-SN-MF-A2T-EVO-PROPOSER-R01-PLAN-V1` (section 10). The target set was closed by the owner
on 2026-09-06 (RELAXED WITH SENTINELS) and section 2 is rewritten to it; track E3c, the proposer
runner, is landed; and round 1's PROPOSE step has itself landed model-free, with
`check_ledger_budget` accepting the round.

**Registration is not authorization for a contact.** What this status means is that every gate a
round-1 takeoff needs is closed on the model-free side. The flight agent's FIRST contact is the
**prompt fit** of section 12 item 9, under its own `bounded-discovery-probe` row, and nothing may
precede it.

Cell EVO-A1 of `docs/readiness/2026-09-05-three-dimension-experiment-program.md` (section 4c, loop
constants section 5). Model-free prerequisites already closed:

| prerequisite | receipt |
|---|---|
| MF-1, the query-cue audit and the TARGET list | `docs/readiness/2026-09-05-a2t-query-cue-audit-v1.md` |
| construction capacity, `SAEA-A2T-MF-EVO-CONSTRUCTION-CAPACITY-V1` | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-construction-capacity/` |
| the three loop rosters, `SAEA-SN-MF-A2T-EVO-FOLD-ROSTERS-V1` (superseded, kept as history) | `docs/receipts/rosters/a2t-evo-fold-{a,b}-v1.json`, `a2t-evo-exemplars-v1.json` |
| the three loop rosters under the sentinel rule, `SAEA-SN-MF-A2T-EVO-FOLD-ROSTERS-V2` | `docs/receipts/rosters/a2t-evo-fold-{a,b}-v2.json`, `a2t-evo-exemplars-v2.json` |
| the folds' flight products, `SAEA-SN-MF-A2T-EVO-FOLD-SUPPLEMENTS-V2` | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-fold-flight-products/` |
| the curve roster and its flight products, `SAEA-SN-MF-A2T-EVO-CURVE-ROSTER-V1` | `docs/receipts/rosters/a2t-evo-curve-400-v1.json`, `docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-curve-roster/` |
| the decontamination gate, `SAEA-A2T-MF-EVO-DECONTAMINATION-V1` | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-decontamination/` |
| the round-1 propose step and its anchors' supplement, `SAEA-SN-MF-A2T-EVO-PROPOSER-R01-PLAN-V1` | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-a1/round-01/`, `docs/receipts/artifacts/d1-a2t-evo-proposer-r01.json` |

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

**The ceiling is stated before takeoff.** Under the owner's sentinel rule a sealed miss is
addressable when its GOLD tool carries fold reward rows — the row the loop is rewarded on is the
row whose gold is the tool the model failed to choose — and **216 of MF-1's 235 TARGET misses**
qualify: an arithmetic maximum of **+5.40 pp** on the 4,000 if every addressable row were
recovered, against a 61.40 % pooled baseline. **Exactly 19 rows are unreachable and both directions
are named**: 13 whose gold is `setBrightness` and 6 whose gold is `getLightState`, each a harm
sentinel with no reward row of its own (section 2).

This supersedes the pre-sentinel arithmetic this document carried, 67 rows and +1.68 pp under
STRICT, 90 and +2.25 under a RELAXED reading that still dropped thin tools. That count treated a
target as addressable only where a whole confusable pair was intact, which is the wrong arithmetic
once a thin tool is a sentinel rather than a drop: the lighting cluster's dominant confusion has
`setAmbientLighting` on the PREDICTED side, so its 88 rows are rewarded through the capable gold
side and were never the corpus's to refuse. What the corpus still cannot support is the reverse
direction, and that is what the 19 rows are. EVO-A1 remains a test of whether the loop mechanism
works at all, on the mass the corpus can supply.

## 2. Targets — CLOSED (owner 2026-09-06, RELAXED with sentinels)

`configs/knowledge/a2t-kc-a1/targets-v1.json` names MF-1's five disjoint targets over 23 tools, and
under the owner's decision **all five survive and all 23 tools are drawn**. The machine-readable
authority is `configs/knowledge/a2t-evo-a1/loop-v1.json` (`targets`, `sentinel_tools`); the receipts
are the V2 rosters.

**The rule, and why it is the right test.** A target survives when the GOLD side of its DOMINANT
miss direction has construction capacity. That is not a softening of the census, it is the correct
reading of what the loop is rewarded on: the rows the loop scores are the rows whose gold tool is
the one the model failed to choose, so `setLighting` rows are what reward a `setAmbientLighting`
rewrite. The census asked the wrong question of a thin tool — whether it could supply its own
reward rows — when the tool's job in a confusable pair is to be the thing wrongly chosen.

**A thin tool is a HARM SENTINEL, not a drop.** A tool the census gave a fold quota of 0 keeps
`min(4, u // 2)` of its `u` units as exemplars, paid from its smallest blocks first so the proposer
can still see what the tool is, and every remaining BLOCK is split evenly between fold A and fold B,
the odd block to fold A. Its description is rewritten like any other member of its target. Its rows
are never reward rows: they leave stage one's per-target slice, they count in the stage-two
background bound, and **any harm on a sentinel row is reported by name** in the round receipt's
`sentinel_harms` line (`rails.evolution.sentinel_harms`). The decision stays the preregistered one
— a sentinel harm does not by itself reject an assembly — and the 4,000 final read remains the harm
detector at scale. `LoopConfig.assert_sentinels_are_target_tools` refuses a sentinel that is not a
member of the target it guards.

### The per-tool table

Units and blocks are the construction pool at the 60 s cap; the last three columns are rows actually
DRAWN into the V2 receipts, not capacities.

| target | tool | units | blocks | exemplars | fold A | fold B | sentinel |
|---|---|---:|---:|---:|---:|---:|---|
| activateRoutine | `activateRoutine` | 65 | 46 | 25 | 20 | 20 | |
| activateRoutine | `activateScene` | 46 | 36 | 8 | 19 | 19 | |
| activateRoutine | `setApplianceMode` | 20 | 10 | 8 | 6 | 6 | |
| activateRoutine | `setSecurityMode` | 59 | 14 | 11 | 20 | 20 | |
| activateRoutine | `startCleaning` | 32 | 12 | 8 | 12 | 12 | |
| calibrateCameras | `calibrateCameras` | 7 | 7 | 3 | 2 | 2 | **yes** |
| calibrateCameras | `rebootDevice` | 50 | 15 | 14 | 12 | 12 | |
| calibrateCameras | `streamCamera` | 44 | 39 | 8 | 18 | 18 | |
| calibrateCameras | `updateFirmware` | 55 | 45 | 15 | 20 | 20 | |
| castContent | `castContent` | 39 | 10 | 8 | 14 | 14 | |
| castContent | `playMedia` | 22 | 7 | 8 | 7 | 7 | |
| getBiometricData | `getBiometricData` | 56 | 41 | 10 | 20 | 20 | |
| getBiometricData | `getHRV` | 51 | 41 | 21 | 15 | 15 | |
| getBiometricData | `setHapticStrength` | 38 | 34 | 14 | 12 | 12 | |
| getBiometricData | `setRomanceMode` | 10 | 10 | 4 | 3 | 3 | **yes** |
| lighting | `getLightState` | 29 | 9 | 4 | 6 | 1 | **yes** |
| lighting | `resetFilterStatus` | 61 | 46 | 21 | 20 | 20 | |
| lighting | `setAmbientLighting` | 9 | 9 | 4 | 3 | 2 | **yes** |
| lighting | `setBrightness` | 18 | 8 | 4 | 6 | 6 | **yes** |
| lighting | `setColor` | 49 | 14 | 9 | 20 | 20 | |
| lighting | `setColorTemperature` | 30 | 10 | 9 | 9 | 9 | |
| lighting | `setGroupLightState` | 55 | 40 | 15 | 20 | 20 | |
| lighting | `setLighting` | 89 | 46 | 43 | 20 | 20 | |
| **total** | **23 tools** | **934** | | **274** | **304** | **298** | 5 sentinels |

Of the drawn rows, 284 per fold are REWARD rows; the sentinel rows are 20 on fold A and 14 on fold
B (the asymmetry is the odd-block rule, and `getLightState` alone accounts for 5 of the 6). Each
fold then adds 120 background rows, 15 per tier over all eight tiers, one row per block, from blocks
no target tool occupies: **fold A 424 rows, fold B 418**.

`getLightState` is a sentinel for a DIFFERENT reason from the other four and is recorded as such:
the census gave it 9 units, and block contention — a contended block goes to the tool with fewer
blocks in the pool — sent its three shared blocks to the block-poorer `playMedia`, leaving fold
quota 0. Census thinness accounts for the other four.

### Surviving targets and addressable mass

Every dominant direction has a capable gold side, so all five targets survive:

| target | tools | dominant miss direction (gold -> predicted) | gold-side capacity | MF-1 mass | addressable |
|---|---:|---|---:|---:|---:|
| **lighting** | 8 | `setColor`+`setColorTemperature`+`setLighting` -> `setAmbientLighting` | 168 units | 147 | **128** |
| **activateRoutine** | 5 | `activateScene` -> `activateRoutine` | 46 units | 44 | **44** |
| **getBiometricData** | 4 | `getBiometricData` -> `getHRV` | 56 units | 23 | **23** |
| **calibrateCameras** | 4 | `updateFirmware` -> `calibrateCameras` | 55 units | 16 | **16** |
| **castContent** | 2 | `castContent` -> `playMedia` | 39 units | 5 | **5** |
| **total** | **23** | | | **235** | **216** |

**216 of MF-1's 235 TARGET rows are addressable, a +5.40 pp arithmetic ceiling.** The 19 that are
not are named rather than summarised: **13 whose gold is `setBrightness`** (`setBrightness` ->
`setAmbientLighting`) and **6 whose gold is `getLightState`** (`getLightState` ->
`setAmbientLighting`). No TARGET direction has `calibrateCameras`, `setAmbientLighting` or
`setRomanceMode` as its gold at all, so three of the five sentinels cost no addressable mass.
Re-derived from the MF-1 per-pair table's own `A->B / B->A` direction counts, with the cluster pair
deduplicated against the three individual pairs it covers (88 = 35 + 28 + 25) as that table
requires.

**The lighting caveat stands and must be read beside the ceiling.** MF-1 recorded that 147 of the
235 rows are directions ORG-1 already halved without gaining a point. The loop can be rewarded on
128 of them, but the gold side of the reverse direction — `setAmbientLighting`, 9 units — can never
supply more than a sentinel's worth of evidence, so a lighting gain has to come from the rewrite of
a tool the model over-reaches for rather than from teaching the model when that tool is right.

### What the V2 receipts are

| roster | rows | blocks | audio s | identity | file sha256 |
|---|---:|---:|---:|---|---|
| `A2T-EVO-FOLD-A-V2` | 424 | 269 | 2,016.519 | `f84ef663...70917325` | `8e65f508...5962d153` |
| `A2T-EVO-FOLD-B-V2` | 418 | 300 | 1,950.418 | `b2d1f634...1758ef9d` | `b108cac3...727f417c` |
| `A2T-EVO-EXEMPLARS-V2` | 274 | 197 | 1,073.947 | `ed750060...304e87f9` | `5a2beddf...c2f852b7` |

Seed 20260906, `split_role = "discovery"`, `roster_role = "construction"`, drawn over the V3
exposure-free construction pool restricted to runtime wav at most 60 s. Disjointness re-proved and
fail-closed before a byte was written: 0 blocks shared pairwise, 0 blocks and 0 sample ids against
the 5,279-identity exposure union, 0 duplicate ids. The V1 receipts stay as history and are never
deleted; `scripts/build_a2t_evo_fold_rosters.py --version v1` still reproduces them byte for byte.

## 3. State, and `A_0` — CLOSED (coordinator 2026-09-06)

**`A_0` = `A_0-compact`, the released compact registry, rendered sha256
`752dd381a02028dc7345a6ac826109bdcc879d82547a9029a43d559d0de8a605` over 15,854 characters and 152
lines, measured at 3,581 text tokens on the pinned tokenizer.** That value is re-derived, not
copied: `scripts/build_a2t_evo_decontamination.py` renders `A_0` through
`data.audio2tool_tools.render_registry_compact()` with no overrides and exits before writing a byte
unless the characters, the line count and the sha256 all reproduce. The token cap every candidate is
measured against is therefore **3,581 + 40 = 3,621 tokens**, priced by the serving geometry's own
`/tokenize` route at prompt fit and never by an estimator.

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
| **F3 placebo** | 5 | round 1 only | 1 text contact per target | `render_placebo_instruction`: a rewrite explicitly told to carry no distinguishing cue. The instruction asks for a LENGTH match, but the control is closed on a TOKEN match measured at prompt fit on the flight tokenizer (section 12 item 9) — a form twin is a token twin, not a character count |

So **`K_1 = 5` and `K_r = 4` for r >= 2**; the program's "K = 4" is the steady-state value and the
round-1 placebo is the extra slot, not a replacement for a proposer draw.

**The exemplar draw is a seeded ORDERED sample, and this matters.** `A2T-EVO-EXEMPLARS-V2` holds
exactly `M = 8` units for six of the twenty-three tools (`activateScene`, `castContent`,
`playMedia`, `setApplianceMode`, `startCleaning`, `streamCamera`), because the quota rule spends
everything else on the folds — V1 had twelve such tools, and the sentinel rule returned units to
four of them. It holds FEWER than eight for all five sentinels, whose reserve the rule caps at
`min(4, u // 2)`: `calibrateCameras` 3, and `getLightState`, `setAmbientLighting`, `setBrightness`
and `setRomanceMode` 4 each. For those five `exemplars_per_tool = 8` is a ceiling that cannot be
reached and the draw takes what the rule leaves. Three draws over an 8-unit pool cannot differ in membership, and the
frozen core
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
   arm, drawing its exemplars from `A2T-EVO-EXEMPLARS-V2` (the plan's own split identity is that
   round's proposer roster -- section 15 item 8). Build F2 with no contact. Validate
   every candidate; a candidate that fails a form or decontamination gate is dropped and its slot
   flies the incumbent's descriptions for that target.
2. **Assemble.** `assemble_portfolio` merges candidate `k` of every target into one registry state;
   `write_candidate_fragments` emits the artifact and the baseline fragment.
3. **Fold A.** Fly the incumbent plus the `K_r` portfolios over all 424 rows of
   `A2T-EVO-FOLD-A-V2`, one contact per row, greedy, the official protocol otherwise unchanged.
   Score once per complete manifest with `a2t-toolcall-official` through `core.scoring_batch`.
4. **Stage one, per target** (`select_per_target`, gates `saves >= 4, harms <= 1, net >= 3`):
   slice each arm to that target's own REWARD rows -- **a sentinel tool's rows are excluded from
   the slice** and never enter saves/harms/net -- and count against the incumbent. Winner = largest
   net, ties by fewer harms, then fewer override bytes, then lowest `k`. A count rule, not an
   interval: at 6 to 20 rows per tool a bootstrap says nothing, and a reviewer can recount this by
   hand. `sentinel_harms` is computed beside the selection and names every harmed sentinel row's
   tool; it is REPORTED, and by preregistered design it does not itself change the decision.
5. **Assemble the winners** into one candidate state.
6. **Stage two, fold B** (`confirm_assembly`): fly the incumbent and the assembly over all 418 rows
   of `A2T-EVO-FOLD-B-V2`. Accept the assembly **whole** iff the targeted pooled CI90 lower bound is
   strictly above 0 **and** the background CI90 lower bound is at or above **-1.0 pp**. Never
   partially. **The 14 sentinel rows of fold B count in the background bound**, not in the targeted
   slice, so a rewrite that wins its reward rows by breaking a thin tool is charged for it here.
   10,000 replicates, stratified by tier, seed 20260903, `analysis.paired.paired_contrast`.
7. **Curve.** Read the round's incumbent (post-decision) once on the 400-row curve roster. Curve
   only: it decides nothing.
8. **Stop rule** (`should_stop`): `R_max = 4`; stop after two consecutive rejects, or after an
   accepted round whose gain is under 0.5 pp.
9. **Receipt.** `write_round_receipt` under
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-a1/`, carrying the selection
   record, the confirmation record and the decontamination record; `replay_selection` must
   reproduce every stage-one decision from the sealed per-sample score files alone.

**Fold-B power is stated, not hidden.** The targeted slice of fold B is its 284 reward rows,
against 120 background rows plus 14 sentinel rows that also score against the background bound.
That is below the owner's `n >= 400` rule, and it is why fold B is an internal selection gate and
never a claim: the claim-bearing read is the 4,000.

## 6. The reads

| read | population | when | what it produces |
|---|---|---|---|
| fold A | `A2T-EVO-FOLD-A-V2`, 424 rows (284 reward / 20 sentinel / 120 background), 269 blocks, identity `f84ef663…70917325` | every round, `K_r + 1` arms | per-target saves/harms/net, plus the sentinel-harms line |
| fold B | `A2T-EVO-FOLD-B-V2`, 418 rows (284 / 14 / 120), 300 blocks, identity `b2d1f634…1758ef9d` | every round, 2 arms | targeted and background CI90 |
| curve | `A2T-EVO-CURVE-400-V1`, 400 rows (50 per tier), 363 blocks, 3,470.346292 s, identity `b40043be…92987f` — a strict subset of the final read's population (section 7) | every round, incumbent only, after that round's decision | the evolution curve. It decides nothing |
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

## 7. The curve roster — CLOSED (coordinator 2026-09-06): Option A, frozen

The program says "the frozen 400 per round (curve only)". Two rosters answered to that name and they
are not the same population. The tier-1 official 500 was neither of them and was not proposed. The
coordinator chose **Option A**, and it is now drawn, hash-pinned and committed.

**`A2T-EVO-CURVE-400-V1`** — a 400-row, tier-stratified (50 per tier) sub-roster of the union 4,000,
drawn **once** by `core.roster.freeze_roster` with seed 20260906, `split_role = "discovery"`,
`roster_role = "evaluation"`, strata = tier, no exclusion and no group key. Every one of its rows is
**already consumed**: contacted on 2026-09-04 under the official protocol and again on 2026-09-05
under ORG-1, each carrying a sealed official-protocol output the curve read is paired against. Its
virtue is that the curve is a strict subset of the final read, so the curve and the evaluation
delta are measured on one distribution and the gap is not confounded by a population change.

| fact | value |
|---|---|
| rows / blocks | 400 (50 per tier over all eight) / 363 |
| domains | smart_home 281, wearables 82, smart_car 37 |
| audio, one pass | **3,470.346292 s**; longest row 654.635667 s, shortest 0.958417 s |
| identity (FlightRuntime) | `b40043be23ed364b5121612b74cfbe52c044e1d83a2139c90229cdd72e92987f` |
| identity (probe-receipt `key`) | `4df3986d29bc98a788d2ab1249e697b4c2c13269e2b3b164b1f959a7db79e49b` |
| roster receipt | `docs/receipts/rosters/a2t-evo-curve-400-v1.json`, sha256 `443e9ac70021c12018f5511d0eca792a70c61270c2b3a79884cf293aad99bbc7` |
| flight-roster receipt | `docs/checks/.../2026-09-06-a2t-evo-curve-roster/flight-roster-receipt.json`, sha256 `b22741ac5be7f8bf8be4bd9e46de256ff870aa0f6a6ed7e37d2cc722b9cc3af4` |
| dataset fragment | `configs/dataset/audio2tool-evo-curve-400.json` |
| exposure row | `SAEA-SN-MF-A2T-EVO-CURVE-ROSTER-V1` |

**Two measured corrections to what this section used to say, and the measurement governs.**

1. **One pass costs 3,470.346292 s, not the estimated 2,342 s.** The estimate scaled the union's
   mean to 400 rows. The draw inherited **two of the union's four 654-second synthesis defects**
   (`tier6_correction:003151` and `tier7_multiturn:001033`), which alone are 1,309.3 s — 38 % of the
   pass. They are **kept**: the sealed baseline outputs this read pairs against were produced on
   exactly these rows, and dodging them would make the draw a selection rather than a subset.
2. **Its cost is NOT "a new subset receipt and its own D1 media supplement".** It needs **neither**,
   and writing the first would be a defect: all 400 ids already resolve inside `data.audio2tool`'s
   frozen-receipt universe (196 + 143 + 49 through the three official-population views, 8 through
   `r1-audio2tool-sample`, 4 through `select-fill-agentloop-104-postseal-scoring`) and
   `_resolve_items` refuses a sample id two probe-sample receipts claim, so an additive view would
   break the loader for every Audio2Tool cell rather than add a row. All 400 are likewise already
   inside the D1 identity closure — 392 through `d1-a2t-org1-union-4000.json` and 8 through the
   immutable `d1-identity.json` — so the curve cell configures the union's own supplement. The
   builder asserts both fail-closed and refuses to write if either is false.

**Consequences the flight must carry.** The registered speech ceiling is `R_max x 3,470.346292 =`
**13,882 s** (section 10), and under the encoder's one-second window rule the 654.6 s row costs 8,515
speech tokens, so the curve cell's serving geometry is the union's rather than the folds' looser one.
The prompt fit re-derives both.

**Option B is recorded as not taken.** `A2T-CALIBRATION-400` (identity
`e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c`, 2,159.688 s) already carries a
sealed official-protocol read (`SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1`, cell `R-official-raw`)
and needed no supplement either, but only 68 of its 400 rows are in the union 4,000, so the curve and
the final read would have sat on different draws. That is the cost the coordinator declined to pay,
and it is the whole reason Option A won.

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
4. the placebo is indistinguishable from the proposer candidate — read against a placebo whose
   whole-block TOKEN count, measured at prompt fit on the flight tokenizer, sits inside the proposer
   candidates' range (section 12 item 9);
5. every candidate fails the background tolerance.

## 10. Budget

**Every term is now MEASURED rather than estimated, and two of them moved.** Per-round arithmetic
(`rails.evolution.ledger_budget` reproduces the speech terms). Fold A carries **2,016.51925 s** of
audio per pass and fold B **1,950.417958 s**; the curve roster **3,470.346292 s** (not the 2,342 s
this section estimated before the draw existed — section 7), and the 4,000 23,418.083083 s.
Generation is costed at 0.80 s per call, the rate the sealed Audio2Tool cells showed at two slots.
The proposer term is **20 contacts in round 1 and 15 thereafter**, because five targets are flown.

| round | fold A | fold B | curve | proposer | calls | speech s |
|---|---:|---:|---:|---:|---:|---:|
| 1 (`K_1 = 5`, 6 arms) | 2,544 | 836 | 400 | 20 | 3,800 | 19,554.4 |
| 2 (`K_r = 4`, 5 arms) | 2,120 | 836 | 400 | 15 | 3,371 | 17,504.0 |
| 3 | 2,120 | 836 | 400 | 15 | 3,371 | 17,519.6 |
| 4 | 2,120 | 836 | 400 | 15 | 3,371 | 17,514.8 |
| loop total (R_max 4) | 8,904 | 3,344 | 1,600 | 65 | 13,913 | 72,092.8 |
| final read on the 4,000 | | | | | 4,008 | 23,419 |
| **whole cell** | | | | | **17,921** | **95,511.8** (26.53 h) |

The speech columns include each round's proposer ANCHORS, and those are now measured too: **84.114 s
in round 1** (wav headers, from the landed propose step) and 50.2 / 65.8 / 61.0 s in rounds 2 to 4
(the same deterministic draws, priced from the manifests' `duration` column). The arm sends no audio
part, but `FrozenCoreAdapter` charges the payload's own `audio_seconds` against the plan regardless,
so the seconds are an accounting term (section 12 item 8).

Registered **ceilings are `R_max` x the WORST round**, per run id, because plan budgets are
cumulative across every attempt of a run id. All five rows are written and are `consumed = no`:

| run id | roster | attempts | calls ceiling | speech s ceiling | GPU h | profile |
|---|---|---|---:|---:|---:|---|
| `SAEA-A2T-EVO-A1-FOLD-A-V1` | `A2T-EVO-FOLD-A-V2` | `attempt-r{r}-i`, `attempt-r{r}-c{k}` | 10,176 | 48,397 | 2.5 | `baseline-reproduction` |
| `SAEA-A2T-EVO-A1-FOLD-B-V1` | `A2T-EVO-FOLD-B-V2` | `attempt-r{r}-i`, `attempt-r{r}-a` | 3,344 | 15,604 | 1.0 | `baseline-reproduction` |
| `SAEA-A2T-EVO-A1-CURVE-400-V1` | `A2T-EVO-CURVE-400-V1` | `attempt-r{r}-curve` | 1,600 | **13,882** | 0.8 | `baseline-reproduction` |
| `SAEA-A2T-EVO-A1-PROPOSER-V1` | the per-round proposer rosters | `attempt-r{r}-p{target}-k{k}` | 80 | **400** | 0.1 | `bounded-discovery-probe` |
| `SAEA-A2T-EVO-A1-FINAL-4000-V1` | `A2T-ORG1-UNION-4000` | `attempt-<stamp>-evofinal` | 4,008 | 23,419 | 1.0 | `baseline-reproduction` |
| **total** | | | **19,208** | **101,702** | **5.4** | |

Fold A's ceiling is 4 x 6 arms x 424, fold B's 4 x 2 x 418. **Two ceilings changed from this
document's earlier draft and the measured numbers govern.** The curve's is 13,882 s rather than
9,368, because one pass costs 3,470.346292 s (section 7). The proposer's is **400 s rather than
879**: the four rounds' draws are deterministic and computable without a contact, their anchors sum
to 84.1 / 50.2 / 65.8 / 61.0 s, `check_ledger_budget` compares the WORST round x `R_max`
(4 x 84.114333 = **336.457 s**), and 400 is registered for margin. It is 400 rather than 0 because
`ExecutionPlan` refuses a non-positive value and the adapter charges the anchors (section 12
item 8). The landed round-1 propose step recorded exactly that check: planned 80 calls and 336.457
speech seconds against 80 and 400, `within: true`.

GPU hours: 19,208 calls x 0.80 s = 4.27 h nominal against **5.4** registered across the five rows.
The curve carries 0.8 h rather than the 0.36 h a flat rate would give, because two rows of every
pass carry 654 s of audio to encode. Paid API spend 0.
Proposer contacts are counted in `calls` and never as audio on the wire: the arm is text-only and
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
| `configs/knowledge/a2t-evo-a1/loop-v1.json` | the loop AS DATA: targets, `sentinel_tools`, the three V2 roster relpaths, run ids, fragment names, metric, scorer, slots, gates, seed, `R_max`. `rails.evolution.LoopConfig.from_json` reads it and refuses an unknown key, an overlapping target set, or a sentinel that is not a member of the target it guards. The driver carries no cell knowledge of its own |
| `configs/dataset/audio2tool-evo-fold-a-424.json`, `configs/dataset/audio2tool-evo-fold-b-418.json` | the two fold populations on the `a2t_calibration_*` key contract, so both folds fly through the same entry point and the same `FlightRuntime` as every other Audio2Tool direct cell. Named for their true V2 sizes; the `-404` names of the V1 draft never existed as files |
| `configs/dataset/audio2tool-evo-curve-400.json` | the curve population on the same key contract. It configures the UNION's own D1 supplement (`receipts/artifacts/d1-a2t-org1-union-4000.json`, sha256 `b94439af…64ec59`) and no probe-sample view of its own, because all 400 ids are already inside both closures — section 7 |
| `configs/baseline/a2t-evo-a1-base.json` | the official-protocol cell byte for byte with `task_instruction_fill` REMOVED. `write_candidate_fragments` owns `task_instruction_fill`/`task_instruction_fill_params` and refuses a base that already sets either; with no fill declared this fragment is also the incumbent `A_0` arm's own baseline, because falling through renders the released compact registry, which is exactly what `A_0` is |
| `configs/baseline/a2t-evo-a1-proposer.json` | the proposer arm: `arm: construction-proposer-text`, `policy: fixed`, `scorers: ["cost"]`. It declares NO instruction — every contact's system message is its draw's own rendered instruction — and no roster, because the roster is per round |

**Emitted per round, by `scripts/run_evolution_round.py`:**

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
  `A2T-EVO-EXEMPLARS-V2`'s;
* each item's `sample_id` is the draw's ANCHOR — a real construction row of
  `A2T-EVO-EXEMPLARS-V2`, and for a proposer draw one the same contact's prompt actually shows.
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

1. ~~**Close A_0**~~ **DONE (coordinator 2026-09-06).** `A_0 = A_0-compact`, sha256
   `752dd381a02028dc7345a6ac826109bdcc879d82547a9029a43d559d0de8a605`, 15,854 characters, 152 lines,
   3,581 text tokens; cap 3,621. Section 3 pins it and
   `scripts/build_a2t_evo_decontamination.py` re-derives it fail-closed.
2. ~~**Ratify STRICT or RELAXED**~~ **DONE (owner 2026-09-06, RELAXED with sentinels).** The
   target set is closed at five targets and 23 tools, `configs/knowledge/a2t-evo-a1/loop-v1.json`
   carries it with its `sentinel_tools` map, and the V2 rosters were re-drawn for it
   (`SAEA-SN-MF-A2T-EVO-FOLD-ROSTERS-V2`). This one DID need a fresh draw, contrary to the earlier
   reading: sentinels take blocks the V1 cut had left in the exemplar pool.
3. ~~**Choose the curve roster**~~ **DONE (coordinator 2026-09-06): Option A, drawn and landed**
   under `SAEA-SN-MF-A2T-EVO-CURVE-ROSTER-V1`. `A2T-EVO-CURVE-400-V1`, 400 rows, identity
   `b40043be…92987f`, 3,470.346292 s per pass, with its roster receipt, its flight-roster receipt
   and its dataset fragment. It needs no probe-sample view and no D1 supplement of its own, and
   writing the first would break the loader — section 7.
4. ~~**Make the folds hydratable**~~ **DONE** under `SAEA-SN-MF-A2T-EVO-FOLD-SUPPLEMENTS-V2`.
   All three artifacts exist for both folds: the probe-sample views
   `docs/receipts/probe-samples/a2t-evo-fold-{a,b}-v2.json` (322 and 291 new ids, additive against
   `a2t-construction-800-v1`, growing the loadable universe from 5,274 to 5,887 with 0 duplicates
   so both folds resolve 424/424 and 418/418), the flight-roster receipts under
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-fold-flight-products/`, and
   the supplements `docs/receipts/artifacts/d1-a2t-evo-fold-{a,b}-v2.json`. The gate was RUN, not
   asserted: `verify_media_identity` through a real `FrozenCoreGate.for_study_repo` passed all 424
   and all 418 rows, and refused an unlisted id with `GateClosed`.
5. **The exemplar roster needs none of those three; its ANCHORS need a D1 media supplement.** This
   corrects the earlier reading. `A2T-EVO-EXEMPLARS-V2` itself is never flown and needs no
   probe-sample view: the proposer's identities come from the per-round proposer roster the driver
   writes, which already carries the media facts a flight-roster receipt would. But
   `core.model.lifecycle` calls `gate.verify_media_identity` for every sample the binding names, and
   the payload names each draw's anchor, so **each round's anchors need a `d1-a2t-evo-proposer-r{NN}`
   media supplement** even though no audio part is sent. Anchors are few (twenty in round 1,
   fifteen thereafter, one per proposer or placebo contact over five targets) and are a strict
   subset of the exemplar roster, so one supplement per round is small.
   **ROUND 1 IS DONE** under `SAEA-SN-MF-A2T-EVO-PROPOSER-R01-PLAN-V1`:
   `docs/receipts/artifacts/d1-a2t-evo-proposer-r01.json` (20 ids, 4,038,368 media bytes, sha256
   `b6782823ca062bddac3bae543a29065fc7c5d7531d58083873c01014d9ca7f8a`), and the I-4 gate was RUN
   rather than asserted — PASS on all 20 anchors through a real `FrozenCoreGate.for_study_repo`,
   with an unlisted id refused as the negative control. Rounds 2 to 4 repeat this after their own
   propose step. **A defect this closed**: the proposer roster used to record the manifest's
   three-decimal `duration` as `audio_seconds`, which no supplement built from wav headers could
   ever match, so this supplement was unbuildable and the anchors could never have passed the gate;
   `load_carrier_material` now measures headers through
   `analysis.a2t_evo_capacity.measured_media_facts`, the same function and the same FIRST-user-turn
   tier-7 rule the folds used.
6. **Write the dataset fragments** — the two fold fragments and the curve fragment are DONE
   (`audio2tool-evo-fold-a-424`, `audio2tool-evo-fold-b-418`, `audio2tool-evo-curve-400`). One per
   round for the proposer roster is emitted by the driver;
   `configs/experiment/a2t-evo-a1-proposer-r01.json` has landed, so every cell flies through the
   same entry point with no new code path.
7. ~~**Register `SAEA-A2T-MF-EVO-DECONTAMINATION-V1`**~~ **DONE (2026-09-06)**, before any candidate
   exists. Its artifact is
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-decontamination/`: the
   evaluation gate set of **77,899** word 6-grams, PINNED at
   `a98d5dd093571f3a63d58d91ab25dcc5ce04cc2a2ba201bbf4f56e96e00c44e9` and never listed, beside
   `A_0`'s **2,005** registry grams committed verbatim as the exemption list. All of KC-A1's counts
   reproduce. One inherited defect is recorded rather than silently fixed: KC-A1's rule swept in each
   chat turn's wav `path` and `role`, so 9,252 of the 77,899 grams are not speaker text (the
   speaker-only core is 68,647); the superset is kept because it is strictly stricter and because it
   is what makes the anchor reproduce.
8. **The proposer run id cannot be registered at zero speech seconds.** `contracts.ExecutionPlan`
   refuses a non-positive `planned_speech_audio_seconds` outright, and
   `core.model.FrozenCoreAdapter` charges the payload's own `audio_seconds` against the plan even
   for a text-only request that sends no audio part. The arm still sends none — section 10's claim
   about the wire is unchanged — but `SAEA-A2T-EVO-A1-PROPOSER-V1`'s registered speech ceiling must
   cover the sum of its anchors' durations across every round, and the driver sizes each round's
   fragment accordingly. The ledger row's `speech audio seconds` cell is therefore an ACCOUNTING
   ceiling, not a claim that audio was heard.
9. **Prompt fit — THE FLIGHT AGENT'S FIRST CONTACT, and nothing may precede it.** Under its own
   `bounded-discovery-probe` row: `/tokenize` the `A_0` block and every round-1 portfolio on the
   resident server, confirm the headroom against `A_0`'s measured **3,581** tokens (cap 3,621), and
   re-derive the serving geometry for all four populations — the two folds, whose worst rows are
   39.6 s and 53.8 s, and the CURVE roster, whose worst row is 654.6 s and therefore costs 8,515
   speech tokens, so the curve cell needs the union's geometry and not the folds'. Zero generated
   tokens. A candidate that only an estimator admits is refused: KC-A1 died four tokens over a
   forty-token cap because its builder injected the ORG-1 ratio as its counter. The driver
   deliberately prices NO candidate — `run_candidates_step`'s `validator` seam is left unfilled,
   because filling it would be a contact — so this row is where `validate_candidate_artifact` runs
   with the serving tokenizer as its `token_counter` and with
   `scripts.build_a2t_evo_decontamination.evaluation_invocation_texts(...)` as its
   `evaluation_query_texts`, under `SAEA-A2T-MF-EVO-DECONTAMINATION-V1`. A candidate it refuses is
   appended to that round's refusal record.

   **The F3 placebo is TOKEN-matched here, and that is what makes it a control.** Its instruction
   asks for a length-matched rewrite carrying no distinguishing cue, but LENGTH is not the quantity
   the comparison is about: the owner's 2026-09-06 ruling is that a control is a FORM TWIN measured
   on the flight tokenizer, not a character count, and KC-A1 is the standing proof that a
   chars-per-token estimator misprices this family (3.659 chars/token on short appended English
   against the block's own 4.427). So the prompt fit `/tokenize`s the placebo portfolio and the
   proposer portfolios on the SAME route and records each one's whole-block token count beside
   `A_0`'s 3,581. **Kill result 4 — "the placebo is indistinguishable from the proposer candidate"
   — is read against a placebo whose token count sits inside the proposer candidates' range**, and a
   placebo that lands outside it is re-drawn rather than flown, because a form twin that differs in
   volume tests volume rather than content. The `+40` headroom stays what it always was: the loop's
   search budget, advisory over a rewrite, never the thing the score is locked against.
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
python scripts/run_evolution_round.py --config configs/knowledge/a2t-evo-a1/loop-v1.json \
    --round 1 --plan-only

# (a) the proposer roster + its bounded-discovery-probe fragment + the prompt digests
python scripts/run_evolution_round.py --config configs/knowledge/a2t-evo-a1/loop-v1.json --round 1

# then FLY the proposer cells (attempt-r1-p{target}-k{k}) and copy the sealed outputs to
#   docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-a1/round-01/proposer-outputs.jsonl

# (b) candidates, portfolios, their committed fragments, the fold-A fragment
python scripts/run_evolution_round.py --config configs/knowledge/a2t-evo-a1/loop-v1.json --round 1

# then FLY fold A (attempt-r1-i, attempt-r1-c{k}), score once per complete manifest with
#   include_per_sample=True, and write .../round-01/fold-a-scores.json as
#   {"incumbent": "<path>.score.json", "1": "<path>", "4": "<path>", ...}

# (c) stage one, the assembly, the fold-B fragment
python scripts/run_evolution_round.py --config configs/knowledge/a2t-evo-a1/loop-v1.json --round 1

# then FLY fold B (attempt-r1-i, attempt-r1-a) and write .../round-01/fold-b-scores.json as
#   {"incumbent": "<path>", "assembly": "<path>"}

# (d) confirmation, the next incumbent, the stop rule, the round receipt
python scripts/run_evolution_round.py --config configs/knowledge/a2t-evo-a1/loop-v1.json --round 1
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

1. ~~**A_0**~~ **CLOSED, coordinator 2026-09-06: `A_0-compact`.** The released compact registry,
   sha256 `752dd381a02028dc7345a6ac826109bdcc879d82547a9029a43d559d0de8a605`, 15,854 characters,
   152 lines, 3,581 text tokens, cap 3,621. The +40-token cap is NOT re-priced; it stays the loop's
   advisory search budget over a rewrite. Section 3 carries it and the decontamination builder
   re-derives it fail-closed before writing a byte.
2. **KC-A1 is VOID, not pending** (master `35193cb1`): it never flew, so A_0 is the released
   compact registry unless the coordinator re-prices the +40-token cap. That result also retires
   the ORG-1 chars-per-token estimator for this family.
3. ~~**STRICT or RELAXED**~~ **CLOSED, owner 2026-09-06: RELAXED WITH SENTINELS.** Five targets,
   23 tools, 216 addressable rows, +5.40 pp ceiling; thin tools are harm sentinels rather than
   drops. Section 2 is rewritten to it and the V2 rosters are frozen. The lighting caveat MF-1
   raised — 147 of the 235 rows are directions ORG-1 already halved without gaining a point —
   survives the decision and is restated there.
4. ~~**The curve roster**~~ **CLOSED, coordinator 2026-09-06: Option A, drawn and landed.**
   `A2T-EVO-CURVE-400-V1` — 400 rows, 50 per tier, seed 20260906, `roster_role = "evaluation"`,
   identity `b40043be…92987f`, 3,470.346292 s per pass, exposure row
   `SAEA-SN-MF-A2T-EVO-CURVE-ROSTER-V1`. Two things the recommendation got wrong and the measurement
   corrected, both now in section 7: the pass costs 3,470.3 s and not the estimated 2,342 s (the draw
   inherited two of the union's four 654-second synthesis defects, kept because the sealed outputs it
   pairs against were produced on exactly those rows), and its cost is NOT "one subset receipt plus
   its own D1 media supplement" — it needs neither, and an additive probe view repeating its ids
   would break `data.audio2tool` for every Audio2Tool cell. The registered speech ceiling moves from
   9,368 to 13,882 s, and the curve cell inherits the union's serving geometry.
5. **`K_1 = 5`** — the round-1 placebo as an extra slot rather than a replaced proposer draw.
6. **The exemplar draw as a seeded ORDERED sample** — the only way `K = 3` proposer draws differ at
   all for the six tools whose V2 exemplar pool is exactly `M`, and the five sentinels whose pool is
   smaller still.
7. **Fold-B power** — fold B's targeted slice is its 284 reward rows, against 120 background rows
   plus 14 sentinel rows that score against the background bound. That is an internal gate, not a
   claim; confirm that reading rather than raising `n`.
8. **Track E3c is landed and no longer blocks round 1.** The proposer runner exists inside the
   base -- `rails.evolution`'s draws/roster/material, the `construction_material_resolver` seam and
   `_run_construction_proposer` on `FlightRuntime`'s own `_dispatch_fixed_policy` path, the
   per-request narrowing seam on `FrozenCoreClient`, and
   `scripts/run_evolution_round.py` -- with no launcher, no probe module and no controller or
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
     `A2T-EVO-EXEMPLARS-V2`'s `ed750060...`. The gate's construction-role scan accepts it for the
     same reason it would have accepted the exemplar roster, and the exemplar roster remains the
     pool every draw is taken from;
   * the **placebo** contact declares one construction target (its anchor) whose gold its prompt
     never renders -- an over-declaration of exactly one row, the conservative direction, recorded
     as such. Confirm that reading rather than giving the placebo a second arm.
9. **Every model-free prerequisite of a round-1 takeoff is now landed.** The four things this item
   named as blockers are all closed: `A_0` (item 1), the curve roster (item 4), the five LOOP
   exposure rows plus `SAEA-A2T-MF-EVO-DECONTAMINATION-V1`, and the round-1 anchors'
   `d1-a2t-evo-proposer-r01` supplement. The round-1 PROPOSE step itself has landed model-free
   (`SAEA-SN-MF-A2T-EVO-PROPOSER-R01-PLAN-V1`): 20 draws, 20 distinct anchors, 20 of 20 distinct
   prompt digests, `check_ledger_budget` accepting 80 calls and 336.457 speech seconds against 80
   and 400, and the I-4 gate run offline against all 20 anchors with a negative control.

   **What remains is a CONTACT, not a document, and it is in this order**: (a) the prompt fit,
   section 12 item 9, under its own `bounded-discovery-probe` row — the flight agent's FIRST
   contact, where the serving tokenizer prices `A_0`, every round-1 portfolio and the token-matched
   placebo, and where the serving geometry is re-derived for the folds and separately for the curve;
   (b) the contact-free wire check of item 10 on a clean committed tree; (c) the 20 proposer cells of
   `configs/experiment/a2t-evo-a1-proposer-r01.json`, whose sealed outputs the `candidates` step
   blocks on. Nothing in this document authorizes any of them: the exposure rows do, and they are
   written `consumed = no`.

   **A correction to how the round-1 plan is produced, recorded because it changes what a receipt
   means.** `--plan-only` writes NOTHING — it reports which step is next and why the others are not.
   The artifact carrying the round's draws, anchors and prompt digests is the PROPOSE step's own
   `round-01/propose.json`, produced by running the driver without `--plan-only`. Both are
   model-free; only the second lands a receipt.

11. **Three defects the round-1 propose step surfaced, all fixed at the base with tests, recorded
   because two of them would have refused a flight rather than a document.**
   * A released `expected_tool_call` is occasionally NAMESPACED — `smart_home.setApplianceMode(...)`
     against a bare `setApplianceMode` — in 1 of the 274 rows of `A2T-EVO-EXEMPLARS-V2` and 3 of fold
     A's 424. `build_proposer_material` demanded byte equality with the row's `tool_name` and refused
     the whole round on `tier5_needle:001403`. The manifest's `tool_name` is the authority the
     OFFICIAL scorer itself compares a prediction against, so the namespace is cosmetic; both guards
     now compare the last dotted segment, the call string is still rendered VERBATIM, and a genuine
     disagreement is still refused — the released `tier3_multi_intent:002505` pairs `updateFirmware`
     with a `setTargetTemperature` call and is a fold-A row rather than an exemplar.
   * The proposer roster recorded the manifest's three-decimal `duration` as `audio_seconds`, which
     no D1 supplement built from wav HEADERS can match within 1e-6, so item 5's supplement was
     unbuildable and the anchors could never have passed the I-4 gate. Fixed at the source — see
     item 5.
   * The study's one D1 supplement builder could not read a `saea-roster-receipt-v1`. It now accepts
     either shape, so a proposer roster (which has no flight-roster view, because it is not a speech
     population) is served by the same builder as every other roster.

12. **A defect this work surfaced, recorded because it changes what a receipt means.** A
   construction roster's own flight products used to poison the pool it was drawn from:
   `rails.knowledge_build_a2t._exposure_sources` read an unmarked probe-sample receipt as
   EVALUATION exposure and every `d1-a2t-*` supplement as exposure unconditionally, so landing the
   folds' views and supplements pushed the Audio2Tool exposure union from 5,279 to 6,121 ids and
   collapsed the V2 draw to 185/180/101 rows -- and the V1 draw with it, to 157/157/172. Neither
   committed receipt could be reproduced from a tree that contained its own flight products. The
   fix has a probe view declare its source roster's `roster_role`, and has the union subtract a
   CONSTRUCTION IDENTITY UNIVERSE (1,661 ids over 10 committed construction-role receipts) from
   every supplement -- which a supplement cannot declare for itself, because
   `contracts.gate_media_identity` requires its ten keys exactly. The union returns to 5,279 over
   the same 14 sources with identical per-source counts, and the system is now a fixpoint. Nothing
   here for the coordinator to decide; it is recorded so a reviewer knows why the union reader has
   a construction branch.

   **The fixpoint was re-verified once more when the curve roster landed.** Committing
   `docs/receipts/rosters/a2t-evo-curve-400-v1.json` — a genuine `roster_role = "evaluation"`
   exposure source of 400 ids — leaves the union at **5,279 identities over 15 sources instead of
   14**, because all 400 were already inside it through the three official-population probe-sample
   receipts. The V2 fold draw, which excludes that union, is therefore unchanged by the curve
   roster, and no committed receipt of this cell has to be re-derived.
