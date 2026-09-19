# Cell B8a: the delivery-time normaliser node, preregistration

Status: **PREREGISTERED BEFORE CONTACT.** Author: the B8a registration agent, main checkout
`studies/speech-aware-evidence-acquisition`, base commit `6bd8506a` (item E11 merged). Authority:
**owner decision 27 of 2026-09-19**, which names this cell and places it after the B4b replicate
resume; **owner directive 26 of 2026-09-18** ("analyses into nodes"); **owner decision 23 of
2026-09-18** (the bar and every final evaluation read the OFFICIAL, unprojected
`slurp-slu-official-train` number); **owner decision 25** (the HARMFUL form); **owner decision 7**
(projection v3 as the fixed post-processing, and the statement that about 2.5 pp of the 64-point
bar is representation alignment); **owner decision 17** (the per-scenario net-harmed-rows
diagnostic); **owner decision 22** (the resume-recovery clause every new registration carries). All
in `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`. Engineering:
`docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` section 3, item **E11**, and
`docs/superpowers/specs/2026-09-17-node-context-policy-design.md` section 16 (family B8).

This document grants no model contact. The one cell it registers stays readiness `held` until the
coordinator mints the root decision receipt and flips it with `scripts/flights/repin_cell.py`.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer, server
and paid-API contacts**. The resident service was never started, stopped or queried; no run
directory was written; sealed outputs were read only through read-only copies under a temporary
directory; no utterance text, filler or gold is printed or persisted anywhere in this package.

## 1. Why this cell exists

Owner directive 26 rules that an offline analysis this program trusts belongs **inside an agent
node**, not only in a report. Owner decision 23 rules that the bar and every final evaluation read
the **official, unprojected** SLURP `evaluate.py` number. Together they move module **M3** — the
SLURP USE projection v3 identified by the A1 audit
(`docs/results/2026-09-17-slurp-a1-use-projection-audit-v1.md`) — out of the scorer and into the
episode.

Projection v3 is the label rule `R_action`, then the registered legal-label projection v2, then
filler normalisation **P2** (case, whitespace, punctuation, meridiem, numeric words; **no support
filter**, which A1 rejected). Since item E4 it has lived as scorer-side post-processing
(`slurp-slu-official-projected-v3[-train]`). On the three sealed TRAIN Fold A arms it is worth
**+3.46 pp** (anchor), **+1.53 pp** (cell B1) and **+1.44 pp** (cell B5e) of official pooled SLU-F1
— and the official scorer **credits none of it** while it lives in the scorer.

Cell B8a applies **the same rule, by the same two functions**, inside the episode, immediately
before the answer is delivered. The official scorer then reads an answer the system itself
produced. Nothing about the model, the prompts, the knowledge or the role graph changes.

## 2. What the node is, and what it is not

**It is** one registry-resolved entry, `saea-deliver-normalise-v3`, in
`core.base.DELIVERY_NORMALISERS`, implemented in `rails/delivery_normalisers.py` by calling
`rails.slurp_projection_v3.apply_slurp_projection_v3_delivery` — **the same pair of functions**
(`project_slu_label_v3`, `normalize_filler_p2`) the v3 SCORER applies in
`reproduction.slurp_official_eval`. There is exactly one implementation of the rule; a second one
is precisely what would let the runtime form and the scorer form drift apart.

**It is pure, deterministic and zero-contact.** It makes no model, tokenizer, encoder, tool, server
or network contact, reads no gold for the row it rewrites, and needs only the 60-id legal intent
inventory — the same closed list the task contract already renders into the prompt, mined from
TRAIN and only from TRAIN. It therefore changes **no request byte**, spends no budget, and is
replayable offline from sealed bytes (`analysis.deliver_normaliser_replay`).

**It is applied exactly once per row**, by `rails.runner`, after the Planner ACCEPTs (or after the
terminal delivery of the last revision), after every guard that binds the accepted answer to its
actual source response, and before that answer becomes the delivered text. **An abstention is never
normalised**: it delivers empty text whose identity is a derived record, there is no answer to
project, and a normalisation receipt on such a row would claim custody of bytes that came from no
model response.

