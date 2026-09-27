# SLURP test sample and closure rosters: design record, v1

## 1. Status

Owner decision 141 (2026-09-27, `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`): the
programme's absolute 95 per cent intent target of decision 137 is a TEST-SET number; dev sampling comes
first for iteration, and a coverage-guaranteed sample of the test split is PERMITTED for comparison,
superseding decisions 99 / 107 / 108 to that extent and no further. This record is the design that
permission was used with, and the receipts it produced. It is a model-free preparation:

* **Nothing here registers a cell, authorises a contact, writes an owner allowance, flips a readiness
  state, countersigns an exposure row or touches a runtime surface.** No model, tokenizer, encoder, ASR,
  scorer, server, GPU or network was reached (offline guard armed before the first input, zero outbound
  attempts). No audio file was opened. No worker pool was used.
* **Test gold WAS read, offline, once**, for stratification, inside the sealed freeze process
  (decision 141 item 5), and both receipts say so in their own words: `scenario` and `action` of the
  governed `test.jsonl` were read to stratify the prompt draw; the `sentence` field was touched digest-only
  for the TRAIN text-overlap count of section 6.3; `tokens`, `entities`, `sentence_annotation`, `intent`,
  `recordings[].wer / ent_wer / status` were never read. Per-intent facts are published as AGGREGATES
  only; no item carries its stratum (`stratum_withheld_per_item: true`). No test id and no label was
  written into any config, query vector, store or fragment.

Generator: `scripts/build_slurp_test_sample_roster.py` (one invocation writes both receipts and the
proof). Tests: `tests/unit/test_build_slurp_test_sample_roster.py`. Proof and size table:
`docs/checks/speech-aware-evidence-acquisition/2026-09-27-slurp-test-sample-roster/`.

## 2. The two rosters, sealed at one moment

| Roster | Receipt | Recordings | Prompts | Headset / far-field | Audio (s) | `split_identity_hash` (carrier-prefixed, the value an ExecutionPlan declares) | bare-id hash |
|---|---|---|---|---|---|---|---|
| `SLURP-TEST-SAMPLE-3010-V1` | `docs/receipts/rosters/slurp-test-sample-3010-v1.json` | **3,010** | **682** | 1,456 / 1,554 | 8,206.436875 | `0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9` | `6c1283003458abe08b8c636b14643e62c56d9cc858560d171aa6f97641fbd167` |
| `SLURP-TEST-CLOSURE-10068-V1` | `docs/receipts/rosters/slurp-test-closure-10068-v1.json` | **10,068** | **2,292** | 4,825 / 5,243 | 28,705.5019375 | `377b937df3c29e52e3596426741b03129fa526bf677d92b5c03b78dd8dc2457b` | `7f4de1fa4e91d46f07687ec3ac561bce29be8e00b99741712a2ad0cba835a4a8` |
| parent `SLURP-TEST-FULL-13078-V1` (frozen `947e79e4`) | `docs/receipts/rosters/slurp-test-full-13078-v1.json` | 13,078 | 2,974 | 6,281 / 6,797 | 36,911.9388125 | `7247647b8c8b37becd564b7031691565d4e6b09d8e124823054906d36372c95d` | `3f7063cb8b1e60d69c383d2215b5f244bbd7164d484010193a093a5e879389bd` |

Both receipts are `saea-roster-receipt-v1`, `carrier_lock_key: slurp`, `split_role: final-report`,
`roster_role: evaluation`, seed `20260927`, and each carries `derived_from` (the parent by relpath, file
SHA-256 and both identity hashes; the sibling by roster id and identity hash; the partition proof), the
per-intent table, both weightings, the gold-access statement and the pin of the proof document. The
roster ids carry the REALISED recording counts: the draw is sized in prompts (section 3), so 3,000 target
recordings became 3,010.

**Partition proof** (recomputed by the unit test from committed bytes): sample ∩ closure = ∅ at recording,
utterance and prompt-number level; sample ∪ closure = 13,078 recordings = the parent, and the union hashes
to the parent's `7247647b…`. Audio seconds add up (8,206.436875 + 28,705.5019375 = 36,911.9388125).

