# Priority-1 plan — Audio2Tool generality campaign (reviewer-grade design)

Date: 2026-08-25. Status: **PLAN — not registered; nothing flies until the owner approves and
each stage lands its own registration.** Authority: the DEV-500 confirmatory verdict §4.2 gate
(Audio2Tool admitted as the generality surface) and the baseline-lock verdict §5 (the locked
cell is what gets carried). Discipline: the ladder that produced the lock — offline projection
first, single variable per round, one-touch reads, unexposed statistics.

## 1. The reviewer question this campaign answers

The locked result is one task, one label space, one carrier: knowledge-conditioned two-contact
decode beats direct decode on SLURP dev, +20.20 pp on 500 unexposed. A reviewer reading only
that asks the obvious question — **is the paradigm general, or was a pipeline tuned to SLURP's
60-way intent classification?** Audio2Tool discriminates because it differs on every axis a
skeptic would name:

| axis | SLURP | Audio2Tool |
|---|---|---|
| output | one label from 60 | a JSON CALL LIST: tool names plus argument dicts |
| scoring | exact-match accuracy | tool accuracy AND exact match (name+argument multisets) |
| label space | 60 intents, enumerable in-prompt | **152 tools**, registry about 12.7k tokens |
| difficulty structure | scenario/action | **8 registered tiers** (direct, parametric, multi-intent, …) |
| failure modes | wrong intent | wrong tool, right tool wrong arguments, empty call list |
| knowledge unit | utterance exemplar + intent | tool schema + argument patterns + invocation exemplars |

If the locked form transfers, the claim upgrades from "works on SLURP" to "works on a
speech-to-structured-action family". If it fails, we learn precisely which assumption was
SLURP-specific — also a publishable finding, and a cheap one.

## 2. What already exists (no re-derivation needed)

- `Audio2ToolAdapter` implements `build_task_contract` (renders the frozen 152-tool registry)
  and reuses `data.audio2tool.load_audio2tool` / `audio2tool_receipts` / `render_tool_schemas`
  plus `reproduction.toolcall_scoring` for scorer-side gold — the same seam SLURP uses.
- A frozen 400-item discovery split (`docs/receipts/probe-samples/r1-audio2tool-sample.json`,
  8 tiers × 50, seed 20260807, split identity pinned).
- **A measured direct-decode baseline on exactly that split** (registered one-shot read,
  `2026-08-18-pa2t-a0-verdict.md`): **tool accuracy 0.5425 (217/400), exact match 0.2425
  (97/400)**, gap +30.0 pp, empty-call rate 0.1025, a full per-tier table, and a machine-listed
  120-sample headroom set (tool-correct but not EM-correct).
- Prior probe history on this carrier (P-EMB-2, the loss decomposition, S2/S2b/S2c verdicts) —
  all consumed, all citable, none re-flyable.

**Reviewer note on baseline strength:** 0.5425 tool accuracy is not a straw baseline — it is
the frozen core with the full 152-tool registry in-prompt, the strongest zero-shot form
available on this carrier. The exact-match figure (0.2425) is where the headroom lives.

## 3. Scientific design

### 3.1 Claim under test

The locked knowledge-conditioned form transfers to Audio2Tool: BLEND(locked) − M0 on an
UNEXPOSED A2T split has a 90% CI excluding zero on tool accuracy, and the mechanism profile
(dispatch-driven gain, safe retain subgroup) replicates.

### 3.2 Knowledge construction — the campaign's main scientific decision

SLURP's KB unit was "utterance text → intent". The A2T unit must be tool-shaped:

- **Content facets**: TRAIN invocation utterances (the spoken command text) — the analogue that
  made SLURP work (answer-text retrieval keys; the HyDE mechanism).
- **Label facets**: one per tool (152), carrying the registry identity — the closed-set anchor
  the protect-direct term needs.
