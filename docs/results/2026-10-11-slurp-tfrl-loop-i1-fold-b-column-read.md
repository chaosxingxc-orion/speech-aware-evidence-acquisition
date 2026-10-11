# TFRL loop iteration 1 (TRAIN Fold B column, lock / aa / ace): ACE i1 REFUSED (SLU +0.87 [-0.40, +2.10] vs lock, below the 1.49 floor; intent 0.00 [-0.74, +0.74]); typed arm EMPTY by measurement; the parent stays s0-lock-v2.2

Read 2026-10-11 by Claude Opus 5.5 (results-note agent, on the coordinator's brief, Fable 5.1) in the worktree
`opus/tfrl-i1-results-note` (base master `c43e22f02`). Model-free: this note opened no model, server, encoder,
embedder, tokenizer or GPU, ran no scorer and wrote nothing under the data root. It reads the close receipt of
`tfrl_loop_driver.py close --iter 1`, the loop archive, the on-file outputs of the registered read
`SAEA-SLURP-STAGE3-TFRL-LOOP-I1-FOLD-B-COLUMN-READ-V1`, and the sealed manifests of the column, the typed proposer and
the ACE reflector runs. One extra figure was computed here, ACE vs the `aa` twin, because no `ace-vs-aa` pair file
exists. It was computed from the three sealed per-arm official score files with the repository's own paired-read core
(`scripts/analysis/slurp_paired_roster_read.py`: `_rows_table`, `_pooled_contrast_block`, `_per_row_block`; cluster
`sample_id`, 10,000 draws, seed 20260915). The same call reproduces the `ace-vs-lock` and `aa-vs-lock` files to every
printed digit. No utterance text, transcript, gold value, slot filler, playbook item text, reflector or proposer
output was printed or persisted. Only counts, rates, deltas, ids, hashes, scenario and slot-type names appear below.

**DESCRIPTIVE.** These are development numbers on TRAIN Fold B (`SLURP-EVO-FOLD-B-V2`, owner decisions 28 and 86),
n = 1,080, all arms in the same flight. Fold B is the loop's held-out selection split: the proposer tables and the ACE
material come from the construction roster R01C, not from Fold B. Nothing here is a benefit claim, a test claim, a
system-level claim or an admission. The ACE column is a non-delivering comparator that can never be locked (263-A Q2;
design 4.4). The verdict words apply the preregistered rule (`tfrl-loop-protocol-v1.json` `selection`, protocol sha256
`3ba5e4ee...`).

## 0. Verdict

**ACE i1 (state `e7b4fa57...`) is REFUSED under the protocol. The typed arm is EMPTY by measurement. The parent for
iteration 2 stays `s0-lock-v2.2` (state `a8f1d50e...`).** The clauses, from `iterations/i1/close-receipt.json`:

| clause | rule | value | threshold | result |
| --- | --- | ---: | ---: | --- |
| a | CI95 lower bound of ace - lock (official pooled SLU-F1) | -0.40 pp | > 0 | FAIL |
| b | point of ace - lock | +0.87 pp | >= 1.49 pp (decision-190 floor, same-flight-supply-variant, n = 1,080) | FAIL |
| c | point of ace - lock exceeds aa - lock | +0.87 pp | > -0.49 pp | PASS |
| d | point vs the previous ACE state | -- | -- | vacuous (no previous-ACE-state column flies in this flight) |
| e | intent guard: CI95 lo >= -0.65 AND point >= 0 | lo -0.74 / point 0.00 | -0.65 / 0 | FAIL (by width) |

The spec's prose form of clause e (design 5.3: "at most 7 rows whose official intent correctness differs from `lock`
in the losing direction") fails too: 8 rows lose and 8 gain.

The three headline numbers:

- **ACE vs lock:** SLU +0.87 [-0.40, +2.10].
- **ACE vs the twin:** +1.36 [+0.12, +2.58]. This is the paired bootstrap computed for this note, not the arithmetic
  64.87 - 63.51.
- **Intent:** 0.00 [-0.74, +0.74] (8 saves / 8 harms).
- The twin's own offset (aa vs lock) is -0.49 [-1.12, +0.12].

Ledger entry (decision 262, clause c, the negative result reported with equal rigour): a reflector-written prose
playbook at equal token budget (27 items, about 0.97k proxy tokens) does not clear the instrument on SLURP SLU in one
iteration. Its point gain comes almost entirely from fewer empty-gold false fills, a mass that the locked v4g
normaliser already harvests.

## 1. What flew

| item | value |
| --- | --- |
| cell / package | `slurp-native-stage3-tfrl-loop-i1-fold-b-v1`; `docs/readiness/2026-10-11-slurp-tfrl-loop-i1-fold-b-v1/` (recipe `slurp-tfrl-loop-i1-fold-b-column-analysis-v1`, design `same-flight-supply-variant`, claim ceiling nominated) |
| run / attempt | `SAEA-SLURP-STAGE3-TFRL-LOOP-I1-FOLD-B-V1` / `attempt-slurp-native-stage3-tfrl-loop-i1-fold-b-generation-v1`; status COMPLETED, `study_repo_dirt` empty |
| flight commit | `2b64166866233340e0ee2a702da55790dca41d01` (`study_commit` of the run manifest and the ledger row) |
| base and program | the review-off COMP-1b module graph at lock v2.3 (= v2.2 plus the empty `ace-playbook-i0` declaration; P-ACE-0 byte-identical requests), v4g delivery normaliser on 1,080 / 1,080 rows; program `phase-native-module-v1-c4` |
| arms (`arm_visits: first`) | `ace` (`release_swap` of store `ace-playbook` to `knowledge/slurp/semantic/ace-playbook-i1/release.json`, `max_supplied_items` 63); `aa` (`replicate_of lock`, 55); `lock` (delivering, last, 55). No `typ`, because the typed arm was empty; no `par`, because there is no parent before iteration 2 |
| contacts | 4,320 = 4 per row (Perception + the lock Solver + one first-visit Solver contact per non-delivering arm); 0 tool calls; 12,619.19 repeated speech-audio seconds; plan 4,320 calls / 12,620 s (run manifest `cost`) |
| tokens | 38,444,398 prompt / 200,150 completion (35,596.7 / 185.3 per row). This is the whole flight's cost; the passes do not split it by arm |
| timing | `run_phases` wall 9,831 s (2 h 43.9 m), GPU-active 8,978 s = **2.49 GPU-h** (2.31 per 1,000 rows), mean utilisation 74.5 %, 26.4 contacts per minute, slot occupancy 0.762 (`pairs/ace-vs-lock/efficiency.json`, `flight-receipts.json`); sealed 18:33Z (registry); packets 1,080 in 23.4 s at 8 workers |
| registered GPU-h | `planned_gpu_hours` 1.5 (`generation-plan-registered-v1.json`). The monitored GPU-active time is 66 % above it; see section 7 |
| serving | attached session `serving-slurp-native-candidate-five-train-a-np4-v1` (np4, 24,576-token slot, `max_tokens` 512), reused |
| smoke and its recovery (rec1) | The first smoke `attempt-...-fold-b-smoke-4-generation-v1` refused at preflight (13:22Z, flight commit `6cbd9c707`) before any model contact: "supply action 'ace' is invalid: knowledge store ace-playbook snapshot SHA-256 mismatch". The ACE pin carried the snapshot FILE sha256 (`e1584617...`); the runtime checks the content hash `c91ca2dd...` from the preparer's `completion.json`. The package was re-derived (`785b2fb9d`), and the smoke re-flew whole as `...-smoke-4-generation-rec1-v1` / `...-smoke-4-fit-rec1-v1`: 16 contacts, 40.7 s, sealed. This was the cell's single recovery. The arm attempt never opened before it (package README, recovery section) |
| identities | finalized manifest `766b9e97a0ffbf9fe4ed9da33efd35fe4f508266f956a81a8393fa0f6628c731`; generation manifest `65f21dde4df78c28eca31645c293626334e3f829e61491152cc2e333d02b9e6e`; run protocol hash `8460a68564a4fc3ae04c812945bf2941526350618e3c6891a77fabe308853606`; config hash `58904bf2...`; packet manifest `780f8b4d...`; per-arm official score files: lock `fdcb9173...`, ace `abcae6d0...`, aa `3dccbc6c...` (each `stop.json` reproduces the official aggregate in process, status PASSED) |
| roster | TRAIN Fold B, 1,080 rows (392 empty-gold, 688 non-empty-gold, 944 gold entities); split identity `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`; roster file `47b89b9e...`; 60 rows per scenario |
| exposure | `docs/exposure-ledger.md` rows for the arm (CONSUMED, sealed: 4,320 contacts, 12,619.2 s), the FIT identity, the rec1 smoke (CONSUMED: 16 contacts) and its FIT, and the READ (`model-free-check`, root countersigned 2026-10-11T12:30:51Z BEFORE READ). Split role discovery. TRAIN Fold B rows were already exposed by prior SLURP cells, and that prior exposure is inherited in full; the cell opens no split |

## 2. The material path (construction column -> proposer and reflector -> curated playbook -> column)

1. **Construction-source column.** `SAEA-SLURP-STAGE3-TFRL-CONSTRUCTION-LOCK-R01C-V1`: the plain lock on R01C (625
   TRAIN rows outside Fold A, Fold B and DEV) under the minus-r01 construction variant. It sealed 10:35Z at flight
   commit `70eabd973` with 1,250 contacts (registry). Its contrast tables are
   `analysis/SAEA-SLURP-TFRL-LOOP-V1/construction-source/tables/tables-v1.json`: file sha256 `c51f4c97...`,
   `tables_sha256` `6c925de6...`, schema `saea-tfrl-contrast-tables-v1`, 625 rows, scorer `slurp-slu-official-train`,
   suppression `min_cell` 3, table A with 294 rows, per-scenario row counts from 26 (alarm) to 42 (calendar, general),
   tables F and G empty at iteration 1. The same column serves all three iterations (protocol `material_source`).
2. **Propose stage** (`iterations/i1/open-propose-receipt.json`, inputs sha256 `6cedf0ec...`): the proposer tables and
   context, 18 per-scenario ACE material files, the empty playbook i0 (content hash `53268ec0...`), lock p99 supplied
   tokens 13,728, and `T_cap` = 13,728 + 1,880 = 15,608. The edit budget is L_1 = 2.
3. **Typed proposer** `SAEA-SLURP-STAGE3-TFRL-PROPOSER-I1-V1` (flight commit `bd43ded89`, text-only seam): 3 contacts
   on 3 carriers, 18,845 prompt / 555 completion tokens, 11.5 s wall, 0 tool calls. All three responses are
   byte-identical (response sha256 prefix `e6807ba7c2` in each of the three receipts in `typed-receipts-i1.json`), so
   there is **one distinct candidate**: `688e0fd0...`, operator `deliver-rule`, class `delivery`, family
   `fx-oclock`, guard none, hypothesis `rule-filter`, target SPURIOUS `time` in `alarm`
   (`alarm_query`/`alarm_remove`/`alarm_set`), `value_in_supply` none. The validator found it legal (no refusal code)
   and routed it to `read: offline`, since delivery rules are not arms. No supply-form candidate exists, so nothing is
   flyable and the typed ARM is empty. The open-cell receipt shows both facts at once: `inputs.typed_arm_empty` is
   `false` because the coordinator passed `--typed-receipts` (the three sealed receipts) and not the
   `--typed-arm-empty` flag, while `typed_arm` reads "empty (legal)" with `valid` 1, `offline` 1, `refused` 0,
   `not_flown` 0. `predictions-i1.json` is empty, and `proposer-meta.json` records `never_shipped: true` with no rows.
4. **ACE reflector** `SAEA-SLURP-STAGE3-TFRL-ACE-REFLECTOR-I1-V1` (flight commit `58ebe92ea`): 18 contacts on 18
   carriers (`docs/receipts/rosters/slurp-tfrl-ace-reflector-fold-b-carriers-i1-v1.json`) covering 14 strata. Cooking,
   lists, recommendation and social have two carriers each; iot, qa, takeaway and weather have none. Totals: 20,270
   prompt / 2,986 completion tokens, 29.3 s wall, 0 tool calls. 10 answers carry 3 `add` deltas each (**30 deltas**)
   and 8 are empty. A carrier maps to its scenario through the roster's `stratum`, and for a scenario with two
   carriers the first non-empty answer is kept. Recommendation therefore keeps its second (non-empty) answer;
   cooking's and lists' second answers (both empty) are dropped. Social's second answer is non-empty: its 3 deltas
   were dropped before the answers file was built, because the ACE schema caps adds per contact
   (`max_adds_per_contact` 3) (`reflector-answers-i1.json` `dropped_duplicates`, response-sha prefix
   **`3e762386bc`**). The answers file therefore carries 14 scenario answers, 9 non-empty, holding **27 deltas**.
   Answers sha256: `da8e2ff6...`.
5. **Curator** (deterministic, constants `0eeb1946...`): 27 deltas in, 27 items out. 0 exact or near duplicates,
   0 refused (sample identifier, evaluation 6-gram, unknown target, empty after cleaning), 0 dropped by the cap,
   counters empty at iteration 1. Rendered 966 proxy tokens (`proxy-utf8-bytes-div-3-v1`) against the 1,880-token
   allowance. Sections: 14 `strategy`, 12 `pitfall`, 1 `format-rule`. Item text totals 2,512 bytes (66-149 bytes per
   item). Declared scopes: 3 items each for alarm, calendar, datetime, lists, news, recommendation, takeaway and
   weather, plus 3 items scoped to `all` scenarios. Several declared scopes name a scenario other than the carrier's
   stratum (takeaway, news and weather items exist, while the takeaway and weather strata had no carrier and news
   answered empty). Every item has `helpful` 0 and `harmful` 0. The flown playbook is
   `analysis/SAEA-SLURP-TFRL-LOOP-V1/i1/ace-release-staging/playbook-i1.json` (content hash `e12fabcc...`, file
   `beba27ab...`, 27 items; equal to `open-cell-receipt.json` `playbook_content_hash`).
6. **Release i1** (`ace-playbook-i1-release-registration.json`, registration `SAEA-SLURP-ACE-PLAYBOOK-PREPARATION-I1`,
   policy `saea-authored-stage3-deltas-v2`, train source split `7c603857...`, 50 R01C carriers, 27 rows): release
   `593761b7...`, snapshot content hash `c91ca2dd...`. The open-cell loader verification is ok. The supply swap adds
   **5,841 item renders** to the ace arm (5.41 per row on average; no row keeps the lock's id set; 0 items removed;
   51,100 vs 45,259 supplied items), per `node-local/report.json` `supply_stats`.
7. **Column** as in section 1, then **close** (`close-receipt.json`, inputs sha256 `97a32a97...`).

## 3. The read

**Official pooled micro SLU-F1 and intent** (score files under `supply-variants/`; paired cluster bootstrap):

| arm | SLU-F1 % | span-F1 % | intent % | SLU vs lock pp [CI95] | SLU vs aa pp [CI95] | intent vs lock pp [CI95] (saves / harms) |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `lock` (delivering) | 64.00 | 53.59 | 82.31 | -- | +0.49 | -- |
| `aa` (twin) | 63.51 | 53.26 | 82.22 | **-0.49 [-1.12, +0.12]** | -- | -0.09 [-0.46, +0.19] (1 / 2) |
| `ace` | 64.87 | 54.93 | 82.31 | **+0.87 [-0.40, +2.10]** | **+1.36 [+0.12, +2.58]** | 0.00 [-0.74, +0.74] (8 / 8) |

Other channels (ace vs lock): span-F1 +1.35 [-0.13, +2.79]; per-row SLU-F1 +0.21 [-0.80, +1.23] (50 / 42);
`slot_f1_exact_f1` +0.33 [-0.73, +1.38] (38 / 26); `action_exact` +0.09 (7 / 6); `scenario_exact` +0.19 (8 / 6).
CI90 of the pooled SLU delta: [-0.18, +1.90]. Equal-stratum weighting: SLU +1.03 [-0.33, +2.46], intent 0.00
[-0.74, +0.74]. The roster is not floored, so the natural mixture is the raw roster. Headset (527 rows) vs far-field
(553 rows), per-row SLU-F1: +0.41 vs +0.02.

ACE vs twin on the other channels (computed here): span-F1 +1.67 [+0.22, +3.09]; intent +0.09 [-0.56, +0.83]
(8 / 7). The ACE-vs-twin CI excludes 0 because the twin landed below the lock in this flight. Against the lock, which
is the gated contrast, the CI does not exclude 0. On this design the twin offset is noise around 0 (the R6-P1 twin
read +0.72 [+0.12, +1.37]; this one reads -0.49 [-1.12, +0.12]). Read the +1.36 as the same +0.87 seen from a low
twin, not as a separate result.

The lock level (64.00 %) sits 0.34 pp under the R6-P1 lock column on the same roster and base (64.34 %). That is a
cross-flight difference, inside the cross-flight bar.

**Node-local (normalised, primary; `node-local/tables.md`, whole-utterance clusters, 10,000 draws, seed 20260915):**

| arm | exact set % | empty-gold false fill % (n = 392) | non-empty exact % (n = 688) | predicted items |
| --- | ---: | ---: | ---: | ---: |
| lock | 54.35 | 23.98 | 42.01 | 896 |
| aa | 53.89 | 24.74 | 41.72 | 896 |
| ace | 56.30 | 19.64 | 42.59 | 880 |

| contrast vs lock | ace | aa |
| --- | --- | --- |
| exact set | **+1.94 [+0.28, +3.61]** (52 / 31) | -0.46 [-1.20, +0.28] (5 / 10) |
| empty-gold false fill | **-4.34 [-7.40, -1.02]** (12 rows newly filled / 29 rows newly emptied) | +0.77 [-0.51, +2.04] (5 / 2) |
| non-empty exact | +0.58 [-1.31, +2.47] (23 / 19) | -0.29 [-1.16, +0.44] (3 / 5) |
| parse valid | +0.09 (1 / 0) | +0.09 (1 / 0) |

The node-local mechanical screen (exact-set CI-LB > 0, no secondary against) passes for ace. It gates nothing. The
raw view (before the v4g normaliser) shows the same direction, larger: false fill -9.95 [-13.52, -6.38], exact set
+3.70 [+1.94, +5.46], non-empty exact +0.15. The normaliser changes the text of 170 ace rows, against 203 for the
lock.

**Exchange-rate check** (`docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md`: +0.033 pp per false fill
emptied, 0.070 pp per non-empty exact row): 17 net false fills emptied x 0.033 = +0.56, plus 4 net non-empty exact
rows x 0.070 = +0.28, totals +0.84. The measured delta is +0.87, so about two thirds of the pooled gain is the
false-fill channel.

**Per scenario** (60 rows each; `pairs/ace-vs-lock/per-scenario-tables.json`; no scenario CI excludes 0 for SLU):

| scenario | ace items scoped (declared) | SLU ace - lock pp [CI95] | intent pp | twin SLU aa - lock pp |
| --- | ---: | --- | ---: | ---: |
| recommendation | 3 | +4.38 [-0.95, +11.12] | 0.00 | +1.81 |
| alarm | 3 | +4.35 [-1.39, +11.85] | +3.33 | -0.82 |
| weather | 3 | +3.10 [-1.02, +7.78] | -1.67 | +0.95 |
| lists | 3 | +3.09 [-4.52, +11.47] | +1.67 | -3.47 |
| qa | 0 | +3.02 [-0.59, +7.87] | 0.00 | -0.59 |
| calendar | 3 | +2.61 [-0.86, +6.54] | 0.00 | -0.23 |
| general | 0 | +2.15 [-8.59, +13.58] | +1.67 | 0.00 |
| music | 0 | +2.03 [-9.34, +12.87] | -3.33 | +4.41 |
| transport | 0 | +1.46 [-2.64, +5.54] | 0.00 | -1.24 |
| audio | 0 | +1.44 [-3.34, +6.94] | 0.00 | 0.00 |
| email | 0 | +0.81 [-2.43, +4.88] | -1.67 | -0.77 |
| iot | 0 | -0.59 [-3.34, +2.04] | -1.67 | 0.00 |
| datetime | 3 | -1.01 [-5.47, +2.72] | 0.00 | -0.59 |
| play | 0 | -1.07 [-5.48, +3.66] | 0.00 | -1.98 |
| takeaway | 3 | -1.47 [-7.05, +2.88] | -1.67 | -0.04 |
| cooking | 0 | -1.68 [-7.50, +3.17] | +1.67 | -1.00 |
| social | 0 | -1.69 [-7.11, +3.48] | 0.00 | -2.11 [-4.63, -0.26] |
| news | 3 | -2.45 [-8.80, +4.10] | +1.67 | +0.05 |

"Items scoped" counts the items whose declared scope names the scenario; the 3 `all` items are excluded. This note
does not infer how the runtime resolves a scope; the release swap adds items to every row. The unweighted mean SLU
delta is +1.58 over the 8 scenarios that have scoped items and +0.59 over the 10 that do not. The twin's own
per-scenario deltas reach -3.47 (lists) and +4.41 (music), so the scenario pattern is inside the same-flight noise.

**Per slot type** (normalised; totals over the 944 gold entities): ace has 501 exact, 224 missing, 219 wrong and
160 spurious from 880 predicted; the lock has 493 / 228 / 223 / 180 from 896; the twin has 490 / 238 / 216 / 190.
So against the lock, ace has 8 more exact entities and 20 fewer spurious ones. The twin differs from the lock by
+10 spurious, which sizes the noise on that count. The largest ace - lock movements are:

- spurious entities: `device_type` -8 (10 -> 2), `date` -4, `event_name` -3, `business_type` -3, `meal_type` -3 and
  `song_name` -3; against those, `business_name` +4, `order_type` +3, `person` +2, `game_name` +2, `change_amount`
  +2 and `personal_info` +2;
- exact entities: `date` +4 (63 -> 67, missing 54 -> 51) and `transport_type` +2.

## 4. What the ACE form did and did not do on this task

The comparison isolates the four deficits the lineage analysis names as the measured differences
(`docs/readiness/2026-10-11-slurp-tfrl-lineage-and-algorithm-baseline-analysis-v1.md`, D1/D2/D3/D7; D4 and D6 are
held equal by the instrument and `T_cap`).

- **D1 (reflector = the frozen core).** The reflector wrote 30 deltas in 18 contacts. 8 of 18 answers were empty, and
  the 3 typed-proposer contacts returned one byte-identical response. No legality refusal was needed (0 illegal
  answers, 0 decontamination refusals), so the reflector's output is clean but thin. Nothing in this column measures
  lesson quality directly; the column measures only the effect.
- **D2 (prose items at equal budget).** 27 items, 966 proxy tokens, 5.41 item renders per row. That is about half
  the 1,880-token allowance, so the budget did not bind. The prose moves the Solver toward emptier answers: false
  fill -4.34 [-7.40, -1.02] normalised (-9.95 raw), predicted items 896 -> 880, spurious entities 180 -> 160.
  Non-empty exact barely moves: +0.58 [-1.31, +2.47]. The false-fill channel is the one the locked v4g normaliser
  already works on (rows changed by the normaliser: 203 lock, 170 ace). That is why the raw-view gain (+3.70 exact
  set) shrinks to +1.94 after delivery, and why the pooled SLU gain is +0.87, not the +1.5 the floor asks for. In
  short, the prose substitutes for delivery-side work that the lock already does. It does not add values the lock
  misses: the gold-side missing count falls only 228 -> 224, and the coverage pre-read finds 61 % of MISSING already
  in supply.
- **D3 (no key).** The items carry declared scopes but no input-conditioned key, and the swap adds items to every
  row. Scenarios with scoped items averaged +1.58 against +0.59 for those without, but no scenario resolves, and the
  twin's own per-scenario spread is just as large. This column cannot separate a scope effect from noise.
- **D7 (interference).** The losses (news -2.45, social -1.69, cooking -1.68, takeaway -1.47) sit both in scenarios
  with their own items (news, takeaway) and in scenarios without (social, cooking). Intent moved on 16 rows in both
  directions (8 / 8) against 3 for the twin, so prose in the Solver context perturbs intent on rows it does not
  target. That is the clause-e failure: the point is 0.00, but the interval is wider than the guard.
- **Instrument floors** (`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`; decision 190):
  SLU 1.49 pp and intent 0.65 pp at n = 1,080 same-flight. ACE's +0.87 is 58 % of the SLU floor. Its CI half-width
  (1.25 pp) is about twice the twin's (0.62 pp): a supply change perturbs many rows both ways (50 saves / 42 harms
  per row, against 9 / 12 for the twin).

