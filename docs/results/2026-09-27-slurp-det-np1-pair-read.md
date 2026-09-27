# Cell DET read: 50 of 50 rows byte-identical between two request-identical passes on one slot with the prompt cache off (DESCRIPTIVE)

Read 2026-09-27. The registered model-free read row `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-READ-V1` was
executed by the coordinator with `scripts/flights/det/det_read.sh`, which runs
`scripts/analysis/slurp_det_pair_read.py` (sha256
`ffea63e6a4659ebd69c8478e9d3734c1ad1d3f986495d79059b2cbea6c1c0e16`, the registered bytes; a copy sits
beside the output) and then `scripts/analysis/slurp_paired_roster_read.py` (sha256
`90831272906e0b149c0ef70dca39130bfa7a8190f615cb7077d6c572ffb1faac`, likewise), following the registered
recipe `slurp-stage3-det-np1-fold-a-50-pair-read-v1`
(`docs/readiness/2026-09-26-slurp-stage3-det-np1-fold-a-50-v1/analysis-recipe-v1.json`) step by step.
This note was written by Fable 5.1 (worktree `/home/chao/saea-worktrees/detread`, branch `fable/detread`)
from the sealed files only. Analysis root
`$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-READ-V1` (`summary.json` sha256
`2d8c4f548c7288f461c5c1e392e832eac74369fd7a34c81c833ec0e47ee97b74`, `per_row.json`
`c928f1997069daf626b7bbef4f385abbb6c913194327738d04f16d86b99667c9`, `stop.json`
`d8e3f5b3fe8b5fc66214d4506d8d091f8021d4b225de16a02025cc31bf6cd500`, `stage-pair-read.log`
`f62f63671d5326afe87c7180f656d6d892b7d1a91d4acdcef919c2851561ba34`; the descriptive stage's
`paired-roster-read/` files are hashed in section 3 and its `stage-paired-roster-read.log` is empty,
0 bytes). Model-free: zero model, tokenizer, encoder, embedder, scorer, llama-server and network
contacts; the official scorer ran once per pass at finalize and its sealed per-sample output is read,
never re-run; nothing under either sealed run directory was opened for writing. No utterance text,
transcript, gold label string, intent name, entity value or delivered answer is printed or persisted
here or in the receipt; the delivered text was read into memory only to re-hash it against its recorded
digest.

Status: **DESCRIPTIVE** (a reproducibility count on a 50-row TRAIN Fold A prefix whose pair is its own
control; no admission, no effectiveness, superiority or generalisation claim, no floor re-estimate; the
cell decides a determinism question and informs a throughput one, and this note disposes nothing).

## 1. What flew

The locked v2.0 plan, cell PLAN (`SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`), byte-identical in every
knob, flown twice in one chain on a new serving geometry: one 24,576-token slot with the prompt cache
off. Session `serving-slurp-native-det-np1-nocache-v1` (started 2026-09-27 05:03:43 UTC, model fragment
`q4km-mmproj-free-slurp-native-bounded-perception-proof-np1-nocache-ctx24k-max512-v1`, fragment sha256
`2618cda4e58e4c51eb6850c962564e8556d57833cb249dc33e99242262bd0424`; llama-server binary sha256
`d0b42ace8d8e02dc772a0e4a1e1667068b3ad799b1ca4c98c741cf89d58404f2`, runtime receipt sha256
`b061c8f53635916f6169acac75896048112a9fad5860db4bf7d1a51700e96e77`, session receipt sha256
`1908e9e6f7411db5806deb8fca251e40bf3c6954b3f0eef6b3df49a02d1618b0`). Recorded server argv beyond the
model: `-c 24576 -np 1 -b 2048 -ub 512 -fa on -ngl 999 -ctk q8_0 -ctv q8_0 --no-cache-prompt
--cache-ram 0 --no-cache-idle-slots`; `/props` reported `total_slots` 1 and `slot_n_ctx` 24576; no
`--cache-prompt`, no `--slot-prompt-similarity`. Against the resident np4 geometry the flag diff is
exactly `-np 4 -> 1`, `-c 98304 -> 24576`, `--cache-prompt -> --no-cache-prompt` and
`--slot-prompt-similarity 0` removed (`geometry-diff-v1.json`); the q8_0 KV cache, flash attention,
batch sizes, model file, packets, prompts and decoding parameters (temperature 0, seed 20260913,
max_tokens 512) are the PLAN cell's own bytes.

