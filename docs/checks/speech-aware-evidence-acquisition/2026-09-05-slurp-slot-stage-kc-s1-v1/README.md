# SLURP slot stage, cells KC-S1a and KC-S1b (2026-09-05)

Verdict: `docs/readiness/2026-09-05-slurp-slot-stage-kc-s1-v1-verdict.md`.
Preregistration: `docs/readiness/2026-09-05-slurp-use2-slot-stage-v1-preregistration.md`.
Exposure rows: `SAEA-SLURP-KC-S1-PROMPT-FIT-V1`, `SAEA-SLURP-KC-S1-SMOKE-4-V1`,
`SAEA-SLURP-KC-S1A-SLOTS-DEV1000-V1`, `SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1`.

**KC-S1b ADMITTED**: SLU-F1 44.35 against the sealed closed-list direct baseline's 35.80, paired
+10.11 pp per-sample slot F1 on the unexposed NEW500 (CI90 [+8.11, +12.19]) and +10.02 pp over the
equal-contact control KC-S1a (CI90 [+8.01, +12.10]), with intent identical by construction on every
row. **KC-S1a null**: the extra contact alone is worth +0.09 pp (CI90 [−0.20, +0.38]).

## What each cell sent

Both cells add ONE contact per DEV-1000 row to the sealed closed-list direct baseline. The system
message is that baseline's, byte for byte (7,583 chars, sha256 `4073f79e…37db`). The added CONTROL
turn (`configs/probes/slurp_phase_slots.txt`) asks for the entity list alone, and the sealed
closed-list response for that row is appended under the fixed `Prior phase response` framing
(`predecessor_binding: sealed-manifest` over run manifest `f908ff4c…c94c`). KC-S1b appends ONE more
thing after that: the per-intent TRAIN slot schema block of the intent that sealed response names
(`state_fill: slurp-intent-slot-schema-for-state`). Every KC-S1b instruction is therefore the KC-S1a
instruction plus a per-sample suffix, asserted on all 1,000 rows before takeoff.

## Scoring

The real, unmodified official `evaluate.py` at pinned commit
`8eb16545762be97ace75334109d73824217311f1` in `~/.venvs/slurp-official-eval` (used, never modified),
`--average micro --errors --table-layout csv`, reached through the registered `slurp-slu-official`
scorer, which also runs this study's per-sample port and asserts numeric identity. **All five scored
sets passed the identity check at an absolute difference of 0.0.**

Each arm is scored twice, over complete 1,000-row files, never sharded:

* **as sealed** — the arm's own outputs rows, whose `text` is `{"entities": [...]}`. The official
  script computes `entities`, both distance blocks and SLU-F1 from the entity lists alone, so the
  primary metric has **no projection in its path**; these are the numbers `core.scoring_batch`
  produced from each sealed manifest, one job each. The scenario/action/intent columns of this view
  are meaningless by construction and are never reported.
* **joined** — a model-free projection that copies `scenario`/`action` from the sealed closed-list
  row for the same `sample_id` and takes `entities` from the arm's sealed row. Source and projection
  sha256 are in `read.json`; intent identity against the closed-list arm is asserted row by row, and
  the joined view's entity columns are asserted equal to the as-sealed view's. Same device as the
  2026-09-04 alignment audit.

## Files

- `prompt-fit.json` — schema `saea-slurp-kc-s1-prompt-fit-v1`: all 2,000 real envelopes (1,000 rows
  x 2 cells) tokenized through the resident server's own `/apply-template` + `/tokenize`, zero
  generated tokens; the per-cell token distributions, the worst envelope and its margin, the
  pure-suffix assertion, which intent block each row got, and the 42 full-schema fallback rows by id.
  Produced by `scripts/slurp_kc_s1_prompt_fit.py`.
- `wire-check-kc-s1a.json`, `wire-check-kc-s1b.json` — contact-free wire checks (fake gate, fake
  transport, zero sockets) on the 4-row smoke fragment; both `seal_and_score: OK`.
- `smoke-receipt-kc-s1a.json`, `smoke-receipt-kc-s1b.json` — the 4-row end-to-end smokes.
- `flight-receipt-kc-s1a.json`, `flight-receipt-kc-s1b.json` — the registered 1,000-row flights.
- `read.json` — schema `saea-slurp-kc-s1-slot-stage-read-v1`: the single registered read. Official
  blocks for all five scored sets, per-sample paired contrasts with per-stratum tables, both
  weightings, the per-entity-type table, entity supply, N-predicted, join statistics and the
  fallback rows.
- `read.py` — the exact script that produced it (`scripts/slurp_kc_s1_read.py`).
- `result-summary.json` — schema `saea-slurp-kc-s1-result-summary-v1`: the machine-readable verdict.
- `MANIFEST.sha256` — SHA-256 of every file in this directory.

## Boundaries

Devel only; the held-out test split is never named, loaded or scored. Gold never enters a flight
process — the roster is built label-free from the frozen runtime view and the adapter's `gold()`
refuses outright; gold opens once, scoring-side, after both seals. Rung 1 of the claim ladder: no
superiority claim, no generalization claim, no Stage-3 activity.