The ACE result fits the record of free-text updates (262 (c): TF-GRPO semantic deltas, GEPA prose, template
columns), with one difference: the sign is positive and the false-fill effect is real. The ACE form produced a
measurable node-local change (CI-LB > 0 on exact set and false fill) that does not reach the delivered metric's floor
on top of v4g.

## 5. The typed arm

- **Why empty.** Decision 265's class (credit-driven selective knowledge augmentation from TRAIN) had no candidate
  over the +1.5 pp predicted bar in the coverage pre-read
  (`docs/results/2026-10-11-slurp-tfrl-coverage-preread-fold-b-offline.md`). The pre-read's cross-fitted composite
  was -1.00 pp SLU / +0.07 intent; the largest honest number was +0.27 pp, from a non-credit reference. Decision 266-A
  ruled the stall default. The proposer was still contacted so the archive records what it proposes: a single
  delivery-class candidate, which by protocol is read offline and never flies as an arm. With no supply-form
  candidate, the arm set is `ace, aa, lock`, and the typed curve point for iteration 1 is `unflown` at level 0.
- **The offline deliver-rule candidate** (`688e0fd0...`: `fx-oclock` on alarm `time`, target SPURIOUS). By protocol it
  is accepted iff its cross-fitted CI95-LB > 0 AND point >= 0.67 pp over the column of the state it edits, here the
  lock column. **This read did not happen.** The close step runs the delivery fitter only for families in
  `FIT_FAMILY` (`scripts/flights/tfrl/tfrl_loop_driver.py:72`: `ee5`, `ee10`, `ti0`, `ti1`, `fx-article`). `fx-oclock`
  is not among them, so the candidate was skipped without a record. No `analysis/SAEA-SLURP-TFRL-LOOP-V1/i1/offline/`
  directory exists, the close receipt has no `offline` verdict, and the archive has no state for the candidate.
