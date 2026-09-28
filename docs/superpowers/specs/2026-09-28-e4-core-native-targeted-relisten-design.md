# E4: core-native targeted re-listen (design)

Date 2026-09-28. Owner decision 180 says to do the core-native re-listen first and to leave
Whisper until E4 has a read. The 2026-09-06 direction (no transcript state, no ASR tool) is **not**
revised. This note is model-free: it registers no cell, authorises no flight and claims no effect.
The carrier is SLURP.

## 0. What exists today

- **The Solver already hears the audio.** Every native role contact is composed from
  `base_messages(ctx)` (`rails/runner.py:2250`). That calls `_agent_messages`
  (`rails/runner.py:1463`), which opens the user message with the row's own speech packet
  (`input_audio` or `input_speech_features`, `rails/runner.py:1524-1539`). The Solver binding uses
  these messages (`rails/runner.py:2796`), and so do supply-variant arms (`:2310`). E4 therefore
  adds no new audio access. It adds a **targeted question about one value**, asked after the answer
  has been decided.
- **The graph** runs Perception, then `solver_i`, `reviewer_i` and `planner_i`, and routes to
  ACCEPT, REVISE, or ACQUIRE followed by acquisition
  (`reproduction/ojw/native_episode.py:1705-1903`). Perception's note
  (`slurp-intent-hypotheses-v1`) carries intent candidates and holds **no slot values**. The
  "current span" is therefore the accepted Solver answer's filler.
- **E18 `speech-reobserve`** (`rails/acquisition.py:50`, `:687`) is a Perception-kind
  `NativeRoleNode` at the acquisition phase (`rails/runner.py:3884-3960`). Only the Planner's
  ACQUIRE reaches it, and B9a-rec routed ACQUIRE on 18 of 1,080 rows, all 18 acquiring 0 items
  (`docs/results/2026-09-22-slurp-b9a-rec-acquisition-node-verdict.md` section 2). E4 reuses the
  node class and its metering, but not that routing.
- **W2 / OBS-E1 / DR-1** built observation revisits as `recut-span` media derivations. SLURP rows
  average about 2.9 s per contact (B9a-rec: 12,642 s over 4,420 contacts), so E4 re-sends the
  **same packet**: no cut, no derived media. Earnings E-C3 (90 s windows) would need the W2
  re-cut.

## 1. Mechanism

**Position.** A post-accept stage, `relisten`, runs after ACCEPT and after the deliver normaliser
(`rails/runner.py:4325-4341`), and before the seal. It reads the normalised values that would be
scored.

**Trigger** (model-free). For each delivered entity `(type t, value c)`, in delivery order, the
stage re-listens to at most **3** entities per row. There is no type filter: the hearing errors are
spread across more than 12 types (business_name 16, place_name 12, food_type 9, time 8). The
decided intent is never re-opened.

**Contact 1: blind re-listen.** It receives the packet, the decided intent and `t`, but **not**
`c`. It uses the pinned template `slurp_relisten_blind_v1.txt` and the format
`slurp-relisten-value-v1 = {"heard": bool, "value": string <= 8 words}`, and it returns the words
the speaker used for `t`. If `heard` is false, or if the returned value `v` is canonically equal to
`c` (`normalize_filler_p2` plus number-word folding), the row keeps `c` and spends nothing more.

**Contact 2: forced-choice confirm** (only when `v != c`). It receives the packet, the intent, `t`,
and `c` and `v` in an order fixed by `sha256(sample_id, t)`, so position bias cancels over the
roster. The format is `{"choice": "A"|"B"|"neither"}`. This is where the owner's "current span"
conditioning enters. It comes second and is paired with a competitor because a draft-conditioned
signal echoed its draft on 71.3 % of rows (MF-7 audit, 2026-09-06).

**Acceptance rule.** Replace `c` with `v` **iff** the blind contact returned `v != c` **and** the
confirm chose `v`. In every other case keep `c`. The alternatives were rejected:

- A confidence rule has no admitted signal: logprob min-token AUROC was 0.69 (not admitted), and
  sample agreement scored 0.535 (`docs/results/2026-09-21-slurp-stage3-prelude-frontier-and-verifier-v1.md`).