- **Value bundles**: tool name + **argument-pattern exemplars** (argument dicts actually used
  with that tool in TRAIN) + a short invocation exemplar. This is the A2T-specific bet: SLURP's
  values were labels; here the value must carry ARGUMENT STRUCTURE, because the measured 30 pp
  tool-acc→EM gap says argument construction, not tool selection, is the dominant loss channel.
- **Distribution-modeled sampling** with hard floors: ≥1 exemplar per tool (all 152 — the
  >100-label clause), ≥1 per argument-pattern family, tier-stratified.
- **Decontamination** against the exposed 400 and any future eval tier by utterance identity,
  fail-closed, on the same pattern the SLURP build used.

### 3.3 Split governance — the reviewer's first attack surface

The existing 400-item split is EXPOSED (A0 baseline, P-EMB-2, S2/S2b/S2c all read it):

- **A2T-DEV-N (new, unexposed)**: a fresh tier-stratified draw, disjoint from the 400 by
  utterance identity, frozen as its own receipt with both hash conventions.
- The exposed 400 may fly (it hosts the A0 comparator and the 120-sample headroom list) but its
  numbers are SECONDARY readings, never the claim — the nested-tier discipline the DEV-500 and
  DEV-1000 reads already used.

### 3.4 Arms

| arm | purpose |
|---|---|
| M0 | prompt-matched direct decode (registry in-prompt), one contact per sample |
| BLEND(locked) | the locked cell, unchanged, over the A2T KB |
| ABL-RANDRET | random retrieval through the same fusion path — isolates the retrieval signal |
| ABL-RANDICL | random TRAIN exemplars — the "any exemplars help" control (NEGATIVE on SLURP) |

The two ablations fly only at the confirmatory stage, matching the DEV-500 pattern.

### 3.5 Statistics and power (pre-committed)

- Primary metric: **tool accuracy** (the label-selection analogue of SLURP intent accuracy).
- Always reported alongside: **exact match**, the tool-acc−EM gap, empty-call rate, and the
  per-tier table — a tool-accuracy gain that leaves EM flat is a DIFFERENT claim and must not
  be smuggled.
- Paired cluster bootstrap N=10,000 seed 20260807, 90% and 95% CIs, McNemar exact — the same
  machinery as the sealed reads, imported rather than reimplemented.
- **Power**: SLURP's held-out σ̂ was ~1.9–2.1 pp at n=400–500; A2T per-sample variance is higher
  (multi-call items), so a comparable interval needs **n ≥ 400 unexposed**. Do not shrink it.
- **The variance channel must be re-measured on this carrier** — SLURP's ±2/100 at 8-slot decode
  does not transfer. A repeated-decode replication at fixed config is part of the confirmatory
  stage, not an optional extra.

### 3.6 Stage ladder

