# W-A/W-B/W-C/W-D validation plan — items, carriers, waves, and what binds them (2026-08-11)

Owner directive: turn the 2026-08-09 exploration plan (~4 dimensions, ~24 probe
items) into a detailed validation plan, explicitly multi-carrier — "the
programme is not an Earnings-21/22 study". This document is that plan. It
carries the current status of every item (several are already answered or
dead), the measured constraints that bind the rest, the carrier unlock matrix,
and a wave schedule with pre-stated decision rules. Companion docs:
`2026-08-09-exploration-plan.md` (the item definitions),
`2026-08-11-segmentation-efficiency-frontier.md` (S0–S5/P0–P5),
`2026-08-10-serving-config-verdict.md` (locked config A).

## 0. Facts that bind the plan (all measured in this study)

1. **Run-to-run noise floor** (P0, three same-config runs): ±3.2 pp on a
   3-sample mean WER, per-sample range up to 13.6 pp, orderings inverting.
   Any long-audio WER item whose expected effect is smaller is unreadable as
   a single run at small n. Treatments: n=10+, repeated runs, `-np 1`
   composition-invariant serving (~1.7× wall), or a cascade-free segmentation
   (S1/S2 — the A-1a repeat below measures how much of the noise they
   remove).
2. **Short-utterance carriers are structurally exempt** from that floor: one
   request per item, no stitch, no boundary cascade, deterministic scorers.
   Multi-carrier breadth is therefore not just coverage — it is the escape
   route from the noise problem, at ~4–6 s per item.
3. **Serving config A is locked**; serving args are load-bearing (numerics
   diverge across configs). Any protocol change (slot affinity, prompt
   reordering, segmentation) re-enters through a registered bench + re-lock,
   never mid-campaign.
4. **10 s overlapping slicing is dead** (P1: 1.75× slower AND +26.6 pp WER);
   per-call floor ≈ 4.3 s; steps below ~20 s are not viable without
   amortising that floor. Efficiency direction: fewer/longer calls (S1/S2) +
   cache affinity (S5).
5. **Evidence prefixes currently get zero cache hits**, and the id_slot bench
   located the root cause: the rolling tail is appended to the SYSTEM
   message, ahead of the evidence block, so the cacheable prefix dies before
   the evidence starts (`ojw/components.py` OBS_TAIL_FRAME placement). Slot
   pinning alone cannot fix this; the tail must move after the evidence
   (a request-byte change → its own bench).
6. **Two capability gaps** block ~⅓ of the plan's stated success signals:
   (a) entity-class WER scorer unwired (`scoring/entity.py` frozen but not
   registered) — blocks B-2a's headline signal, B-3a, C-5a, ladder L3;
   (b) no QA/EM-F1/intent scorers and no loaders/D1 for any secondary
   carrier — blocks B-6a, C-4a, A-4a/b, X-1/X-2/X-3, B-8a.
7. **Confirmatory work is frozen** until the owner rules on the 2026-08-09
   confirmatory-touch incident (id 4420696). Discovery/dev items are
   unaffected.

## 1. Item-by-item plan

Legend: status DONE / DEAD / READY (arms+configs exist, register and run) /
BUILD (design exists, artifacts missing) / BLOCKED-ON(x). Costs are wall-clock
at the locked config.

### W-A · agent-system construction

| item | question | carrier/split | design | read rule | status → action | cost |
|---|---|---|---|---|---|---|
| A-1a | model-declared boundary vs fixed window | e21 `wave1-sub5` (unexposed) | 5×2 arms + **one repeat of the fixedwindow arm** | ΔWER ≥1 pp directional + boundary-tier histogram; the repeat reads residual noise WITHOUT the cascade — the datum the noise-treatment decision needs | READY (= frontier P3/S1). **Highest priority in the plan** | ~5 h incl. repeat |
| A-2a | buffer geometry 30/60/90 | same, shared control | 5×3 arms | purpose redefined by IC-001: find the commit-window where verbatim accuracy peaks; the 10 s point is already DEAD | READY, same sequence | ~4 h |
| A-3a | VAD trim off / loudness norm | same | 5×2 arms | ΔWER + trimmed-seconds; expected null on trim (fires 1/614 at 5 s) — a clean null retires the knob | READY, same sequence | ~2.5 h |
| A-4a | direct vs self-cascade | **big-bench-audio** (200-item frozen sample `c602bd7e…`) | 200×2 paired | McNemar paired; deterministic string scorer — noise-floor exempt | BLOCKED-ON(profile+loader+D1+scorer) | ~25 min |
| A-4b | same, second task shape | slurp (intent) | 60×2 | intent accuracy; official `slurp` scorer in ref_repos | BLOCKED-ON(profile+loader+D1+scorer); NC audio license noted | ~20 min |
| A-5a | determinism | — | — | — | **DONE — negative.** Superseded by the A-1a repeat (does S1 restore stability?) | — |
| A-6a | serving config | — | — | — | **DONE — config A locked** | — |