- **Its ceiling on this column is small either way.** The lock column has **4** spurious `time` entities across all
  18 scenarios (node-local per-type table), so a rule that only removed spurious alarm times could remove at most 4.
  At the pre-read's rate of about +0.029 pp per spurious entity removed, that is at most about +0.12 pp, below the
  0.67 pp floor even with zero harm. This is consistent with the pre-read's measurement for the sibling class:
  per-scenario anti-pattern guards on top of v4g read -0.45 [-1.13, +0.18] cross-fitted, against +0.87 in-sample
  (1.3 pp selection optimism).

## 6. Ledger line and what iteration 2 does

- **Ledger entry (decision 262, clause c).** Negative result, equal rigour. ACE's form (reflector prose, global
  inclusion, deterministic curator, script counters, equal token cap) moved SLURP SLU-F1 by +0.87 [-0.40, +2.10]
  over lock v2.2 on TRAIN Fold B, n = 1,080 same-flight. That is below the 1.49 pp floor; intent is 0.00 [-0.74,
  +0.74]. The mechanism is fewer empty-gold false fills (-4.34 [-7.40, -1.02]) that the v4g delivery normaliser
  partly already provides. The typed loop had no flyable candidate (the 265 pre-read). This is the first ACE point on
  the curve; the ACE series is reported either way (claim rule).
