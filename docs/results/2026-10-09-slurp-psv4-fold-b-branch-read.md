# Cell P-SV-4 (NX round R4; same-flight Perception branch, boundary key K6p) branch read: NOT NOMINATED -- level-2 intent b-k6p vs a-agree -0.19 pp CI95 [-0.56, +0.19] against a twin bar of 0.23 pp and a declared +1.1; the K6p block-rank lift (+15 rows at block rank 1) does not reach the note (top1 -0.09 pp), and the level-2 branch Solver column is shown to replicate A's Solver request, on TRAIN Fold B (DESCRIPTIVE)

Read 2026-10-09 (UTC; read outputs generated 22:00Z to 22:07Z) by Claude Opus 5.5 (analysis agent, on the
coordinator's brief, Fable 5.1) in the worktree `fable/psv4-results` (model-free; `core.flight.cli` and `lease_cli`
were not invoked; no GPU, model, server, encoder or tokenizer contact; no scoring in this note -- the three official
column scorings were made once by the registered driver). READ row `SAEA-SLURP-STAGE3-PSV4-FOLD-B-BRANCH-READ-V1` was
root countersigned at master `6a8d317fc` (2026-10-09T21:52:14Z), after the seal and before any branch column score
existed. Recipe `docs/readiness/2026-09-30-slurp-stage3-psv4-fold-b-v1/analysis-recipe-v1.json` (sha256
`ed92a6acd940bb387d2d406211f20ddaf122bb4a4fa06e808db378afa05ad102`), recipe id
`slurp-stage3-psv4-fold-b-branch-analysis-v1`, rule kind **`level2-intent`**. Paired row bootstrap, cluster key
`sample_id`, 10,000 draws, seed 20260929, TRAIN gold through the governed loader and `slurp-slu-official-train`.
Owner decisions 184 (the read form), 186 (Fold B rollout exposure), 190 (floors), 208 (P-SV-4 flies) and the NX
programme row R4 (`docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`, section C2).

The driver was `scripts/flights/psv/psv_read.sh psv4` (run once by root). It called
`scripts/analysis/slurp_perception_branch_read.py` (sha256
`499598f3726f97e2050c1d2bd8424afe2ab943be3e45376e91a71de3ddbe626e`).