### W-B · knowledge construction

| item | question | carrier/split | design | read rule | status → action | cost |
|---|---|---|---|---|---|---|
| B-1a | evidence dose (R4) | e21 `r4-sub10` (n=10) | 10×3 arms under a noise treatment | pre-registered Wilcoxon + bootstrap (analysis plan 2026-08-09); run only after the noise-treatment decision and any re-lock | READY for re-run; **the W-B main battle** | ~5–9 h |
| B-2a | bias-list form (4 arms, 3 contrasts) | e21 `r4-sub10` | 10×4, one shared control | corpus WER read now; **entity-class WER pre-registered as deferred computation** — outputs are persisted, the adapter version is pinned before any deferred read | READY (engineering closed 2026-08-09). Register + run in Wave 0 | ~3 h |
| B-3a | phonetic confusable sets | e21 | 10×2 | entity-class WER | BLOCKED-ON(entity scorer + confusable generator); Wave 3 | ~2 h |
| B-4a | self-generated rolling glossary | e21 long-audio | ladder rung L3 | entity-class WER vs L2; zero leakage by construction | folded into the IC-001 ladder | — |
| B-6a | indexed KB retrieval | spoken-squad | 60×2 | EM/F1; note the carrier is closed-book TTS — treat as retrieval mechanics, not evidence value | BLOCKED-ON(profile+loader+D1+QA scorer+embedding pin); Wave 2/3 | ~25 min |
| B-7a | state compression | e21 long-audio | ladder rung L2 | compacted history vs verbatim tail at equal token budget — IC-001's central question | folded into the IC-001 ladder | — |
| **B-8a (new)** | **evidence arms on a purpose-built contextual-ASR carrier** | **contextasr-bench** (COMPLETE, MIT, profile already speech-aware-secondary) | 60 utt × 3 arms (none/matched/mismatched contexts, the carrier ships them) | utterance-level paired accuracy/WER; noise-floor exempt; cross-carrier replication of the R4 direction | BLOCKED-ON(loader+D1+split freeze) — no profile action needed. **The flagship multi-carrier W-B item** | ~40 min |
| B-5 | cross-slice inconsistency detection | — | — | — | **GAP — owner decision: define a probe or strike the work-group line** | — |

### W-C · knowledge consumption

| item | question | carrier | read rule / dependency | status → action |
|---|---|---|---|---|
| C-1a | whole block vs top-k injection | e21 | WER per evidence token; REDESIGN after the tail-reorder/cache bench — the injection cost model changed | BUILD; Wave 3 |
| C-2a | injection timing (every slice vs once) | e21 | measured input already in hand: zero cache hits, root cause = tail placement; the item is largely ABSORBED by the tail-reorder + id_slot bench — respecify as "timing residual under working cache" | redefine after that bench |
| C-3a | dose ladder none→k1→k5→whole | e21 | R4's three arms are three dose points; add k=1/k=5 fragments | BUILD; Wave 3 |
| C-4a | retrieval query source: audio- vs transcript-derived | **slue-sqa-5** (profile already correct) | retrieval accuracy → task metric; official slue-toolkit scorer | BLOCKED-ON(loader+D1+QA scorer) — cheapest secondary unlock; Wave 2 |
| C-5a | biasing-before vs correction-after (unpublished comparison) | e21 | entity-class WER by strategy; needs a post-hoc-correction policy registered | BLOCKED-ON(entity scorer + new policy); Wave 3 — **the W-C crown item** |
| C-6a | negative controls | e21 | rotation control HAS RESULTS (0.2623); distractor control rides in E-003 | partially DONE; rest rides E-003 |

### W-D · system optimization

| item | status → action |
|---|---|
| D-1a/b | **DONE** (weak monotone signals; words/s is a regime detector, not a ranker). One follow-up, zero GPU: re-run correlations on the R4 traces (~1,800 slice-level observations) once the n=10 set exists |
| D-2a | trigger REDESIGNED per D-1: fire on catastrophic signals (words/s < 0.5), not "worst 15 %"; = ladder L5; Wave 3 |
| D-3a | doubly blocked (carrier profiles + no usable routing signal); re-evaluate after A-4a produces the direct-vs-cascade delta | 
| D-4a | same signal blocker; cost instrumentation already in place (`supplied/admitted_evidence_bytes`) |
| D-5a | carrier-blocked + decode contract frozen at temperature 0 — needs its own probe-manifest entry when designed; Wave 3 |
| D-6 | joint policy over all knobs — **GAP — owner decision: define or strike** |

