# Cell B8b-anchor: the Reviewer slot-audit context block on the sealed anchor, preregistration

Registered before contact, 2026-09-19, by the item E19 agent on branch `fable/e19`.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer, server and
paid-API contacts**. The resident service was never started, stopped or queried; no run directory
was read or written; no flight lock was touched; and no utterance text, filler or gold is printed or
persisted anywhere in this package.

Package: [`2026-09-19-slurp-b8b-anchor-reviewer-audit-v1/`](2026-09-19-slurp-b8b-anchor-reviewer-audit-v1/README.md).

## 1. Why this cell exists, and why it is re-registered

Owner directive 26 of 2026-09-18 asks that an analysis this program trusts be placed **inside** an
agent node rather than left in a report. Item E11 built the write-side instance (the delivery
normaliser, cell B8a). Item E12 built the read-side one: the A3 coverage and slot-loss audits
rendered as declared context at the Reviewer boundary, so the node that is supposed to criticise a
draft finally has something deterministic to criticise it against.

Item E12's cell B8b was registered on the Node Context Policy **L1** stack. On 2026-09-19 cell B7a
v2 read that stack **HARMFUL** — official pooled SLU −0.3100 pp [−1.8072, +1.1211], intent −0.6481 pp
[−2.1849, +0.8688], +11.6 % GPU hours for no gain — and the pre-authorised branch of owner decision
32 fired: cells B7r and B7c close unflown, level L2 stays unflown, and **cell B8b is re-based on the
anchor and re-registered**. Owner decision 15 forbids flying any cell on a HARMFUL base.

**The block never depended on the L1 policy.** The B7a v2 rendering diagnostics say so in one line:
*0 parsed of 1,243 structured review-finding rows — FALLBACK-RAW on 100 % of them.* The audit read
no parsed Reviewer output. What it needed was a place to be appended — the structured **rendering
slot** of the Reviewer's own draft boundary. Item E19 gives it a second attachment, `sealed-draft`:
with that boundary at `raw`, the block is appended to the **sealed Solver response** the Reviewer
already receives. That is an addition to exactly the same one thing the consumer would otherwise
have got, and it lets the cell fly on the anchor with the audit as its only factor.

## 2. What the block is, and what it is not

`rails/slot_audit.py` plus the committed template `configs/probes/ncp_slurp_slot_audit_reviewer_v1.txt`
render the released construction view `knowledge/slurp/semantic/slot-audit-v1/` — 60 intents, 54
entity types, 9,354 construction utterances, counts and shares only — for the intent of the draft
under review, followed by four flags the **harness** computes:

| flag | fires when |
| --- | --- |
| `TYPE-UNSEEN` | the draft carries an entity type the construction table never attests with the drafted intent |
| `EMPTY-DRAFT` | the draft carries no entity and the intent's construction rows carry one at least as often as `empty_draft_min_entity_row_share` (0.5) |
| `MISSING-COMMON` | a type attested on at least `missing_common_min_row_share` (0.5) of the intent's construction rows is absent from the draft |
| `REPRESENTATION` | a filler violates `saea-spoken-form-v1` (no ASCII digit, no colon, no slash) for a type whose released convention is spoken |

It is **not** a judge, a retriever, a tool or a second model. It makes **zero contacts of any kind**,
so the bounded contact ceiling stays 11 and every budget is the anchor's, unchanged. Every
substituted value is a construction count, a construction share, a released convention sentence, a
closed flag name, or an entity **type** the draft or the table already carries — never a filler,
never a sentence, never an utterance id, never any gold of an evaluated row.

### The boundary that makes it legal

The construction pool is the governed SLURP TRAIN split **minus** every utterance with a recording
in TRAIN Fold A, TRAIN Fold B or DEV-1000, and the 2026-09-13 exclusion. The builder refuses a pool
that kept an evaluated row and refuses a table not bound to the pool it proved clean. The released
table carries counts and shares only, which is why it is committed rather than kept under
`SPEECHRL_DATA_DIR`: its pin is a git blob hash.