Roster: the first 50 rows of TRAIN Fold A in roster order
(`docs/receipts/rosters/slurp-stage3-det-fold-a-50-v1.json`, sha256
`c68366a5e5d73c0de280a46f8ce16b746b93f334935270c48051fd5c356306a8`, id-list sha256
`1fed658cdf96580f021887e54b1964d544dd55e8d70afd39a7e3744640f2f4b5`, split identity
`af8154d5dedd3768b145a9d5f5ef6d90eb0ab0f6611a02ee82b2f22fd73a07fa`; 10 of 18 scenarios; 26 far-field
and 24 headset recordings). Flight commit `99a3f1f5` (`99a3f1f57ff13d51ab572505f19a2970b098f256`) on
both passes, study tree clean at both seals (`study_repo_dirt` empty). Both manifests COMPLETED, both
attempts FINALIZED, 50 of 50 rows admitted and parsed on each pass, one complete official scoring job
each (`slurp-slu-official-train`, evaluator commit `8eb16545`, identity check passed; 55.4 s and 50.5 s,
`failed` 0, never sharded).

| artefact | pass A `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-A-V1` | pass B `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-B-V1` |
| --- | --- | --- |
| attempt | `attempt-slurp-native-stage3-det-np1-fold-a-50-a-generation-v1` | `attempt-slurp-native-stage3-det-np1-fold-a-50-b-generation-v1` |
| composed config / protocol hash | `658e8032585f7214133d21528d5b7b2afebabe8ebfb48432c6645cf45a2d2ac9` / `3c915405b94fac53bb59d91d34f098a56ac85adb3f0b9ff74cbf472dd5b77931` | `26b248f6541989f25205169a6c963b66bc00c345ee362e89ad963b5277c6de78` / `6548e1ff67469a5318badf614cd96c70ea5ea9e01e3f6760dda835cc49e3fc53` |
| run manifest | `c26bbece79c75632021cba0ca945156338bcb04b52ccceedb6bc13f66ea240b2` | `dfadbec23b68376da68ec48b289d527ab4845ae064ecd14711aa973a47f0f2f9` |
| generation manifest | `deab321a4b7e1e0a27e85594f71a582c6440e0b31523e8633620eb94339eb61b` | `9d51f3f50a75a2f63d380ad86c697de68856c4f172c59258a3b246adab030c5b` |
| outputs | `65d97afc0ae1768b343182b3ecd5acbd2a37e2c62d6b3e3a13998767bea05bbf` | `20f56d5287e55fdfbd5a326f795088dbb745b1c673da500805a09cf5c31ddb92` |
| scores | `04b2f6629d1e6141923e418162c1083f4ab9586419e48293e70a612fd0c7bc45` | `4345f0a06b8a277456d0cefcaf71cfeae6d46fcfc644fce7b1eb8095eb021176` |
| phase artefact | `8441147e110ff8fd4531c11497136b8fae9c005723debf16fd43392d3720d5ca` | `caf285ad53ea7850b539c1b352bd520f4b70240a993db556513eee5d6937f4cd` |
| trace manifest / raw trace | `ddc07dc8f22f13160d3e2abdf941a18f95699d17ef6eb7889614ee39bb83fa38` / `afa38550230362e3ec1adb0f19d093fd1214478de97d984eaf0b9b805d5bb747` | `0accb41739aa2feaf2915683fceddc5a6555166270cf96573f8ae0b9cafccea5` / `5a76784d42899604107ffea2ad2900dea0cbd0821c2ee438eb2a59afd27db88a` |
| flight receipts | `4b5fc10769a8898d1693f40cf4c24b8533238715883924557ff138143901c822` | `762cfd6cf6814efef02be488b31a70105aa93dded5187b13b55f7906bbf238e0` |
| session-attach receipt | `e8166db31975d6e2599310995f2cc97f115b71590e4a95abe586832a37e01847` | `ac3bbaa76a6473af26f00c0079ba0f2de3ccd10c624836bebf986337baf4d541` |
| official score-batch result | `b6f735df053dda4e7ae37379c124a88423f985f9cde4d2046a1a3553cf453df0` | `298e7eba8ce346e7509f20febfd8ba2f3261a7336eb878791e867bfc30aaebd2` |

## 2. The recipe's gates