- Majority-of-k temperature samples is the route that decisions 112 and 179 closed. Temperature
  also rarely moves a value: the B2 medoid came from sample 0 on 702 of 822 clusters.

Two observations under different framings that must agree is the cheapest rule that can be
pre-declared and carries an echo control. It is asymmetric toward no harm. v1 never deletes or adds
an entity.

**No transcript state.** The returned value is one slot filler of at most 8 words: the same kind of
string the Solver's answer already contains. An over-length or empty value keeps `c` as a per-row
disposition. The value never enters any role's context. The receipt `saea-relisten-v1` binds, per
entity:

- the contact ids;
- `sha256(value)` and `sha256(canonical)`;
- the word count and the choice;
- the accept bit.

The value's bytes live only in the sealed trace, as every draft's do, and in the bound answer when
the value is accepted. No utterance text is requested, stored or used as a key. The frozen core
re-observes its own input under one question. It is not a second answering LLM and not an ASR tool,
and answer authority stays with the core.

**Node-gain claim.** The claim is `SLU-F1(bound column) - SLU-F1(delivered column)` on the same
flight's rows. The two columns differ only by accepted replacements, so the delta belongs to the
re-listen contacts alone.

## 2. Addressable mass and expected effect

The source is the AGREE arm on TRAIN Fold A, 1,080 rows
(`docs/results/2026-09-27-slurp-agree-arm-error-sources.md` sections 3-4, and
`2026-09-27-slurp-knowledge-content-audit.md`).

| class | items | isolated pp SLU | E4 v1 |
| --- | ---: | ---: | --- |
| NEAR + WRONG-VALUE (hearing) | 97 | **4.09** joint | target |
| BOUNDARY | 75 | 2.88 | incidental: extent is a convention (audit K4; 91 of 183 wrong same-type fillers are sub- or super-spans of gold) |
| FORMAT | 11 | 0.39 | skipped by canonical equality; surface format is not a deficit |
| MISSING / SPURIOUS / WRONG-TYPE | 173 / 253 / 51 | 9.80 / 8.46 / 4.63 | out of scope |
| intent via hearing | 10 rows | <= 0.93 intent | out of scope; intent is never changed |

**The upper bound is 4.09 pp SLU-F1, and 0 pp intent by construction.**

**Dependency.** `docs/results/2026-09-28-slurp-node-information-gain-ledger.md` **does not exist
yet**. Its share `p` (the final slot errors that were already wrong in the Perception note) scales
the bound to `4.09 x p`. If that product falls under about 0.4 pp, E4 should not fly (see section
4 for the floor).

**Expected effect.** No measured analogue exists: E-C3 is unflown, and VERIFY-1's +1.40 entity
filter is a precision mechanism. The Fold A flight therefore registers `admission: no-harm`,
`claims_benefit: false` and `harm_margin_pp 0.32`, which is not tighter than the 0.3163 floor. The
read-roster cell declares `expected_effect_pp` equal to the Fold A measured delta, which serves as
its analogue. As an illustration only: at `p = 0.5` and a 30 % save rate, the expected effect is
about 0.6 pp.

## 3. Cost

