# Directional exploration plan for W-A…W-D (owner directive, 2026-08-09)

**Stage framing (owner, this session): this is DIRECTIONAL EXPLORATION, not a
large-scale comparison campaign.** Every probe below is sized to answer
"does this move the needle at all, and roughly how much?" — not to estimate an
effect precisely. Probes are 30–60 items, minutes to ~1 h each; precise
estimation is deferred to whichever directions survive. A probe that returns a
clear null is a success: it removes a direction cheaply.

**Multi-carrier by default.** The programme is not an Earnings-21/22 study;
those two were simply the first carriers plumbed. Short-utterance carriers are
*cheaper* than earnings calls (one request per utterance vs ~61 slices per
call), so breadth costs less than depth here.

---

## 1. Carrier readiness (measured 2026-08-09)

The gate admits a carrier only if its umbrella-lock `profiles` intersect
`{speech-aware-core, speech-aware-secondary, speech-aware-diagnostics,
speech-aware-small-public}`, a loader is registered in `core/carriers.py`, and
(for media identity) D1 has per-sample entries.

| carrier | lock profile | loader | D1 | ready? | unlock cost |
|---|---|---|---|---|---|
| earnings21-original | core | ✅ | ✅ | **READY** | — |
| earnings22-original | core | ✅ | ✅ | **READY** | — |
| conec (evidence layer) | core | n/a | ✅ | **READY** | — |
| slue-sqa-5 | secondary | ✖ | ✖ | gate-OK | loader + D1 |
| ami-meeting-corpus | secondary | ✖ | ✖ | gate-OK | loader + D1 |
| audio2tool | local-candidates | ✅ (P1) | ✖ | **blocked** | lock profile + D1 |
| voiceagentbench | local-candidates | ✖ | ✖ | blocked | lock profile + loader + D1 |
| full-duplex-bench-v3 | local-candidates | ✖ | ✖ | blocked | lock profile + loader + D1 (license unstated) |
| slurp / speech-massive / minds14 | (none) | ✖ | ✖ | blocked | lock profile + loader + D1 |
| spoken-squad / heysquad | (none) | ✖ | ✖ | blocked | lock profile + loader + D1 |
| big-bench-audio / voicebench / uro-bench / voiceassistant-eval | (none) | ✖ | ✖ | blocked | lock profile + loader + D1 |

**Owner decisions required to widen the surface** (each is a data-identity
change, same formal path as the 2026-08-09 Q4 model amendment): assign
`speech-aware-*` profiles to the carriers we intend to probe. Recommended
first batch, chosen to unlock the most distinct mechanisms per unit of work:
**slurp** (structured output + short utterances), **spoken-squad** (retrieval/
SUPPLY-sensitive QA), **audio2tool** (tool calling; loader already exists),
**big-bench-audio** (cascade-vs-direct, deterministic scoring).

---

## 2. Probe catalogue

Cost model from measurement: **13.0 s per 60 s slice request**; a short
utterance (2.9–9 s) is ONE request and generates far fewer tokens, so ≈4–6 s.
"Cost" below is wall-clock for the whole probe at `-np 4`.

### W-A · agent-system construction

| id | probe | carrier(s) | design (sampled) | success signal | cost |
|---|---|---|---|---|---|
| A-1a | boundary policy: model-guided vs fixed-window (degenerate config) | e21 | 10 calls × 2 arms | WER delta ≥1 pp either way; boundary-tier histogram | ~4.5 h |
| A-2a | buffer geometry: 30 s vs 60 s vs 90 s | e21 | 6 calls × 3 arms | WER vs slices/call (cost-quality curve) | ~4 h |
| A-3a | VAD trim on/off; loudness norm on/off | e21 | 6 calls × 2 arms (trim), reuse for norm | WER delta; trimmed-seconds | ~2.5 h |
| A-4a | **pass structure: direct vs self-cascade** | **big-bench-audio** (deterministic answers, 19 s clips) | 60 items × 2 arms | accuracy delta; precedent says +26 pp | **~25 min** |
| A-4b | same contrast on a second task shape | slurp (intent) | 60 items × 2 arms | accuracy delta | ~20 min |
| A-5a | determinism/resumability | any | re-run 1 call twice | byte-identical traces | ~15 min |
| A-6a | serving config (np/mmproj/KV) | e21 | ops benchmark, no study claim | s/req, VRAM drift | in flight |

### W-B · knowledge construction

| id | probe | carrier(s) | design | success signal | cost |
|---|---|---|---|---|---|
| B-1a | external context block (**running now**: R4) | e21+conec | 10 calls × 3 arms | WER(matched) < WER(none) and < WER(mismatched) | ~6.5 h |
| B-2a | **bias lists at prompt level — REDESIGNED 2026-08-09, see the leakage note below** | e21 | 6 calls × 3 arms (none / ConEC-derived / distractor-only) | entity-class WER; ConEC-derived should beat distractor-only | ~2.5 h |
| B-3a | phonetic confusable sets derived from the entity list | e21 | 6 calls × 2 arms | entity-class WER delta | ~2 h |
| B-4a | self-generated rolling glossary (no external source) | e21 | 6 calls × 2 arms | WER delta vs no-carry; glossary growth | ~2 h |
| B-6a | **indexed KB + local generative embedding** retrieval | spoken-squad | 60 questions × 2 arms (closed-book vs retrieved) | EM/F1 delta | ~25 min |
| B-7a | state compression: deterministic extract vs model summary | e21 | 4 calls × 2 arms | WER vs state size | ~1.5 h |

### W-C · knowledge consumption

