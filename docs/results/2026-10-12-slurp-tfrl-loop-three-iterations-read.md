# Sealed-credit TF-RL loop (decision 263-A), iterations 1-3 on TRAIN Fold B: LOOP CLOSED WITH NO ADMITTED STATE. ACE refused three times (SLU vs lock +0.87 [-0.40, +2.10], +1.38 [+0.15, +2.57], +0.27 [-1.15, +1.71]); the typed arm was empty three times (every fitted deliver rule +0.00 pp, editing 0 rows); the parent stays s0-lock-v2.2

Read 2026-10-12 by Claude Opus 5.5 (results-note agent, on the coordinator's brief, Fable 5.1) in the worktree
`opus/tfrl-loop-results-note` (base master `92e8938e7`). Model-free: this note opened no model, server, encoder,
embedder, tokenizer or GPU, ran no scorer, and wrote nothing under either data root. It reads the loop's committed
receipts and archive, the three column packages, the registry, the exposure ledger, and the on-file outputs of the three
registered column reads and of the six proposer / reflector runs under the legacy data root
(`/mnt/e/.../speechrl-data`; the new root `/home/chao/saea-data/speechrl-data` does not yet hold
`analysis/SAEA-SLURP-TFRL-LOOP-V1/` or these runs). No figure was re-bootstrapped. No utterance text, transcript, gold
value, slot filler, playbook item text, reflector or proposer output was printed or persisted; only counts, rates,
deltas, ids, hashes, scenario, intent and slot-type names appear below.

**DESCRIPTIVE.** Development numbers on TRAIN Fold B (`SLURP-EVO-FOLD-B-V2`, owner decisions 28 and 86), n = 1,080
per column, every arm in the same flight. Fold B is the loop's held-out selection split and was read three times, so
the winner's curse applies to any single iteration's number (design R6). Nothing here is a benefit claim, a test
claim, a system-level claim or an admission. The ACE column is a non-delivering comparator that can never be locked
(263-A Q2; protocol `selection.ace_column.lockable: false`). Verdict words apply the preregistered rule
(`docs/readiness/2026-10-11-slurp-tfrl-loop-v1/tfrl-loop-protocol-v1.json`, `protocol_sha256` `3ba5e4ee...`, pinned
in `loop-state.json`).

**Ledger entry (decision 262, clause c).** Under the same instrument as the stable-gain ledger, three iterations of
the autonomous typed loop produced no candidate that cleared it. The typed operator class the proposer actually used
(deliver rules) produced no candidate with any measured effect. The ACE prose-item form, at equal token budget,
peaked at +1.38 pp SLU-F1 (CI-LB +0.15) with an intent cost, and fell back to +0.27. It never cleared the 1.49 pp
floor.

## 1. Headline

**Official pooled micro SLU-F1 and joint intent (`scenario_action_exact`), paired whole-cluster bootstrap CI95
(10,000 draws, seed 20260915).** Sources: `analysis/SAEA-SLURP-TFRL-LOOP-V1/i{1,2,3}/pairs/{ace-vs-lock,aa-vs-lock}/score-contrasts.json`.
The ACE rows equal `credit.vs_lock` of archive states `e7b4fa57...` (i1), `cadd84f6...` (i2) and `38c024f8...` (i3)
to every printed digit.

| iteration | arm | SLU-F1 % | intent % | SLU vs lock pp [CI95] | intent vs lock pp [CI95] (saves / harms) | span-F1 vs lock pp [CI95] |
| --- | --- | ---: | ---: | --- | --- | --- |
| i1 | `lock` (delivering) | 64.00 | 82.31 | -- | -- | -- |
| i1 | `aa` (twin) | 63.51 | 82.22 | -0.49 [-1.12, +0.12] | -0.09 [-0.46, +0.19] (1 / 2) | -0.33 [-1.04, +0.36] |
| i1 | `ace` (27 items) | 64.87 | 82.31 | **+0.87 [-0.40, +2.10]** | 0.00 [-0.74, +0.74] (8 / 8) | +1.35 [-0.13, +2.79] |
| i2 | `lock` | 64.51 | 82.96 | -- | -- | -- |
| i2 | `aa` | 64.82 | 82.87 | +0.32 [-0.33, +0.97] | -0.09 [-0.46, +0.19] (1 / 2) | +0.05 [-0.80, +0.88] |
| i2 | `ace` (35 items, credit) | 65.88 | 82.41 | **+1.38 [+0.15, +2.57]** | -0.56 [-1.20, +0.09] (3 / 9) | +1.50 [+0.07, +2.90] |
| i3 | `lock` | 64.45 | 82.69 | -- | -- | -- |
| i3 | `aa` | 64.08 | 82.78 | -0.37 [-1.08, +0.25] | +0.09 [-0.19, +0.46] (2 / 1) | -0.70 [-1.46, -0.03] |
| i3 | `ace` (36 items, credit) | 64.72 | 83.15 | **+0.27 [-1.15, +1.71]** | +0.46 [-0.19, +1.20] (10 / 5) | +0.05 [-1.60, +1.74] |

| iteration | typed arm | ACE clauses (a CI-LB > 0 / b point >= 1.49 / c > twin / d / e intent guard) | ACE verdict | false fill (n = 392) | non-empty exact (n = 688) | contacts | GPU-active h |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| i1 | empty (1 deliver rule, offline) | FAIL / FAIL / PASS / vacuous / FAIL (lo -0.74) | refused | -4.34 | +0.58 | 4,320 | 2.49 |
| i2 | empty (1 new deliver rule offline + 1 duplicate-of-archived) | **PASS** / FAIL (by 0.11) / PASS / vacuous / FAIL (point -0.56) | refused | -2.81 | +0.44 | 4,320 | 2.45 |
| i3 | empty (2 deliver rules refused `class-masked`) | FAIL / FAIL / PASS / vacuous / PASS | refused | -4.08 | -0.73 | 4,320 | 2.48 |

Clause values are from `iterations/i{1,2,3}/close-receipt.json` `verdicts.ace.clauses`. False fill and non-empty exact
are node-local normalised pp, ACE minus lock (`i{t}/node-local/tables.md`). GPU-active hours are from
`pairs/ace-vs-lock/efficiency.json` (`gpu_active_seconds` 8,978 / 8,810 / 8,924 s).

**Loop verdict.** Exactly three iterations ran, as the stop rule requires (`loop.stop_rule`). No ACE state was
accepted; no typed state flew. The i3 close receipt reads `loop_complete: true`, `parent_for_next: s0-lock-v2.2`.
The typed curve is level 0 at every point (marked refused, refused, unflown). The ACE curve is level 0 at every point
(marked refused three times), and its flown children are +0.87, +1.38 and +0.27 (`iterations/i3/curve.json`). Decision
269 A ends the loop here: this note and a ledger entry, no Fold A confirmation and no DEV composed read for refused
states.

**Two corrections to the brief's figures.** (i) The i1 lock level is **64.00 / 82.31**
(`i1/pairs/ace-vs-lock/score-contrasts.json`), not 64.34 / 82.41. 64.34 / 82.41 is the Fold B level of the system of
record (lock v2.2, the R6-P1 lock column) quoted in the 09:00Z decision brief. The lock levels of the three loop
columns are 64.00, 64.51 and 64.45 SLU and 82.31, 82.96 and 82.69 intent. (ii) "twins vs lock -0.49 / +0.32 / -0.37"
is right as a twin-vs-lock figure. The archive field that carries it is named `credit.vs_twin`, but it holds aa minus
lock, not ACE minus twin (section 6).

## 2. What the loop is

- **Archive.** Write-once states under `docs/readiness/2026-10-11-slurp-tfrl-loop-v1/archive/` (ids, hashes and
  numbers only). Two roots: `a8f1d50e...` (typed root, the lock v2.2 supply fragment `b6340f5f...`) and
  `81fc5504...` (ACE root, the empty playbook i0 `53268ec0...`). It ends with seven states: the two roots, three
  refused ACE states, and two refused typed delivery states (`ccbe1075...` i1 fx-oclock, `ad25d9da...` i2 ee5). It also
  holds one correction record (`archive/corrections/`) and one reread (`archive/rereads/`). The parent choice
  (`LB_slu - 0.25 pp x flown children`, mask a class after 2 refused children) kept `s0-lock-v2.2` throughout. After
  i2 it masked the `delivery` class (`iterations/i{2,3}/parent.json`: `masked_classes: ["delivery"]`, score -0.5).
- **Material.** One construction-source lock column on R01C (625 TRAIN rows outside Fold A, Fold B and DEV;
  `SAEA-SLURP-STAGE3-TFRL-CONSTRUCTION-LOCK-R01C-V1`, 1,250 contacts). It gave every iteration the same contrast
  tables (`tables_sha256` `6c925de6...` in all three open-propose receipts) and the same 18 per-scenario ACE material
  files. Fold B contributes only the ACE counters and the refused-candidate buffer (protocol
  `material_source.fold_b_role`).
- **Typed proposer.** The frozen core's text-only seam (264 A): 3 carriers, one contact each, temperature 0, schema
  `saea-tfrl-typed-candidate-v1`. The carriers carry the class sets `construction`, `supply` and `delivery+scope`
  (`scripts/flights/tfrl/tfrl_family.py:133`, `configs/baseline/slurp-native-stage3-tfrl-proposer-i{1,2,3}-baseline-v1.json`).
  A deterministic validator and the script objective decide. The model never judges (invariant I-OBJ). Edit budget
  L_t = 2, 1, 1. A supply or construction candidate flies only over the +1.5 pp predicted bar (decision 192). Delivery
  and scope rules are read offline, cross-fitted over the sealed columns. They are accepted iff CI95-LB > 0 and the
  point is >= 0.67 pp (`selection.offline_candidate`).
- **ACE comparator.** Reflector = the frozen core: 18 carriers, one per scenario, at most 3 adds and 6 deltas per
  contact. A deterministic curator (`ace-grow-refine-v1`, constants `0eeb1946...`) handles dedup (exact or Jaccard
  0.8), legality refusals, counters and pruning (harm margin 3, at least 10 scoped rows), and a token cap
  `T_cap` = lock p99 13,728 + 1,880 = 15,608. Counters are script credit: helpful / harmful / scoped_rows from the
  per-row official SLU-F1 of the previous ACE column against its lock, cumulative. The playbook is released as a
  knowledge store (`ace-playbook-i{t}`) and swapped into the Solver supply of the `ace` arm (`release_swap`).
- **Instrument.** Same-flight supply-variant design. In every column the arms fly in the order `ace`, `aa`
  (replicate_of lock), `lock` (delivering, last). Each column has 4 contacts per row (Perception + lock Solver + one
  first-visit Solver per non-delivering arm). The floors come from decision 190 at n = 1,080: SLU 1.49 pp, intent
  0.65 pp.
- **Acceptance (clauses a-e).** (a) SLU CI95-LB > 0. (b) SLU point >= 1.49. (c) SLU point above the same-flight twin's
  point. (d) Above the parent column; vacuous here, since no parent or previous-ACE column flew in any iteration.
  (e) Intent guard: CI95-LB >= -0.65 and point >= 0. A state is accepted iff every clause present holds
  (`selection.accepted_iff`).

## 3. Per-iteration reads

| item | i1 | i2 | i3 |
| --- | --- | --- | --- |
| open-propose receipt (inputs sha) | `6cedf0ec...`; L = 2; ACE playbook in = i0 (0 items) | `579659f2...`; L = 1; ACE playbook in = i1 release (27) | `b5c63add...`; L = 1; ACE playbook in = i2 release (35) |
| typed proposer run (flight commit) | `SAEA-SLURP-STAGE3-TFRL-PROPOSER-I1-V1` (`bd43ded89`) | `-I2-V1` (`192ba338c`) | `-I3-V1` (`7250fac92`) |
| proposer contacts / prompt / completion tokens / latency s | 3 / 18,845 / 555 / 11.4 | 3 / 19,178 / 548 / 11.4 | 3 / 19,676 / 548 / 11.7 |
| proposer receipts: legal, distinct ids, class | 3 legal, 1 distinct (3 x `688e0fd0` fx-oclock), all `delivery` | 3 legal, 2 distinct (2 x `e05bb6e9` fx-oclock, 1 x `714d10ff` ee5), all `delivery` | 3 legal, 2 distinct (1 x `7ed171a7` ee5, 2 x `3b62d42d` fx-oclock), all `delivery` |
| validator outcome (open-cell receipt) | valid 1 (offline), refused 0 | valid 1 (offline: ee5), refused 1 (`duplicate-of-archived`: fx-oclock = archived `ccbe1075`) | valid 0, refused 2 (`class-masked`) |
| ACE reflector run (flight commit) | `SAEA-SLURP-STAGE3-TFRL-ACE-REFLECTOR-I1-V1` (`58ebe92ea`) | `-I2-V1` (`08caeb10a`) | `-I3-V1` (`7250fac92`) |
| reflector contacts / prompt / completion tokens / latency s | 18 / 20,270 / 2,986 / 28.1 | 18 / 46,388 / 5,765 / 58.1 | 18 / 56,144 / 6,015 / 65.1 |
| answers kept / duplicate-carrier dropped / deltas in | 14 kept (9 non-empty) / 3 deltas dropped / 27 | 11 / 7 / 33 | 12 / 6 / 36 |
| curation | add 27; 0 dedup; 0 refused; counters none (no credit) | add 16, modify 8, delete 4; dedup 4 exact; refused 5 `unknown_target`; counters on 27 items (credit `640fc98d...`) | add 18, modify 7, delete 6, **pruned 6** by counters; dedup 4 exact + 1 near; refused 5 `unknown_target`; counters on 35 items (credit `9e5a5fe3...`) |
| playbook (content hash) | 27 items `e12fabcc...` (14 strategy, 12 pitfall, 1 format-rule; 3 `all`-scope) | 35 items `5a092424...` (22 / 12 / 1; 15 from i1, 20 new; 1 `all`-scope) | 36 items `1a93c791...` (25 / 10 / 1; 6 from i1, 10 from i2, 20 new; 1 `all`-scope) |
| rendered proxy tokens (allowance 1,880) / item bytes | 966 / 2,512 | 1,373 / 3,623 | 1,576 / 4,216 |
| ace item renders added (per row) | 5,841 (5.41) | 5,005 (4.63) | 5,559 (5.15) |
| column run (flight commit) | `SAEA-SLURP-STAGE3-TFRL-LOOP-I1-FOLD-B-V1` (`2b6416686`) | `-I2-FOLD-B-V1` (`cc51b4eff`) | `-I3-FOLD-B-V1` (`d39224f1c`) |
| contacts / speech s / prompt / completion tokens | 4,320 / 12,619.19 / 38,444,398 / 200,150 | 4,320 / 12,619.19 / 38,380,708 / 200,013 | 4,320 / 12,619.19 / 38,388,105 / 199,787 |
| generation wall s / GPU-active h / util % / contacts per min | 9,831 / 2.49 / 74.5 / 26.4 | 9,810 / 2.45 / 75.1 / 26.4 | 9,899 / 2.48 / 79.8 / 26.2 |
| registered `planned_gpu_hours` | 1.5 | 3.3 | 3.3 |
| sealed / closed (registry) | 2026-10-11 18:33Z / 18:40Z | 2026-10-12 05:49Z / 07:35Z | 2026-10-12 12:05Z / 12:35Z |
| close receipt (inputs sha) | `97a32a97...`; `ace_credit: not-built` | `a0072154...`; `ace_credit: written`; offline ee5 refused; reread fx-oclock refused | `bf830efc...`; `ace_credit: written`; `loop_complete: true` |

Sources: run manifests (`cost`, `plan`, `study_commit`, all `COMPLETED`, `study_repo_dirt` empty), `typed-receipts-i{t}.json`
(receipt fields only), `reflector-answers-i{t}.json` (counts and `dropped_duplicates` counts only),
`ace-release-staging/playbook-i{t}.json` (`curation` block, item counts by section, scope and `created_iteration`),
`node-local/report.json` `supply_stats`, and `iterations/i{t}/*.json`.

**What the proposer did.** All 9 proposer contacts over the three iterations returned a legal `deliver-rule` in class
`delivery`. Only two rule families appear: `fx-oclock` on alarm `time` (target SPURIOUS) in 7 of the 9 contacts, and
`ee5` on general `joke_type` (SPURIOUS) in 2. The proposer re-proposed the refused fx-oclock rule at i2 (twice, new
candidate id `e05bb6e9`) and at i3 (twice, `3b62d42d`). At i2 the open step refused it as `duplicate-of-archived`
(after the repair, section 6). At i3 the class mask pre-empted that check. The i3 ee5 candidate differs from the i2
one only in `target.value_in_supply` (`any` vs `none`), so it carries a new id. No construction, supply or scope
candidate was ever proposed. Each iteration had one carrier offered only `construction` and one offered only
`supply`. So at least 6 of the 9 delivery candidates came from carriers not offered `delivery`. Those 6 should have
been refused `class-not-allowed` but were not (section 6, defect 9).

**What the reflector did.** Every reflector answer kept at i2 and i3 carried exactly 3 deltas. The scenarios without
a kept answer were iot, qa, takeaway and weather at i1 (no carrier); cooking, datetime, email, iot, lists,
recommendation and takeaway at i2; and alarm, calendar, cooking, general, news and transport at i3. Its prompt grew
with the playbook (20.3k -> 46.4k -> 56.1k prompt tokens over 18 contacts).

## 4. The ACE curve and its composition

| | i1 | i2 | i3 |
| --- | --- | --- | --- |
| SLU vs lock (pooled) | +0.87 [-0.40, +2.10] | +1.38 [+0.15, +2.57] | +0.27 [-1.15, +1.71] |
| CI95 half-width (ACE / twin) | 1.25 / 0.62 | 1.21 / 0.65 | 1.43 / 0.67 |
| per-row SLU-F1 (saves / harms) | +0.21 [-0.80, +1.23] (50 / 42) | +0.68 [-0.29, +1.67] (44 / 37) | -0.18 [-1.20, +0.79] (44 / 48) |
| equal-scenario SLU / intent | +1.03 [-0.33, +2.46] / 0.00 | +1.22 [-0.32, +2.85] / -0.56 [-1.20, +0.00] | +0.74 [-0.55, +2.07] / +0.46 [-0.28, +1.20] |
| ACE minus twin, SLU point | +1.36 [+0.12, +2.58] (bootstrap, i1 note) | +1.06 (arithmetic only) | +0.64 (arithmetic only) |
| node-local exact set | +1.94 [+0.28, +3.61] | +1.30 [-0.37, +2.96] | +0.93 [-0.46, +2.41] |
| empty-gold false fill (newly filled / newly emptied) | -4.34 [-7.40, -1.02] (12 / 29) | -2.81 [-5.87, +0.26] (14 / 25) | -4.08 [-6.63, -1.53] (6 / 22) |
| non-empty exact (gained / lost) | +0.58 [-1.31, +2.47] (23 / 19) | +0.44 [-1.45, +2.33] (24 / 21) | -0.73 [-2.47, +1.02] (17 / 22) |
| raw (pre-v4g) false fill | -9.95 | -4.34 | -7.65 |
| predicted items lock -> ace | 896 -> 880 | 883 -> 877 | 908 -> 870 |
| rows whose text the v4g normaliser changed (lock / ace) | 203 / 170 | 181 / 175 | 186 / 172 |
| exchange-rate prediction (0.033 per emptied false fill, 0.070 per non-empty exact row) | +0.56 + 0.28 = +0.84 | +0.36 + 0.21 = +0.57 | +0.53 - 0.35 = +0.18 |
| scenarios up / down / flat (SLU) | 11 / 7 / 0 | 14 / 3 / 1 | 12 / 5 / 1 |
| per-scenario SLU range | -2.45 (news) .. +4.38 (recommendation) | -3.73 (audio) .. +4.07 (recommendation) | -5.28 (transport) .. +8.43 (lists) |
| twin per-scenario SLU range | -3.47 (lists) .. +4.41 (music) | -2.18 (calendar) .. +3.57 (recommendation) | -3.80 (general) .. +5.85 (lists) |
| scenarios whose CI excludes 0 (SLU) | none | none | audio +6.54 [+1.37, +13.67], lists +8.43 [+0.42, +18.43] |

Sources: `pairs/*/score-contrasts.json`, `pairs/*/per-scenario-tables.json`, `node-local/tables.md`; exchange rates
from `docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md` as applied in the i1 note. "Arithmetic only" means
the difference of two bootstrap points with no CI: no `ace-vs-aa` pair file exists for i2 or i3, and none was
computed here.

**Reading.**

- **The mechanism is the same in all three iterations: fewer empty-gold false fills.** False fill falls by 2.8 to
  4.3 pp normalised (4.3 to 10.0 raw) in every column, and ACE predicts fewer items than the lock in every column.
  This is the mass the locked v4g normaliser already works on: it changes 170-175 ace rows against 181-203 lock rows.
  The non-empty side never resolves (+0.58, +0.44, -0.73). The prose makes the Solver emptier; it does not add values
  the lock misses.
- **i2 was the high point and the only CI-LB > 0.** The exchange-rate model explains about +0.57 of the +1.38. The
  rest sits in partial-credit movement on rows whose exact status did not flip: per-row SLU +0.68, headset +1.40 vs
  far-field 0.00 (`per_channel.slu_f1_f1`). It came with the only intent loss of the series (-0.56; 3 saves / 9
  harms; cooking -3.33 and five scenarios at -1.67).
- **Why i3 fell back.** False fill held (-4.08). Non-empty exact turned negative (17 gained, 22 lost), and per-row SLU
  went to -0.18 (44 / 48). Intent moved the other way, +0.46 (10 / 5). The playbook churned: 20 of 36 items were new
  at i3, 6 were pruned by the counters and 6 deleted by reflector deltas, and only 6 of i1's 27 items survive. The
  counters behind the pruning are small: the i3 counter updates cover 35 items, mostly 4-60 scoped rows each, with
  helpful and harmful counts mostly 0-7. So the prune rule (harm margin 3) acts on a handful of rows per item. The
  record cannot separate "i3's items are worse" from noise. The i2 -> i3 step (-1.11 pp) is smaller than one ACE
  contrast's CI half-width (1.21-1.43). The lock level itself moved 0.51 pp across the three flights. The twin's
  offset swung from -0.49 to +0.32 to -0.37.
- **The two resolved i3 scenarios do not resolve as an ACE effect.** In the same flight the twin moves lists by
  +5.85 against the lock, so the lock was low on lists in that column. Audio was -3.73 at i2.
- **The series is flat, not converging.** The mean of the three points is +0.84 pp, about the i1 value. The SLU and
  intent deltas trade sign between i2 and i3. Credit-driven curation did not produce a monotone curve. The protocol
  marks every point refused and repeats level 0.

## 5. The typed arm: why it stayed empty

- **Before the loop.** Decision 265's class, credit-driven selective knowledge augmentation from TRAIN, had no
  candidate over the +1.5 pp predicted bar. The coverage pre-read
  (`docs/results/2026-10-11-slurp-tfrl-coverage-preread-fold-b-offline.md`) found a cross-fitted composite of -1.00 pp
  SLU and a largest honest number of +0.27. It also found that 61 % of MISSING items already sit in the delivered
  supply, 36 % of gold-side error items have no value in TRAIN outside the folds, and 18 reachable MISSING items are
  spread over 14 slot types. Its prediction was "no supply or construction candidate will clear the bar". Decision
  266-A flew the stall default on that basis.
- **In the loop.** The prediction held trivially: the proposer never proposed a supply or construction candidate (all
  9 contacts returned `delivery`; section 3). The record therefore does not measure whether the proposer could find a
  supply candidate. It measures that the proposer, under these prompts, reached for delivery rules even when not
  offered that class.
- **The offline fits.** Three reads, each `+0.00 pp`, CI [0.00, 0.00], **`rows_edited` 0**:
  - fx-oclock (`ccbe1075`) on the i1 lock column, read by `repair --iter 1` (`iterations/i1/repair-receipt.json`);
  - ee5 (`ad25d9da`) on the i2 column (`iterations/i2/close-receipt.json` `verdicts.offline`);
  - the fx-oclock reread on the i2 column (`archive/rereads/ccbe1075...-i2.json`).

  A rule that edits no row cannot move the score, so these are non-firing rules, not measured null effects. On the i1
  lock column there were only 4 spurious `time` entities across all 18 scenarios (i1 note, section 5). The i3
  candidates were never fitted: both were refused `class-masked` before any read, so the typed curve point for i3 is
  `unflown`.
- **Operator class exhausted.** "Exhausted" means here: the only class the proposer used (delivery), with the two
  families it reached for, edits no Fold B row, and the parent choice masked that class after two refused children.
  It does not mean that construction, supply or scope candidates were tried and failed. None were proposed.

## 6. Defects and repairs across the three iterations

| # | defect | iteration | effect | repair / status |
| --- | --- | --- | --- | --- |
| 1 | archived ACE i1 state bound the stale 0-item playbook (`6c69ae03...`, written by a superseded open-cell run) instead of the flown 27-item one | i1 | i2 curation would have grown from 0 items | write-once correction record `archive/corrections/state-e7b4fa57...-playbook-hash.json` (wrong `6c69ae03` -> right `e12fabcc`, derived from the open-cell receipt `a42c3c43...`); `repair --iter 1`; the state file itself still names `6c69ae03` (immutable) |
| 2 | ACE credit not built at i1 (`close` ran without `--row-scores`) | i1 -> i2 | first i2 curation ran credit-free | built 2026-10-12 01:03Z with the driver's own function (`iterations/i1/ace-credit-build-receipt.json`; row scores `f4c1d2d5...`, 1,080 rows); i2 inputs re-extracted with `--supersede` (playbook `27dabd20...` superseded by `5a092424...`); `close` now exports row scores and builds the credit itself (i2, i3: `ace_credit: written`). Checked here: the credit-free and the credit i2 playbooks hold the **same 35 item ids and texts**. The credit changed counters on 14 items and the item order only. So the credit's first effect on playbook membership was the i3 pruning |
| 3 | offline fx-oclock candidate skipped silently (family not in `FIT_FAMILY`) | i1 | no record of the refused candidate | read by `repair --iter 1`: +0.00, 0 rows edited, refused, archived as `ccbe1075` |
| 4 | duplicate of an archived candidate (re-proposed fx-oclock, same artefact set -> same state id) | i2 | `close --iter 2` refused (`state ccbe1075a873 is archived with different content`) | `repair --iter 2 --duplicates-only` (`iterations/i2/repair-duplicates-receipt.json`): reclassified `duplicate-of-archived` at open, three receipts superseded at `20261012T010412Z`, reread written as an `archive/rereads/` sibling; open now refuses archived duplicates and shows them to the proposer |
| 5 | column READ row countersigned after the close's sub-steps had read the sealed column | i2 | ledger lapse: the countersignature (06:38:27Z) follows the 05:50Z close start | recorded in the READ row and the registry; i3 READ row countersigned 08:20:17Z BEFORE READ, with the flight rows |
| 6 | planned vs actual GPU hours | i1-i3 | i1 plan 1.5 vs 2.49 GPU-active h (spec estimate 1.1); i2 / i3 plan 3.3 (measured rate, 1.3 margin) vs 2.45 / 2.48 | calls and audio at plan in all three (4,320 / 4,320; 12,619.19 / 12,620 s); no breach of the run-cumulative rule; the i2 / i3 plans over-cover by about 35 % |
| 7 | flip time on the 9p mount | i1-i2 | 40-80 min per package (`import core.flight.cli` 38.3 s cold from `/mnt/d`, `git status` 7.6 s) | decision 267: flips from an ext4 worktree (`flip_in_ext4.sh`), lazy runtime imports; registry reports 9 min for a proposer package and 34 min for a column package afterwards (registry figures, not re-measured here) |
| 8 | i1 build-wave defects (ACE snapshot pin = file hash; campaign inspector without a native config; placeholder in the exposure rows' artifacts cell; construction-role gate scanning companion files) and the i2 reflector re-pin refused by a six-digit sample-identifier false positive on item ids | i1, i2 | one smoke recovery (i1 rec1, 0 calls before it); batch STOPs; i2 reflector delayed | fixed `785b2fb9d` / `02dc21855`, `58ebe92ea`, `535ae32f2`, `16512119e`, `4c9d2bfb5` (as recorded in the i1 note and the registry) |
| 9 | **found by this read: the carrier class set is not enforced.** `tfrl_cell_stage_inputs.build_typed_receipts` (line 160) writes entries with only `receipt` and `sample_id_sha_prefix`. `tfrl_loop_driver.py:555` passes `entry.get("allowed_classes")`, which is therefore `None`, so `validate_candidate`'s `class-not-allowed` check (`tfrl_typed_proposer.py:1194`) never ran | i1-i3 | at least 6 of 9 delivery candidates came from carriers offered only `construction` or `supply` and were accepted as legal (`refused: 0` at i1) | **open**. Also: the field `sample_id_sha_prefix` holds the first 12 hex digits of the response sha256, not a sample id hash |
| 10 | **found by this read: `credit.vs_twin` holds aa minus lock in all three ACE states**, not ACE minus twin | i1-i3 | the field name misreads; the registry corrected the i1 label and the i2 / i3 entries print it as "twin vs lock" | **open** in the archive schema (states are write-once; a rename needs a successor schema). Clause c compares the points correctly |

## 7. What the record supports, and what it does not

**Supports (ledger entry, decision 262 clause c; Fold B only, development numbers).**

1. Three iterations of the sealed-credit loop, each with a same-flight twin and the preregistered clauses a-e,
   produced **no accepted state**. The loop is closed with the parent at `s0-lock-v2.2`.
2. The typed proposer, a frozen-core text seam reading aggregate contrast tables from a fixed construction column,
   proposed only delivery rules. They came from two families, with one rule re-proposed three times. Every rule
   edited 0 Fold B rows (+0.00 pp), and the class was masked after i2. No supply, construction or scope candidate was
   ever proposed. The class restriction per carrier was not enforced (defect 9).
3. The ACE prose-item form at equal budget (27, 35 and 36 items; 966-1,576 of 1,880 allowance tokens) moved SLU-F1 by
   +0.87, +1.38 [+0.15, +2.57] and +0.27 against the lock. It never reached the 1.49 floor, and its best point came
   with an intent cost (-0.56). Its effect is fewer empty-gold false fills in every column, a mass the locked v4g
   normaliser already harvests. The non-empty side never resolved. Credit-driven curation did not make the curve
   monotone.
4. The loop's engineering is complete and reusable for another operator class: archive with write-once corrections
   and rereads, script credit built by the close, duplicate refusal at open, class masking, and ext4 flips.

**Does not support.**

- Any claim beyond TRAIN Fold B. There is no Fold A confirmation, no DEV composed read and no test read (decision
  269 A). The Fold B split was read three times.
- Any ACE benefit claim. The i2 CI-LB > 0 is one of three reads on the same split, with the intent guard failing. It
  is not replicated at i3. ACE is non-lockable by design.
- "The supply or construction class cannot help". That class was never proposed in the loop; the evidence for it is
  the 265 pre-read, not the loop.
- Any statement about other carriers (Audio2Tool, Earnings), the Thinking core (268 B), or system-level performance.
- A causal attribution of the i2 -> i3 fall to the curation step. It is inside the flight-to-flight noise of this
  design.

**Unverifiable or not verified here.** The i3 column's launch time (only the generation wall, 9,899 s, and the
12:05Z seal are on file). The smoke contact counts of the i2 and i3 columns (not read). The ACE-minus-twin CIs for
i2 and i3 (arithmetic points only). The flip durations after decision 267 (registry figures). The mapping of each
proposer response to its carrier: trace response hashes and receipt hashes use different encodings, and the request
texts were not read, so the "at least 6 of 9" bound is derived from the carrier class assignment and the receipt
classes, not from a per-carrier read. Per-contact reflector delta counts at i2 and i3 are taken from the curation
`deltas_in` and the registry; the answer strings were not parsed here.

## 8. Records read

- Loop: `docs/readiness/2026-10-11-slurp-tfrl-loop-v1/` (`README.md`, `tfrl-loop-protocol-v1.json`, `loop-state.json`,
  `archive/state-*.json` (7), `archive/corrections/state-e7b4fa57...-playbook-hash.json`,
  `archive/rereads/ccbe1075...-i2.json`, `iterations/i{1,2,3}/{open-propose-receipt,open-cell-receipt,candidates,offline-candidates,close-receipt,curve,parent,proposer-meta}.json`,
  `iterations/i1/{ace-credit-build-receipt,repair-receipt}.json`, `iterations/i2/repair-duplicates-receipt.json`).
- Column packages: `docs/readiness/2026-10-11-slurp-tfrl-loop-i{1,2,3}-fold-b-v1/generation-plan-registered-v1.json`
  (`planned_gpu_hours`, calls, audio); proposer packages `docs/readiness/2026-10-11-slurp-tfrl-loop-i3-proposers-v1/`
  (file list).
- Registry: `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, from "Decisions 263-265 ruled" through
  "Loop iteration 3 CLOSED" (262, 266, the build wave, i1-i3 opens, seals, closes, the 267 directive, the 09:00Z and
  11:40Z briefs, rulings 268-273 and 287-295).
- Exposure ledger: the three `...-FOLD-B-COLUMN-READ-V1` rows (countersign times).
- Data root (legacy, read-only): `analysis/SAEA-SLURP-TFRL-LOOP-V1/i{1,2,3}/pairs/{ace-vs-lock,aa-vs-lock}/{score-contrasts,per-scenario-tables,efficiency,verdict}.json`;
  `i{t}/node-local/{tables.md,report.json}`; `i{t}/ace-release-staging/playbook-i{t}.json` and the superseded i2
  playbook (counts, ids and text hashes only); `i{t}/reflector-answers-i{t}.json` and `i{t}/typed-receipts-i{t}.json`
  (counts and receipt fields only); run manifests of `SAEA-SLURP-STAGE3-TFRL-{PROPOSER,ACE-REFLECTOR}-I{1,2,3}-V1` and
  `SAEA-SLURP-STAGE3-TFRL-LOOP-I{1,2,3}-FOLD-B-V1`; proposer `trace.jsonl` (response-hash fields only).
- Code (read only): `scripts/flights/tfrl/{tfrl_family.py,derive_tfrl_iteration_cells.py,tfrl_loop_driver.py,tfrl_cell_stage_inputs.py}`;
  `src/speech_aware_evidence_acquisition/rails/tfrl_typed_proposer.py`;
  `configs/baseline/slurp-native-stage3-tfrl-proposer-i{1,2,3}-baseline-v1.json` (carrier class sets).
- Notes: `docs/results/2026-10-11-slurp-tfrl-loop-i1-fold-b-column-read.md` (i1 structure, ACE vs twin bootstrap, the
  4 spurious `time` entities); `docs/results/2026-10-11-slurp-tfrl-coverage-preread-fold-b-offline.md` (section 0);
  `docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md` (cited through the
  protocol's `authority`).