**One factor, down to the byte.** The node delivers the accepted answer **verbatim** whenever the
rule repairs neither a label nor a filler, rather than re-rendering it in canonical JSON. On the
sealed B1 arm the re-render alone would have changed 1,076 of 1,080 rows against 24 repaired labels
and 82 repaired filler rows — a difference no verdict could read. With the suppression the ON arm
differs from its comparator on exactly the rows the rule repairs, and `changed` means "the rule
repaired this row".

**It is NOT a judge.** Owner Decision 11-C makes the Reviewer seat criticism-only and
`core.base.JudgeRegistry` refuses at the door anything that could return replacement text, while
this node's whole job is to rewrite the delivered answer. Its registry is the seam
`COMMIT_POLICIES` already is.

**It is NOT authored from evaluated rows' gold.** Section 16 of the NCP design fixes the boundary
for every B8 node: construction data and closed lists only. `R_action` was identified against gold
after the fact, which is exactly why E4 preregistered it as a **rule to be confirmed
prospectively** rather than tuned, and why the node applies it to every row unconditionally rather
than where it helps. Nothing in this cell re-fits it.

**It is NOT the E4 seal-time key.** The run-level key `slurp_projection_v3_delivery` applies the
same rule at the SEAL, outside the agent, and a cell flown with it would be refused at bundle
verification (program spec, "One gap recorded, not closed"). The loader refuses both spellings
declared together. Every fragment that declares the E4 key stays `held` and has never flown.

**Custody.** A normalised row is held to the new bundle invariant **I7n** (`core.bundle.outputs`):
the trace's own MODEL_RESPONSE bytes for the row's request id must be the rule's recorded input,
the named rule must resolve and be deterministic, and re-running it over those bytes must reproduce
the delivered bytes byte for byte. I7 is untouched. A row carrying both a `solver_group` and a
`deliver_normaliser` receipt is refused, and the grouped-Solver combination is refused before any
contact by `rails.native_episode_config`.

## 3. The switch, and the harness-admission entry form

One `episode`-class key, the fourth and last of that closed allowlist
(`rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS`). Registered here before any read so the entry
cannot be written to fit the number:

| field | value |
| --- | --- |
| `module` | delivery-time normaliser node (module M3 executed inside the agent: SLURP USE projection v3 — `R_action`, then legal-label projection v2, then filler normalisation P2 — applied once to the accepted answer immediately before delivery) |
| `carrier` | `slurp` |
| `switch.table` | `episode` |
| `switch.key` | `native_episode.deliver_normaliser` |
| `switch.off` | `null` — the key's absence. A delivery node is either absent or armed; there is no third shape (`rails.config_tables.is_episode_null_arm`). |
| `switch.on` | `{"normaliser": "saea-deliver-normalise-v3"}` |
| `switch.proof` | `tests/unit/test_config_table_module_switches.py::test_deliver_normaliser_is_one_episode_class_key` |
| `switch.why_this_table` | it is a NODE of the episode, declared beside the roles it runs after and applied by `rails.runner` between the Planner's ACCEPT and the delivered answer — not a per-phase request-table entry, and not the `run` class, whose zero-request-byte licence it does not claim even though it happens to move no request byte |

The row itself is **not written by this preregistration and not written by the read**: the
coordinator owns `docs/receipts/harness-admission.json` and
`scripts/checks/harness_admission_check.py` is its oracle, exactly as the B1 twin verdict's
harness-admission consequence section states.

## 4. The default-plan consequence, stated before the number is known

`scripts/checks/harness_admission_check.py` requires every ADMITTED or NEUTRAL module to appear in
at least one default plan for its carrier, and refuses a HARMFUL one in any plan. So:

