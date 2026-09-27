# The dispatcher slot fill: the gap reproduced, the cause located, the key proven byte-identical

Owner decision 159 (2026-09-27): keep every serving slot loaded during a phase-program flight with no change
to any byte a node sees. This directory is the model-free falsifier receipt of the `dispatch` key
(`rails.dispatch_slot_fill`), the run-class licence `scripts/checks/harness_admission_check.py` re-verifies
through `MANIFEST.sha256`. Zero model, server, encoder, scorer, endpoint and network contacts: the proof bench
refuses every INET connect in its own process, and ports 8080 and 8081 were never touched.

## 1. The gap, reproduced exactly

`scripts/analysis/slotfill_gap_decomposition.py --compare-note` over the sealed ROLL-2 trace and the ROLL-2
lifetime of the resident np4 session's `server.log` (lifetime 11 of 14 in the file today, selected as the one
that launched the most tasks in the attempt's own contact window; the note parsed the file's last lifetime,
later lifetimes have been appended since) -> `gap-decomposition-v1.json`. Every figure of the note's
accounting matches to the tenth of a second:

| figure | note | reproduced |
| --- | ---: | ---: |
| joined contacts | 8,994 | 8,994 |
| slot capacity (4 x 8,227.2 s) | 32,908.6 slot-s | 32,908.6 |
| empty slot | 8,997.4 slot-s (27.3 %) | 8,997.4 |
| of which client turnaround | 7,287.3 slot-s | 7,287.3 |
| every slot empty | 1,055.3 s | 1,055.3 |
| turnaround before Solver #1 | 3,023.7 slot-s, 2.67 s mean | 3,023.7, 2.67 |
| before Solver #2-5 / Reviewer / Planner / Perception | 2,166.6 / 681.1 / 858.5 / 557.5 | the same |

**The fit gate on the same clock.** Joining every contact to its own sealed fit receipt
(`prepared/SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-FIT-V1/...`, file times) shows the per-contact fit -- which runs
inside one process-wide `fit_lock` while the row holds its slot -- takes 0.063 s median and keeps that lock
busy 10.5 % of the window, with no two fits overlapping: a real but minor serial cost, not the gap. The
Solver #1 turnaround is spent BEFORE the fit (median 2.0 s), i.e. in the row's own role input.

## 2. The cause, located on the real code

* Rows in flight already exceed the slots: `rails.phase_runner` admits `queue_depth = 4 x slots` = 16 rows
  over 4 slots. But `reproduction.ojw.runner.execute_speech_agent_workflows` pins each admitted row to ONE
  slot from its first contact to its delivery, because the per-slot KV prefix serves 88.9 % of the flown
  prompt tokens; releasing the slot between contacts would re-prefill the row's ~7,500-token supply block
  (about 3.3 s at the measured 2,267 tok/s) to save a ~0.5 s gap. So the slots empty while their OWN row
  prepares the next contact, and parking more rows does not help.
* The largest preparation is the first Solver visit's role input: `settle` -> the train-exemplars recall
  (`rails.kb_policy.multidim_recall`, a pure-Python cosine over every exemplar key vector) -> material,
  run SYNCHRONOUSLY inside the OpenJiuwen role-query component (`reproduction.ojw.native_episode._RoleQuery`)
  on the ONE asyncio event loop every row shares. Measured on the bench: 1.43 s per row for the Solver's role
  input against under 0.02 s for every other role (cProfile: `multidim_recall` is 93 % of it). While one row
  recalls, no other row can route or dispatch -- which is how four independent rows produce correlated
  all-slots-empty time.
* **Lever 1b is possible for the recall and impossible for the rest.** The recall's inputs are the frozen
  snapshot, the row's own sealed speech query record and the key vectors (`rails.phase_supply`
  `supply_for_phase` -> `KbFacetProvider.candidates` -> `multidim_recall`) -- not the Perception answer. The
  rank, the fusion and the candidate-bound slot-contract selection (`knowledge_stores.slot-contracts.
  candidate_supply.solver`, `candidate_state_phase: perception`) DO read the sealed Perception state; they
  stay exactly where they are.

## 3. The key: three switches, scheduling only, default off

