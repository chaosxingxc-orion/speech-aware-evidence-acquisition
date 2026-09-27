# Cell SLOTFILL: the dispatcher keeps every serving slot loaded

Registered before contact 2026-09-27 at study commit `583f04c99fc9b5bc8f2179761e210d6439c0a6fe` (owner decision 159, a
row-127 engineering-base no-harm item; throughput first-class under decision 140); all three cells **held**.
Nothing here authorises a flight, a flip or an admission entry.

**The gap.** [`docs/results/2026-09-27-slurp-throughput-baseline-and-levers.md`](../../results/2026-09-27-slurp-throughput-baseline-and-levers.md): 27.3 % of ROLL-2's slot capacity
(8,997 of 32,909 slot-seconds) sat empty while the client prepared the next contact; 1,055 s with every slot empty;
2.67 s before every first Solver contact. Reproduced exactly on the sealed ROLL-2 trace and the ROLL-2 lifetime of the
session's server log ([`docs/checks/speech-aware-evidence-acquisition/2026-09-27-dispatch-slot-fill-byte-identity-v1/README.md`](../../../docs/checks/speech-aware-evidence-acquisition/2026-09-27-dispatch-slot-fill-byte-identity-v1/README.md)).

**The cause, located.** The first Solver visit's role input runs the train-exemplars recall -- a pure-Python cosine
over every exemplar key vector, a function of the row's own sealed speech query alone -- synchronously on the ONE event
loop every row shares (measured 1.4332 s per row offline), and full
garbage collections over the loaded key vectors freeze every thread; rows-in-flight already exceed the slots
(queue depth 16 over 4 slots), but each row is pinned to its slot for its KV prefix (88.9 % of prompt tokens are served
from it), so releasing slots between contacts would cost more prefill than it saves.

**The mechanism: one key, three switches, scheduling only.** `dispatch` = `{"gc_freeze": true, "recall_prefetch": true, "role_input_offload": true, "schema": "saea-dispatch-slot-fill-v1"}`
(`rails.dispatch_slot_fill`): the recall is computed ahead while the row's Perception contact is in flight (lever 1b --
the candidate-bound slot-contract selection DOES depend on Perception and stays where it is); the role-input builder
runs on one dedicated worker instead of the shared loop (lever 1a); the loaded heap is frozen out of the collector.
Absent -- every committed configuration -- the dispatch is byte-for-byte what it was.

**Proven byte-identical.** On the REAL locked PLAN cell through the REAL flight dispatch against a recording fake
server (60 rows, 285 contacts per run, three runs OFF/ON/OFF): every request body the server
received, every client payload, every sealed row, every canonical output row and the multiset of trace records are
identical ON vs OFF and OFF vs OFF, once the two facts today's dispatcher already assigns by arrival -- the request-id
counter and the slot number -- are named by content. The minted first-phase supplies agree on their output bytes.
Crash plus resume-recovery with the key on keeps E10/I7r semantics (`tests/unit/test_dispatch_slot_fill.py`).

**Throughput, estimated honestly.** On the proof bench (the locked PLAN cell, 60 rows, 285 contacts per run, each request holding its slot for a draw from ROLL-2's own per-role server busy times) the key moved the empty-slot share 15.6 % -> 10.5 % and contacts per hour of contact window 2,736 -> 2,899 (+6.0 %; the two key-on runs +7.3 % and +4.6 %, the two key-off runs within 0.3 %; the sealed pair +6.1 %), removing 1.40 slot-seconds of empty slot and 0.35 s of wall per row; recall_prefetch alone +6.4 %, role_input_offload alone +2.1 %, gc_freeze alone +1.0 %.

**One key, proven.** Arm and smoke: `dispatch` added; the composed-config diff against the locked PLAN cells
(`registered-facts-v1.json`) is that key plus bookkeeping only. The in-chain A/A is the locked form WITHOUT the key.
`tests/unit/test_slotfill_config.py` re-proves it.

**Three cells, one chain.** `configs/campaign/slurp-native-stage3-slotfill-fold-a-v1.json` carries the A/A and the
arm (instrument rule 4); the four-row smoke is outside the plan and never scored.

**`stage3_measurement`.** The arm declares `admission` **`no-harm`**, `harm_margin_pp` **1.2485**, by metric intent
**0.9943** / SLU **1.2485**, `claims_benefit` false, `expected_effect_pp` 0.0, `measurement_design`
`cross-flight-with-in-chain-replicate`, `replicate_run_id` `SAEA-SLURP-STAGE3-SLOTFILL-AA-FOLD-A-V1`, primary metric intent accuracy, and a
`throughput_ceiling` block naming the contacts-per-GPU-hour read. `stage3_algorithm`: `none`.

| file | what it holds |
| --- | --- |
| `../2026-09-27-slurp-stage3-slotfill-fold-a-v1-preregistration.md` | the preregistration proper, including the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact, the one-key diffs, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, budgets, the no-harm rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's two plans |
| `aa-generation-plan-registered-v1.json` / `aa-fit-plan-registered-v1.json` | the in-chain A/A's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the four-row smoke's plans |
| `analysis-recipe-v1.json` | the paired no-harm read and the throughput read |
| `root-admission-draft-v1.json` | the decision receipt root mints with `scripts/flights/slotfill/slotfill_mint_receipt.py` |

**Budgets (the locked family's).** Arm and A/A each: 11,880 generation contacts,
47,520 FIT endpoints, 6,480 native task-contract calls,
33,930 repeated speech seconds, 12.0 GPU hours, one
official complete score. Smoke: 44 / 176 /
24 / 117 /
1.0, never scored.

**No committed `prepared_phase_supply`.** The flip mints each cell's own (item E16); `--allow-output-change` must never
be passed; every minted supply must carry the sealed PLAN output digest `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`.

**Mint, flip, queue.** Root countersigns the seven DRAFT exposure rows (six flight rows and `SAEA-SLURP-SLOTFILL-MODEL-FREE-PROOF-V1`),
mints `coordination/slurp-stage3-slotfill-fold-a-v1/root-admission-v1.json` (id `slurp-stage3-slotfill-fold-a-admission-v1`, six eligible run ids) with
`scripts/flights/slotfill/slotfill_mint_receipt.py`, flips with `scripts/flights/slotfill/slotfill_flip.sh` (the
generic re-pin loop over the three per-cell scripts), then queues `scripts/flights/slotfill/batch_chain_slotfill.sh`
behind whatever occupies the np4 session (decision 77).

**Not authorised by this package.** No flight before the receipt is minted and the cells are flipped; no contact by
this registration; no re-flying of the comparator; no test-split, Fold B or DEV read; no second factor; no re-pin of
the committed configs; no report of a quality gain; no admission entry.
