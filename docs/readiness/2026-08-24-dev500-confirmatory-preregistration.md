# DEV-500 confirmatory preregistration — one-touch read at the frozen cell

Date: 2026-08-24. Status: **REGISTERED — prep missions next; flies after packet
materialization + prompt-fit land.** Profile: `bounded-discovery-probe` (dev-tier
confirmatory; no test contact). Authority: the owner ladder (rulings §2.2), the DEV-100
campaign verdict (`2026-08-24-dev100-campaign-verdict.md`), and the reviewer standards
adopted in `2026-08-24-dev100-literature-consistency.md` §4 and
`2026-08-24-dev100-reviewer-audit.md` §6.

## 1. Confirmatory object and statistic (frozen in advance)

- **Surface**: DEV-500 (receipt `docs/receipts/probe-samples/DEV-500.json`, identity
  `c0f1c753…452b`). **The confirmatory statistic is computed ONLY over the 400 UNEXPOSED
  samples** (DEV-500 minus the nested DEV-100); the exposed 100 are scored and reported
  separately, never pooled into the claim.
- **Statistic**: paired per-sample BLEND − M0 over the 400; paired cluster bootstrap
  (N=10,000, seed 20260807) 90% and 95% CIs; McNemar exact test on the discordant pairs.
  **Claim condition (preregistered): the 90% CI excludes zero.** W→C/C→W and per-scenario
  confusion reported alongside, whatever they show.
- **One touch**: all arms fly, seal, then ONE registered read of everything together. No
  knob change, no re-fly, no partial read, regardless of outcome. The DEV-100 round-5
  variance estimate (±2/100 at 8-slot decode) is carried as the registered variance prior.

## 2. Arms (all at the byte-frozen cell `configs/policy/kb-policy-v1-dev100.json`; same
## base binary, same np8 profile, same session where feasible)

| Arm | Construction | Contacts (worst) |
|---|---|---|
| M0 | direct decode, prompt-matched, in-session (removes the cross-build confound) | 400 |
| BLEND | the frozen α-.45 chain, unchanged | ≤800 (expect ~550 at ~62% retain-primary) |
| ABL-RANDRET | random-retrieval control: uniformly random facets/values from the SAME datastore through the SAME fusion path (seeded) | ≤800 |
| ABL-RANDICL | random-exemplar ICL control: k random train exemplars (no retrieval, no gold conditioning) in the evidence slot | ≤800 |

**Oracle-retrieval ceiling — charter-constrained substitution (disclosed):** the literature
standard (RASU's GT-prompt line) requires gold-conditioned supply, which this repository's
immutable charter forbids in runtime ("gold labels must never enter runtime"). The
registered substitute is the analytic **retrieval-reachability ceiling** (gold-facet
recall@k over the 400, computed scoring-side at the read) plus the DEV-100 damage-channel
anatomy; the limitation is stated wherever the ceiling is cited.

## 3. Ceilings (row `SAEA-DEV500-CONFIRMATORY`)

≤ **3,200** frozen-core contacts; ≤ **1,000** tool (embedding) contacts; ≤ **8,000** metered
audio-seconds; ≤ **3.0** GPU-h (GPU-active). One-shot semantics per arm attempt; the
sentinel (1,000 ms/token rolling median), canary (<300 ms/token + byte-compare), GPU
preflight (SmartFanMode==3, ≥95W, clock-lock check), AttemptStore pre-takeoff inspection,
trace-sink isolation, and the two-leg hosting recipe are all mandatory rails.

## 4. Prep prerequisites (each its own registered artifact)

1. DEV-500 runtime-view dataset fragment (canonical-recording rule identical to DEV-100's)
   + ~400 new devel packets via the CPU preprocessing sidecar (own preprocess row) +
   promotion receipt.
2. Composition against the base-binary np8 fragment; session-bound tokenizer prompt-fit
   (all four arms' prompt shapes).
3. Campaign row with the four arms' plans (run-cumulative semantics).

## 5. Scope

Dev-tier confirmatory: a positive read supports "the frozen knowledge-conditioned form
beats direct decode on held-out dev data" and authorizes DEV-1000 + the Audio2Tool surface
per the ladder. It makes NO test claim, NO generalization claim, and NO controller/RL claim.
A negative read falsifies the dev-transfer of the frozen cell and returns the program to
knowledge-construction (the dead-direct set and recall-limited retrieval agenda) without
touching test. Gold opens once, at the single read. FINAL60 and test remain untouched.
