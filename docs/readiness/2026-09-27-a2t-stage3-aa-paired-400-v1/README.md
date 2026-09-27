# Cell A2T-AA: Audio2Tool's own request-identical null on the paired 400

Registered before contact 2026-09-27 at study commit `eb5e463b`; all three cells are
**held**. Nothing here authorises a flight, a flip or an admission entry.

**Why an own null and not a mechanism.** Every Audio2Tool interval in `docs/results/stage2-results-ledger.md` is read
against zero: row A2T-NULL says NOT MEASURED. The measurement instrument
(`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`) shows what that costs: on SLURP two request-identical
flights of the same 625 rows differ by +1.87 pp SLU-F1 with a CI95 that excludes zero. Owner decision 68
orders the null FIRST on the paired 400 of decisions 67 and 71; decision 139 (2026-09-27) puts it on the
GPU queue; instrument rule 6 seals a roster's own null BEFORE any contrast on it. The 2026-09-04
official-protocol replication failed on seven tiers within noise and the construction pool cannot reward
the dominant lighting confusion, so no mechanism is proposed here: the instrument is established.

**The treatment is the sealed direct baseline, twice.** `a2t-native-role-direct-union4000-v1` -- the
direct-only phase program of the shared controller (`phase-direct-only-v1`) through `FlightRuntime` and
the OpenJiuwen executor, official-protocol compact registry, promoted speech packets, c98304 np3 max2048
-- flies as pass A and pass B in ONE batch-driver chain on ONE resident Audio2Tool session, after a
four-row smoke. Between the passes the only config bytes that differ are the `live_phase_fit`
identities and the `what_this_is` prose, neither of which enters a request (proved by composing both
cells: `registered-facts-v1.json` `request_identity_proof_before_contact`). No separate code path exists
for the baseline: the same harness that flies every arm flies this one.

**The roster.** `docs/receipts/rosters/a2t-paired-400-v1.json` -- `A2T-PAIRED-400-V1`, 50 rows per tier over the eight tiers,
one seeded draw (seed 20260921, decision 71) by `core.roster.freeze_roster` from the sealed union-4000;
2760.438 s of speech, 355 distinct query blocks, domains
smart_home 306, wearables 74, smart_car 20;
1 of the union's four 654-second synthesis-defect
rows kept. Every row already carries a sealed direct comparator row
(`SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1`), whose per-row request and response hashes are frozen in
`docs/receipts/rosters/a2t-paired-400-v1.comparator-rows.json` -- never the text. Split identity `965f145f581753874353216a25109a4746627095027cefbab0ed91c88090990a`.

**Geometry: NOT the resident SLURP geometry.** The last flown Audio2Tool cells (SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1 and its dual-store sibling, 2026-09-15) served q4km-mmproj-free-a2t-native-role-np3-max2048-v1: -c 98304 -np 3 (three 32,768-token slots), max_tokens 2048, --no-mmproj, LLAMA_SPEECH_FEATURE_ROOT /home/chao/feat-cache/a2t-native-system-4000-packets-04ccc72a, port 8080, session serving-a2t-native-role-base-np3-max2048-v2. The resident SLURP session serving-slurp-native-candidate-five-train-a-np4-v1 serves q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1: -c 98304 -np 4 (four 24,576-token slots), max_tokens 512, LLAMA_SPEECH_FEATURE_ROOT /home/chao/feat-cache/slurp-q4km-packets-04ccc72a. FlightRuntime.serve attaches only to a session whose recorded identity (model fragment and its sha256, argv flag by flag, env) matches the cell's fragment, and the runtime refuses a speech_feature_root that disagrees with the promotion receipt's feature_root; the two sessions therefore differ in identity twice over (slot count and packet root) and NO Audio2Tool cell can attach to the resident SLURP session. Consequence: Audio2Tool cells do not interleave with SLURP cells inside one session. They fly only after the SLURP session is stopped and SAEA-Serving-A2T is resident (one geometry swap in, one back), which is why decision 69 pays the swap only when at least two Audio2Tool cells are ready -- this chain is three flights on one session.

**Packets: already promoted; no preparation registered.** Every one of the 400 rows already holds a promoted SpeechFeaturePacketV1 under /home/chao/feat-cache/a2t-native-system-4000-packets-04ccc72a, pinned by the sealed 2026-09-12 promotion receipt prepared/SAEA-A2T-NATIVE-SYSTEM-PACKETS-V1/promotion.json (sha256 720d81f63a1923f19893c0ee171e1ab7b47f9a946c1e62a06bdddd839243de8a) that the committed direct baseline pins; the roster builder proved 400 of 400 packet ids present. No CPU packet preparation is registered because none is owed: zero encoder contacts.

**The read** (`analysis-recipe-v1.json`) is descriptive. Request identity first (`request_sha256` equal on
400 of 400), then per-row byte identity of the delivered tool call (identical of 400), then the pair's
paired difference on the official tool accuracy (`a2t-toolcall-official`, the repo scorer `a2t-toolcall`
beside it) with a tier-stratified paired bootstrap CI95 (10,000 draws, seed 20260903) in the
natural-mixture and the equal-tier weighting; its half-width is **h_A2T**, the margin every later
Audio2Tool interval is read at. Beside it: each pass against the sealed direct rows of the same ids, and
contacts per minute (decision 140). There is no verdict and no admission.