Outputs under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-PSV4-FOLD-B-BRANCH-READ-V1/`:

- receipt `perception-branch-read.json` (schema `saea-perception-branch-read-v1`) sha256
  `a47153eb25b436b2b6d065206d78070dfb7992f7c7cd2d5fd87d8145efddbc61`;
- `twin-null/`: `verdict.json` `c4d1429391d3a3539179985665acf24adb6ed411dd88516dffd238cb543fb002`,
  `score-contrasts.json` `9705e0234564bb9068d15d8d037feb8a3efd42e0a64341886003a9eab77e9333`,
  `per-scenario-tables.json` `8ca737146a7b8908e3296ca7b5999a54513fdcabc9728b859285521a326fdb74`,
  `stop.json` `4fa300620a61a3133a40a3923f83d8fe8a81a9f77f099c8a69bc1337ed1f8fc3`;
- `branch/`: `verdict.json` `2b9fbba08cd138bb1d82cf38c8e7485f4b46acd1fb395042e289c391d0288b6b`,
  `score-contrasts.json` `22768b8520fa073634c119920a73d9bd695c1e2f0a981ee4a6d20a1a7406231f`,
  `per-scenario-tables.json` `e892c5d973dbc4ee5e0d514acdc89c3862ac6bda0f04f575624b51cd7fa22124`,
  `structural.json` `150e09dcd5b16e36386894256d825185742c14ff1ae9906b760fdf4ea1da2de9`,
  `efficiency.json` `1694b7cbf601bad8ef9a7a95b0c4b8b5f861d5d656a8e5b461619a5b0b82dfca`,
  `stop.json` `b8da2273aa51f4b30368b70a2f02431daff56e65d66a4eca9a5207a30d6401b2` (status PASSED; official
  SLU-F1 reproduced to 1e-16);
- the three column scorings: `supply-variants/score-summary.json` under the sealed attempt, sha256
  `5374c226927e68dfd6cf20f1ec269486f5b373be70e7ce56f5007f2583663d29` (column score files: a-agree `076b0d96...`,
  b-k6p `ef8a14c0...`, t-twin `74c0a492...`).

Sections 1, 3 and 3a add numbers from a read-only aggregate pass of this agent over the sealed attempt (outputs,
trace, the three column score files, the campaign log) and over the governed TRAIN loader (gold intent held in
memory only). The pass counted items, read `usage.prompt_tokens`, compared hashes and counted correctness per cell;
it persisted nothing. No utterance text, gold label, slot filler, note text or model output was printed or
persisted. Only counts, rates, deltas, ids and hashes appear below.

**DESCRIPTIVE.** Development numbers on a TRAIN construction fold (decisions 28 and 86); branch-local, never a
system-level or test claim. Claim ceiling "nominated". The K6p key family was chosen offline over the sealed
vectors of BOTH folds (selection disclosure, package README; coordinator ruling 2026-09-30): this Fold B read
carries a selection bias of unknown size, which could only have favoured B. The verdict word belongs to the
coordinator (decision 139).

## 0. Answer in five lines

1. **Primary (registered, level 2):** official intent b-k6p minus a-agree **-0.19 pp [-0.56, +0.19]** (1 save /
   3 harms) against the twin intent bar 0.23 pp and the declared +1.1 pp; SLU guard holds (+0.08 [-0.52, +0.68]).
   The registered rule lands in **NOT NOMINATED** (not harm).
2. **The key was delivered:** K6p put gold at boundary-block rank 1 on 815 rows against A's 800 (+15 net; 23 up,
   8 down), in block on 1,029 against 1,015 -- exactly the pinned proof's Fold B counts (815 / 1,029).
3. **It does not reach the note:** Perception's note puts gold first on 887 (B) vs 888 (A) rows (top1 -0.09
   [-1.39, +1.20]); gold-on-list +0.46 [-0.65, +1.57] sits inside the twin present bar 0.56. At A's own rank
   conversions the B note implies about -0.2 intent rows. The +1.06 pp offline prediction assumed block rank 1
   converts like note rank 1; it does not.
4. **Instrument finding:** the level-2 branch Solver column did not carry the branch note -- every b-k6p and
   t-twin first-visit Solver prompt equals A's in tokens (1,080 / 1,080) and in rendered candidate supply (1,080 /
   1,080, including the 713 rows whose B list differs); the same holds in P-SV-1, P-SV-2 and P-SV-3. The level-2
   primary is therefore a second A/A replicate, and the closure rests on level 1 (line 3).
5. **Line status:** the K6p key-source line -- the last registered intent item of the NX programme -- is CLOSED.
   Intent stays LOCKED at COMP-1b (decision 229); the residual is Perception recall (gold-on-list 91-93 %) and
   rank, with no registered lever left. The programme continues on the slot line (R1 iteration 2 flying, v4g
   locked, Stage S supply rounds next).

## 1. Identities and what flew

| item | value |
| --- | --- |
| cell / run | `slurp-native-stage3-psv4-fold-b-v1` / `SAEA-SLURP-STAGE3-PSV4-FOLD-B-V1`, attempt `attempt-slurp-native-stage3-psv4-fold-b-generation-v1` |
| program | `phase-native-candidates-review-revise-pbranch3-l2-v1` (ceiling 15; K = 3, level 2) |
| branches | `b-k6p` (B, key_source K6p: facet `prepared/SAEA-SLURP-CENTRED-CENTROID-KEY-V1/key-v1.jsonl` `98533f82...`, query `prepared/SAEA-SLURP-CENTRED-QUERIES-V1/fold-b/query-vectors-speech-segments.jsonl` `6b056fef...`, agreement unchanged), `t-twin` (replicate of A), `a-agree` (A, delivering, last) |
| roster | `SLURP-EVO-FOLD-B-V2`, 1,080 rows, split identity `4407794c...`, roster receipt `docs/receipts/rosters/slurp-evo-fold-b-v2.json` (`47b89b9e...`) |
| config / protocol | composed config `02ed6409e04341152a11738eaafe4779d066769b3af09483d10e2577c0dc643a`, protocol `6e095615dd9a246219709d4345cc3bb08f593a5dd0c9edb6d25a92386074ae6b` |
| flight commit | **`684f970ef`** (`study_repo_dirt` empty), on the attached resident `slurp-np4` session `serving-slurp-native-candidate-five-train-a-np4-v1` (session receipt `af74c99b...`) |
| run manifest / outputs / scores | `60711bd280392e6074c9f2708f0c40e167fddeeb0e29ec3249d0ab5c37745710` / `f995c24037f6795588c84593c70cd5d692eafcc58d9a9fd22b64006d81929fac` / `0f48df905e483e47d380563a4392813d6a1bd2d13ad288bd77e6f8787171f6b1` |
| trace / trace manifest / generation manifest / flight receipts | `1410cad5...` / `5c9ada7b...` / `759c8946...` / `7fdadb18...` (receipts hash `af731634...`) |

**Pre-flight refresh.** The registered plans predated the `registered-supply-binding` finding of
`scripts/checks/flight_registration_check.py` (commit `38ff537f2`, 2026-10-03: a registered supply declaration
must equal the runtime's). `f3e7e8f4e` regenerated the four registered plan copies so they declare the minted
`prepared_phase_supply` pin (the writer now copies the cell baseline's pin verbatim, as the NX writer does), and
`5b5ea2ce4` added the model-free preflight test `tests/unit/test_psv4_cell_registration.py` (FIT cap, budgets,
identities, supply binding); merged as `396d2ac26` (launch gate PASS on both cells, the arm with the
`tuning-roster-unverified` advisory only). After the NX R1 arm sealed, `psv_flip.sh psv4` re-pinned the two cells
at the new instrument commit (`ab37def0e`, `fda61c249`, converging at `684f970ef`).

**Chain.** `scripts/flights/psv/batch_chain_psv.sh psv4` through the batch driver on `slurp-np4`, launched
directly (the stale `queue_psv4.sh` was not used). Campaign log `/home/chao/batch-campaign-1-psv4-20261009T182255Z.log`
(18:22:55Z to 21:05:04Z, 2 h 42 min including the smoke and the seal). Smoke
`SAEA-SLURP-STAGE3-PSV4-FOLD-B-SMOKE-4-V1`: 4 rows, 32 contacts, COMPLETED at the same commit (manifest created
18:22:40Z), inspect passed, never scored. Arm generation 18:27:52Z to 21:02:06Z; run manifest 21:03:06Z; scored once
(finalize, one job, 96 s).

| run | rows | contacts | speech s | prompt / completion tokens | GPU-h (monitor) | wall | state |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
| `SAEA-SLURP-STAGE3-PSV4-FOLD-B-V1` | 1,080 | 8,727 | 25,470.906 | 67,920,467 / 564,908 | 2.567 (mean utilisation 81.7 %) | generation 9,435 s (2 h 37 min); campaign 2 h 42 min | COMPLETED, FINALIZED, scored once |

Contacts by role: Perception 3,240 (3 per row), Solver 3,271 (3,240 first visits + 31 revisions), Reviewer 1,111,
Planner 1,105. Against the registered caps (16,200 contacts, 47,322 speech s, 16.4 GPU-h) the flight spent 54 %,
54 % and 16 %. Dispositions: finite completion 6, revision limit 7 (disjoint); tool calls 0; context-fit
compaction 0. The two non-delivering branches add 4 contacts per row, 4,320 in total, 49.5 % of the flight.

**Supply and fit (the branch's declared change).** Boundary items supplied per Perception contact:

| branch | 8 items | 3 / 1 / 0 items | prompt tokens per Perception contact, mean / max (min) |
| --- | ---: | --- | --- |
| `a-agree` (delivering) | 1,076 | 1 / 1 / 2 | 3,594.9 / 3,814 (2,506) |
| `b-k6p` (K6p key) | **1,080** | 0 / 0 / 0 | 3,602.4 / 3,820 (3,518) |
| `t-twin` | 1,076 | 1 / 1 / 2 | 3,594.9 / 3,814 (2,506) |

The re-keying changes which items are shown, not how many (B fills the 8-item block on all rows, including the 4
rows where the description key admits fewer); cost +7.5 prompt tokens per Perception contact, far inside the
24,576-token slot. First-visit Solver prompt: mean 10,231.5, max 14,709 tokens -- **identical in all three
columns on every row** (section 3a).

**Custody.** Every row carries a level-2 `saea-perception-branch-arms-v3` receipt (1,080 / 1,080). The delivering
note reproduces the ledger driver's P-node parse on 1,080 / 1,080 rows (0 differ, 0 missing; 28 raw duplicate
rows; collapsed rank never differs from raw rank).

| branch | note_parse_status ok | duplicates-collapsed | list size 1 / 2 / 3 |
| --- | ---: | ---: | --- |
| `a-agree` (delivering) | 1,052 | 28 | 48 / 264 / 768 |
| `b-k6p` | 1,062 | 18 | 49 / 233 / 798 |
| `t-twin` | 1,053 | 27 | 52 / 274 / 754 |

## 2. The branch tables

### 2.1 Level 1: the branch note and the supplied block (beside, never gating)

| branch | top1 % | present % | rank 1 | rank 2 | rank 3 | absent | mean gold rank when present |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `a-agree` | 82.22 | 91.02 | 888 | 77 | 18 | 97 | 1.115 |
| `b-k6p` | 82.13 | 91.48 | 887 | 78 | 23 | **92** | 1.126 |
| `t-twin` | 82.04 | 91.11 | 886 | 80 | 18 | 96 | 1.118 |

| contrast (right minus `a-agree`) | metric | delta pp | CI95 pp | half-width | discordant |
| --- | --- | ---: | --- | ---: | ---: |
| twin null `t-twin` | present | +0.09 | [-0.37, +0.56] | 0.46 | 7 |
| twin null `t-twin` | top1 | -0.19 | [-0.83, +0.46] | 0.65 | 14 |
| `b-k6p` | present | +0.46 | [-0.65, +1.57] | 1.11 | 41 |
| `b-k6p` | top1 | -0.09 | [-1.39, +1.20] | 1.30 | 49 |

The twin present bar (|offset| + half-width) is 0.556 pp; B's +0.46 sits inside it. The utterance-level reads
(reported beside) equal the row-level reads to four decimals.

**The mechanism the cell was built on: gold at supplied-block rank** (this agent's pass; gold offline only):

| branch | gold at block rank 1 | in block, rank 2-8 | off block | in block total |
| --- | ---: | ---: | ---: | ---: |
| `a-agree` (description key + agreement, as flown) | 800 | 215 | 65 | 1,015 |
| `b-k6p` (K6p) | **815** | 214 | 51 | **1,029** |
| `t-twin` | 800 | 215 | 65 | 1,015 |

Moves A -> B: block rank 1 gained on 23 rows and lost on 8 (+15 net); into the block on 21, out of it on 7 (+14
net). B's 815 / 1,029 equal the pinned proof's Fold B K6p counts (`analysis/SAEA-SLURP-K6P-ARTIFACT-PROOF-V1/proof.json`,
`ad34e12f...`), so the key reached Perception exactly as built. The registered +26 was measured against
centroid + agreement (789); the flown A (description key) already had 800, so the available lift was +15.

The block-rank lift does not survive Perception: note rank 1 moves 888 -> 887. Perception re-ranks the block
itself. The note's own changes are small and mixed (rank 3 +5, absent -5, rank 2 +1, rank 1 -1). Applied to A's
measured conversions (98.65 / 20.78 / 11.11 / 0.00 % at ranks 1 / 2 / 3 / absent), the B note implies
-0.99 + 0.21 + 0.56 + 0 = **-0.2 intent rows (-0.02 pp)**.

### 2.2 Level 2: the branch Solver column (primary; official, `slurp-slu-official-train`)

| column | intent % | official SLU-F1 % | per-row SLU-F1 % |
| --- | ---: | ---: | ---: |
| `a-agree` (delivering) | 82.78 | 62.54 | 42.64 |
| `b-k6p` | 82.59 | 62.61 | 42.74 |
| `t-twin` | 82.87 | 62.75 | 42.90 |

| contrast (right minus `a-agree`) | metric | delta pp | CI95 pp | half-width | saves / harms |
| --- | --- | ---: | --- | ---: | --- |
| twin null `t-twin` | intent | +0.09 | [0.00, +0.28] | 0.14 | 1 / 0 |
| twin null `t-twin` | official SLU-F1 | +0.21 | [-0.37, +0.79] | 0.58 | -- |
| twin null `t-twin` | per-row SLU-F1 | +0.26 | [-0.16, +0.69] | 0.43 | 15 / 8 |
| **`b-k6p` (primary)** | **intent** | **-0.19** | **[-0.56, +0.19]** | 0.37 | 1 / 3 |
| `b-k6p` (guard) | official SLU-F1 | +0.08 | [-0.52, +0.68] | 0.60 | -- |
| `b-k6p` | per-row SLU-F1 | +0.09 | [-0.35, +0.54] | 0.45 | 15 / 15 |

Twin bars: intent 0.2315 pp, SLU-F1 0.7855 pp (the provisional floors of decision 190 are 0.65 / 1.49 pp). The
delivered row (A through Solver, Reviewer and Planner; never contrasted) scores official intent 83.24 % and
SLU-F1 62.53 %; it agrees with A's first-visit intent outcome on 1,075 / 1,080 rows.

Conversion P(correct intent in the column | gold rank r in that branch's note), against the ledger's 97.57 /
26.98 / 12.0 %:

| branch | rank 1 | rank 2 | rank 3 | absent |
| --- | --- | --- | --- | --- |
| `a-agree` | 98.65 % (876 / 888) | 20.78 % (16 / 77) | 11.11 % (2 / 18) | 0.00 % (0 / 97) |
| `b-k6p` | 96.84 % (859 / 887) | 30.77 % (24 / 78) | 17.39 % (4 / 23) | 5.43 % (5 / 92) |
| `t-twin` | 98.42 % (872 / 886) | 23.75 % (19 / 80) | 16.67 % (3 / 18) | 1.04 % (1 / 96) |

Read the B and T rows with section 3a: their Solver saw A's note, not their own, so these are A's Solver outcomes
tabulated by the other branch's note rank (B's 5 "absent" successes are rows where A's note had gold).

### 3a. Instrument finding: the level-2 branch Solver did not carry the branch note

The design (`rails/runner.py`, `perception_branch_solver_messages`) renders a non-A branch's first Solver visit
over an `agent_states` view whose Perception state content is replaced by the branch's own note
(`_perception_note_view`), and records the value ids actually rendered (`candidate_supply_value_ids`). The sealed
bytes show the swap had no effect on what the Solver received:

| check (b-k6p vs a-agree, per row) | rows |
| --- | ---: |
| B note text differs from A's | 1,009 / 1,080 |
| B candidate list differs from A's | 713 / 1,080 |
| first-visit Solver `prompt_tokens` equal to A's | **1,080 / 1,080** (also t-twin) |
| rendered Solver `candidate_supply_value_ids` equal to A's | **1,080 / 1,080** (incl. all 713 differing-list rows) |
| Solver request history (agent state, supplied evidence, task instruction) equal to A's; control turn equal after masking the contact id | 1,080 / 1,080 |
| B Solver answer text equal to A's (twin: 1,029) | 1,009 / 1,080 |

Outcome cross-tab on the 82 rows where gold's note rank differs between A and B: the B column is correct exactly as
often as the A column in every cell -- for example, gold absent from A's note but rank 1 in B's: 0 / 10 correct in
both columns; rank 1 in A and absent in B: 5 / 6 in both; rank 2 in A and rank 1 in B: 5 / 13 in both. The B column
follows A's note.

The same check over the sealed P-SV-1 (both attempts), P-SV-2 and P-SV-3 outputs: the rendered Solver candidate ids
of the treatment branch equal A's on every row (lists differ on 674-686, 465 and 455 rows respectively). So every
level-2 branch column flown so far was an A/A replicate of A's Solver request. Not root-caused here: the rendered
prompt evidently does not read the replaced `content` of the Perception state (whatever the Solver's history and
candidate rendering read, it is not the swapped field); a model-free unit test that a non-A branch with a different
note renders a different Solver prompt is the obvious guard.

Consequences:

- The P-SV-4 primary measures sampling noise of one request, not K6p. Its NOT NOMINATED word is mechanically
  correct but uninformative; the closure of K6p rests on level 1 (section 2.1).
- P-SV-1 to P-SV-3 gated on level 1 (presence), so their verdicts stand. Their level-2 "beside" numbers do not:
  P-SV-2's SLU-F1 +0.81 [+0.11, +1.66] (the observed `min_candidates = 3` knob) and P-SV-3's "the Solver still
  answers absent gold on 9 of 105 rows" were A replicates. The 2026-09-30 coordinator reading already struck the
  P-SV-1 Solver-contrast lead as an artefact; this finding generalises it to the whole column.
- No level-2 Perception-branch read should be registered until the render is fixed and proven by that test.

## 3. Reviewer length truncations and the finite-completion rows

The campaign log holds 6 `workflow_execute_error` events (18:44:07Z, 19:00:24Z, 19:10:22Z, 19:59:53Z, 20:11:08Z,
20:40:38Z). Each is one contact; each is logged on 7 lines (vertex ability / call / super-step / workflow errors
and their propagation), which gives the 42 log lines carrying `finish_reason`. By role:

| role | non-authoritative completions (`finish_reason` length, the 512-token cap) |
| --- | ---: |
| Reviewer (`reviewer_0_role`, the first Reviewer visit) | **6** |
| Perception / Solver / Planner | 0 / 0 / 0 |

The finite-completion policy (`native_episode.finite_completion_policy` `deliver-latest-or-abstain`, item E13) did
what it is declared to do: on each of the 6 rows the truncated Reviewer contact was rejected as non-authoritative
(`terminal_disposition` reason `finite_completion`, role `reviewer`, stage `review`, revision count 0, planner not
consulted; `interrupted_role` recorded), the episode stopped, and the latest Solver answer -- A's first-visit
answer -- was delivered (role visits 2). No arm aborted. The 6 rows are scored in the delivered column (4 / 6
intent correct, the same 4 as A's first-visit column on those rows).

They do not touch the branch read: the branch Perception contacts and the three first-visit Solver contacts precede
the Reviewer, every row carries its level-2 fields (1,080 / 1,080), and the columns contrasted in section 2 are
first-visit answers. The 7 revision-limit rows (Planner REVISE after the one executed revision; disjoint from the
6) delivered the latest revision (4 / 7 intent correct against 3 / 7 in A's first-visit column); they too lie after
the branch contacts.

For the programme, this failure mode is already gone: the NX base is the review-off COMP-1b graph (programme
section F), and the NX R1 campaign log (`/home/chao/batch-campaign-1-nxr1-20261009T152010Z.log`) holds 0
`workflow_execute_error` events and no Reviewer node.

## 4. The registered rule, applied mechanically, and the verdict

NOMINATED iff the intent CI95 lower bound is above zero AND the point exceeds the twin intent bar AND the SLU-F1
CI95 lower bound is not below minus the twin SLU bar. BRANCH-LOCAL HARM iff the intent CI95 upper bound is below
zero and the point magnitude exceeds the twin bar.

- intent CI95 lower bound above zero: -0.56, **no**;
- intent point exceeds the twin intent bar 0.23: -0.19, **no**;
- SLU guard: lower bound -0.52 >= -0.79, **holds**;
- harm: upper bound +0.19 is not below zero, **no**.

Driver verdict `NOT NOMINATED`. (The rule kind is `level2-intent`, not presence: P-SV-4 is the first P-SV cell whose
primary is the Solver column. Gold-on-list was reported beside, and it too stays inside its twin bar.)

## Verdict (analysis agent, for the coordinator)

**P-SV-4 (R4) K6p key source: NOT NOMINATED** under the registered level-2 intent rule and the twin bar: -0.19 pp
[-0.56, +0.19] against a bar of 0.23 and a declared +1.1. Because the level-2 column replicated A's Solver request
(section 3a), the substantive evidence is level 1: K6p was delivered as proven (block rank 1 on 815 rows, +15 over
the flown description key) but Perception's note does not pass it on (note top1 887 vs 888; present +0.46 inside
the 0.56 twin bar; implied intent about -0.2 rows). A correctly rendered column would therefore not be expected
to approach the 0.65 pp floor. The **K6p key-source line is CLOSED**; the selection disclosure is moot (a bias that
could only favour B did not produce an effect).

**Intent after R4.** K6p was the last registered intent item of the programme. The intent levers at the
Perception node are now all closed: contrast presentation (P-SV-1), forced list length (P-SV-2), boundary depth
(P-SV-3, both directions by the offline amendment) and the retrieval key (P-SV-4, and the 2026-09-30 recall read:
no pinned-vector key adds +4 pp presence). The Solver-node intent blank was closed on 2026-09-30 (R5). The residual
is Perception recall (gold-on-list 91.0 % on this flight's A; 93.1 % on Fold A and 91.8 % on DEV in the
exchange-rate note) and rank: of COMP-1b's 155 wrong Fold A rows, 75 have gold off the shortlist, 70 on it below
rank 1, 9 at rank 1 with the Solver choosing otherwise, 1 unparsed. No registered lever addresses either.
**Intent is already LOCKED at COMP-1b** (decision 229; DEV +4.60 [+2.58, +6.73], signed test sample +5.80
[+4.04, +7.42]); R4 could only have added a nominated increment, and it does not. The programme continues on the
SLU slot line: NX R1 iteration 2 (Solver template column on TRAIN Fold B) is flying, post-processing v4g is
locked, and the Stage S supply rounds follow R1. R5 composes without R4.

**For the coordinator to rule.** (i) Record the section 3a defect (level-2 Perception-branch Solver render ignores the
branch note) with a root cause and a model-free render test before any level-2 branch cell is registered again.
(ii) Strike the level-2 "beside" readings of P-SV-1 to P-SV-3 (notably the P-SV-2 `min_candidates = 3` SLU knob)
as A/A replicates. (iii) Any future intent work at Perception needs a new, unpinned retrieval key or a different
Perception note mechanism under its own brief; it is not part of the NX programme.

## 5. Reproduce

```bash
# WSL Ubuntu-24.04; model-free. The registered read (already sealed; a sealed read is never overwritten):
cd /mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
bash scripts/flights/psv/psv_read.sh psv4 --dry-run     # counts only; no gold, no scorer
# bash scripts/flights/psv/psv_read.sh psv4             # refuses: the receipt and pass directories exist