`dispatch = {"schema": "saea-dispatch-slot-fill-v1", "recall_prefetch": ..., "role_input_offload": ...,
"gc_freeze": ...}`, parsed strictly (`rails.dispatch_slot_fill`), refused outside the native role episode,
absent in every committed configuration (asserted by `tests/unit/test_dispatch_slot_fill.py`), so every
committed config composes to identical bytes and every pinned flight commit is untouched.

* `recall_prefetch` -- at admission, the row's Perception-independent recall is submitted to ONE background
  worker (`rails.phase_supply` `prefetch_recall`, forwarded by `rails.knowledge_stores`); the Solver visit
  consumes it through the provider's existing prepared-recall path; a revisit recomputes live. Same function,
  same snapshot object, same key-vector lookup, same `k`: the same floats in the same order.
* `role_input_offload` -- the unchanged role-input builder is awaited on ONE dedicated worker thread
  (`_RoleQuery` awaits an awaitable builder); role inputs stay mutually exclusive across rows exactly as on
  the loop, and the calling task's context variables are carried over.
* `gc_freeze` -- `gc.collect(); gc.freeze()` before the first episode, `gc.unfreeze()` after the last.

## 4. Byte identity: proven on the real cell

`scripts/analysis/slotfill_fake_server_harness.py` builds the REAL locked PLAN cell
(`slurp-native-default-plan-lock-v1`) with `core.flight.factory.build_flight_runtime`, mints its own
first-phase supply model-free (item E16), narrows the roster through the production resume seam, and drives
`FlightRuntime._dispatch_phase_program(model_free_check=True)` -- the wire check's own dispatch mode --
through the real `FrozenCoreClient` / `FrozenCoreAdapter` and the real `LlamaServerTransport`, whose POST is
replaced by an in-process four-slot fake llama-server that records every body it receives and answers with
canned schema-valid role responses keyed on (row, contact id), never on arrival order (25 % of rows REVISE).

Nine runs of the first 60 rows (285 contacts each, the resume seam narrowing the roster) share one scratch
run id: two key-off runs and seven key-on runs (all three switches twice, each switch alone, and two pairs).
Against the first key-off run, **every** run is identical on all five digests (`bench/*.json`,
`proof-summary-v1.json`):

* the request body bytes the fake server received, per (row, contact), `id_slot` masked;
* the client payloads, per (row, contact);
* every sealed dispatch row and every canonical output row, per row;
* the multiset of all 1,725 trace records (sorted, so ORDER is free).

Exactly two facts are assigned by ARRIVAL and already differ between two runs of today's dispatcher: the
request-id counter (`flight-<n>`) and the slot number (`id_slot` on the wire, `slot_id` / `slot_ids` in the
sealed waves). The normaliser renames each `flight-<n>` and each request sha256 to its own (row, contact)
identity, masks the slot keys and the runtime-trace digest computed over them (its preimage records are
compared), and drops `latency_seconds`. The key-off run against the second key-off run needs exactly the
same normalisation, which is the proof that nothing else moved. Every first-phase supply the bench minted
over the whole 1,080-row roster, key on and key off (eleven, including two runs a run-cumulative budget
later stopped), records the sealed PLAN preparation's output digest `ba5e1faa...` -- the byte-identity check
a flip makes; the two minted over the sealed pair's 60-row roster agree with each other (`b33fe65b...`)
(`proof-summary-v1.json`, `minted_first_phase_supplies`).

**The seal still verifies.** A second pair (`bench/sealoff.json`, `bench/sealon.json`, its own scratch run id,
the adapter's split truncated to the same 60 rows so the verified split, the minted supply and the manifest
describe one roster) was flown on the committed, CLEAN tree and sealed: canonical outputs written, the
COMPLETED run manifest built by `core.bundle.manifest.build_manifest` and `core.bundle.verify.verify_bundle`
run on it (no scorer). Both VERIFIED, and the two runs are identical on all five digests. Their manifest and
as-written outputs digests differ, as two key-off runs' do: the trace is appended in arrival order and the
trace manifest hashes the file as written, and every output row carries its own request id, so those digests
are attempt facts, not content facts. `verify_bundle` checks each record's bindings, not the file order, and
`core.flight.resume` scans the trace by record id, so a resume is unaffected by the order.