## 3. Why the unit of the draw is the prompt, not the recording

Decision 141's cost statement asks for two things at once: (1) sample ∪ complement = the frozen 13,078, and
(2) the complement stays an unbiased final read while the sample is compared against. The
`SLURP-DEV-2000-ADDED-V1` precedent draws RECORDINGS with at most one per utterance. Applied here it would
put the other ~3.4 recordings of every sampled SENTENCE into the closure roster (test prompts carry 1–56
recordings, mean 4.40), so every milestone read of the sample would expose text the final read is later
scored on -- the leak the one-shot rule exists to prevent. Putting those recordings in neither roster
breaks (1). The only design satisfying both is a **partition by test prompt**: every recording of a
selected prompt goes to the sample and every recording of every other prompt goes to the closure roster.
Consequences, stated plainly:

* the conservative sample size is the PROMPT count (rho = 1: every recording of a prompt moves together,
  which is close to the truth for a text-driven intent error); the recording count is the optimistic one;
* the sample and the closure share **no sentence** (`sample_closure_shared_sentence_digests: 0`);
* speaker and prompt-author disjointness is impossible inside one split and is NOT claimed (section 6.2).

## 4. Size: the table and the recommendation

Instrument, not taste. Absolute: CI95 half-width of a proportion at the target p = 0.95 (and at today's
p = 0.8222, the v2.0 lock arm on TRAIN Fold A). Paired: the programme's own null,
`SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-OWN-NULL-V1` (h_intent 1.1520 pp at 913 prompts,
utterance-clustered), scaled by sqrt(913 / prompts). Weighted: the natural-mixture number of a floored
roster is post-stratified (per-intent accuracy weighted by full-test recording shares), so its half-width
is 1.96·sqrt(Σ w_i² p(1−p)/n_i) over the per-intent prompt counts the floor rule leaves in each roster.
Full arithmetic per row in `size-table.json`.

| Target n (rec.) | Prompts | Feasible at floor 5 | Floor-driven share | Sample h at p=.95, rho=0 / rho=1 | Sample natural-mixture h (post-strat., rho=1) | Sample paired h | Closure rec. / prompts | Closure h at p=.95, rho=0 / rho=1 | Closure natural-mixture h (rho=1) | Closure paired h | Milestone cost (system arm) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1,000 | 227 | **NO** (floors alone need 279 prompts ≈ 1,227 rec.) | – | 1.35 / 2.84 | – | 2.31 | 12,078 / 2,747 | 0.39 / 0.82 | – | 0.66 | 4.1k contacts, 1.65 GPU-h (np4) |
| 1,500 | 341 | yes | 0.82 | 1.10 / 2.31 | 2.69 | 1.89 | 11,578 / 2,633 | 0.40 / 0.83 | 0.87 | 0.68 | 6.1k, 2.5 GPU-h |
| 2,000 | 455 | yes | 0.61 | 0.96 / 2.00 | 2.18 | 1.63 | 11,078 / 2,519 | 0.41 / 0.85 | 0.89 | 0.69 | 8.2k, 3.3 GPU-h |
| **3,000** | **682** | yes | **0.41** | **0.78 / 1.64** | **1.71** | **1.33** | **10,078 / 2,292** | **0.43 / 0.89** | **0.94** | **0.73** | **12.3k, 5.0 GPU-h** |
| full 13,078 (reference) | 2,974 | – | – | – | – | – | – | 0.37 / 0.78 | – | 0.64 | – |

Cost columns use the DEV-2000-ADDED replicate's measured np4 rate (4.09 contacts and 0.00165 GPU-h per
row); protocol section 7.3's September rate (5.021 contacts, 0.00321 GPU-h per row) is in the JSON beside
it. A direct arm adds one contact per row.