| step | gate | result |
| --- | --- | --- |
| 1 | STOP unless both attempts FINALIZED, both manifests COMPLETED with an empty `study_repo_dirt`, both bind the roster's split identity, both outputs files carry exactly the roster's ids, and every delivered text re-hashes to its recorded `response_text_sha256`; record both study commits and the expected session id | held on every clause; `same_study_commit` true, `delivered_text_rehash_ok` true on both passes, expected session `serving-slurp-native-det-np1-nocache-v1` |
| 2 | per row, the two delivered digests and `byte_identical`; the count of identical rows out of 50; the per-stratum table | **50 of 50**, every stratum complete (section 3) |
| 3 | ROLL-AA's within-flight np4 statistic and the cross-flight np4 disagreement reported BESIDE, never as a comparator | reported (section 3) |
| 4 | from the sealed official per-sample scores, the paired deltas B - A with CI95 by row bootstrap (10,000 draws, seed 20260915); flip shares where the per-sample rows carry the parsed prediction; then the programme-standard paired roster read | held: both deltas 0.0, CI95 [0.0, 0.0]; the sealed per-sample rows carry `parsed` and the exact flags, not the parsed prediction, so the flip shares have denominator 0 (50 rows `unknown`) and the zero flip counts are entailed by byte identity, not measured through the scorer; the paired roster read ran and its seven files are hashed below |
| 5 | throughput (decision 140): contacts per minute and prompt tokens per second per pass from the sealed `run_phases` window and the generation manifest's cost block, beside ROLL-2's np4 numbers, in one table, window definitions stated | held (section 4) |
| 6 | ROUTE, quoted verbatim in section 6 | quoted; not applied here |

## 3. The numbers

| quantity | value |
| --- | ---: |
| rows whose delivered answer is byte-identical between pass A and pass B | **50 of 50** (share 1.0) |
| `scenario_action_exact` disagreements between the passes | 0 of 50 |
| paired delta, per-row SLU-F1 (B - A), mean and CI95 | 0.0 pp, [0.0, 0.0], sd 0.0 (n 50, 10,000 draws, seed 20260915) |
| paired delta, intent exact (B - A), mean and CI95 | 0.0 pp, [0.0, 0.0], sd 0.0 |
| intent flips / entity-set flips | count 0 with denominator 0 (the scorer's per-sample rows carry no parsed prediction; 50 rows `unknown`); entailed by byte identity |
| official scores, identical on both passes | intent accuracy 84.00 %, scenario 84.00 %, action 90.00 %, SLU-F1 66.58 % (precision 64.63, recall 68.66), span F1 65.62 % |

Per stratum (rows / byte-identical): alarm 7 / 7, audio 3 / 3, datetime 2 / 2, general 5 / 5, iot 9 / 9,
music 7 / 7, news 2 / 2, play 1 / 1, takeaway 6 / 6, weather 8 / 8. Per channel (paired roster read):
far-field 26 rows and headset 24 rows, every per-row metric 0 saves, 0 harms, all ties, McNemar p 1.0.

The two passes also match on every sealed spend counter: 208 contacts, 1,647,247 prompt tokens and
12,426 completion tokens each; per-row contact counts 46 rows at 4, 3 rows at 7 (one revision), 1 row at
3; Planner routes ACCEPT 49 and REVISE 3 on both; the deliver-normaliser changed 3 rows on both (2 on
the already-legal branch, 1 on the r-action branch); the single finite-completion row is the same row on
both passes (`finite_completion_rows` 1 per pass, `deliver-latest-or-abstain`, no Planner route on that
row). Wire-envelope digests (`response_sha256`) differ between the passes, as they carry per-request
fields; the identity read here is on the delivered answer text.

Reported beside, never as a comparator (recipe step 3): on the resident np4 geometry with the prompt
cache on, two greedy passes of one Solver visit INSIDE one flight were byte-identical on 183 of 200 rows
(91.5 %, 15 entity-set flips, 0 intent flips; ROLL-AA,
`docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md`), and two request-identical
FLIGHTS differed on about 28 % of raw outputs and about 5 % of intents, +1.87 pp SLU-F1 with CI95
[+0.41, +3.36] and -1.28 pp intent at n = 625 (VAR1 PLAN vs PLANR; instrument note section 2b). Those
numbers were measured on other rosters at other n; the comparison the programme wanted is
qualitative, and it is answered: with batch composition and cache state removed, the delivered answer
repeats byte for byte on every row.

Descriptive stage (`paired-roster-read/`, recipe
`slurp-stage3-det-np1-fold-a-50-paired-roster-read-v1`, pass B against pass A, `utterance_id`
clustering): pooled micro SLU-F1 66.58 / 66.58, span F1 65.62 / 65.62, every delta 0.00 with CI95
[0.00, 0.00]; structural: 50 rows admitted on each side, 0 tool calls, 0 context compactions, 208
`tokenizer`-class contact-fit receipts per pass, all cache `cold`. Files and sha256: `README.md`
`b391d4f32194a80eb27d9aeb9909da675d29e3637515859792e1d69bee9f9189`, `verdict.json`
`9fa3c249321791edfe0119c4737261a62dea16f0af6005625c833ed34b5eb8d5`, `structural.json`
`d7eafd54eea424ef2c2d9b980c97379c8b9644b2e020029b607ef8158b0ea567`, `score-contrasts.json`
`fcb2c6dc2fb358d1beef9e1ff1ea038ce9c4ea2ee22cdeb6fc41eea1b8990ba9`, `efficiency.json`
`5be3f700830395db25e54ba0f17476d75dde4f2615191e6ad5e36e795110f2ac`, `per-scenario-tables.json`
`ec8b076587f3dabeb50677911abf1d3d1c313748aab9234a99908e5d7df02abd`, `stop.json`
`88ba5e3b9278089c10e0ebc8d37496e9a58bb985a1c16f847a9aa8098e305dd3`. It carries no bar and no verdict.

## 4. Throughput (owner decision 140)

Decision 140 makes the measured throughput a deliverable of this read and states that adoption of any
geometry is decided on throughput, not on determinism. One table, as the recipe requires:

| geometry | contacts | prompt tokens | wall s | contacts per minute | prompt tokens per second |
| --- | ---: | ---: | ---: | ---: | ---: |
| np1 x 24,576, prompt cache off (pass A) | 208 | 1,647,247 | 827.08 | **15.09** | **1,991.6** |
| np1 x 24,576, prompt cache off (pass B) | 208 | 1,647,247 | 838.14 | **14.89** | **1,965.4** |
| np4 x 24,576, prompt cache on (the resident geometry; ROLL-2 sealed arm `SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1`) | 8,996 | 81,435,827 | 8,558 | **63.07** | **9,515.8** |

Ratios, np4 over np1: 4.18x and 4.24x in contacts per minute (about 4.2x), 4.78x and 4.84x in prompt
tokens per second (about 4.8x). Window definitions: the DET passes use each attempt's sealed dispatch
`contact_window` (first to last contact by the runtime's own clock, model load excluded; pass A
05:13:43 to 05:27:31 UTC, pass B 05:29:23 to 05:43:22 UTC, 2026-09-27); the ROLL-2 figure uses the
arm's wall window as the coordinator recorded it (first to last contact of the arm, 16:00:01Z to
18:22:39Z), the same interval measured a different way. Slot occupancy on the single slot was 0.859
(A) and 0.855 (B); mean per-contact latency 3.42 s and 3.44 s.