The episode-level unit tests (`tests/unit/test_dispatch_slot_fill.py`, the real OpenJiuwen graph with a
scripted transport) re-prove it at both revision bounds, prove the prefetched recall yields the live
`PhaseSupply` byte for byte on vector and segmented queries, and fly a crash plus a resume-recovery WITH the
key on: the kept row replayed from a key-on trace equals the key-off seal and the re-flown row delivers the
same answer (E10 / I7r semantics unchanged); the collector is handed back unfrozen.

## 5. Throughput, estimated honestly

Service model: each request holds its slot for a deterministic draw from ROLL-2's sealed per-role server busy
times (launch to release) of the same role; the client is the real code. 60 rows, 285 contacts per run:

| run | dispatch | window s | empty share | all-empty s | contacts / h of window |
| --- | --- | ---: | ---: | ---: | ---: |
| off | none | 374.4 | 15.43 % | 0.15 | 2,740.0 |
| off2 | none | 375.6 | 15.69 % | 1.44 | 2,731.5 |
| all | three switches | 349.4 | 9.38 % | 0.17 | 2,936.6 |
| all2 | three switches | 358.6 | 11.71 % | 0.22 | 2,861.0 |
| prefetch | recall_prefetch | 352.5 | 10.12 % | 0.11 | 2,910.9 |
| pfgc | recall_prefetch + gc_freeze | 357.5 | 11.44 % | 0.28 | 2,869.8 |
| pfoff | recall_prefetch + role_input_offload | 364.7 | 13.03 % | 0.71 | 2,813.1 |
| offload | role_input_offload | 367.3 | 13.77 % | 1.26 | 2,793.5 |
| gc | gc_freeze | 371.3 | 14.71 % | 1.20 | 2,763.5 |
| sealoff (sealed pair) | none | 374.0 | 15.30 % | 0.30 | 2,743.4 |
| sealon (sealed pair) | three switches | 352.6 | 10.19 % | 0.21 | 2,910.0 |

With all three switches the empty share falls 15.6 % -> 10.5 % and contacts per hour of window rise
2,736 -> 2,899, **+6.0 %** (the two key-on runs +7.3 % and +4.6 %; the two key-off runs agree within 0.3 %; the sealed pair, flown later on the committed tree, +6.1 %);
per row the key removes 1.40 slot-seconds of empty slot and 0.35 s of wall. The bench attributes the gain to
`recall_prefetch` (+6.4 % alone); `role_input_offload` (+2.1 %) and `gc_freeze` (+1.0 %) are within the
run-to-run spread on the bench and are carried because they are byte-neutral and aim at the flight's
all-slots-empty mass, which the bench does not reproduce.

**The honest bound for a flown cell.** Transferred as the same 0.35 s of wall per row to ROLL-2's flown
7.62 s per row, the key is worth about **+5 %** contacts per GPU-hour. Its ceiling as a mechanism is lever 1b,
**+10.1 %** (the whole 2.67 s Solver #1 gap; the bench removes about half of the 2.8 slot-seconds per row
that gap costs). The flight's 1,055 s of all-slots-empty time (672 stretches, median 0.8 s, spread evenly over
the window) is not reproduced on the bench (under 1.5 s per 60 rows with or without the key), so no number is
claimed for lever 1a before the flight's own read; the note's +37.6 % lever-1 bound (zero empty slot) is not
approached by anything here. Two cautions travel with the number: the bench's client runs on the same host
while a GPU flight and a CPU sidecar are live, and a fuller slot occupancy changes llama.cpp batch
composition, which the no-harm read at the in-chain A/A is registered to measure.

## Files

| file | what it holds |
| --- | --- |
| `gap-decomposition-v1.json` | the reproduced accounting and the fit gate on the server clock |
| `bench/<run>.json` | one proof-bench receipt per run; per-contact digest keys are `sha256(row|contact)[:16]` |
| `proof-summary-v1.json` | the numbers the registration quotes |
| `MANIFEST.sha256` | `<sha256> *<relpath>` over every other file |
