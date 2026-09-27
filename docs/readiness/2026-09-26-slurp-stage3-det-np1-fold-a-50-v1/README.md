# Cell DET: is the measurement floor an engineering artefact?

Registered before contact 2026-09-27 at study commit `9255ac71` (worktree
`/home/chao/saea-worktrees/fable-det`, branch `fable/det`); both cells are **held**. Nothing here authorises a
flight, a flip, a serving-session change or an admission entry, and the registration made zero model,
tokenizer, encoder, scorer, server, GPU and network contacts.

**The hypothesis.** The binding instrument note
[`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`](../readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md) records that two **request-identical** flights of
the locked plan differ by +1.87 pp SLU at n = 625 (VAR1 PLAN vs PLANR, CI95 [+0.41, +3.36]), +0.17 at
Fold A 1,080 and -0.25 at DEV 1,000, and that even inside one flight only 91.5 % of delivered answers
are byte-identical ([`docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md`](../../docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md), 183 of 200). From that the
programme set a cross-flight admission bar of 2.5-3.0 pp, which no single mechanism has cleared. But
the locked arm decodes at **temperature 0** on a server running **four slots under continuous
batching with the prompt cache on and a q8_0 KV cache** -- exactly the configuration in which
llama.cpp greedy decoding is known not to be bitwise reproducible: a request's numerics depend on
which other requests share its batch and on cache state. Nobody has measured whether a **single-slot
server with the prompt cache off** makes the flight reproducible. If it does, the between-flight
offset collapses and the programme can see effects it currently cannot; if it does not, the offset is
intrinsic and the programme stops hoping.

**The cell.** The locked PLAN arm (`SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`), byte-identical in every knob, flown **twice
in one chain** -- pass A (`SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-A-V1`), then pass B (`SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-B-V1`) -- on the
**first 50 rows of TRAIN Fold A** in roster order (the same first 50 rows PLAN flew; alarm 7, audio 3, datetime 2, general 5, iot 9, music 7, news 2, play 1, takeaway 6, weather 8;
10 of 18 scenarios, a stated limitation), on a **new serving geometry**
`q4km-mmproj-free-slurp-native-bounded-perception-proof-np1-nocache-ctx24k-max512-v1`, resident session `serving-slurp-native-det-np1-nocache-v1`. Per row the read asks one thing: are the two delivered
answers the same bytes?

**The one variable, flag by flag** (the resident `q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1` against the DET fragment;
everything not in this table is identical, including the model file and sha256, the runtime receipt,
`-fa on`, `-ctk q8_0 -ctv q8_0`, `-b 2048 -ub 512`, `-ngl 999`, `--cache-ram 0`, `--no-cache-idle-slots`,
the server_env, the decoding params, the prompt order and the speech packets):

| flag | resident np4 | DET np1 |
| --- | --- | --- |
| `--cache-prompt` | [True] | None |
| `--no-cache-prompt` | None | [True] |
| `--slot-prompt-similarity` | ['0'] | None |
| `-c` | ['98304'] | ['24576'] |
| `-np` | ['4'] | ['1'] |

`--no-cache-prompt` is explicit because llama.cpp defaults `cache_prompt` to **true** and the transport
sends no per-request override; with it the server sets `n_past = 0` for every request and re-processes
the whole prompt from an empty KV cache. `--slot-prompt-similarity` routes requests among idle slots by
cached-prefix similarity and has no object with one slot and no cache. The slot stays 24,576 tokens, so
prompt fit is unchanged.