| stage | surface | purpose | gate |
|---|---|---|---|
| **G0** | offline, zero contacts | A2T KB build, coverage + decontamination report, and a **reachability ceiling** (gold tool's facet rank distribution) | the ceiling must exceed the A0 tool accuracy, else the KB cannot help and the campaign STOPS before any contact |
| **G1** | exposed 400, tier-stratified subset (~100) | mechanics and first signal; knob work if required | prompt-fit passes; mechanism invariants hold (dispatch decomposition, branch-only replay) |
| **G2** | A2T-DEV-N (400 unexposed) | **confirmatory**: four arms plus replication | 90% CI on tool accuracy excludes zero |
| **G3** | — | verdict and generality statement | — |

**G0 is a real stop.** If the reachability ceiling sits at or below the A0 tool accuracy, the
honest outcome is "the paradigm does not transfer to this knowledge shape", stated after zero
contacts.

## 4. Reviewer objections and the design's answers

1. *"You tuned on SLURP and are reporting a second SLURP."* — The locked cell is carried
   UNCHANGED; any A2T-specific knob change is registered as such and forfeits the
   transfers-unchanged claim, declared up front as the stronger, preferred outcome.
2. *"Tool accuracy is the easy metric."* — EM and the gap appear in the same table, per tier,
   always. If EM does not move, the finding is stated as tool-selection improvement only.
3. *"The baseline is weak."* — M0 carries the full 152-tool registry and the same frozen core;
   the published A0 read (0.5425 / 0.2425) is the reference.
4. *"The split is contaminated."* — The claim tier is a fresh unexposed draw; the exposed 400 is
   reported separately; decontamination is machine-checked and receipted.
5. *"Retrieval is doing nothing; the second contact is."* — ABL-RANDRET answers exactly this, as
   it did on SLURP (+4.0 structural versus +19.75 full).
6. *"Single run, no variance estimate."* — A replication arm at fixed config is registered.
7. *"Cherry-picked tiers."* — All 8 tiers fly, the per-tier table is published whole, and the
   headline is the pooled unexposed statistic.

## 5. Cost estimate

G0 offline: zero contacts. G1 (~100 samples × 2 arms): ~300 core contacts, ~30 min. G2 (400
unexposed × 4 arms + replication): ~2,600–3,000 core contacts, ~1,000 tool contacts, 3–4 h GPU.
Total ~3,300 core contacts — comparable to the DEV-500 confirmatory campaign. Registered
ceilings per stage. The measured `multidim_recall` CPU cost (1.147 s/call over 11,514 facets)
applies here too; see the priority-2 plan's engineering note.

## 6. What a positive result licenses, and what it does not

Positive: the claim upgrades to a PARADIGM-level statement across two speech-to-structure task
families — the third pillar of a Stage-2B qualified paper candidate (the other two, held-out CI
gain and mechanism attribution, are already sealed on SLURP). It does NOT license a test-set
claim on either carrier, a generalization claim beyond the two families, or any Stage-3 activity
without the owner's paper contract.

## 7. Amendment 1 (2026-08-25, coordinator) — the transfers-unchanged claim is SPLIT after the
## G1 prompt-fit stop

G1 stopped at zero spend on the binding gate: measured against the resident 8,192-token slot,
the A2T **M0** envelope is 13,236 tokens and the BLEND worst case is 19,047 — a 2.51x deficit,
computed with zero audio tokens and zero output reserve, so it is a LOWER bound. The decisive
observation is that **M0 fails**: M0 carries no evidence slot at all and is the same bare direct
decode that produced the published A0 comparator (0.5425). Therefore the failure is NOT evidence
about the paradigm, and G0's reachability PASS is untouched. What is established is purely
mechanical: the locked cell's SERVING GEOMETRY, not its knobs, is incompatible with a
13,236-token task contract. Cause: A2T's bare registry is larger than SLURP's entire evidence
prompt (2.14x on tokens); the A0 flight itself recorded dropping `-np 4` to `-np 1` for exactly
this reason.

**Ruling.** The claim in section 4.1 is split into two, and the campaign carries both explicitly:

- **POLICY-CELL TRANSFERS UNCHANGED** — the locked v1 cell (alpha .45, tau .65, k/m 5, c 2,
  top_l 3, train priors, rrf, boundary stage off, facet-side admission, the f1060078 repair) is
  carried BYTE-IDENTICAL to A2T. This is the scientific claim and it is unweakened.
- **SERVING GEOMETRY IS CARRIER-FORCED** — three parameters change because the carrier's
  contract and output shape require it, not because any of them was tuned or selected for
  performance: (1) `-np 8 -> 2` at unchanged `-c 65536` (32,768 tokens/slot, worst-case margin
  +12,181; np3 would clear by only +1,258); total context, KV allocation and VRAM are unchanged
  and the only cost is throughput; (2) `max_tokens 64 -> 1024`, forced by the output shape (a
  JSON call list, not a single label) and equal to the value A0 itself registered; (3) A2T
  speech-feature packet materialization, which does not exist yet and is label-free engineering.

**Why this is defensible to a reviewer, stated plainly:** none of the three is a degree of
freedom that could be tuned toward a better number. Slot width is set by the contract's token
count; the output ceiling is set by the task's output shape; packets are an engineering
prerequisite shared by every arm including M0. All four arms fly under the identical geometry,
so the M0-vs-BLEND comparison — the entire claim — is unaffected by them. The registration must
say all of this in the row, and the campaign must NOT claim "everything transfers unchanged";
it claims the policy cell transfers unchanged under carrier-forced serving geometry.

**Consequence for the ladder:** G1 is re-flown under the amended geometry (mechanics + first
signal on the exposed tier), and only then does G2 fly on the unexposed tier with four arms.
The G0 gate result, the split governance in section 3.3, the statistics in section 3.5, and the
reviewer answers in section 4 are otherwise unchanged.

## 8. Amendment 2 (2026-08-25, owner ruling) — serving geometry is a FUNCTION OF THE TASK, not
## an exception to the transfer claim

The owner's ruling supersedes Amendment 1's defensive framing: *different tasks require
different input and output lengths, so a task's model-serving configuration is expected to
differ.* Amendment 1 treated the np/max_tokens change as a carrier-forced EXCEPTION that had to
be disclosed against a "transfers unchanged" ideal. That framing was wrong in the direction of
timidity. The correct architectural statement is:

**Serving geometry is derived from the task contract; it is not a degree of freedom of the
method.** Holding slot width and output ceiling fixed across carriers is not neutrality — it
forces two tasks into one ill-fitting shape and contaminates the comparison with the shape's
own effects. SLURP's 60-label contract implies 8,192/64; A2T's 151-tool registry implies
32,768/1024. Both are consequences of the same rule applied to different contracts.

### 8.1 The derivation rule (registered once, applied to every carrier)

For any admitted carrier, before its first flight:

1. Measure, with the resident tokenizer, the **task contract** envelope (M0) and the **worst-case
   evidence** envelope (BLEND at the locked fusion budget) — the G1 prompt-fit procedure.
2. **Output ceiling** = the task's output-shape upper bound (a single label → 64; a JSON call
   list → 1024, the value A0 registered for this carrier), never a performance choice.
