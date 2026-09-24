# CELL-3 offline four-row dry run (zero contacts)

Driver `scripts/flights/batch/cell3_dry_run.py`, run 2026-09-24 from worktree
`/home/chao/saea-worktrees/fable-cell3reg` (branch `fable/cell3reg`, base `060d822c`) against the
REAL released `stage3-deltas-v2` and `stage3-deltas-twin-v2` stores and the REAL committed smoke
fragments. **Zero model, tool, network, GPU, gate, transport, client, attempt and serving-session
contacts.** Labels, identifiers and counts only: no utterance text, transcript, gold label,
delivered filler or delta statement text is read into this record.

Both forms exit `ok: true` with **zero defects**.

## What was walked

`cell3_dry_run.py` composes the two REGISTERED smoke cells from their own committed fragments
(`slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1` and its twin) and walks each of the four
DEV-2000-ADDED smoke rows node by node with
`speech_aware_evidence_acquisition.analysis.native_episode_dry_run`; only the four role answers are
canned, exactly as a fake frozen core would answer. The Perception candidate ids are the ones the
**sealed comparator itself produced** on these rows
(`SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1`, attempt
`attempt-slurp-native-default-plan-dev2000-added-generation-v1`), read off its sealed `phases.json`
as intent ids only, projected with the route's own bounded first-occurrence rule at three
candidates.

The driver's gate-table helper is imported from `cell3_gate_dry_run.py` and its canned answers and
delta filter from `cell2_dry_run.py`, rather than restated.

## 1. The traced walk, arm

| row | candidate scenarios | majority | solver | reviewer | planner | delta items S / R / Pl |
| --- | --- | --- | --- | --- | --- | --- |
| `slurp:devel:000017:audio-1501773854-headset` | iot, iot, iot | `iot` | CLOSED | CLOSED | CLOSED | 0 / 0 / 0 |
| `slurp:devel:000024:audio-1490195864-headset` | iot, iot, iot | `iot` | CLOSED | CLOSED | CLOSED | 0 / 0 / 0 |
| `slurp:devel:000099:audio-1501754782` | weather | `weather` | open | open | open | 8 / 4 / 0 |
| `slurp:devel:000217:audio-1490367363` | weather, transport, datetime | `weather` | open | open | open | 8 / 4 / 0 |

Totals: perception 0, solver 16, reviewer 8, planner 0. Gate-closed rows per node: 2 / 2 / 2.

## 2. The traced walk, derangement twin

| row | majority | solver | reviewer | planner | delta items S / R / Pl |
| --- | --- | --- | --- | --- | --- |
| `slurp:devel:000017:audio-1501773854-headset` | `iot` | CLOSED | CLOSED | CLOSED | 0 / 0 / 0 |
| `slurp:devel:000024:audio-1490195864-headset` | `iot` | CLOSED | CLOSED | CLOSED | 0 / 0 / 0 |
| `slurp:devel:000099:audio-1501754782` | `weather` | open | open | open | 8 / 4 / 1 |
| `slurp:devel:000217:audio-1490367363` | `weather` | open | open | open | 8 / 4 / 3 |

Totals: perception 0, solver 16, reviewer 8, planner 4. Gate-closed rows per node: 2 / 2 / 2.

**The gate decisions are identical on both forms**, which is the point: the gate reads the row's own
Perception candidates, not the store, so a derangement of the store cannot move a gate decision.
What the derangement moves is WHICH values the open rows select, and it does — the planner slice
supplies 0 on the arm and 4 across the two open rows on the twin. Version 2's planner slice is four
values over four intents; the weather candidates of these two rows reach none of them on the arm,
and the derangement moves whole attachment tuples so the twin's four planner values land on
different rows. **Reported, never failed**: four rows cannot decide whether a candidate-bound route
is inert, and the 1,000-row arm's own delta-consumption table decides that.

## 3. The two tie walks

Same two candidates on `slurp:devel:000099:audio-1501754782`, in the two orders. One is `weather_query`
(not gated), the other `iot_hue_lighton` (gated), so the two scenarios tie at one candidate each and
the first-listed one must decide.

| walk | candidates | gates | delta items S / R / Pl (arm) |
| --- | --- | --- | --- |
| tie | `weather_query`, `iot_hue_lighton` | all OPEN | 8 / 4 / 0 |
| tie reversed | `iot_hue_lighton`, `weather_query` | all CLOSED | 0 / 0 / 0 |

The two orders disagree, on both forms. That is the first-listed tie-break doing its job.

## 4. Perception

**Zero delta items at Perception on every row and both forms.** CELL-3 removes CELL-2's
unconditional Perception route entirely, so the Perception request is byte-identical to the sealed
comparator's for the same row. That is what makes the model-free projection of the gate's reach over
the whole roster (355 closed / 645 open of 1,000 rows) meaningful, and it is also the first thing
the smoke's structural stage must confirm on the live flight.

## 5. What this proves and what it does not

`ok: true` means: every row walked the whole role graph and delivered from the Solver's sealed
draft; every node whose gate CLOSED supplied nothing at that node; every realised gate decision
equalled the registered one; the gate published exactly one decision per gated route per row (three
per row, twelve over four rows, because the Perception route is removed); and the two tie walks
disagreed.

It says **nothing** about whether gating helps. That is a flight.

Byte-identity of an OPEN gate against the ungated route is not re-proved here — it is the unit test
`tests/unit/test_stage3_scenario_gate.py::test_an_open_gate_is_byte_identical_to_the_ungated_route`,
which pins the selected ids, the `RankResult` hash, the `FusionDecision` hash and the
`action_target_ref`.