## 5. Spend and dispositions

| quantity | pass A | pass B |
| --- | ---: | ---: |
| generation contacts used / cap | 208 / 550 (4.16 per row) | 208 / 550 (4.16 per row) |
| speech audio seconds used / cap | 445.863 / 1,184 (roster 107.611 s, replayed 4.14x) | 445.863 / 1,184 |
| GPU, monitored active | 13.00 min (0.2167 GPU-h) inside a 13.55 min window; mean utilisation 81.1 %, parked fraction 0.040, mean 82.1 W, peak 97.5 W; cap 2.0 GPU-h | 13.23 min (0.2204 GPU-h) inside a 13.77 min window; 79.5 %, 0.040, 83.6 W, 97.4 W; cap 2.0 GPU-h |
| prompt / completion tokens | 1,647,247 / 12,426 | 1,647,247 / 12,426 |
| tool calls (native tool calls; rows answered as text) | 0 (208 of 208 as text) | 0 (208 of 208 as text) |
| dispositions | finite_completion 1 row, context compaction 0 contacts and 0 rows, planner_action_illegal 0; Planner ACCEPT 49 / REVISE 3 | the same, on the same row |
| official scoring | one complete job at finalize, 55.4 s | one complete job at finalize, 50.5 s |
| FIT identity | `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-A-FIT-V1` opened no attempt and no run directory (its flip-minted first-phase supply sits under `prepared/`); the 208 `tokenizer`-class contact-fit receipts (0 compactions) sit inside the generation attempt, against the 2,200 FIT endpoint cap | `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-B-FIT-V1`, likewise: 208 of 2,200 |