**`stage3_measurement`.** Pass A and pass B: `cross-flight-with-in-chain-replicate`, `rows` 400,
`expected_effect_pp` 0.0, `claims_benefit` false, `replicate_run_id` the other pass. The smoke:
`form-proof`, `claims_benefit` false. `stage3_algorithm`: `none` -- an instrument carries no operator.

| cell | run id | attempt | fit run id (contact cap) | rows | composed config | protocol |
| --- | --- | --- | --- | ---: | --- | --- |
| smoke | `SAEA-A2T-STAGE3-AA-PAIRED-400-SMOKE-4-V1` | `attempt-a2t-stage3-aa-paired-400-smoke-4-generation-v1` | `SAEA-A2T-STAGE3-AA-PAIRED-400-SMOKE-4-FIT-V1` (13) | 4 | `9adcadaa534c75e9d0f13a5a12fbd7bd979423dec7edbb33f258204fdeb8e63a` | `d5769316f8634c9e76333a8e483dc2bda9afe6633f726726a917867716a552a7` |
| pass A | `SAEA-A2T-STAGE3-AA-PAIRED-400-A-V1` | `attempt-a2t-stage3-aa-paired-400-a-generation-v1` | `SAEA-A2T-STAGE3-AA-PAIRED-400-A-FIT-V1` (1201) | 400 | `cfd6783ce1ebd696329bede91fdc2bc91cabe119c283756f2464b443fc435f95` | `fabed23cfe5b85be32ce6a30b302cf8f0306eb1e6277d3b507cf6011ff9b32d5` |
| pass B | `SAEA-A2T-STAGE3-AA-PAIRED-400-B-V1` | `attempt-a2t-stage3-aa-paired-400-b-generation-v1` | `SAEA-A2T-STAGE3-AA-PAIRED-400-B-FIT-V1` (1201) | 400 | `bad06cd4ef11a7f41dfdbaed0910f317c2c108937dfa66d745000e4c83a158d0` | `b538d2aa3b81a5e12312dbe69c43c2c9381aea237b63ffcccd06dbca5f58ddd7` |

**Budgets, as arithmetic.** Per pass: 400 generation contacts (400 rows x 1,
the direct-only program's exact maximum), 1201 live-fit endpoints
(1 + 3 x 400, the count the fit gate requires), 2761 speech seconds
(one pass over the roster), 0.5 GPU hours (a ceiling: the sealed direct
flew 4,000 contacts in 1,518.6 s at np3, so 400 cost about 152 s of generation),
one official complete score. Smoke: 4 contacts, 13
fit endpoints, 21 s, 0.2 GPU hours, no score.
Whole chain: at most 804 contacts, 2,415 fit endpoints, 1.2 GPU hours; expected about 0.15 GPU hours.

| file | what it holds |
| --- | --- |
| `../2026-09-27-a2t-stage3-aa-paired-400-v1-preregistration.md` | the preregistration proper, including the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free measured fact, the geometry and packet findings, and the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, budgets, the read rule, the claim boundary |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's two plans |
| `a-generation-plan-registered-v1.json` / `a-fit-plan-registered-v1.json` | pass A's two plans |
| `b-generation-plan-registered-v1.json` / `b-fit-plan-registered-v1.json` | pass B's two plans |
| `analysis-recipe-v1.json` | how the null is read, step by step |

**Mint, flip, swap, queue.** (1) Root mints `coordination/a2t-stage3-aa-paired-400-v1/root-admission-v1.json` (decision id `a2t-stage3-aa-paired-400-admission-v1`,
`eligible_run_ids` = the six run ids above) and countersigns the seven exposure rows. (2) Root flips all
three cells at ONE commit: `bash scripts/flights/batch/a2taa_flip_all.sh` (one `repin_cell.py --set-ready`
call over the three cells, so the shared protocol document and every plan sha are rewritten once; the
program has no supplied first phase, item E38, so no artifact is prepared). The flight commit lands in
`/home/chao/a2taa-flight-commit.txt`. (3) When the SLURP queue is idle (no `flight.lock`, no driver):
`bash scripts/flights/batch/serving_switch_to_a2t.sh`; from Windows stop `SAEA-Serving` and
`SAEA-Monitor`, register and start `SAEA-Serving-A2T` on `serving_task_entry_a2t.sh` and `SAEA-Monitor-A2T`
on `serving_monitor_start_a2t.sh`; `bash scripts/flights/batch/a2t_wait_ready.sh`. (4) Register and start
`SAEA-Batch-Driver` on `batch_chain_a2taa.sh` (steps: smoke + pass A, then pass B). (5) After the seal:
`bash scripts/flights/batch/serving_switch_a2t_to_slurp.sh`, restart `SAEA-Serving` and `SAEA-Monitor`,
`slurp_wait_ready.sh`. (6) The read, model-free, per the recipe.

**Not authorised by this package.** No flight before the receipt is minted and the cells are flipped; no
contact by this registration; no benefit or admission claim; no test-split contact; no re-flying of the
comparator; no flight on the SLURP session.