# Hashes of the read and the sealed attempt:
A=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-STAGE3-PSV4-FOLD-B-BRANCH-READ-V1
R=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/SAEA-SLURP-STAGE3-PSV4-FOLD-B-V1/attempt-slurp-native-stage3-psv4-fold-b-generation-v1
sha256sum $A/perception-branch-read.json $A/branch/* $A/twin-null/* \
  $R/SAEA-SLURP-STAGE3-PSV4-FOLD-B-V1.{run-manifest.json,outputs.jsonl,scores.json} $R/supply-variants/score-summary.json

# Section 1 / 3 / 3a aggregates (read-only; print counts only):
#  - supplied_count, candidate_intent_ids, candidate_supply_value_ids, response / solver hashes and
#    terminal_disposition per branch from $R/SAEA-SLURP-STAGE3-PSV4-FOLD-B-V1.outputs.jsonl
#    (native_episode_receipt.perception_branches.branches[*]);
#  - usage.prompt_tokens per contact from $R/SAEA-SLURP-STAGE3-PSV4-FOLD-B-V1.trace.jsonl (MODEL_REQUEST history[-1]
#    contact_id -> the branch's contact_id / solver_contact_id; the method of scripts/flights/psv/psv_fit_measure.py);
#  - block rank: gold intent (data.slurp.load_slurp_split, split train) located in supplied_value_ids
#    (suffix after "intent-boundary:");
#  - per-row column correctness: scenario_action_exact in $R/supply-variants/arm-<branch>-slurp-slu-official-train-scores.json;
#  - Reviewer truncations:
grep -c workflow_execute_error /home/chao/batch-campaign-1-psv4-20261009T182255Z.log   # 6
```