- **Iteration 2, as the protocol and the close receipt set it.**
  - Parent: `s0-lock-v2.2` (`parent.json`: one ranked state, no masked classes).
  - Typed material: the same construction tables (`6c925de6...`).
  - Edit budget: L_2 = 1.
  - ACE: the i2 reflector reads the same construction column plus the current playbook items. The curator grows i1
    into i2 using counters computed by script from this column's per-row official credit (ace vs lock, scoped rows).
    `ace_credit: not-built` and `row_scores: null` are expected at iteration 1: the counter file is built at
    iteration 2's cell stage.
  - Arms: `par` joins the arm set, so iteration 2 flies 5 contacts per row. Clause d then compares the next ACE
    state with this one only through the archive (no previous-ACE column flies).
  - The refused ACE state still generates the next reflection.
- **Before `open --iter 2` runs, see the first two rows of section 7b.** As the driver stands, the i2 curation would
  load an empty i1 playbook.

## 7. Process defects of the first real loop iteration

**(a) Found and fixed during the iteration** (registry sections of 2026-10-11):

| defect | effect | fix |
| --- | --- | --- |
| ACE snapshot pin carried the file sha256, not the content hash | column smoke refused at preflight, 0 calls; the cell's single recovery spent | pins from the preparer's `completion.json`; package re-derived `785b2fb9d`; tfrl `SMOKE_RECOVERIES` / rec1 ids `d8cd13df3`, `69044ba0f` |
| campaign inspector assumed a native episode config | batch STOP after the sealed typed proposer; the reflector did not start (no attempt opened) | text-only branch in `batch_inspect.py` plus `TFRL_ONLY`, `58ebe92ea` |
| registration writer put a placeholder string in the exposure rows' artifacts cell | reflector re-pin refused; launch gate `[no-analysis-recipe]` | writer emits the plan path, the resolved prompt sha and the recipe, `535ae32f2` |
| construction-role gate scanned every `docs/receipts/rosters/*.json` | refused on the A2T comparator-rows companion; proposers flip blocked | skip declared companion schemas, `16512119e` (merge `5f6b9043d`) |

