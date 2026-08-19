# P-KEY — modality × supply factorial — REGISTERED

Date: 2026-08-18. Status: **REGISTERED — flyable once the machinery lands** (GPU slot G-2,
behind the diar smoke). Profile: `bounded-discovery-probe`. Owner GO: 2026-08-18 approval of
the speech-term program (probe ②, the decisive instrument). Samples: the SAME frozen 60
SLURP devel samples (seed 20260807); decode config identical to the consumed P-SLU flights.

## 1. Question

Is the supply benefit realized **through perception** (the roster helps the core re-resolve
the audio) or **after perception** (text-side mechanism; the audio is only a retrieval key)?

## 2. Design change vs the plan sketch (registered here, disclosed)

The text condition uses the core's **OWN transcription** (SELF-TXT), not gold transcripts:
gold reference text entering a prompt would breach the study's hard rule ("reference
transcripts must never enter runtime"), and SELF-TXT asks the sharper question — whether
supply+audio can repair samples the core's own committed transcription already got wrong.
A gold-text oracle variant remains a possible owner-decidable extension; it is NOT part of
this registration.

## 3. Arms (5 passes, 300 requests)

| Pass | Arm | Input | Supply | n |
|---|---|---|---|---|
| 0 | T0 transcription | audio → verbatim transcription instruction | none | 60 |
| 1 | AUD-NOSUP | audio | none (A0 re-fly, in-session comparator) | 60 |
| 2 | AUD-SUP | audio | A3-form 100-entry legal roster | 60 |
| 3 | TXT-NOSUP | T0's transcript text (audio absent) | none | 60 |
| 4 | TXT-SUP | T0's transcript text | A3-form roster | 60 |

All four factorial arms fly in the SAME session (in-session comparators — the measured
±0.013 duplicate-condition floor and the meeting-side server-state spread finding both
argue against citing cross-session baselines for an interaction estimate). T0's transcripts
are model output (deployment-legal); each is hash-recorded and reused byte-identically in
passes 3–4.

## 4. Metrics and verdicts

Primary: SLU-F1 per arm; Δ_AUD = AUD-SUP − AUD-NOSUP; Δ_TXT = TXT-SUP − TXT-NOSUP;
**INTERACTION I = Δ_AUD − Δ_TXT**. Verdicts (mechanical; thresholds on the measured 0.03
separability bar):
- **SPEECH-TERM-PRESENT**: I ≥ +0.06 (2× bar) — supply pays extra only when raw audio is
  present ⇒ part of the benefit repairs perception; speech knowledge participates in the
  supply loop.
- **KEY-ONLY**: |I| ≤ 0.03 — the benefit is modality-invariant ⇒ text-side mechanism.
- **TEXT-DOMINANT**: I ≤ −0.06 — supply helps more once perception is frozen to text.
- Otherwise **INCONCLUSIVE-KEY**.
Mandatory descriptives: the perception gap itself (TXT-NOSUP vs AUD-NOSUP); the
converted-sample SET difference (samples converting under AUD-SUP but not TXT-SUP = the
perception-repair set — cross-referenced against P-PHON's NEAR-MISS class); T0 transcript
quality vs gold (scoring-side WER, reported only); induced substitutions per arm; 3 seeded
silence-swaps on AUD-SUP (unanimity VOID bar).

## 5. Cost (registered ceilings)

303 requests (300 + 3 swaps); ≤340 core calls; ≤2,500 metered audio-seconds (passes 0–2 and
swaps carry audio; passes 3–4 are text-only); ≤0.6 GPU-h.

## 6. Discipline

One-shot read; pinned read suite (`analysis/pkey_read.py`, four-verdict evaluator +
interaction decomposition + converted-set cross-reference) built and coordinator-reviewed
BEFORE the read; exposure row `SAEA-PROBE-pkey-303` appended at registration (consumed=no);
no gold-derived field in any prompt (T0 output is model text; the roster is the consumed
A3 binding reused); SLURP audio CC BY-NC 4.0 carried.

## 7. Amendment 2026-08-19 (pre-read; adversarial-panel Finding 2 + attempt-1 abort)

Registered before any read; nothing consumed. Four changes:
1. **KEY-ONLY becomes a CI-based equivalence decision.** The read suite computes a
   per-sample paired cluster bootstrap over the 60 samples (resampling samples, recomputing
   all four pooled arm scores and I) and publishes σ̂(I) and a 90% CI. KEY-ONLY fires only
   if the ENTIRE CI lies inside [−0.03, +0.03]; a point estimate inside the band with a CI
   crossing it is INCONCLUSIVE-KEY. (Panel calibration: the 0.03 band was imported from a
   single-contrast duplicate pair; I is a four-arm difference-of-differences with
   σ(I) ≈ √2 × 0.0129, so the unamended clause fires ≈90% under a pure-noise null.)
2. **Pre-read reachability statement is mandatory.** Before the verdicts are evaluated, the
   read publishes the maximum |I| attainable given P-PHON's consumed class census (NEAR-MISS
   4/85 baseline failures). If SPEECH-TERM-PRESENT is unreachable, KEY-ONLY may not be
   reported as an affirmative negative — only as INCONCLUSIVE with the reachability bound.
