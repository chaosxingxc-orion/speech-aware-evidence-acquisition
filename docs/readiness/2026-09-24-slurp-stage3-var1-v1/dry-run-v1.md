# VAR-1: the offline seven-form dry run

Driver: `scripts/flights/batch/var1_dry_run.py`. Receipt:
`$SPEECHRL_DATA_DIR`-free — the driver writes its machine-readable record to
`/home/chao/var1-dry-run.json`, outside the repository, and this note is the committed record.

**Contacts: zero.** `{"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "network": 0}`. No GPU,
no gate, no transport, no client, no attempt, no serving session. Every one of the seven REGISTERED
VAR-1 forms is composed from its OWN committed fragments over the REAL released stores and walked
node by node by `speech_aware_evidence_acquisition.analysis.native_episode_dry_run`; only the four
role answers are canned, exactly as a fake frozen core would answer.

Population: the four rows of the registered smoke — the first four rows of
SLURP-STAGE3-CONSTRUCTION-R01C in the roster's own order (`slurp:train:000049:audio-1434542455`,
`slurp:train:000051:audio-1434531302-headset`, `slurp:train:000234:audio-1499688528`,
`slurp:train:000260:audio-1488549919`; strata datetime, takeaway, alarm, audio).

Canned Perception answer: the first `max_candidates` ids of the phase's OWN legal intent enum, read
off the resolved response format — `alarm_query, alarm_remove, alarm_set` at a bound of three, plus
`audio_volume_down, audio_volume_mute` at a bound of five. Labels only; no utterance, transcript or
gold is read or printed anywhere.

## Result: ALL SEVEN FORMS PASS, zero defects

Per form, three walks: the ACCEPT path on all four rows, a REVISE verdict on row 1 (which revisits
Solver, Reviewer and Planner — seven nodes in all), and a duplicate-candidate Perception answer on
row 1. On every form: every row walked `perception → solver → reviewer → planner` and delivered;
every REVISE revisit acquired **0** items it already held; every duplicate-candidate row walked
instead of raising.

## What each knob actually moved

Supplied ITEMS per row (the four rows are identical unless stated):

| form | intent cards @ Perception | exemplars @ Solver | slot-contract values @ Solver |
| --- | ---: | ---: | ---: |
| VAR1-PLAN | 8 | 20 | 11 |
| VAR1-PLANR | 8 | 20 | 11 |
| VAR1-EX-K10 | 8 | **10** | 11 |
| VAR1-EX-K30 | 8 | **30** | 11 |
| VAR1-EX-DIV | 8 | **7 / 15 / 8 / 16** (mean 11.5) | 11 |
| VAR1-PER-K16C5 | **16** | 20 | **12** |
| smoke (PER-K16C5 form, 4 rows) | **16** | 20 | **12** |

Three readings worth registering before contact:

1. **The `k` knobs are exact.** `saea-fuse-supplyfilter-v1` is *k in, k out* on this store, because
   every exemplar value associates with exactly one content facet. 10 and 30 are delivered on every
   row, with no reshaping.
2. **`VAR1-EX-DIV` is data-dependent, and by a lot.** Capping `fuse_coverage.c` at four exemplars
   per intent target leaves **7, 15, 8 and 16** of the twenty on these four rows — a 65 % cut on the
   most intent-concentrated row and a 20 % cut on the least. That is the variant behaving exactly as
   its design says it should, and it is why its realised per-row supply distribution is a registered
   deliverable of the read rather than an assumption. It is also a caveat: EX-DIV changes the
   demonstration **count** as well as its diversity, so its contrast is not a pure diversity
   contrast and the read must say so beside EX-K10, which is the count-only control at a comparable
   mean.
3. **The candidate bound is nearly free at the Solver.** Five candidates instead of three moved the
   slot-contract block from 11 values to 12, not from 11 to 18: `max_total_values` 28 and
   `max_values_per_candidate` 16 are unmoved, so the round robin spreads the same budget. The
   Perception block is where PER-K16C5 spends: 8 cards to 16.

## Supplied content characters, and what they say about prompt fit

The knowledge a store decides for a node does **not** travel in the rendered instruction: it reaches
the node as typed content blocks through the acquire transition. Every VAR-1 form's rendered
instruction is byte-for-byte the same size — Perception 960, Solver 1,129, Reviewer 435, Planner 193
characters. So the quantity that moves is measured directly, by summing `len(content)` over the
released snapshots for the value ids each walk selected:

| form | Perception supplied chars/row (mean / max) | Solver supplied chars/row (mean / max) |
| --- | ---: | ---: |
| VAR1-PLAN | 5,596.0 / 5,862 | 26,551.2 / 27,394 |
| VAR1-PLANR | 5,596.0 / 5,862 | 26,551.2 / 27,394 |
| VAR1-EX-K10 | 5,596.0 / 5,862 | 25,726.5 / 26,186 |
| VAR1-EX-K30 | 5,596.0 / 5,862 | 27,393.5 / 28,728 |
| VAR1-EX-DIV | 5,596.0 / 5,862 | 25,825.2 / 26,256 |
| VAR1-PER-K16C5 | **11,154.8 / 11,570** | 28,156.2 / 28,999 |

Widest-case differences against VAR1-PLAN, and their conservative token bound at 2.5 characters per
token (Qwen's BPE runs about 3.5–4.0 on English prose, so 2.5 over-states the cost):

* `VAR1-EX-K30` Solver: **+1,334 chars ⇒ at most 534 tokens**. CELL-2's *measured* Solver bound on
  TRAIN Fold A was 21,821 required-window tokens **with** a `stage3-deltas` block VAR-1 does not
  carry, so the upper reference is at most **22,355** against the 24,576-token slot.
* `VAR1-PER-K16C5` Perception: **+5,708 chars ⇒ at most 2,284 tokens**, against CELL-2's measured
  19,992, for at most **22,276**.
* `VAR1-PER-K16C5` Solver: **+1,605 chars ⇒ at most 642 tokens**, for at most **22,463**.
* `VAR1-EX-K10` and `VAR1-EX-DIV` only shrink the Solver block.

**REFUSE is arithmetically excluded on every phase of every cell; `COMPACT_REQUIRED` is the
expectation** and is recorded and proceeded on under `context_fit_policy: compact-or-abstain`. The
authoritative measurement is still `core.flight.cli check` in the coordinator's clean-tree cycle,
and the fail-closed fallback (k = 26 for EX-K30, k = 12 for PER-K16C5, each with new run, generation
and fit identities) is registered in the preregistration, section 5.

## The first-phase seed

Every form reported `first_phase_seed_source: "router-bootstrap (no pinned artifact)"` — the
cell-P0 form. No committed baseline carries a `prepared_phase_supply` key; the re-pin mints each
cell's own at flip time from the very function this walk fell back on
(`rails.knowledge_stores`'s `bootstrap_first_phase`), so the flight's seed and this walk's seed are
the same computation over the same bytes.

## What this proves and what it does not

It proves that all seven registered compositions **build**, that the stores bind, that the routes
resolve, that every node boundary resolves its supply on a context carrying the previous node's
sealed state, that the widened five-candidate contract renders and projects, that a REVISE revisit
acquires nothing twice, and that a duplicate-candidate Perception answer walks rather than raising
(the CELL-1 lesson).

It proves nothing about effectiveness, and it cannot: the role answers are canned. Four rows also
cannot decide whether a route is inert — the Reviewer and Planner supply zero items on every form
here because no VAR-1 cell declares a route at those nodes at all, which is the locked plan's own
shape and not a finding.
