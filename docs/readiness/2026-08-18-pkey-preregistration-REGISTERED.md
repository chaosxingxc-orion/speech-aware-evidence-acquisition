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