3. **The NEAR-MISS cross-reference carries an n≤4 caveat** (effectively n≤3 after P-PHON
   disqualified the single A3 NEAR-MISS row as a clock-format variant); it licenses no
   mechanism claim.
4. **A 35-call TXT duplicate sub-block joins the flight** (within the registered ceilings:
   303 + 35 = 338 ≤ 340 calls; zero audio-seconds): a seeded 35-sample sub-block of pass 3
   re-sent byte-identically in the same session, giving this axis its own measured
   duplicate floor for the bootstrap to anchor.
License line bound now: a positive I upgrades the L3 MECHANISM reading and travels with
C1's same-distribution disclosure; it is never a deployment claim.

**Attempt-1 accounting**: `attempt-20260819T085521Z-654dc8` ABORTED at request 184 — the
three audio passes flew clean (183/183: T0 60, AUD-NOSUP 60, AUD-SUP 60, swaps 3, zero
failures) and the first TXT request was refused by the transport invariant ("user message
must carry exactly one input_audio content part"): the client layer was never relaxed for
registered text-only arms, and the machinery's mock-client tests could not see the real
invariant (the P-SLU mock-reality lesson, recurring). Repair: a text-path capability in the
real client, tested through the REAL validation layer; then a full re-fly (attempt-2, all
338 requests in ONE session — resuming across sessions would break the in-session
comparability the factorial is designed around, so the aborted attempt's audio rows are
dead weight, recorded and never read).

## 8. Amendment 2026-08-19 (run closure and successor run; nothing consumed)

Attempt-2's takeoff REFUSED fail-closed at a run-total feasibility preflight check: the
attempt store's one-shot semantics charge attempt-1's durable 183 calls against the run
ceiling forever (183 + 338 = 521 > 340 registered), so no compliant attempt can fly under
`SAEA-PROBE-pkey-303`. Per the coordinator's registration decision (successor run, never a
post-hoc ceiling expansion and never a falsification of the durable spend record):
- **`SAEA-PROBE-pkey-303` is CLOSED NOT-CONSUMED** — its ledger row stays consumed=no
  forever with the closure note; attempt-1's 183-call/554.46-audio-second dead spend
  remains attributed to it; no output of attempt-1 is ever read.
- **Successor run `SAEA-PROBE-pkey2-338`** carries the identical §1–§7 design (six passes,
  338 requests, one session, the §7 CI/reachability read amendments) with fresh accounting
  (ceilings 360 calls / 2,500 audio-seconds / 0.6 GPU-h) and its own exposure row.
Second mock-reality instance recorded: the launcher's hand-rolled HealthProxy narrowed the
real client's signature (would have re-aborted at the first TXT request despite the library
repair); fixed in the launcher, and proxy-signature parity joins the machinery checklist.