### X · cross-cutting (one core, many tasks)

| item | carriers | status → action |
|---|---|---|
| X-1 multi-task sweep | audio2tool (loader + 400-item frozen sample + configs EXIST; needs profile+D1 **and the experiment-id collision fix** — `r1-audio2tool.json` declares SAEA-E-002; reassign SAEA-E-006), big-bench-audio, slurp, spoken-squad | audio2tool is the closest-to-runnable non-ASR carrier in the repo; Wave 2 |
| X-2 cross-lingual evidence sensitivity | speech-massive / minds14 | BLOCKED-ON(profiles); NC licenses noted; Wave 3 |
| **X-3 (new)** | **AMI meeting speech** (COMPLETE, CC-BY-4.0, profile already correct): bare-core obs-loop floor on n=5 meetings, then evidence arms | BLOCKED-ON(loader+D1+split freeze); the research boundary names meeting understanding in scope; Wave 2 |

## 2. Carrier unlock matrix

| carrier | lock status | serves | unlock cost | owner action needed |
|---|---|---|---|---|
| e21 / e22 / conec | in use | A-*, B-1/2, C-*, D-* | — | noise-treatment + confirmatory rulings |
| contextasr-bench | COMPLETE, profile ✓ | **B-8a** | loader + D1 + split freeze | engineering authorization only |
| slue-sqa-5 | COMPLETE, profile ✓ | C-4a, B-6a-variant | loader + D1 + QA scorer | engineering authorization only |
| ami-meeting-corpus | COMPLETE, profile ✓ | X-3 | loader + D1 + split freeze | engineering authorization only |
| audio2tool | COMPLETE, loader ✓, sample ✓ | X-1 (tool calling) | **profile + D1 + id fix** | lock-profile amendment |
| big-bench-audio | COMPLETE, sample ✓ | A-4a, D-3a | profile + loader + D1 + scorer | lock-profile amendment |
| slurp / spoken-squad | COMPLETE | A-4b, D-5a, B-6a | profile + loader + D1 + scorer | lock-profile amendment |
| prism / rare5k / buzzword | COMPLETE (diagnostics) | B-3a materials | as needed | — |

## 3. Wave schedule

- **Wave 0 — now, zero owner action, ~8 GPU-h:** E-004 (A-1a/A-2a/A-3a, six
  arms + the fixedwindow repeat) → E-003 (B-2a, four arms) → D-1a offline
  re-correlation (free). E-004's repeat delivers the noise-treatment datum
  BEFORE the R4 n=10 decision must be made.
- **Wave 1 — after the tail-reorder/cache bench verdict and the noise
  ruling:** any adopted serving/prompt change re-locks first, then the
  **R4 n=10 re-run** (B-1a's formal read) under the chosen noise treatment.
- **Wave 2 — after the engineering authorizations / profile batch,
  ~2 GPU-h total:** B-8a (contextasr), C-4a (slue), X-3 (AMI floor), A-4a
  (bba), X-1 (audio2tool). All short-utterance, noise-floor-exempt, cheap,
  and they answer the multi-carrier mandate directly.
- **Wave 3 — informed by Waves 0–2:** the IC-001 ladder L1→L5 (absorbing
  B-4a, B-7a, D-2a), C-1a/C-2a/C-3a redesigns, C-5a, B-3a, D-5a, X-2.

## 4. Decisions queued for the owner

1. Lock-profile batch (slurp, spoken-squad, big-bench-audio, audio2tool →
   `speech-aware-*`) — unlocks half of Wave 2.
2. Entity-class WER adapter format decisions (owner-decisions-pending item 1)
   — unblocks B-2a's headline signal, B-3a, C-5a, L3.
3. Engineering authorization: loaders + D1 + split freezes + scorers for
   contextasr-bench, slue-sqa-5, AMI (no profile action needed).
4. Noise treatment for long-audio paired reads — recommend deciding AFTER
   the A-1a fixedwindow repeat (if S1 removes most run-to-run noise, the
   structural fix beats paying 1.7× for `-np 1`).
5. Confirmatory-touch disposition (id 4420696) — until ruled, no
   confirmatory work can start.
6. audio2tool experiment-id collision fix (SAEA-E-002 → SAEA-E-006).
7. B-5 and D-6 gaps: define probes or strike the lines.
