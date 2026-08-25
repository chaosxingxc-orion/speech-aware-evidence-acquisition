# DEV-1000 baseline-lock preregistration — the ladder's terminal dev tier

Date: 2026-08-24. Status: **REGISTERED — flies only after (a) the packet prep completes and
(b) the queued dev-iteration experiments (K-WIDEN, E-A, E-C, E-B) either produce a winner
cell or are declared closed.** Profile: `bounded-discovery-probe` (dev-tier; no test
contact). Authority: the owner ladder (100 → ~500 → 1000+ → lock), the DEV-500 confirmatory
verdict §4.1 gate, and the reviewer standards adopted in the literature-consistency memo §4.

## 1. Purpose and the lock decision

This tier answers the ladder's terminal dev question: **does the (possibly improved) frozen
cell hold its held-out margin at 1,000-sample scale, and may it be LOCKED as the
large-scale-experiment baseline version?** A positive read locks the baseline; a negative
or materially shrunken read returns the program to knowledge construction without touching
test.

## 2. Surface and statistic (frozen in advance)

- **Split**: DEV-1000 (receipt `docs/receipts/probe-samples/DEV-1000.json`, identity
  `e9a7b7fe…d853` load-split / `9fb44e33…243b` receipt-integrity; runtime view
  `configs/dataset/slurp-speech-native-dev1000.json`, view sha `e148dbbc…0e87`).
- **The lock statistic is computed ONLY over the 500 samples UNEXPOSED at this tier**
  (DEV-1000 minus DEV-500 — the `DEV-1000-NEW500` receipt, `1feefb8c…234a`). The 500
  previously-exposed samples are scored and reported separately, never pooled into the lock
  claim (the DEV-500 nesting precedent).
- **Statistic**: paired per-sample BLEND − M0 over the unexposed 500; paired cluster
  bootstrap (N=10,000, seed 20260807) 90% and 95% CIs; McNemar exact. **Lock condition
  (preregistered): the 90% CI lower bound ≥ +10 pp** — i.e. not merely "excludes zero" but
  retains the bulk of the DEV-500 margin (+19.75 pp, CI [+16.5, +23.0]) at double scale.
  A CI that excludes zero but falls below +10 is recorded as CONFIRMED-BUT-SHRUNKEN and
  does NOT lock; it returns to iteration.
- **One touch**: all arms fly, seal, then ONE registered read. No knob change, no re-fly, no
  partial read, whatever the outcome.

## 3. Arms

| Arm | Construction | Contacts (worst) |
|---|---|---|
| M0 | prompt-matched direct decode, in-session | 1,000 |
| BLEND | the locked candidate cell (v1 frozen `kb-policy-v1-dev100.json`, or the winner of the queued dev-iteration rounds — pinned by hash at registration of the flight row) | ≤2,000 (expect ~1,350 at ~65% retain-primary) |

Ablations are NOT re-run at this tier: the DEV-500 confirmatory established attribution
(random-retrieval +4.0, random-exemplar −5.5) on an unexposed 400 with the same form; the
lock tier tests scale-stability of the established effect. The reachability ceiling is
recomputed scoring-side over the unexposed 500 as the standing charter substitute for a
gold-conditioned oracle arm (disclosed wherever cited).

## 4. Ceilings (row `SAEA-DEV1000-BASELINE-LOCK`)

≤ **3,400** frozen-core contacts; ≤ **1,200** tool contacts; ≤ **9,000** metered
audio-seconds; ≤ **3.0** GPU-h (GPU-active). Run-cumulative plan semantics; per-arm attempt
meters; the six standard rails mandatory (GPU preflight incl. SmartFanMode/power/clock-lock,
AttemptStore+ledger+service-log pre-takeoff inspection, canary <300 ms/token with
byte-compare, decode-rate sentinel, trace-sink isolation, two-leg hosting).

## 5. What a lock authorizes and forbids

A LOCK records the cell as **the baseline version for large-scale experiments**: its config
hash, KB snapshot hash, code commits, serving profile, and measured dev profile become the
reference point every later comparison cites. It authorizes the Audio2Tool generality
campaign to run against the same locked form, and it makes the training-free RL work
meaningful (a fixed environment to optimize a controller against). It does NOT authorize
test contact, a superiority claim, a generalization claim, or any Stage-3 activity — those
remain owner decisions under `OWNER_GO_AND_PAPER_EXECUTION_CONTRACT`.

## 6. Prep status

Runtime view and NEW500 derivation landed (`eaa35f97`, `9814e186`); the preprocess row
`SAEA-SN-DEV1000-PREPROCESS` is registered (`e7b0117e`) with 500 packets pending
materialization (1,462.712 audio-s, CPU sidecar). Prompt-fit for the lock arms is taken
session-bound at flight registration, as always.