| id | probe | carrier(s) | design | success signal | cost |
|---|---|---|---|---|---|
| C-1a | injection form: whole block vs top-k retrieved | e21 | 6 calls × 2 arms | WER per evidence token | ~2.5 h |
| C-2a | injection timing: every slice vs first slice only | e21 | 6 calls × 2 arms | WER delta; prefix-cache hit rate | ~2.5 h |
| C-3a | **dose ladder** (none → k=1 → k=5 → whole) | e21 | 6 calls × 4 arms | monotonicity in dose | ~5 h |
| C-4a | retrieval query source: audio-derived vs transcript-derived | slue-sqa-5 | 60 items × 2 arms | retrieval acc → task metric | ~30 min |
| C-5a | **correction strategy head-to-head: before (biasing) vs after (post-hoc)** — never published | e21 | 6 calls × 3 arms | entity-class WER by strategy | ~4 h |
| C-6a | negative controls (rotation, distractors) | e21 | folded into B-1a / B-2a | gains are content-driven | — |

### W-D · system optimization

| id | probe | carrier(s) | design | success signal | cost |
|---|---|---|---|---|---|
| D-1a | **behavioural quality signals** vs error | existing E-001 + R4 traces | offline analysis, **zero model touches** | rank correlation; a usable trigger threshold | **~0** |
| D-1b | signal validation across regimes | whole-call (collapsed) vs segmented records | offline | signal separates the two regimes | ~0 |
| D-2a | selective re-observation (denoise → re-ask) | e21 (noisiest slices by D-1) | trigger on worst 15 % of slices | WER change on triggered slices only | ~1.5 h |
| D-3a | condition-aware routing direct↔cascade | big-bench-audio + fdb-v3-style | 60 items, routed vs fixed policy | accuracy vs best fixed policy | ~40 min |
| D-4a | cost-aware evidence policy | e21 | 6 calls × 2 arms | metric per evidence token | ~2.5 h |
| D-5a | sampled n-best / self-consistency | slurp or heysquad | 60 items × (1,3,5) samples | metric vs cost multiplier | ~45 min |

### Cross-cutting exploration (the "one core, many tasks" claim)

| id | probe | carriers | design | cost |
|---|---|---|---|---|
| X-1 | **multi-task sweep of the unchanged agent** | slurp, spoken-squad, audio2tool, big-bench-audio | 60 items each, one arm each | ~1.5 h total |
| X-2 | cross-lingual evidence sensitivity | speech-massive or minds14 | 60 items × 2 arms (none/evidence) in 2 locales | ~40 min |

---

## 3. Execution waves

**Wave 0 (now, zero model touches, zero blockers)** — D-1a, D-1b: mine the
existing traces for behavioural quality signals. Also finish R4 (B-1a).

**Wave 1 (ready carriers only, no owner action needed)** — A-1a/A-2a/A-3a on
e21, B-2a (bias lists already on disk), C-5a. These are the mechanisms with
the strongest published precedent on a carrier we can already touch.

**Wave 2 (needs the recommended lock-profile batch)** — A-4a (big-bench-audio,
25 min for the strongest single contrast in the whole survey), B-6a and C-4a
(spoken-squad / slue-sqa-5), X-1 multi-task sweep, X-2 cross-lingual.

**Wave 3 (depends on Wave-1/2 outcomes)** — D-2a…D-5a, B-3a/B-4a, C-1a…C-3a,
and precise re-runs of whichever Wave-1/2 probes showed a direction worth
pinning down.

Ordering rule: within a wave, run the cheapest probe with the strongest
precedent first; drop any direction whose probe returns a clear null and say
so in the record.

## 3b. Leakage note on the E-21 bias lists (caught 2026-08-09, before any run)

The E-21 release ships `bias_lists/oracle_list.txt` (1,013 entries) and
`bias_lists/distractor_list.txt` (1,782 = oracle + 769 Fortune-500/CEO names
absent from the corpus). Its README states plainly: **`oracle_list.txt`
contains words and phrases found in the Earnings-21 reference transcripts.**

That makes the oracle list a **reference-derived artefact**, and this study's
contract forbids gold / reference transcripts / test annotations from entering
runtime. Injecting it into a prompt would be feeding part of the answer to the
system being measured: the WER would improve and the improvement would be
meaningless. The distractor list is a superset of the oracle list and inherits
the same problem.

This is precisely the line that separates our R4 evidence from leakage: the
ConEC materials are **pre-existing real-world context** (slides, press
releases, participant rosters) that existed before the call, not a distillation
of its transcript.

**Redesigned B-2a arms:**

| arm | source | admissible in runtime? |
|---|---|---|
| none | — | baseline |
| **ConEC-derived bias list** | entities extracted from the call's own ConEC materials (participants, slides) | ✅ deployable, non-gold |
| **distractor-only list** | the 769 Fortune-500/CEO names *absent* from E-21 | ✅ negative control: does irrelevant biasing hurt? |
| ~~oracle list~~ | reference-derived | ❌ runtime-forbidden; usable **only scorer-side** as an unreachable upper bound |

Reporting the oracle bound scorer-side is worth doing on its own terms: the gap
between it and the ConEC-derived list quantifies the distance between *ideal*
context and *actually obtainable* context — a number the published contextual-
ASR literature (which uses the oracle list as its context) does not report.

## 4. Discipline for every probe

Unchanged from the study's rails: pre-register the exposure row and the
success signal before the run; one element per arm; same substrate across the
arms of one contrast (re-run the A0 baseline when W-A changes it); sampled
identities frozen through the sample-once manifest; nulls reported, not
dropped. Because these are directional probes, each record must state
explicitly: **"exploratory, n=…, not powered for a precise estimate"**.