> **If this module is ADMITTED, the SLURP default plan
> (`configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json`) gains the key
> `native_episode.deliver_normaliser = {"normaliser": "saea-deliver-normalise-v3"}`, and every
> later official SLURP number this program reports — cells B7a, B7r, B8b, B4a, B8c, B5b, the v2.0
> lock, and any DEV-1000 or Fold B confirmation — is produced by a system that contains the node.**

That is the point of directive 26 and it is not a side effect. It also means the comparators of
later cells must be stated carefully: a cell registered against a sealed arm that pre-dates the
node compares a node-carrying arm against a node-free one, and its verdict must say so. This
preregistration fixes the consequence; it does not pre-authorise any later cell.

If the module is NEUTRAL it may enter the plan and the same consequence applies. If it is HARMFUL
it never enters any plan, the E4 scorer-side form keeps its diagnostic role, and the record keeps
the negative.

## 5. Arms and comparators — sealed bytes, nothing re-flown

The admission read is **model-free**. There is no B8a arm on the full roster and none is
registered: the node is deterministic and zero-contact, so its ON arm over any sealed OFF arm is
computable from that arm's own bytes. Every hash below was **re-derived by hashing the file** in
this registration.

| role | run id / attempt | `scores.json` SHA-256 | `outputs.jsonl` SHA-256 | run manifest SHA-256 |
| --- | --- | --- | --- | --- |
| **base 1 — the sealed anchor** | `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` / `attempt-slurp-native-dual-store-train-fold-a-anchor-generation-recovery-v1` | `7360876322488e5fda689fcafda00e90da2ebf559e5a35e635c550f940202b47` | `d87d71e8fa0fe93b45d5c6817ba125b016d8d91f44a14309171dd0f3a64270d8` | `049ac230e536bc6c8fe45bc847756ba486c4904e9c7602c698157f78d70c0152` |
| **base 2 — cell B1's recovery arm (module M1)** | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2` / `attempt-slurp-native-exemplars-k20-anchor-train-fold-a-generation-recovery-v2` | `a7105b328509a8bd00c4678fd076e9be4d242b6189bb82bbd290bd596e3c9078` | `db9cd6329b0837d8f120f153556c951a68969da167d245d695eb35916237deca` | `b07ed553ff9f78b8e3ead6797bb66fb92a1820793b8aa5061576c6f66aa1a8ad` |
| **base 3 — cell B5e (M1 + M4b), reported** | `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1` / `attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-generation-recovery-v1` | `aeed7ad9b7fe44e74c4b9e65470e0d96429637ccaa4655c9185515568a70d7b9` | `3d861012bfbbf267d47023d069e5ccfe0442a3212cb3bd855e100eb8475751a6` | `1d827e31bd26e65e1327ec8c81dc96ebb55cd470692b339ab5323fcea1c86808` |