**(b) Found by this read, open** (each verified against the sealed bytes):

| defect | evidence | consequence |
| --- | --- | --- |
| **the archived ACE i1 state binds the wrong playbook** | `archive/state-e7b4fa57....json` has `artefact_hashes.playbook_release` = `6c69ae03...`. That is the content hash of `analysis/.../i1/playbook/playbook-i1.json`: **0 items**, `deltas_in` 0, written 12:22:51Z by the first (superseded) open-cell run, before the reflector answers existed (12:26:20Z). The flown playbook is the 27-item `ace-release-staging/playbook-i1.json` (`e12fabcc...`, 13:25:57Z). `ace_section` writes `playbook/playbook-i{t}.json` only `if not playbook_path.exists()`, and `close` reads that file | the curve and archive name an empty playbook as ACE i1; `open --iter 2` loads `playbook/playbook-i1.json` as i(t-1), so the i2 curation would grow from 0 items instead of 27 and its counters would refer to no items |
| the credit's `vs_twin` field is the twin's contrast, and the registry repeats it as ACE's | `credit.vs_twin.slu` = -0.49 [-1.12, +0.12] = aa - lock (twin vs lock), not ace - aa. The registry's "Loop iteration 1 CLOSED" table prints it in the ace row under "vs twin SLU pp" | the label misreads; ace vs twin is +1.36 [+0.12, +2.58] (section 3). Clause c itself is computed correctly (point vs point) |
| the offline deliver-rule candidate was skipped silently | `fx-oclock` is absent from `FIT_FAMILY`; there is no fit job, no fit report, no archive state, and no `offline` entry in the close receipt. The registry says "the single deliver-rule candidate is read offline" | the archive does not record the refused typed candidate that 266-A intended it to hold; the proposer at i2 will not see it as a refused sibling |
| GPU time above the registered plan | `planned_gpu_hours` 1.5 against 2.49 GPU-active h monitored (wall 2.73 h; spec estimate 1.1 GPU-h). Calls and audio sit exactly at plan (4,320 / 4,320; 12,619.19 / 12,620 s) | not a budget breach under the run-cumulative call / audio rule; the i2 / i3 plans (5 contacts per row) should carry the measured rate, about 0.58 GPU-h per contact per 1,000 rows |
| registry count for the typed proposer | the 12:02Z registry entry says "9 trace contacts"; the run manifest and the ledger row say 3 calls (no retries); the 12:18Z entry says 3 | record only |