## 3. The one factor, and the one further key that is not a factor

The factor is one episode-class key, `native_episode.reviewer_audit`. OFF is the key's absence,
which is the sealed anchor's own configuration. ON is the view id with its two pins and the three
registered thresholds.

The fragment declares **no** `native_episode.context_policy`. The composed policy is therefore the
key's own bare `"raw"` arm: nothing is rendered at any boundary, every boundary emits a
`level: "raw"` receipt row whose `rendered_sha256` equals its source's `content_sha256`, and the
**only** place a byte moves is the Reviewer's draft boundary, which carries the appended block and a
`slot_audit` receipt naming it. Perception, Solver and Planner requests are byte-identical to the
anchor's.

Held identical: the policy `phase-native-candidates-review-revise-v1`, both knowledge stores and
their phase and candidate supply, every `phase_material` instruction template and response format
(the Reviewer's stays `null`), `phase_tools`, the roster, the model fragment, the serving geometry
and the eleven-contact ceiling. Bookkeeping that must differ: the run and attempt ids, the smoke
cell's `contact_cap`, this cell's own prepared-supply pin, the per-cell feature-cache identity
(`speech_feature_matcher_policy_id`, `speech_feature_key_representation_id`) and `what_this_is`.

Proofs, all model-free:
`tests/unit/test_native_episode_runner_reviewer_audit.py::test_on_the_anchor_shape_the_block_moves_only_the_reviewer_contacts`,
`…::test_on_the_anchor_shape_the_reviewer_gains_exactly_the_block`,
`tests/unit/test_reviewer_slot_audit_block.py::test_the_audit_appends_to_the_sealed_draft_under_an_all_raw_policy`,
and `tests/unit/test_b8b_anchor_reviewer_audit_config.py`.

### 3.1 `native_episode.finite_completion_policy` — a harness declaration, not a factor

Both cells declare `native_episode.finite_completion_policy = "deliver-latest-or-abstain"`. Item E13
admitted that key after the cell B7a v1 recovery arm aborted at 1,451 contacts when a single Reviewer
completion hit the 512-token `max512` cap under the module default `"raise"`. It renders **no request
byte** — `rails.runner` reads it once into the core `NativeEpisodeSpec` — and only decides whether a
finite completion aborts the flight or is **retained** with a `terminal_disposition` reason
`"finite_completion"` (the latest delivery-eligible Solver draft delivered, or an abstention).
`tests/unit/test_slurp_finite_completion_row.py` flies both arms and proves the request bytes do not
move.

The comparator is asymmetric on this axis by construction: the sealed anchor flew **without** the
key. Its own exposure receipt records **zero** finite completions, so on the comparator side the key
would have changed nothing — the asymmetry is *measured*, not assumed. The count of retained
finite-completion rows on this side is a mandatory diagnostic, no row is ever filtered, and the
verdict states the asymmetry.

## 4. Arms, comparators and order

| | |
| --- | --- |
| treatment | `SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1`, TRAIN Fold A, 1,080 rows |
| comparator | **the sealed dual-store anchor**, run `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1`: official pooled SLU micro F1 **48.53363**, intent accuracy **77.96296** (842/1080), 5,417 model calls, 3.3880 GPU hours ([`docs/results/2026-09-14-slurp-native-train-a-anchor.md`](../results/2026-09-14-slurp-native-train-a-anchor.md)) |
| not a comparator | the retired Node Context Policy L1 stack — cells B7a v1/v2, B7r, B7c — and the superseded L1-based B8b registration |
| order | the four-row smoke first; the arm opens only after the smoke seals |
| twin | none registered. A derangement or token-matched control flies only if this cell shows a positive CI95 lower bound against the anchor |

**No comparator is ever re-flown or re-scored.**

### Which side of the delivery node this contrast sits on

Both arms are **node-free**: neither carries the delivery-time normaliser node (module M3, cell
B8a), which was admitted after this base was sealed. The verdict must state it, and the number is
therefore not directly comparable to a later default-plan number that carries the node.

## 5. The prepared Perception supply, and what its rebuild proves

Each cell carries **its own** prepared artifact, derived by the model-free
`core.flight.cli prepare-supply` step under its own run id:

| cell | artifact | file sha256 | output sha256 |
| --- | --- | --- | --- |
| arm | `prepared/SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1/phase-supply-v1.json` | `4d3233fd71b2ffa2ffa2e7b1b50d944f238c0729203647460f26fe6986b1f82c` | `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |
| smoke | `prepared/SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-SMOKE-4-V1/phase-supply-v1.json` | `b89ec1caad20d5750932cd8fc441fb4d69fe704781a606d494f2e3bfaf91d233` | `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` |

The artifact's identity digest pins the cell's **whole** composed configuration, which differs from
the anchor's, so a fresh artifact had to be derived. Its **output** is byte-identical to the sealed
anchor's own Perception output (`ba5e1faa…`, the same value the anchor's `PREPARE-V1-R2` and
`RECOVERY-V1` artifacts carry) on 1,080 of 1,080 rows. That is the model-free proof that **neither
declared key moves a knowledge-selection byte**. `--allow-output-change` must never be passed.

## 6. Metrics, diagnostics and resampling

**Primary: official pooled SLU micro F1** from `slurp-slu-official-train` (the pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per manifest through
`core.scoring_batch`, never sharded. **Guard: intent (joint scenario+action) accuracy.**

Secondaries: intent, scenario and action accuracy; official pooled span F1; per-row mean official
SLU-F1; per-row mean exact slot F1; saves / harms / ties with the exact two-sided McNemar p.
Projection v3 (`slurp-slu-official-projected-v3-train`) and the TRAIN symmetric sibling
(`slurp-slu-f1-normalized-v1-train`) are reported beside every official number (owner decisions 7
and 14); owner decision 23 keeps the **official, unprojected** number the one that decides.
Natural-mixture and equal-stratum weightings are both reported.

Resampling: paired per-row bootstrap over the 1,080 shared rows, 10,000 draws, seed 20260919, CI95;
the same draws and seed for the per-scenario sensitivity. Rows are paired by recording id and **no
row is dropped**, including retained finite-completion rows.

Own-null margins, the TRAIN A own null measured by cell B0r on this exact roster and geometry:
**h_SLU = 1.1218 pp**, **h_intent = 1.0051 pp** at CI95
([`docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md`](../results/2026-09-17-slurp-b0-review-off-redecision-v2.md)).
Owner decision 38 fixes the regime: a contrast involving a configuration uses that configuration's
own request-identical replicate; the sealed anchor has none, so B0r's own null is the registered
fallback, and the retired imported DEV-1000 half-widths are never used again.

Mandatory diagnostics, every one of them:

1. The four flag counts over every Reviewer contact, **including the zeros**, with the
   applied / not-applied split and, for every not-applied contact, its machine reason (the only
   reason this attachment can emit is `draft-unparsed`).
2. The **block-rendered receipt** count: Reviewer contacts whose `slot_audit` row carries
   `applied: true` and whose boundary row's `rendered_sha256` therefore differs from its source's
   `content_sha256` — the only place in the whole flight where a `level: "raw"` row's rendered bytes
   are not its source's.
3. The per-boundary `saea-node-context-policy-v1` aggregate: rows, level, `raw_reason` distribution,
   and the count of rows whose `rendered_sha256` equals their source's. Under the composed all-raw
   policy that count must be every row except the applied-true Reviewer draft rows.
4. The before/after table of the four flags against the delivered answer, as a diagnostic only.
5. `planner_action_illegal`: the count of Planner outputs that are not an exact declared action
   token, with roles and revision indices. The harness raises on one — it closed the cell B7a v1 arm
   — so a non-zero count is a flight failure, not a metric.
6. The count of rows whose `terminal_disposition.reason` is `finite_completion`, with the
   interrupted role's breakdown. Retained and scored as delivered, never filtered.
7. Reviewer parse rate under the repository's registered findings parser, for continuity with the
   retired L1 diagnostics; it gates nothing, because this cell declares no producer response format.
8. Native task-contract tool-call count per role against the declared ceiling.
9. Contacts per row and the revision-route distribution, beside the anchor's.
10. **Prompt tokens per role** beside the anchor's, and the whole-run prompt-token and GPU-hour
    deltas. The block adds tokens to the Reviewer contacts only; the efficiency note states the
    per-role figure, never a whole-run figure alone.
11. Per-scenario tables for every reported metric, and net harmed rows per scenario.

### Decision rule, fixed here before any number is read

> **HARMFUL is read first** (owner decision 25, Method B): only by a **measured loss** — a point
> estimate of the official pooled SLU or of intent below **−h** (−1.1218 / −1.0051), or a CI95
> **upper** bound below zero. An interval that straddles zero with the point estimate inside the
> margin is **not** harmful.
>
> **ADMITTED** if and only if all four hold against the **sealed anchor's** score artifact:
> 1. the CI95 **lower** bound of the paired **official pooled SLU-F1** delta is **greater than 0**;
> 2. **intent is non-inferior** at the own-null margin — its CI95 lower bound exceeds **−1.0051**;
> 3. the **TRAIN symmetric scorer** `slurp-slu-f1-normalized-v1-train` **agrees in sign** with the
>    unprojected primary; and
> 4. **no scenario loses intent beyond the null band** — no scenario's paired intent CI95 **upper**
>    bound lies below zero.
>
> **NEUTRAL** otherwise, with "non-inferiority not proven" stated in those words where an interval
> straddles zero. A beneficial but not CI95-proven movement is **recorded** as such (owner decision
> 25) and never claimed as an admission.
>
> **Read exactly once.** No repeat-to-pass, no re-scoring, no second estimator, no re-weighting after
> seeing a number, no row filtering.

Under owner decision 30 this is an **effectiveness** cell: a NEUTRAL or HARMFUL read advances the
one-factor streak toward the v2.0 lock trigger.

**Not a bar attempt.** The verdict states the official pooled SLU the arm reaches and whether it
clears 64.00 as a **fact**, never as a claim, and "replicated on the same roster" is not claimed by
anything here.

## 7. Prompt fit, and a blocker that is not this cell's

The block is bounded by construction: one header line, at most one profile line per entity type
above `profile_min_row_share` (0.05) for the drafted intent, at most four flag lines, one footer. It
adds tokens to the **Reviewer** contacts only.

A blocker must be recorded honestly. Since item E17 merged,
`core.flight.runtime._assess_prompt_budget` measures the preflight prompt budget against the live
24,576-token slot instead of the retired 32,768-token module default, and on this geometry the
**anchor's own** Perception prompt fails it: `rendered_text_tokens` 18,640, `required_window_tokens`
19,183, physical margin +5,393, operational reserve 8,192, operational margin −2,799,
`COMPACT_REQUIRED`. It reproduces byte for byte with and without this cell's two declared keys (same
`payload_sha256` `1315b387d21c24feaa6af03e918ef4f0ba4fc14fc51c18373dc01ca9b4ceab46`), so it is a
pre-existing condition of every SLURP native cell on this geometry, not a property of cell
B8b-anchor. It must be cleared by the coordinator — a declared `context_budget_limits` block, a
wider slot, or a revisited operational reserve — before any flight. The composed and protocol hashes
in this package were therefore derived model-free through `core.flight.repin.compute_cell_identity`,
which composes exactly the four fragments the CLI composes.

## 8. Budgets and cost reporting

Arm: 11,880 generation contacts, 47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0
fit-inclusive GPU hours, 6,480 native task-contract calls, one official complete score. Expected
about 5,420 contacts and 3.6 GPU hours. Smoke: 44 / 176 / 117 / 1.0 / 24 / zero scoring jobs;
expected about 20 contacts. Encoder, ASR and paid-API calls are **0**. Ceilings are not targets.

The FIT rows are fitted **inside** the same worker (smoke) or campaign (arm), under the same lease;
`coordinate-fit` must not be run, or a row is double-charged. Arithmetic: 4 × 11 × (1 + 3) = 176 and
1,080 × 11 × (1 + 3) = 47,520.

Reported cost: contacts and GPU hours beside the anchor's 5,417 and 3.3880; prompt tokens per role;
wall-clock and the realized contacts-per-row distribution.

## 9. The four-row smoke — structural acceptance only

Six criteria, listed verbatim in the package README section 4 and in
`protocol-registered-v1.json` `smoke_acceptance.criteria`. Never scored, never interpreted for
quality, never reported as a result.

## 10. Failure rule

Stop and preserve on the first failure. No automatic restart, no replay, no row filtering, no change
to the roster, role graph, prompts, geometry or caps. At most **one** root-diagnosed recovery
re-registration (a resume-recovery under owner decision 22 for an infrastructure failure with code
and request bytes unchanged); a second failure closes the flight and the fix is proven on the
four-row roster first.

## 11. What is NOT claimed

* **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster and every claim of this cell stops at it. Fold B, DEV-1000 and the test split stay
  untouched and unread.
* **No gold of an evaluated row enters the block**, at build time or at runtime. The only text of an
  evaluated row that can appear is the draft's own entity **type** names, which the consumer already
  holds in the sealed draft immediately above.
* **Nothing about the retired L1 stack.** Cell B7a v2 read HARMFUL and cells B7r and B7c closed
  unflown; no number here is evidence for or against any of them, and the superseded L1-based B8b
  registration is not a comparator.
* **No claim that the Reviewer *acts* on the block.** The cell measures whether the loop's outcome
  moves; whether the Reviewer's criticism changes because of the audit, or for some other reason, is
  not separable here.
* **No attribution to one flag.** The four move together; the per-flag table is a diagnostic, not
  four separate admissions.
* **No claim about the A3 audit's own counts.** They bound what the block can touch; they are never
  a predicted gain.
* **No claim that a larger or differently thresholded table would do better.** The thresholds are the
  registered defaults and are not tuned here; changing one is a new cell.
* **No claim that the retained finite-completion rows are comparable to the anchor's** (section 3.1).
* **No claim that the block's token cost is free.** It is reported per role beside the anchor's.
* **A structural smoke result is never a quality result**, and this is not a bar attempt.

## 12. Pre-contact evidence on file

| what | where |
| --- | --- |
| protocol | `2026-09-19-slurp-b8b-anchor-reviewer-audit-v1/protocol-registered-v1.json` |
| analysis recipe | `2026-09-19-slurp-b8b-anchor-reviewer-audit-v1/analysis-recipe-v1.json` |
| four registered plans | `…/{generation,fit,smoke-generation,smoke-fit}-plan-registered-v1.json` |
| exposure rows | `docs/exposure-ledger.md`, four rows, `consumed = no` |
| decision receipt | `coordination/slurp-b8b-anchor-reviewer-audit-v1/root-admission-v1.json`, decision id `slurp-b8b-anchor-reviewer-audit-admission-v1` |
| the mechanism | `docs/superpowers/specs/2026-09-17-node-context-policy-design.md` section 19 (E19) |
| the superseded registration | `docs/readiness/2026-09-19-slurp-b8b-reviewer-audit-v1/` |

## 13. What this package does not authorise

Any arm flight before this cell's own four-row smoke seals; any flight on the retired L1 base; any
ASR, transcript, encoder or paid-API contact; re-flying or re-scoring any comparator;
`--allow-output-change` on the re-pin tool; `coordinate-fit`; any default-plan edit or
harness-admission entry before the sealed verdict; any DEV-1000, Fold B or test-split contact.