**Recommendation: 3,000 (realised 3,010 recordings, 682 prompts), overturning the 2,000 prior.** The
arithmetic: going from 2,000 to 3,000 widens the closure's conservative half-width by 0.04 pp
(0.851 → 0.892 plain; 0.893 → 0.938 post-stratified; the full split's was 0.783, so the closure keeps
88 rather than 92 per cent of the full read's precision) and its paired half-width by 0.03 pp
(0.694 → 0.727), while it tightens the sample's post-stratified natural-mixture half-width by 0.47 pp
(2.18 → 1.71), its plain conservative half-width by 0.37 pp (2.00 → 1.64) and its paired half-width by
0.30 pp (1.63 → 1.33), and it drops the floor-driven share of the sample from 61 to 41 per cent, so the
natural-mixture estimate rests on 403 rather than 176 mixture-drawn prompts. The price is +50 per cent per
milestone (about +1.65 GPU-h at the np4 rate), spent only at milestones (decision 141 item 4), never per
round. 1,000 is infeasible with any per-intent floor of 5 (the floors alone need 279 prompts); 1,500 is 82
per cent floor-driven. What no size in this table buys: a sample that adjudicates 95 per cent to within
one point under the conservative reading -- that needs about 1,825 prompts and would eat the closure. The
sample is a milestone instrument at ±1.6–1.7 pp; the closure roster is the verdict instrument at ±0.9 pp.

An unread receipt can be superseded before its first contact at no cost (the EVO fold v1 → v2 precedent):
"drawn once" binds from the first contact, not from the freeze. If the coordinator or owner prefers
2,000, the successor is one `--target-recordings 2000 --write` under a new date, and this pair is left
committed and unread.

## 5. Stratification

* **Stratum**: gold intent `scenario_action` of the prompt. Test carries **59 intents** over 2,974 prompts;
  every scored intent is present in the split. Capacities and per-intent recordings are in the receipts'
  `per_intent` table (`test_utterances`, `test_recordings`, `sample_*`, `closure_*`).
* **Floor**: the sample takes **5 prompts** per intent and **5 prompts are reserved for the closure** per
  intent wherever the intent has at least 10 test prompts (53 of 59 intents). Five is the smallest count
  at which a per-intent read is more than presence: a 0/5 against a 5/5 is the coarsest per-intent alarm
  the sample can raise, three would not separate one bad prompt from a bad intent, and eight would push the
  floor-driven share of a 3,000-row sample to 63 per cent (429 prompts).
* **Intents below the floor** (2–9 test prompts) are split as evenly as possible with the closure taking
  the larger half, so BOTH rosters keep them: `audio_volume_other` 6 → 3 / 3, `music_settings` 6 → 3 / 3,
  `music_dislikeness` 4 → 2 / 2, `iot_hue_lighton` 3 → 1 / 2 (sample / closure prompts).
  `iot_wemo_on` has exactly 10 and takes the plain floors, 5 / 5.
* **`general_greet` has ONE test prompt** (15 recordings). It goes to the CLOSURE roster and is the one
  scored intent ABSENT from the sample (58 of 59 present). This deviates deliberately from "take all of
  them": the final read must cover every scored intent, and a prompt cannot be in both rosters without
  breaking the sentence-level independence of section 3. Equal-stratum readings of the sample run over 58
  intents and say so.
* **Remainder**: 682 − 279 floor-driven = **403 prompts**, apportioned by `core.roster.mixture_quotas`
  against test's natural prompt mixture, capped per intent by capacity minus both floors.
* **Draw**: `core.roster.freeze_roster` over prompt candidates, seed 20260927, one shared rng advanced
  across intents in ascending name order (the module's stated rule); deterministic from the committed
  parent receipt and the lock-pinned `test.jsonl` (`fe3449af…`). Per-intent prompt quotas are the
  receipts' `per_stratum`; per-intent recording counts are `strata_counts`.
* **Two weightings** (decision 141 item 3), both in the receipts under `weightings`: natural mixture =
  full-test per-intent shares (recordings and prompts given), read as the POST-STRATIFIED sum of per-intent
  accuracies -- the raw roster mean is NOT the natural-mixture number, because the floors over-represent
  small intents; equal stratum = 1/K over the intents present in the roster (59 closure, 58 sample).

## 6. Hygiene

### 6.1 Disjointness by id -- 87 sources, verdict CLEAN

`disjointness.json` (sha256 `859472d1ba73bea1ead1af12d7fd61ac5207d828af388436073dcfac32c9fc57`)
intersects both rosters with every `slurp` roster receipt under `docs/receipts/rosters/`, every `slurp`
probe-sample receipt, every `slurp` probe-binding config and every knowledge store / exemplar pool snapshot
under the data root (`source_sample_ids` only), at recording, utterance and bare prompt-number level, using
the FULL builder's own source enumerators (imported by file path, not re-implemented). Result: **zero shared
ids on every pair** for R01C (`slurp-stage3-construction-r01c`, 625), R01 (800), TRAIN Fold A v2 (1,080),
Fold B v2 (1,080), the exemplar pool (`slurp-evo-exemplars-v2`, 430, and its `size-pool-annotated-exemplars`
snapshots), DEV-1000 (1,000), DEV-2000 (2,000), DEV-2000-ADDED (1,000), DEV-500-B, the devel remainders,
FINAL60, every DEV-ladder rung and all 33 knowledge snapshots. The one non-zero pair is the parent, where
the overlap is the roster itself by construction (3,010 and 10,068), and it is checked as an equality, not
tolerated. Exposure closure: neither new identity hash appears in any ledger row; the parent's hashes
appear only in the three DRAFT, `consumed = no` preparation rows of 2026-09-23 -- UNREAD.

### 6.2 Speaker and prompt-author overlap -- reported, not claimed away

Counted in memory from the governed `metadata.json` (`recordings[].usrid`, `userid_amt`); no id written.

| | sample | closure | shared | sample-only | closure-only | closure recordings by an identity also in the sample |
|---|---|---|---|---|---|---|
| speakers | 134 | 139 | **131** | 3 | 8 | **10,035 of 10,068 (99.67 %)** |
| prompt authors | 359 | 534 | **323** | 36 | 211 | 7,518 of 10,068 (74.67 %); 214 closure and 47 sample recordings carry no author id |

Speaker disjointness between the two rosters is impossible: SLURP's speakers recorded prompts across the
whole split. The partition is by PROMPT, which is what makes the closure independent of the sample at the
sentence level; speaker and author are shared and a reader should know it.

### 6.3 Sentence-level overlap with TRAIN -- the number the id guard cannot see

The construction-versus-knowledge guard compares ids; these counts say how much of each roster's TEXT a
TRAIN-built store could already contain. Method: the `build_slurp_dev2000_roster.py` digest pass
(whole-sentence SHA-256 and word 6-gram digests via `rails.proposer`), against the TRAIN construction text
pool `slurp-construction-text-pool-v1` (11,514 prompts, 11,483 sentence digests, 25,475 gram digests).

| population | prompts | exact sentence matches in TRAIN | prompts sharing a TRAIN 6-gram |
|---|---|---|---|
| sample | 682 | **2** (0.29 %) | 71 (10.4 %) |
| closure | 2,292 | **10** (0.44 %) | 261 (11.4 %) |
| DEV-2000-ADDED, same method (reference) | 913 | 1 (0.11 %) | 113 (12.4 %) |
| DEV-1000, same method (reference) | 1,000 | 1 | 111 |

The exact matches are a property of the corpus (SLURP re-uses a few short prompts across splits) and are
reported, not acted on. Sample-vs-closure shared sentences: 0. This is the first time a test `sentence`
field has been touched in this repository; it was touched digest-only, inside the sealed offline process,
for this count alone, and the frozen parent's own text pass stays recorded as NOT RUN (protocol section 9
item 3 is exercised here under decision 141, not edited there).

## 7. The allowance gate: what the owner signs, and what the mechanism refuses today

### 7.1 What exists

`contracts.plan.require_owner_split_allowance` (`d8c184c4`) admits `split_role: final-report` only when the
plan carries `owner_allowance = {path, sha256}` naming a committed `saea-owner-split-allowance-v1` receipt
under `docs/receipts/owner/` whose bytes hash to the pin, whose `status` is exactly `authorised`, whose
`split` names the plan's carrier AND **one** `split_identity_hash`, whose `permitted_run_ids` contains the
plan's run id and partitions into disjoint `read_run_ids` + `preparation_run_ids`, and which names the dated
owner decision and states in `venue` why the read is not promoted to a `papers/<slug>` repository. The only
receipt committed, `docs/receipts/owner/2026-09-23-slurp-test-split-allowance-v1.json`, binds the FULL
roster's hash `7247647b…` and reads `pending-owner`.

### 7.2 The exact signature the SAMPLE needs -- one owner signature away, nothing else

A NEW receipt `docs/receipts/owner/<date>-slurp-test-sample-allowance-v1.json` (this commit does not write
it; the FULL receipt cannot be reused because its `split.split_identity_hash` is a single value and check 7
compares it to the plan's), with:

1. `schema: saea-owner-split-allowance-v1`, `study: speech-aware-evidence-acquisition`;
2. `status: "authorised"`;
3. `split.carrier_lock_key: "slurp"` and `split.split_identity_hash:
   "0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9"` (SLURP-TEST-SAMPLE-3010-V1;
   the receipt's `roster_receipt_sha256` and `carrier_split_identity_hash` beside it as the FULL receipt
   does);
4. `permitted_run_ids` = `read_run_ids` ∪ `preparation_run_ids`, disjoint: each MILESTONE check is its own
   owner-named read run id (the gate allows exactly ONE attempt per read run id, so a series of milestones
   is a list of run ids named in advance, or a re-pin per milestone), plus the three label-free
   preparations on the sample's own rows (packet ENCODE+PROMOTE, speech query encoding, vector export) --
   unless the owner authorises the FULL preparations first, which already cover all 13,078 rows and would
   make the sample's preparations unnecessary (section 7.4);
5. `dated_owner_decision`: "141 (2026-09-27)" with its text, and `venue`: the owner's sentence on why a
   development-side milestone read of a test sample runs in this study rather than in a `papers/<slug>`
   carrier;
6. every plan then carries `execution_profile: bounded-discovery-probe`, `split_role: final-report`,
   `split_identity_hash` = the sample's, and `owner_allowance = {path, sha256}` of that receipt; and every
   contact is registered in `docs/exposure-ledger.md` before its result is read.

Separately and later, the CLOSURE needs its own receipt of the same shape binding `377b937d…`, with exactly
one read run id (and the direct arm's, if authorised), and the FULL receipt's read run ids
(`SAEA-SLURP-TEST-FULL-LOCKED-SYSTEM-V1`, `-DIRECT-V1`) become void to the extent of decision 141.

### 7.3 What the mechanism as built REFUSES, and what would have to change (not changed here)

`contracts.gate_exposure._require_final_report_disjointness` intersects a `final-report` plan's roster with
**every other committed roster receipt of the carrier** and refuses on the first shared id. A partition of
the frozen parent shares ids with its parent by construction. Probed model-free against this worktree's
committed receipts (stub plan, no allowance, no contact):

```
SLURP-TEST-SAMPLE-3010-V1   REFUSED: shares 3010 sample id(s) with slurp-test-full-13078-v1.json
SLURP-TEST-CLOSURE-10068-V1 REFUSED: shares 10068 sample id(s) with slurp-test-full-13078-v1.json
SLURP-TEST-FULL-13078-V1    REFUSED: shares 10068 sample id(s) with slurp-test-closure-10068-v1.json
```

So as the code stands the mechanism admits only ONE roster whose ids appear in no other committed roster
of the carrier -- in effect only the full split, and now not even that. Every other check passes for the
new receipts: `_carrier_roster_receipts` parses all 35 `slurp` receipts without `GateClosed`, and
`_final_report_roster` finds each of the three hashes exactly once. **What would have to change** (a paired
code change with tests, never made by this commit): the gate must recognise a DECLARED PARTITION and earn
the exemption from live bytes -- for a roster whose `derived_from.source_roster` names a committed parent
and whose `derived_from.sibling_roster` names a committed sibling, skip the parent and the sibling in the
intersection ONLY after re-proving from their committed items that roster ∩ sibling = ∅ and
roster ∪ sibling = parent (hash equality), and symmetrically skip a receipt that declares the plan's roster
as its parent under the same re-proof; every other receipt and every snapshot stays in the intersection.
The alternative that needs no code change is to withdraw the FULL roster from `docs/receipts/rosters/`
(an immutable record: it would be superseded, not deleted, and its three draft ledger rows and prep
configs re-pointed), which the coordinator should weigh against the code change.

### 7.4 Consequence for the FULL preparations already registered

The three DRAFT preparation rows of 2026-09-23 (`SAEA-SN-TEST-FULL-PREPROCESS`,
`SAEA-SLURP-TEST-FULL-SPEECH-QUERY-ENCODING-V1`, `SAEA-SLURP-TEST-FULL-QUERY-VECTOR-EXPORT-V1`) and their
configs bind the FULL roster's hash. They are label-free and would serve BOTH new rosters (their outputs
are keyed by media identity), but with these receipts committed their plans are refused at gate time by
section 7.3 even after the FULL allowance is flipped. Nothing live is broken -- the FULL allowance is
`pending-owner` and decision 108 deferred the read -- but the coordinator must choose: the gate change of
section 7.3, or re-registering the preparations per roster. Either way the closure roster, not the full
split, is the final-read roster from decision 141 onward.

## 8. What this commit does not do

It does not write an owner allowance, register a run id, write an exposure row, build a runtime view
(`configs/dataset/…`), a D1 supplement or a preparation config for either roster, change any contract or
gate, fly anything, contact anything, or open any audio. It leaves the FULL receipt, its disjointness
proof, its allowance receipt and its draft rows byte-identical.

## 9. Allowance signed for the SAMPLE under owner decision 151; the closure is not

Owner decision 151 (2026-09-27, "决策3：现在签" -- "Decision 3: sign now.") signed the section 7.2 receipt
for the sample: `docs/receipts/owner/2026-09-27-slurp-test-sample-allowance-v1.json`, schema
`saea-owner-split-allowance-v1`, status `authorised`, binding `SLURP-TEST-SAMPLE-3010-V1` (split identity
`0164dabf…`, both identity hashes recomputed from the committed item ids when the receipt was written) and
naming nine run ids: the sample's three label-free preparations (`SAEA-SN-TEST-SAMPLE-3010-PREPROCESS`,
`SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1`, `SAEA-SLURP-TEST-SAMPLE-3010-QUERY-VECTOR-EXPORT-V1`)
and six one-attempt reads -- the locked PLAN system's own sample read
`SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-V1`, which every milestone is compared against, and the
numbered family `…-MILESTONE-{01..05}-V1` for composed arms. There is no direct-baseline read on the sample.
A milestone id is consumed by its one attempt; a further milestone needs a fresh id in a successor receipt
under a fresh coordinator report. Two things the signature does NOT do, stated in the receipt itself: it
does not lift the first-contact gate of decision 151 (no sample contact of any kind, preparations included,
until the coordinator has reported a dev-admitted composed arm to the owner in conversation; not met at
signing), and it does not touch the closure -- `SLURP-TEST-CLOSURE-10068-V1` receives no receipt and stays
`pending-owner` until the Stage-3 closure read, while the FULL receipt of 2026-09-23 is left byte-identical.
One departure from section 7.2 item 5 is recorded plainly: the owner did not dictate a venue sentence, so the
receipt's `venue` is the coordinator's statement of the reason decisions 141 and 151 carry (a development-side
milestone comparison, not the final read; the closure's venue stays with decision 108). Proof:
`tests/unit/test_final_report_split_role.py` section 4 loads the committed receipt and shows a sample-identity
`bounded-discovery-probe` plan accepted for every permitted run id at plan and gate level, the closure and
FULL identities refused naming the hashes, `paper-scale-confirmatory` refused, and the FULL receipt still
refusing.