Whole cell: 416 contacts, 891.725 speech-audio seconds, 0.4371 monitored GPU-active hours (26.23 min)
over two contact windows totalling 27.75 min, with 112.9 s between the end of pass A's window and the
start of pass B's (seal, score and the next launch). The registration expected about 251 contacts and
about 0.6814 GPU-h per pass at an assumed 4x np1 per-contact cost (about 502 contacts and 1.36 GPU-h
for the cell); realized 208 and 0.2167 / 0.2204, so the assumed 4x per-contact GPU cost came in at
about 1.5x of PLAN's 0.000679 GPU-h per contact while the wall-clock throughput fell about 4.2x, the
difference being the four overlapping slots the np4 geometry keeps busy.

## 6. The reading

The between-flight offset the instrument note records on np4 (section 2b: +1.87 pp SLU-F1 with a CI95
excluding zero between two request-identical flights at n = 625, about 28 % of raw outputs and 5 % of
intents differing, and only 91.5 % byte identity even inside one flight) is therefore a serving property
of that geometry -- continuous batching across four slots with the prompt cache on, over a q8_0 KV
cache -- and not a property of the model or of the harness: the same model file, the same q8_0 KV
cache, the same harness, prompts and packets, on one slot with the prompt cache off, repeat the
delivered answer byte for byte on 50 of 50 rows with zero paired difference. What this cell removed
was batch composition and cache state; the quantised KV cache stayed, so the offset is attributed to
the batching-and-cache side of the np4 configuration.

The price is measured, not assumed: np1 with the cache off is deterministic and about 4.2x slower in
contacts per minute and about 4.8x slower in prompt tokens per second than the resident np4 geometry
(section 4). Decision 140 decides adoption on that throughput, not on determinism.

The recipe's routing rule, verbatim (`analysis-recipe-v1.json`, step 6): "ROUTE: 50 of 50 identical ->
the coordinator registers the 200-row re-estimate; fewer -> the offset is intrinsic and this axis
closes. State in the same paragraph that a 50-row cell cannot support a floor re-estimate, that the cell
decides a determinism question and informs a throughput one, and that np1 is not adopted for
sampling-heavy work on determinism alone." The machine result's own routing line (`summary.json`,
`routing_rule`) reads: "50 of 50 rows byte-identical. ALL rows repeat: the between-flight offset is an
artefact of batch composition and cache state on the np4 geometry; the coordinator scales this probe
to 200 rows for a floor re-estimate (a separate registration). A 50-row cell cannot support a floor
re-estimate; it decides only whether the 200-row re-estimate is worth flying." Both are quoted as
pre-declared text. This note applies neither: under owner decision 139 no disposition is taken on a
branch written before the number was seen, and the owner disposes in conversation. A 50-row cell
cannot support a floor re-estimate, this cell decided a determinism question and informed a throughput
one, and np1 is not adopted for sampling-heavy work on determinism alone.

Claim boundary: DESCRIPTIVE. A byte-identity count measures the instrument, not an effect; 50 of 50
does not make a 200-row floor, does not re-estimate any bar, and says nothing about any mechanism,
carrier, held-out split or paper-scale claim. Development rows only (owner decisions 28 and 86).

## 7. Records

- `docs/exposure-ledger.md`: rows `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-A-V1`,
  `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-A-FIT-V1`, `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-B-V1`,
  `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-B-FIT-V1` and `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-READ-V1`
  flipped to consumed with the sealed facts above and closed by a closure block each; no other row
  touched.
- `docs/results/stage2-results-ledger.md` and `.json`: a DESCRIPTIVE entry for cell DET (`SLURP-DET`,
  tally `instrument`).
- Machine receipts `summary.json`, `per_row.json` and `stop.json` under the analysis root, sha256 as
  above; the two driver copies beside them hash to the registered driver bytes.
- Gates: the seven offline gates (`finite_completion_policy_check`, `results_ledger_check`,
  `harness_admission_check`, `engineering_base_check`, `tool_catalog_check`,
  `stage3_algorithm_label_check`, `stage3_effect_floor_check`) pass in the read worktree with these
  records applied (`results_ledger_check` PASS: 87 rows, 133 run ids registered and closed, the
  status word re-parsed from this note's first line); `bash scripts/flights/batch/main_gates_generic.sh`
  on the main checkout exits 0. `handoff_freshness_check` reports `stale-vs-results` against the
  standing handoff's stamp `2026-09-27T05:23:19Z`; refreshing that file is the coordinator's step at
  landing, not this read's.
