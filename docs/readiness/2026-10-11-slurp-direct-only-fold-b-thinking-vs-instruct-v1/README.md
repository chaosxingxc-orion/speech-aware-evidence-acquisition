# Cell 266-E: the bare-core read on TRAIN Fold B, Thinking versus Instruct

Registered before contact 2026-10-11 at study commit `918d13ad42e0728b0e5b6d20a2c6898f33a4bacc`; all four cells are **held**. Nothing here authorises a
flight, a flip, a serving swap or an admission entry.

**The question (owner decision 266-E).** The 265 coverage pre-read left the supply side of SLURP SLU at its plateau; the remaining mass is values TRAIN
never shows and values already supplied and not used, both core-side. Is the CORE, not the system, the binding constraint? The system is core-agnostic
by design, so a stronger core transfers every locked component. This read holds the system out entirely: the sealed direct-only form
(`phase-direct-only-v1`, the shared controller, `FlightRuntime`, OpenJiuwen, the `slurp-direct-max512` task instruction) flies on TRAIN Fold B 1,080 on
the Instruct core and on the Thinking core. The Thinking model is admitted ONLY for this read, never as the serving core of a system cell.

**The cells.**

| cell | run id | attempt | fit run id (contact cap) | rows | composed config | protocol |
| --- | --- | --- | --- | ---: | --- | --- |
| four-row Thinking decode-cost smoke | `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SMOKE-4-V1` | `attempt-slurp-direct-only-fold-b-thinking-smoke-4-generation-v1` | `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SMOKE-4-FIT-V1` (13) | 4 | `669453c509da06ac3783a9b86b724127a8eba04641b585396852174a74c0c84d` | `043b2190799f41958c049bc500259a212c54e3135585a64beafe07354a45ebec` |
| Thinking arm | `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-V1` | `attempt-slurp-direct-only-fold-b-thinking-generation-v1` | `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-FIT-V1` (3241) | 1080 | `ec7e8a224b3e5047b540fa5724e6c669b0fc1368176b27785a218183c2c22838` | `38e3c3e08f36f49a9b6d4da09ca0e2992909c0a3f7d4ea039ad7e686b6905545` |
| Instruct arm | `SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-V1` | `attempt-slurp-direct-only-fold-b-instruct-generation-v1` | `SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-FIT-V1` (3241) | 1080 | `e0b5ca15eac7e8d28c6ea138297c6d5a247c9a9983f4609e80edd0b1a44678b4` | `29181d729d63139e56423295427f18d7b7ce23451d874cc1ac6e05f811d5248d` |
| Instruct in-chain replicate | `SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-REPLICATE-V1` | `attempt-slurp-direct-only-fold-b-instruct-replicate-generation-v1` | `SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-REPLICATE-FIT-V1` (3241) | 1080 | `1cc456aab4d0a7659d00c0b4859866b9b3126e3ed002fcdd28dd930109db5fc9` | `96ee26f07726feac2a43158b01849be6e39c0c37dc5846d8bb41551bac1efefe` |

**Cross-session by necessity.** The 24 GB card holds one core, so Thinking and Instruct cannot share a flight. The Instruct arm therefore flies twice
(arm and request-identical replicate, one chain, one session) and the Thinking delta is read against the mean of the two at the cross-flight bar (about 2.5 pp
at n = 1,080; instrument note section 2d); `stage3_measurement` is `cross-flight-with-in-chain-replicate` on every arm, `claims_benefit` false, `stage3_algorithm`
`none`. The smoke is `form-proof`. No sealed Instruct direct-only Fold B column exists. The sealed direct-only (phase-direct-only-v1, slurp-direct-max512) columns are SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-V1 (Fold A), -DEV1000-V1 and -DEV2000-ADDED-V1 (devel rosters). Fold B carries only the older EVO-S1 confirmation flight of the 'fixed' closed-list arm (SAEA-SLURP-EVO-S1-FOLD-B-V2), a different form on a different code path, which is not a same-harness comparator. The Instruct arm and its replicate therefore fly in this chain: the comparison must be same-chain.