| item | estimate |
| --- | --- |
| blind contacts | min(entities, 3), about 0.95 per row (1,021 entities on 1,080 rows) |
| confirm contacts | fired on disagreement; bounded by entity-set instability of 7.5 % within a flight to 31 % across seeds, about 0.1-0.3 per row |
| added contacts | **about +1.05-1.25 per row**, against about 4.09 per row in the plan (+25-30 %) |
| repeated audio | the full packet on each contact (about 2.86 s), **about +3.0-3.6 s per row** |
| plan caps | run-cumulative: add +1.3 calls and +3.8 s per row; raise the row `max_contacts` by 6 |
| GPU | at most 0.5 GPU-h per 1,080 rows (B9a-rec's 1.37 s per contact includes long Solver outputs); outputs of 8 words or fewer and the same packet (featcache and prefix cache) make the real cost lower; one resident geometry |

## 4. Measurement

The Phase-1 supply-variant instrument fans out only the **first Solver visit's supply**, and it
cannot carry a post-accept OBS contact. A Solver-visible form, E4-B, would render the value as
acquired evidence to a second Solver visit. That visit is outside Phase 1, so E4-B would fly
cross-flight with an in-chain A/A. Its bar is about 2.5 pp at n = 1,080, which is above anything
the 4.09 bound can deliver after conversion.

**Recommended: E4-A, `same-flight-paired`, shadow delivery.**

- The flight delivers its normal answer. A pure `bind(normalised answer, sealed relisten records)`
  renders the **bound column** from the same flight's sealed bytes, in the same form as the
  projection-v3 deliver node and its replay.
- Each complete column is scored once through `score_complete_derived_copy` and the pinned official
  `evaluate.py`.
- Columns are read per row through the column entries of `stage3_paired_read.py` (row resampling,
  10,000 draws, seed 20260915).
- The floor is 0.735 x sqrt(200 / n): 0.3163 at n = 1,080 and 0.3287 at n = 1,000.
- The read tests one pre-declared rule and searches over no rules, so it is consistent with decision
  179.

The read specification:

- **Primary:** official pooled SLU-F1 (micro), bound column minus delivered column.
- **Guard:** intent. Per-row intent must be identical between the columns; this is tested, and the
  read refuses otherwise.
- **Descriptive:**
  - saves and harms by error kind, with gold read on the scoring side only;
  - the per-type table;
  - a confirm-skipped column, reported but never gating;
  - equal-scenario weighting.
- **Rosters (D3):** `tuning_roster` is TRAIN Fold A, where this design's numbers came from.
  `read_roster` is DEV-2000-ADDED (1,000 rows). The two must not overlap.
- **Claim ceiling:** `nominated`. Promotion means binding in delivery and then a full-system read
  against an in-chain A/A.

## 5. Whisper as a later form twin (note only)

The twin keeps the same trigger, confirm and binder, and replaces contact 1 with a pinned Whisper
pass. Choosing between `c` and `v` would then use a model-free match against a transcript, which
makes transcript text runtime state. It therefore needs:

1. an owner row that revises the 2026-09-06 direction for this twin;
2. a pinned tool receipt: model id and revision, per-file weight sha256, decoding, normaliser and
   runtime build. The 2026-09-12 `slurp-whisper-v1` large-v3 registration is prior exposure to
   inherit, not this receipt;
3. a `core.base` tool-catalog row and exposure-ledger rows before contact;
4. the same roster and instrument as E4-A.

Earnings E-C3 (decision 174, after E-C1 and E-C2) is the same primitive with a W2 `recut-span`
around each numeric.

## 6. Implementation plan

**[ID]** marks identity-bound files (`core/flight/runtime.py:7310-7322, 7654-7660`). Changing one
breaks every pinned prepared artifact and forces a loop-form `repin_cell.py` of the ready cells. E4
is designed to touch none of them.

| file | change |
| --- | --- |
| `rails/relisten.py` (new; not under `rails/probes/`) | trigger, canonical compare, order, acceptance, `bind()`, receipt |
| `core/base.py` | policy `saea-obs-targeted-relisten-v1`; `STAGE3_ALGORITHMS` label |
| `rails/native_episode_config.py` | `native_episode.relisten {policy, max_slots_per_row, value_max_words, delivery: "shadow"}`; refuses with `supply_variants` or a grouped Solver in v1 |
| `rails/runner.py` | post-accept stage: a Perception-kind `NativeRoleNode` at phase `relisten`, with metering as at `:3884`; seals receipts |
| `configs/probes/slurp_relisten_{blind,confirm}_v1.txt`, two response formats | pinned |
| `core/bundle/outputs.py`, `analysis/relisten_column.py` | a `relisten` bound column, built as `supply_variants` columns were |
| `core/flight/runtime.py`, `rails/kb_policy.py`, `rails/knowledge_provider.py`, `rails/phase_supply.py`, `rails/core_client.py` **[ID]** | **untouched**; if the wiring needs `runtime.py`, re-pin the ready cells (E16 preflight names them) |

**Tests** (`tests/unit/test_e4_targeted_relisten.py`):

- an absent key leaves the episode and receipt byte-identical;
- the trigger cap applies;
- a FORMAT-only difference spends no confirm;
- `heard = false`, an over-length value and `neither` all keep `c`;
- the candidate order is deterministic;
- intent never changes;
- `bind` replay equals the runtime record;
- no role context ever contains a re-listen value;
- a confirmatory-split plan is refused.

**Gates:**

- `engineering_base_check`
- `stage3_effect_floor_check`
- `stage3_algorithm_label_check`
- `finite_completion_policy_check`
- `derived_media_confinement_check`
- `flight_registration_check`
- `results_ledger_check`
- `handoff_freshness_check`
- `ruff`

**Sequence:**

1. `analysis.native_episode_dry_run` (zero contacts).
2. A **4-row charged dry run** (form proof, `claims_benefit: false`). It passes when:
   - every row seals `saea-relisten-v1`;
   - the contact count equals the declared count;
   - there are zero truncations;
   - the bound column renders and scores;
   - there are 0 intent differences.
3. Fold A, 1,080 rows.
4. The DEV-2000-ADDED read.

## 7. Open questions

1. What is `p` in the ledger? If `4.09 x p` is under about 0.4 pp, should E4 be shelved before any
   flight?
2. Should the confirm contact also see Perception's intent candidates, or only the decided intent?
3. Should v2 add a deletion rule (both contacts "not heard" leads to dropping the entity)? It
   reaches SPURIOUS (8.46 pp) but is precision-risky and would need its own no-harm margin.
4. Should there be a MISSING probe for intent-bound types absent from the answer (relative-day
   date: 30 of 72 missed)? That is recall, not hearing.
5. Should the Fold A flight use shadow delivery or live delivery?
6. Which plan hosts E4: v2.0 PLAN, or COMP-1's successor if COMP-1 is admitted first? Only one
   experiment is in flight at a time.

## 8. Coordinator rulings (2026-09-28, after E1)

Recorded by Claude Opus 5.5 at the coordinator's (Fable 5.1) direction, after the node information-gain ledger
(`docs/results/2026-09-28-slurp-node-information-gain-ledger.md`, sections 2.3 and 5) landed. These rulings answer
section 7 and supersede section 2's dependency paragraph where they differ.

1. **`p` is not narrowable from the ledger, so E4 is NOT shelved (Q1).** Of the 407 delivered gold-side errors, 71 are
   visible hearing/span origin and 229 are undetermined because the Perception note is not a transcript. The hearing
   share therefore lies between 17 % (71 / 407) and 74 % ((71 + 229) / 407), and `4.09 x p` lies between about 0.71
   and 3.0 pp, above the 0.4 pp shelving line at both ends.
2. **v1 carries two shadow columns from the same contacts (Q3, Q5).**
   - (a) **replace-only**: the section 1 acceptance rule, unchanged;
   - (b) **replace + drop-when-both-contacts-say-unheard**: as (a), plus the entity is dropped when the blind contact
     returns `heard = false` and the confirm contact also answers that it was not heard. It is aimed at the 253
     SPURIOUS predictions (74 of them with the filler in the note). The confirm contact is therefore also fired on a
     blind `heard = false`, so that both contacts vote; the cost table in section 3 is re-estimated at implementation.
   - The delivered column stays the flight's normal answer; both columns are rendered by `bind()` from the same sealed
     relisten records. The blind contact also records the hearing state of the undetermined items, a diagnostic
     gain in itself.
3. **The forced-choice contact does NOT see Perception's intent candidates (Q2).** It sees the decided intent only.
4. **The missing-slot probe is out of v1 (Q4).** It is E3's job.
5. **Shadow delivery, on TRAIN Fold A first (Q5).**
6. **Host plan: the AGREE arm bytes (Q6),** that is COMP-1's successor after its read. One experiment in flight.
7. **Expected effect and bar.** Both columns declare `expected_effect_pp` 0.0 with claim ceiling `nominated`, since
   no measured analogue exists; the bar is the twin/shadow null.
8. **Metrics.** Official pooled SLU-F1 (micro) is the primary metric for both columns; intent is identical between
   columns by construction and is tested as a guard (section 4).
