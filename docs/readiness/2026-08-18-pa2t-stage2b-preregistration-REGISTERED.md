# P-A2T Stage-2b follow-up probe — REGISTERED

Date: 2026-08-18. Status: **REGISTERED — flyable once the machinery delta lands** (ticket
dispatched same day; flight after the P-ATTR smoke frees the GPU). Profile:
`bounded-discovery-probe`. Owner GO: same-day approval of the coordinator's two-arm proposal.
Parent: the consumed Stage-2 read (`5269eee`, verdict COPY-TRAP) whose own §"structural
findings" designed these arms. Samples: the SAME 120 headroom ids; seed 20260807 throughout;
**B2 reuses Stage-2's exact per-sample derangement mapping** (same wrong tool per sample, for
direct comparability with S4).

## 1. The two questions (independent; each with its own mechanical verdict — no exclusive
branch lattice, per the P-SLU rule-gap lesson)

**Q-A — corruption-channel localization.** Stage-2's S1' converted 16/120 but injected 34
supplied DEFAULT VALUES. Arm **B1 (nodefaults row)**: the correct tool's registry row with
`argument_defaults` STRIPPED (schema structure + constraints only, no values), ×120,
replacing-form like S1'. Verdicts:
- **CONFIRMED-CUT**: B1 induced-substitutions ≤ 5 AND B1 conversion ≥ 8/120 — the corruption
  channel IS the default values; the clean supply form is "row minus defaults".
- **NOT-DEFAULTS**: B1 induced ≥ 20 — corruption flows from another field; the channel hunt
  continues.
- Otherwise **INCONCLUSIVE-A** (report ingredients).

**Q-B — schema vs knowledge (the question Stage-2's S4 could not test).** Arm **B2
(augmented wrong row)**: the FULL 152-row registry exactly as A0's system prompt, PLUS the
deranged wrong tool's row appended under a "particularly relevant" header, ×120 — correct
tool PRESENT, wrong row highlighted. Verdicts:
- **SCHEMA-CONTRIBUTES**: B2 conversion ≥ 6/120 (= max(2× the established noise floor, 5%))
  — a wrong-content row still converts ⇒ a real format/attention effect exists.
- **KNOWLEDGE-TIED**: B2 conversion ≤ 2/120 AND B2 tool-selection retention ≥ 85% — only the
  right row converts; Stage-2's 16 conversions are knowledge-tied.
- **MISLEAD overlay** (fires independently): B2 retention < 80% (clearly below the measured
  12.5% selection-noise band) — a highlighted wrong row drags selection.
- Otherwise **INCONCLUSIVE-B**.

## 2. Metrics

Same instrument set as Stage-2 (EM conversion on the 120 vs the consumed A0 comparator;
retention; slot micro P/R/F1 via the approved direct primitives; induced-substitution with the
approved bare-key alignment; empty-call and parse-failure rates; per-tier tables mandatory
with small-n flags). No new noise arm: the Stage-2 N0r established a perfectly stable EM
comparator (0/40) and a 12.5% selection-noise band; both are cited, not re-measured.

## 3. Cost (registered ceilings)

240 requests (2×120); ≤280 core calls; ≤2,000 metered audio-seconds; ≤0.5 GPU-h (featcache
fully warm; B1 prompts tiny, B2 prompts registry-sized with prefix-cache reuse — Stage-2
measured 86–115 req/min in exactly these regimes).

## 4. Discipline

One-shot read; pinned read suite (a small extension of `analysis/a2t_s2_read.py` evaluating
the two-question verdicts) built and coordinator-reviewed BEFORE the read; exposure row
`SAEA-PROBE-a2t-s2b-120` appended at registration (consumed=no); all supply content from the
shipped tool registry (legal tier; B2's highlight header is instruction text, not evidence);
NC license carried on audio-derived results.