**Where the geometry lives, and the composed-config proof.** The harness declares a geometry in two
places that must agree: the fragment's `-np`/`-c` (what llama-server is handed) and the baseline's
`serving_slots`/`serving_slot_tokens` (the adapter's flight-side geometry, which
`core.session.serving.merge_server_args` writes back over `-np`/`-c` at attach time and which sizes the
dispatcher's concurrency, `workers = slots`). So the derived baselines move **exactly one**
non-bookkeeping key against the PLAN lock baseline -- `serving_slots` 4 -> 1 -- and the composed diff
against the locked PLAN cell ([`geometry-diff-v1.json`](geometry-diff-v1.json)) is, fragment by fragment:
model `{geometry_basis, profile_slot_count, server_args}`; baseline `{serving_slots}` plus the per-cell
bookkeeping `{native_contact_fit, prepared_phase_supply (dropped), what_this_is}`; dataset nothing;
experiment the per-cell identities, budgets, population and prose only. `native_episode`,
`knowledge_stores`, `phase_material`, `policy`, `scorers`, `decoding_params`, `prompt_order`,
`server_env`, `speech_feature_root` and every other key are the PLAN cell's own bytes
(`tests/unit/test_stage3_det_np1_cells.py`). Pass B differs from pass A only in its FIT identity and its prose. **No code change
is needed** to express `-np 1` or the prompt cache off: `merge_server_args` is the identity on the DET
fragment, `resolve_serving_profile` resolves one 24,576-token slot, and the only `--cache-prompt`
requirement in the tree (`core.driver.speech_native.profile_agent_kv_policy`) is reached from the legacy
`speech-native-profile` CLI, never from `FlightRuntime`.

**Declarations.** `stage3_measurement` (both run ids): `measurement_design` `form-proof`, `rows` 50,
`claims_benefit` **false**, `expected_effect_pp` **0.0** -- the cell measures reproducibility (per-row byte
identity across two passes and the SLU/intent difference of the pair) and makes no effectiveness claim;
no `admission` mode. `stage3_algorithm` `none`: no rollout, no per-sample scoring, no credit assignment,
no update operator, no evolving store; the cell is a property of the rig, not of any algorithm.

**Decision 140.** Owner decision 140 (2026-09-26): the np1 cache-off test is authorised as a CHEAP TEST, but ADOPTION of any geometry is decided on THROUGHPUT, because future rounds need massive sampling. This cell decides a DETERMINISM question and INFORMS a THROUGHPUT one; the coordinator will not adopt np1 for sampling-heavy work on determinism alone. The read therefore reports, beside per-row byte identity, contacts per minute and prompt tokens per second for each pass at the np1 cache-off geometry -- from the sealed dispatch window (flight-receipts.json run_phases: wall_seconds, contact_window, contact_count) and the sealed generation manifest's cost block (prompt_tokens_total) -- and the same two numbers for the resident np4 geometry from ROLL-2's sealed arm (8,996 contacts, 81,435,827 prompt tokens, 16:00:01Z to 18:22:39Z, 8,558 s: 63.07 contacts per minute, 9,515.8 prompt tokens per second), so the trade is one table.

| geometry | contacts per minute | prompt tokens per second | source |
| --- | ---: | ---: | --- |
| np4 x 24,576, prompt cache on (resident) | 63.07 | 9,515.8 | ROLL-2 sealed arm, 8,996 contacts / 81,435,827 prompt tokens / 8,558 s |
| np1 x 24,576, prompt cache off (pass A) | measured | measured | sealed `run_phases` window + generation manifest cost |
| np1 x 24,576, prompt cache off (pass B) | measured | measured | sealed `run_phases` window + generation manifest cost |

**Budgets, as arithmetic (per pass).** 550 generation contacts (50 x the
program's own 11-contact ceiling, run-cumulative), 2200 FIT
endpoints (4 x), 300 native task-contract calls (50 x 6, a
tool-free form; expected 0), 1184 repeated speech seconds
(ceil(107.6111875 x 11)), 2.0 GPU hours, one
official complete score. Expected spend about 251 contacts per pass (PLAN's
realised 5.023 per row) and about 0.6814 GPU hours per pass at an
assumed 4x np1 per-contact cost (0.1704 at the np4
rate); the whole cell about 502 contacts and
1.36 GPU hours. The brief's own estimate of
about 850 contacts assumed 8.5 per row; PLAN realised 5.0.

| file | what it holds |
| --- | --- |
| `../2026-09-26-slurp-stage3-det-np1-fold-a-50-v1-preregistration.md` | the preregistration proper, including the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free measured fact, and the CANONICAL `stage3_measurement` |
| `geometry-diff-v1.json` | the flag-by-flag argv diff, both serving profiles, the two-halves proof, the composed diff by fragment |
| `protocol-registered-v1.json` | identities, hashes, budgets, the read rule, the claim boundary |
| `a-generation-plan-registered-v1.json` / `a-fit-plan-registered-v1.json` | pass A's two plans |
| `b-generation-plan-registered-v1.json` / `b-fit-plan-registered-v1.json` | pass B's two plans |
| `analysis-recipe-v1.json` | the read, step by step (`scripts/analysis/slurp_det_pair_read.py`, run by `scripts/flights/det/det_read.sh`) |
| `root-admission-draft-v1.json` | the decision receipt for root to mint (`scripts/flights/det/det_mint_receipt.py`) |

**Registered identities.**

| pass | run id | FIT run id | composed config | protocol |
| --- | --- | --- | --- | --- |
| A | `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-A-V1` | `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-A-FIT-V1` | `658e8032585f7214133d21528d5b7b2afebabe8ebfb48432c6645cf45a2d2ac9` | `3c915405b94fac53bb59d91d34f098a56ac85adb3f0b9ff74cbf472dd5b77931` |
| B | `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-B-V1` | `SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-B-FIT-V1` | `26b248f6541989f25205169a6c963b66bc00c345ee362e89ad963b5277c6de78` | `6548e1ff67469a5318badf614cd96c70ea5ea9e01e3f6760dda835cc49e3fc53` |

Split identity `af8154d5dedd3768b145a9d5f5ef6d90eb0ab0f6611a02ee82b2f22fd73a07fa`; id-list sha256 `1fed658cdf96580f021887e54b1964d544dd55e8d70afd39a7e3744640f2f4b5`; roster
`docs/receipts/rosters/slurp-stage3-det-fold-a-50-v1.json`. Every configs/baseline and configs/experiment hash moves at the flip and the re-pin
tool rewrites this package.

**No committed `prepared_phase_supply`, empty requirements lists.** The flip mints each pass's own
first-phase supply under its own run id (item E16); pass B's output block must reproduce pass A's byte
for byte -- a different value means the pair is not request-identical: stop and report, never pass
`--allow-output-change`.

**Mint, flip, swap, launch, read, restore** (the coordinator; this package authorises none of it):

1. Let the CONV probe seal; confirm no flight, lease or driver process and no `locks/flight.lock`.
2. `python scripts/flights/det/det_mint_receipt.py` -- mints `coordination/slurp-stage3-det-np1-fold-a-50-v1/root-admission-v1.json` (decision id
   `slurp-stage3-det-np1-fold-a-50-admission-v1`) from the draft with the four eligible run ids; countersign the five DRAFT
   exposure rows (A, A-FIT, B, B-FIT, READ).
3. `bash scripts/flights/det/det_flip_all.sh` -- pass A then pass B through `repin_loop_generic.sh`
   (the check attaches to nothing; the np4 session may still be resident here). The last flip's commit
   is the flight commit (`/home/chao/det-flight-commit.txt`).
4. Swap the serving session: stop the Windows task that owns the np4 wrapper, `bash
   scripts/serving_session.sh stop --session-id serving-slurp-native-candidate-five-train-a-np4-v1`, confirm `serving_session.sh
   resident` exits 3, the card is free and port 8080 is closed; then run
   `scripts/flights/det/serving_task_entry_det.sh` as the task action (it refuses while the np4 session
   is recorded resident) and `bash scripts/flights/det/det_wait_ready.sh`, which proves `/props`
   `total_slots` 1 / `n_ctx` 24576 and the recorded argv (`--no-cache-prompt`, no `--cache-prompt`, no
   `--slot-prompt-similarity`).
5. `bash scripts/flights/det/batch_chain_det.sh` -- two steps, pass A then pass B, `BATCH_SESSION`
   the DET session; the driver's prelaunch requires that session idle and healthy.
6. `bash scripts/flights/det/det_read.sh` once both passes are sealed.
7. Stop the DET session and restore the np4 session (`scripts/flights/batch/serving_task_entry.sh`)
   so the np4 queue resumes.

**Not authorised by this package.** No flight before the receipt is minted, the rows are
countersigned, both passes are flipped and the DET session is resident; no contact by this
registration; no test-split, Fold B or DEV contact or read; no knob change; no floor re-estimate from
50 rows; no adoption of np1 for sampling-heavy work on determinism alone.