3. **Slot width** = smallest `-c / -np` combination whose per-slot context exceeds
   (worst-case envelope + speech tokens + output ceiling) with a stated margin; `-c` stays at
   the profile's value, so this reduces to the smallest `-np` that clears the requirement.
4. All arms of that carrier fly under the identical derived geometry, and the derivation is
   recorded in the campaign row with its measured inputs.

The rule is mechanical, pre-registered, and identical across carriers — which is exactly what
makes the cross-carrier comparison fair. A reviewer's legitimate question is not "did the
numbers stay the same?" but "was the geometry derived by a fixed rule from the task, applied
uniformly to every arm, and fixed before results were seen?" — and the answer to all three is
yes.

### 8.2 What this does to the claim

The campaign's scientific claim is now stated without hedging: **the locked POLICY CELL
transfers byte-identical across carriers; serving geometry is derived per carrier by the §8.1
rule.** There is no "exception" to disclose, only a rule to state. Amendment 1's three concrete
values for A2T (`-np 8 → 2`, `max_tokens 64 → 1024`, packet materialization) stand unchanged —
what changes is their status: they are the §8.1 derivation's OUTPUT for this carrier, not a
deviation from a baseline.

### 8.3 Retrospective consistency

The SLURP geometry (8,192-token slots via `-c 65536 -np 8`, `max_tokens 64`) satisfies the same
rule: measured worst-case evidence envelope 6,187 + speech + a 64-token reserve inside 8,192,
margin +1,954. The locked baseline is therefore not "the 8,192 configuration" — it is the
policy cell under a contract-derived geometry, which is the form that generalizes.