**Finding 1: the Instruct speech packets are not valid for the Thinking core.** The audio-encoder tensors of the two mmproj files differ: 748 of 860 tensors are not byte-identical (name-for-name comparison of the GGUF tensor tables of mmproj-Qwen3-Omni-30B-A3B-Instruct-bf16.gguf and mmproj-Qwen3-Omni-30B-A3B-Thinking-bf16.gguf; the 112 identical tensors are the non-audio ones). The Instruct speech-feature packets (/home/chao/feat-cache/slurp-q4km-packets-04ccc72a) are decoder-ready projector outputs of the Instruct encoder and are therefore NOT valid input for the Thinking decoder. The Thinking core needs its OWN packet root (/home/chao/feat-cache/slurp-q4km-packets-thinking-afdaeff6) prepared by an encoder pass over TRAIN Fold B (registered, held: ledger row SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-V1, fragment q4km-thinking-preprocess-featcache-cpu-sidecar-np4-v1); the Thinking baselines pin its future promotion receipt with a zero sentinel the flip refuses.

**Finding 2: reasoning stays out of `content`.** Reasoning stays out of the delivered content by the server flag --reasoning-format deepseek (registered explicitly in the serving fragment's server_args). Evidence from the pinned featcache build 04ccc72a2 (read-only grep): tools/server/README.md line 220 documents the option (none leaves thoughts in message.content; deepseek puts thoughts in message.reasoning_content; deepseek-legacy keeps <think> in content AND fills reasoning_content); common/arg.cpp line 3130 defines it; common/common.h line 622 makes COMMON_REASONING_FORMAT_DEEPSEEK the build's own default; common/chat.cpp line 828 maps it. The transport (core/model/transport.py) reads ONLY choices[0].message.content (and tool_calls); it never reads reasoning_content. The cells set preserve_wire_responses false, so no raw wire bytes (which would carry reasoning_content) are persisted. Client-side guard: the fragment declares reasoning_content_guard refuse-think-marker-in-content, and the transport raises FrozenCoreError when a delivered content string carries <think>, </think>, <thinking> or </thinking> (case-insensitive), BEFORE anything is returned or persisted; the flight stops (a leak means the option is not effective). The reader counts leak markers in the sealed delivered text (count only) as a second check.

**Finding 3: the completion cap.** Completion cap 2048 tokens. Slot budget: -c 98304 / -np 4 = 24,576 tokens per slot. The direct-only prompt is about 2,300 tokens per row (the sealed Instruct direct form measured 2,262 to 2,280 prompt tokens per contact; 3,733 on the A2T registry). 2,300 + 2,048 = 4,348 tokens, 17.7 percent of a slot, so the cap is bound by decode cost, not by the slot; a cap of 8,192 would still use only 42.7 percent. 2048 is proposed because a SLURP answer is a short structured object, so a thinking trace that needs more than 2,048 tokens is itself the signal the read must see (a truncated answer is an abstention, counted in the cap-hit table), and because the smoke measures the real distribution before the arm is queued. The coordinator may amend the cap at the decode-cost sign-off (one re-registration changes the fragment hash and re-pins the cells); the GPU-hour ceiling of 3.0 is the 1,080-contact worst case at ~250 aggregate tokens per second.

**Chain.** Chain order. The brief's order smoke -> sign-off -> Instruct arm -> replicate -> Thinking arm would swap the serving geometry three times (Instruct resident now: swap to Thinking for the smoke, back to Instruct, to Thinking again, and back to restore). The registered order is smoke -> sign-off -> Thinking arm (Thinking session), then ONE swap back to the Instruct session (which is also the required restore) and the Instruct arm -> Instruct replicate: two swaps total. The Instruct segment has no dependency on the Thinking one, so the coordinator may fly it first on the resident session before the swap if GPU idle time during the sign-off is the concern; batch_chain_direct_fb.sh takes the segment as an argument (smoke | thinking | instruct), checks the resident session by id and refuses on a mismatch. All segments fly from ONE flight commit.  The Thinking arm segment refuses until the coordinator's decode-cost sign-off marker `/home/chao/direct-fb-decode-signoff.marker` exists.

**Pins.** `VERIFIED against the umbrella lock entry (local hash receipts == lock revision text, sizes equal)`. Per-file hashes are carried by `docs/receipts/runtime-q4km-thinking-mmproj-free.json` (main GGUF, as the Instruct receipt does) and `docs/receipts/runtime-q4km-thinking-preprocess.json`
(main + mmproj) and live in the umbrella lock entry `qwen3-omni-30b-a3b-thinking-gguf-q4km`; `scripts/flights/direct/direct_fb_pins.py` refuses to write a fragment if a local
hash is absent or differs from the lock.

## Serving release and restore checklist (the coordinator's; nothing here executes it)

0. Preconditions: the four cells are flipped at one flight commit (scripts/flights/direct/direct_fb_flip.sh); the Thinking packet root is prepared and its promotion receipt pinned (the flip refuses while the zero sentinel remains); the decision receipt is minted; no generation flight, lease or driver is alive and no CPU sidecar runs (one experiment in flight).
1. Tell the uptime guard: create /home/chao/saea-queue/watchdog.hold (the idle watchdog then exits at step 3 of every tick and cannot swap the geometry back, force an uptime restart, or launch another chain while the Thinking session is resident or the sign-off is pending). Confirm with scripts/flights/batch/idle_watchdog.sh --dry-run that it logs the hold. Do not edit ready_chains.json; leave the hold in place until step 9.
2. Dry run: bash scripts/flights/batch/serving_swap.sh think-np4 --dry-run (prints every precondition verdict; starts, stops and registers nothing).
3. Release Instruct and start Thinking: bash scripts/flights/batch/serving_swap.sh think-np4. The tool stops serving-slurp-native-candidate-five-train-a-np4-v1 cleanly and its tasks (SAEA-Serving, SAEA-Monitor), verifies port 8080 free, starts the Windows task SAEA-Serving-THINK (scripts/flights/direct/serving_task_entry_think.sh) and SAEA-Monitor-THINK 20 s later, then the strict readiness wait; on any failure it tears the Thinking session down and restores Instruct. The two task names are new: the first run registers them through saea_task.ps1 -Start with the entry script.
4. Smoke: bash scripts/flights/direct/batch_chain_direct_fb.sh smoke (flies the four-row smoke through the batch driver on the Thinking session; the driver's structural inspector runs). Then python -B scripts/analysis/slurp_direct_fold_b_core_read.py --stage smoke prints tokens per answer p50/p99, seconds per contact and the 1,080-row GPU-hour projection.
5. Sign-off: when the decode cost is acceptable, create the marker /home/chao/direct-fb-decode-signoff.marker (a one-line file naming the approved completion cap). The thinking segment refuses to start without it. If the cost is not acceptable, close the line (restore, step 8) or amend the cap by one re-registration.
6. Thinking arm: bash scripts/flights/direct/batch_chain_direct_fb.sh thinking.
7. Release Thinking and restore Instruct: bash scripts/flights/batch/serving_swap.sh slurp-np4 (the restore; the Instruct task entry is the existing serving_task_entry.sh), then bash scripts/flights/direct/batch_chain_direct_fb.sh instruct (the Instruct arm, then its replicate).
8. If the Thinking line closes before the arm: bash scripts/flights/batch/serving_swap.sh slurp-np4 alone restores the resident geometry; the Instruct segment may still be flown (it is a useful Fold B direct-only column on its own).
9. After the Instruct session reports ready (SLURP SESSION READY from serving_wait_ready.sh slurp-np4) remove /home/chao/saea-queue/watchdog.hold; the watchdog resumes from the committed ready_chains.json. Stop SAEA-Serving-THINK and SAEA-Monitor-THINK (serving_swap does this on the stop) and leave them unregistered or disabled; remove the decode sign-off marker.
10. Read: bash scripts/flights/direct/direct_fb_read.sh (countersign the READ row first).

## Prerequisites still open

1. **Thinking speech packets (P0).** Prepare the Thinking packet root over TRAIN Fold B (CPU sidecar, `q4km-thinking-preprocess-featcache-cpu-sidecar-np4-v1`) and pin its promotion receipt
   in the two Thinking baselines (zero sentinel today). `scripts/slurp_evo_fold_preprocess.py` is wired to the Instruct runtime receipt and root and needs a Thinking
   variant; ledger row `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-V1` is a DRAFT placeholder for it.
2. **Task registration.** `SAEA-Serving-THINK` / `SAEA-Monitor-THINK` are registered by the first `serving_swap.sh think-np4` through `saea_task.ps1`.
3. **Countersignatures and the receipt.** `countersign-row-texts-v1.json`; then `scripts/flights/direct/direct_fb_mint_receipt.py`, then `direct_fb_flip.sh`.

| file | what it holds |
| --- | --- |
| `../2026-10-11-slurp-direct-only-fold-b-thinking-vs-instruct-v1-preregistration.md` | the preregistration proper, with the `stage3_measurement` fence and the read rules |
| `registered-facts-v1.json` | every model-free fact, the findings, the checklist, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | the protocol document every plan pins |
| `*-generation-plan-registered-v1.json`, `*-fit-plan-registered-v1.json` | the eight registered plans (smoke, thinking, instruct, replicate) |
| `analysis-recipe-v1.json` | the read recipe, declaring the READ run id `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-VS-INSTRUCT-READ-V1` |
| `root-admission-draft-v1.json` | the draft decision receipt (eight eligible run ids) |
| `countersign-row-texts-v1.json` | the row texts root writes when countersigning |