## 8. Records read

- Loop: `docs/readiness/2026-10-11-slurp-tfrl-loop-v1/` (`tfrl-loop-protocol-v1.json`, `loop-state.json`,
  `ace-playbook-i1-release-registration.json`, `archive/state-{81fc5504,a8f1d50e,e7b4fa57}...json`,
  `iterations/i1/{open-propose-receipt,open-cell-receipt,candidates,offline-candidates,close-receipt,curve,parent,proposer-meta}.json`).
- Column package: `docs/readiness/2026-10-11-slurp-tfrl-loop-i1-fold-b-v1/` (`README.md`, `analysis-recipe-v1.json`,
  `generation-plan-registered-v1.json`). Proposers package: `docs/readiness/2026-10-11-slurp-tfrl-loop-i1-proposers-v1/`
  (`registered-facts-v1.json`).
- Data root, analysis: `analysis/SAEA-SLURP-TFRL-LOOP-V1/` (`construction-source/tables/tables-v1.json`;
  `i1/{reflector-answers-i1,typed-receipts-i1,predictions-i1,ace-i1-release-files,ace-release-pins-i1}.json`;
  `i1/playbook/playbook-i{0,1}.json`; `i1/ace-release-staging/{playbook-i1,source-ace-playbook-i1-wrap-receipt}.json`;
  `i1/node-local/{report.json,tables.md}`; `i1/pairs/{ace-vs-lock,aa-vs-lock}/{README.md,verdict.json,stop.json,efficiency.json,per-scenario-tables.json}`).