All three manifests are `COMPLETED`, carry split identity
`61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role `discovery`, roster
`docs/receipts/rosters/slurp-evo-fold-a-v2.json`
(`1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`), 1,080 rows, 125 speaker
clusters, 18 scenarios of 60 rows, 523 headset and 557 far-field rows.

Registered aggregates, to be reproduced before any table is read:

| arm | official SLU / intent | projection v3 SLU / intent | TRAIN symmetric SLU |
| --- | ---: | ---: | ---: |
| anchor | 48.53 / 77.96 | 51.99 / 79.35 | 52.09 |
| cell B1 | 61.14 / 80.19 | 62.67 / 81.76 | 62.97 |
| cell B5e | 62.34 / 80.09 | 63.78 / 81.85 | 64.18 |

**The ON arm of each base is that base's own sealed rows after the node.** It is produced by
`analysis.deliver_normaliser_replay` over a read-only COPY of the sealed `outputs.jsonl`, which
never opens the sealed file for writing and reports `model_calls: 0`. The OFF arm is the sealed
bytes themselves. The two arms are therefore **perfectly paired**: the same 1,080 rows, the same
requests, the same responses, one deterministic transform apart. No second decode exists, so none
of the interval below is decoding noise.

## 6. What this registration already measured, model-free

Run in this registration over read-only copies, zero contacts of any kind:

| arm | rows | rows the rule repaired | label repairs | filler-repaired rows (entities) | unparsed rows, left byte-identical |
| --- | ---: | ---: | ---: | ---: | ---: |
| anchor | 1,080 | 191 | 20 | 174 (195) | 7 |
| cell B1 | 1,080 | 103 | 24 | 82 (90) | 4 |
| cell B5e | 1,080 | 102 | 31 | 75 (80) | 1 |

**Triple equality holds on every row of all three arms.** For each arm, on every parsed row, the
prediction triple `(scenario, action, entities)` parsed back out of the node's delivered text is
**byte-identical** to the triple the v3 SCORER builds from the same row (1,073 / 1,076 / 1,079
parsed rows; **0 mismatches**), and every unparsed row is delivered byte-identically with
`applied: false`. The official SLU number of a set of rows is a pure function of those triples and
the fixed gold, so **the official number of the node-ON arm IS the v3-projected number of the
sealed arm — identically, not to two decimal places.** This is the licence for reading the
admission without a flight, and it is what section 8's STOP condition re-checks.

**Determinism holds everywhere; idempotence has one exception, and it is recorded here rather than
discovered later.** Re-applying the node to its own output changes nothing on 1,080 / 1,080 rows of
cell B1 and of cell B5e, and on 1,079 / 1,080 rows of the anchor. On **one anchor row** a `date`
filler is not a fixed point of P2: the first application removes punctuation and converts one
numeric token to words, which changes the token boundaries so that a second application converts a
remaining digit as well; the third application is a fixed point. This does **not** touch I7n, which
requires the rule to be **deterministic** (the same input twice gives the same bytes) and not
idempotent, and it does not touch the read, because the scorer applies P2 exactly once and so does
the node. It does mean the E11 docstring's unqualified "idempotent by construction" is proved on
cell B1's 1,080 rows and is **not** a general property, and that
`analysis.deliver_normaliser_replay`'s "idempotence witness" use over a future ON arm may legitimately
report a small number of `changed: true` rows. Reported to the coordinator as an engineering
finding; no code is changed by this registration.

## 7. The four-row smoke — the one thing a flight still owes

Everything in section 6 is an offline property of the rule. What sealed bytes cannot show is that
the node **executed inside the agent**. That is what the smoke is for, and it is the only contact
cell B8a asks for.

| item | value |
| --- | --- |
| experiment / cell | `slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1` |
| run / attempt | `SAEA-SLURP-NATIVE-B8A-DELIVER-NORMALISE-V3-EXEMPLARS-K20-SMOKE-4-V1` / `attempt-slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-generation-v1` |
| FIT run / attempt | `SAEA-SLURP-NATIVE-B8A-DELIVER-NORMALISE-V3-EXEMPLARS-K20-SMOKE-4-FIT-V1` / `attempt-slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-fit-v1`, 176 endpoints, inside the same worker |
| baseline fragment | `configs/baseline/slurp-native-anchor-exemplars-k20-deliver-normalise-v3-smoke-4-v1.json` |
| experiment fragment | `configs/experiment/slurp-native-b8a-deliver-normalise-v3-exemplars-k20-smoke-4-v1.json` |
| composed config / protocol | `c281111fa1f79d03cedf741614c6941544a8f0ee4ffca43a8796ee2e4ab2fc74` / `2095bbfd11767a497d16b880b62e34325cd60af8a47a503961ae92bbc0015e5e` |
| roster | the four already-exposed TRAIN A engineering rows this repository reuses for every four-row form smoke, split identity `4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb` |
| budgets | 44 generation contacts, 176 FIT endpoints, 117 repeated speech seconds, 1.0 fit-inclusive GPU hour, 24 native task-contract calls, **zero official scoring jobs** — cell B5e's smoke ceilings, unchanged |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |

**The base is cell B1's recovery arm plus the node and nothing else.** Proved on the committed
fragments by `tests/unit/test_b8a_deliver_normalise_smoke_config.py`: against
`configs/baseline/slurp-native-anchor-exemplars-k20-train-fold-a-recovery-v2.json` the smoke
baseline differs in `native_contact_fit`, `prepared_phase_supply`, the two speech-feature identity
ids, `what_this_is`, `scorers` (the v3-projected scorer is declared beside the primary and is
expected to be a **no-op** on this cell's own outputs, which is itself part of the receipt) and
`native_episode` — and inside `native_episode` the **only** differing key is `deliver_normaliser`.
Against the E11 full-cell baseline it differs in the four bookkeeping fields and the note, nothing
else.

**The prepared Perception supply does not move, and the re-pin tool proves it.** The smoke baseline
inherits cell B1's own recovery-smoke prepared pin
(`prepared/SAEA-SLURP-NATIVE-B8A-DELIVER-NORMALISE-V3-EXEMPLARS-K20-SMOKE-4-V1/phase-supply-v1.json`,
SHA-256 `eca235e6719888cc629b6e4efbdb4a31666637aca656538fac3c76ce78899e0f`, Perception output
SHA-256 `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` on 4 of 4 rows — the same
output cell B5e's smoke carries). Item E11 changed `core/flight/runtime.py`, so the prepared
artifact's identity no longer matches and `core.flight.repin` **will** rebuild it into this run's
own prepared directory; `_compare_artifact_output` then **refuses** the rebuild unless the new
selection is byte-identical to the inherited one. That refusal is the enforcement, and
`--allow-output-change` must never be passed.

### Structural acceptance — all five, and nothing else

1. **Five contacts per row**, on the B1 arm's own trajectory statistics (11 is the program
   ceiling); no row exceeds 11; the trace carries Perception, Solver, Reviewer and Planner
   contacts.
2. **Every MODEL_REQUEST byte is what the OFF base would send.** The node makes no contact and runs
   after every contact of the episode is already spent, so this is a property of the code, pinned
   end to end by `tests/unit/test_native_episode_runner_deliver_normaliser.py` (the real episode
   run twice through the shared fake transport, all four rendered requests compared). In flight it
   is re-read as: the twenty `train-exemplars::…` typed content blocks present on the Solver
   request, and one `*.request-fit.json` per realized contact with `every_request_fits = true` and
   every required-token count below 24,576.
3. **The `native_episode_receipt.deliver_normaliser` block is present on 4 of 4 rows**, with
   `schema` `saea-deliver-normaliser-v1`, `normaliser_id` `saea-deliver-normalise-v3`, `version`
   `1`, `carrier_lock_key` `slurp` and `applied: true`.
4. **The delivered triples equal the v3 scorer's triples on 4 of 4 rows**, checked offline by
   `analysis.deliver_normaliser_replay` over a copy of the smoke's own sealed outputs plus the same
   triple comparison section 6 ran: the replay's delivered text must equal each row's own delivered
   text.
5. **Invariant I7n is verified at the seal** — the manifest seals clean and
   `core.bundle.outputs.verify_bundle` re-derives every normalised row's delivered bytes from the
   trace's own recorded model response.

**What the four rows will probably NOT show, stated in advance.** On the sealed B1 arm's own bytes
the rule repairs **nothing** on all four of these rows: `applied: true`, `changed: false`,
`rendering_suppressed: true`, 4 of 4. Greedy decoding at temperature 0 is not bitwise reproducible
across batch compositions, so the smoke's own answers may differ and a repair may occur — but the
smoke is **not** expected to exercise the repair path and **acceptance does not require it**. The
repair path is proved by section 6's 1,080-row sealed replay on three arms and by the E11 unit
tests, not by four rows. A smoke row with `changed: true` is equally acceptable provided criteria
1–5 hold.

No answer, reference or quality interpretation, and no scorer. A failure stops cell B8a until the
fix is proven on this same four-row roster.

## 8. The model-free admission read

Registered here, run by the coordinator after the smoke passes. **Zero GPU, zero model contacts.**
It re-applies the registered rule to read-only copies of the three sealed arms and scores the
result with the pinned official scorer — the same shape as the A1 audit
(`docs/results/2026-09-17-slurp-a1-use-projection-audit-v1.md`) and the TRAIN symmetric re-read
(`docs/results/2026-09-17-slurp-train-symmetric-reread-v1.md`), both of which are on the exposure
ledger as zero-contact rows and are this read's precedent.

**Primary metric:** official pooled SLU micro F1 from `slurp-slu-official-train` (pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per arm-side through
`core.scoring_batch`, never sharded.

**Secondaries:** intent (joint scenario+action) accuracy, scenario accuracy, action accuracy,
official pooled span F1, per-row mean official SLU-F1, per-row mean exact slot F1, saves / harms /
ties with the exact two-sided McNemar p.

**Reported beside, never a gate:** `slurp-slu-f1-normalized-v1-train`, the TRAIN symmetric sibling
owner decision 14 registered. Owner decision 7 states that about 2.5 pp of the 64-point bar is
representation alignment rather than capability; owner decisions 23 and 26 make the official number
the metric and the node the legitimate carrier of that alignment. **The verdict states the
symmetric delta and what share of the official gain it represents**, and says out loud that the
share the symmetric scorer scores at zero is representation alignment the system now performs for
itself.

**Resampling:** paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for
the clauses and CI90 for diagnostics, both as percentile pairs of the same retained replicate
sequence. Sensitivity: paired scenario-stratified row bootstrap, same draws and seed. Every table
is reported in **both** the natural-mixture and the equal-scenario weighting. Clusters and strata
come from `analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`
(SHA-256 `07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34`).

`delta = ON minus OFF`, in percentage points; negative means the node is worse.

**Own-null margins:** the TRAIN A own null measured by cell B0r on this exact roster — the CI95
half-widths of (B0r minus B0): **h_SLU = 1.1218** and **h_intent = 1.0051** percentage points.

> **STOP condition, before any table of this read is looked at.** (1) All three sealed comparators
> must reproduce their registered **official** aggregates (section 5) to the hundredth of a point.
> (2) The node-ON side of each arm must reproduce that arm's registered **projection v3**
> aggregates to the hundredth — 51.99 / 79.35, 62.67 / 81.76 and 63.78 / 81.85 — which is what
> section 6's triple equality predicts exactly. (3) Every row of every arm must be accounted for:
> 1,080 in, 1,080 out, no row dropped, no `sample_id` invented. If any of the three fails, the read
> stops and is reported: the same sealed bytes under the same rule cannot give two answers.

### Decision rule, fixed here before any number is read

> **ADMITTED** if and only if **on the anchor base AND on the cell B1 base** all of the following
> hold:
> 1. the CI95 **lower** bound of the paired **official pooled SLU-F1** delta (node ON minus OFF over
>    the same sealed rows) is **greater than 0**;
> 2. the paired **intent** delta is **non-inferior at -h_intent**, i.e. its CI95 lower bound exceeds
>    **-1.0051**;
> 3. **no scenario's paired intent CI95 upper bound lies below zero**; and
> 4. **owner decision 17's diagnostic is reported** — net harmed rows per scenario on every
>    contrast, flagging any scenario with five or more.
>
> The **cell B5e base is read and reported under the same four clauses and does not gate**: it is a
> third base, present to show whether the node's effect survives on top of two admitted modules.
>
> **HARMFUL** only by a **measured loss** (owner decision 25's Method B form): a point estimate of
> official pooled SLU or of intent below **-h** (-1.1218 / -1.0051), or a CI95 **upper** bound below
> zero, on either gating base. An interval that straddles zero with the point estimate inside the
> margin reads **NEUTRAL** with "non-inferiority not proven" stated.
>
> **NEUTRAL** otherwise.
>
> The **TRAIN symmetric number is reported beside and is NOT a gate for this module.** Neither is
> the program bar: this cell is a one-factor module admission, not a bar attempt. The verdict states
> the official pooled SLU each base reaches with the node, and whether any of them clears 64.00, as
> a fact and not as a claim.
>
> **Read exactly once.** No repeat-to-pass, no re-scoring, no second estimator, no re-weighting
> after seeing a number.

**The interval is unusually tight and the verdict must say why.** The ON and OFF arms are the same
sealed rows one deterministic transform apart, so the paired bootstrap carries **no decoding noise
at all** — only the row-to-row variation of the rule's own effect. Cell B0r's own-null margins were
calibrated on a request-identical replicate whose two passes DO differ by decoding noise, so they
are, if anything, conservative here. The verdict states this rather than treating a narrow interval
as extra evidence.

## 9. Failure rule

**The read** cannot fail loudly in the way a flight can; it fails by STOP condition. If a STOP
clause fails, the read stops and the discrepancy is reported before anything else happens.

**The smoke.** A first failure stops the flight and preserves the attempt — no automatic restart,
replay, row filtering, roster, role-graph, prompt, geometry or cap change, and no silent recovery.
**At most one root-diagnosed recovery re-registration**; a second failure closes cell B8a and the
fix must be proven on a four-row dry run before the node is proposed again. One experiment in
flight at a time.

**Resume-recovery clause (owner decision 22 of 2026-09-18).** If the smoke attempt dies of an
**infrastructure** failure with code and request bytes unchanged — never a harness or config defect
— the one allowed recovery may be a **resume-recovery** under item E10 instead of a re-fly: every
complete row of the aborted attempt is kept without selection, every partial or unstarted row is
flown under the same run id, and the merged manifest declares the predecessor attempt with its
trace hash, kept-row list and that list's hash. It changes no question, roster, factor, comparator,
decision rule or cap, and the run-cumulative budget must be re-checked because a resumed attempt and
its predecessor share one run id. (On a four-row smoke a resume will rarely pay; the clause is
registered because owner decision 22 requires every new registration to carry it.)

## 10. What is NOT claimed

- **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster. Nothing is said about Fold B, DEV-1000 or the test split, which stay unread.
- **This is not a bar attempt.** Cell B8a is a one-factor module admission. If a base plus the node
  happens to cross 64.00 official, that is reported as a fact of that base, and "replicated on the
  same roster" (owner decision 1) is not claimed by anything here.
- **No claim that the node adds capability.** The node performs, inside the system, a
  representation alignment that the official scorer charges for and the symmetric scorer scores at
  zero. Owner decision 7 already named about 2.5 pp of the bar as alignment rather than capability;
  admitting the node moves who performs that alignment, not what the system understands. The
  verdict says this in its own words, with the symmetric delta beside the official one.
- **No claim about the rule itself.** Projection v3's content was decided by the A1 audit and fixed
  by item E4; nothing here re-estimates, re-tunes or re-selects it, and the support filter A1
  rejected stays rejected.
- **No component attribution below the rule.** The label half and the filler half move together;
  the per-half counts are reported as diagnostics, not as separate admissions.
- **No claim of idempotence as a general property.** Section 6 records the one anchor row where P2
  is not a fixed point.
- **A structural smoke result is never a quality result.**
- **No claim about any later cell's comparator.** Section 4 fixes the default-plan consequence;
  every later cell owes its own statement of which side of the node its comparator sits on.

## 11. Analysis recipe and the read driver

`docs/readiness/2026-09-19-slurp-b8a-deliver-normalise-v1/analysis-recipe-v1.json` pins the three
sealed arms, the roster metadata, the shared estimators
(`analysis.null_calibration_cli.rows_for`, `analysis.null_calibration.pooled_f1`,
`analysis.paired.resampled_statistic`, `analysis.paired.paired_contrast`,
`analysis.bootstrap._percentile`), the seed, the draws, the two interval levels, the contrasts, the
own-null margins, the STOP condition, the metric list and the expected reproduction values.
`analysis.score_compare_cli` is deliberately not the runner: it hard-codes CI90 and DEV population
names.

**The driver is to be written**, model-free, as
`src/speech_aware_evidence_acquisition/analysis/b8a_delivery_node_read.py` (module
`speech_aware_evidence_acquisition.analysis.b8a_delivery_node_read`, function plus CLI), following
`analysis.deliver_normaliser_replay`'s own discipline: copy in, never write the sealed input, refuse
to overwrite an existing output. Its contract is fixed by the recipe:

1. copy each sealed `outputs.jsonl` to a caller-named working directory and verify its SHA-256
   against the recipe;
2. replay `saea-deliver-normalise-v3` over each copy (`analysis.deliver_normaliser_replay.replay`),
   asserting `model_calls: 0` and 1,080 rows in and out;
3. score OFF (the sealed scores, re-verified by hash) and ON (the replayed copy) with
   `slurp-slu-official-train`, and both with `slurp-slu-f1-normalized-v1-train`, through
   `core.scoring_batch` over byte-identical copies of the sealed bundle, never the sealed directory;
4. assert the STOP condition of section 8;
5. emit the paired contrasts, the per-scenario tables and the decision-17 diagnostic to
   `analysis/SAEA-SLURP-B8A-DELIVER-NORMALISE-PAIRED-ANALYSIS-V1/` under `SPEECHRL_DATA_DIR`;
6. print, and never persist, only aggregates — no utterance text, filler or gold.

Verdict document, on completion: `docs/results/2026-09-19-slurp-b8a-deliver-normalise-verdict.md`.

## 12. Pre-contact evidence on file

In this readiness directory (`docs/readiness/2026-09-19-slurp-b8a-deliver-normalise-v1/`), all
model-free:

| file | what it carries |
| --- | --- |
| `README.md` | the launch runbook: mint the receipt, re-pin and flip, launch the smoke under a worker lease or a Windows Scheduled Task, inspect it, run the read |
| `protocol-registered-v1.json` | the frozen protocol: purpose, arms, factors, metrics, decision rule, STOP condition, budgets, prompt fit, failure policy, what is not claimed |
| `smoke-generation-plan-v1.json`, `smoke-generation-plan-registered-v1.json` | the registered generation plan of the smoke |
| `smoke-fit-plan-v1.json`, `smoke-fit-plan-registered-v1.json` | the registered native contact-fit plan of the smoke |
| `analysis-recipe-v1.json` | the model-free read recipe and the driver contract of section 11 |
| `sealed-inputs-v1.json` | the three sealed arms with every SHA-256 re-derived here, the replay counts of section 6, and the expected reproduction values of the STOP condition |

**No `core.flight.cli check` receipt is on file, and that is deliberate.** `FlightRuntime.preflight`
asserts a clean study tree and reserves the attempt in the durable `AttemptStore`; a registration
agent that has not committed cannot run it without either failing on its own uncommitted files or
writing an attempt reservation it has no authority to make. The composed and protocol hashes above
were therefore computed directly through `core.config.compose` / `core.config.protocol_hash` — the
same two functions `check` itself uses — and the **method was verified against sealed, registered
values on this tree**: the sealed anchor recovery reproduces protocol
`2527b52714789cf6b3fc090ea77aca2fc1fe7657806f4a082aab04d6e4e7158c`, and cell B1's recovery arm
reproduces composed `114b791752e160ed0f409fedf12d034b3cc05a8789b4423d1700cc6cb7df000c` / protocol
`c66d507d1ae03c081d04a72dda7b5be28c29d7d5d22e4f196c38e5912211da2d`, all three exactly the values
the B5e package and cell B1's own note register.

**These hashes describe the fragments exactly as committed**: readiness `held`, the inherited
`preparation` requirement pinned, **no `decision` requirement**. `compose()` hashes the whole merged
fragment set, so adding the decision requirement, flipping readiness and re-pinning the prepared
artifact each change the composed hash and therefore the protocol hash. The re-pin tool does all
three in one cycle and rewrites every dependent hash; nothing here is edited by hand.