- Data root, runs: `runs/SAEA-SLURP-STAGE3-TFRL-LOOP-I1-FOLD-B-V1/attempt-slurp-native-stage3-tfrl-loop-i1-fold-b-generation-v1/`
  (run manifest, ledger row, flight receipts, `supply-variants/{score-summary,render-manifest,arm-*-slurp-slu-official-train-scores}.json`);
  the run manifests, ledger rows, flight receipts and output row counts of `SAEA-SLURP-STAGE3-TFRL-PROPOSER-I1-V1` and
  `SAEA-SLURP-STAGE3-TFRL-ACE-REFLECTOR-I1-V1` (counts and hashes only).
- Rosters: `docs/receipts/rosters/slurp-evo-fold-b-v2.json`, `slurp-tfrl-ace-reflector-fold-b-carriers-i1-v1.json` (strata only).
- Registry: `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, the 2026-10-11 sections (decisions
  262-266, the build wave, "Loop iteration 1 CLOSED").
- Design and analyses: `docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md`
  (sections 0, 4, 5); `docs/results/2026-10-11-slurp-tfrl-coverage-preread-fold-b-offline.md` (sections 0, 5, 6);
  `docs/readiness/2026-10-11-slurp-tfrl-lineage-and-algorithm-baseline-analysis-v1.md` (D1-D7);
  `docs/results/2026-10-10-slurp-nx-r6-perception-fold-b-column-read.md` (house style, the R6-P1 lock level and twin).
- Code (read only): `scripts/flights/tfrl/tfrl_loop_driver.py` (`FIT_FAMILY`, `ace_section`, the close step);
  `scripts/analysis/slurp_paired_roster_read.py`; `scripts/analysis/stage3_paired_read.py`.
- Exposure ledger rows for the run ids above (HEAD `c43e22f02`).
