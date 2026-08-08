# Unified agent abstraction across carriers (owner design session, 2026-08-08)

Question (owner): does the obs-agent-loop design generalize to the other
in-scope carriers/tasks, and if not, what unified abstraction is needed?
Answer: it generalizes iff five seams are pluggable; three need additions,
all additive to the v1 substrate (the A-family long-form case is the hardest
OBS instantiation — the other families are degenerate or outer-loop cases).

## Per-family fit

| family / task shape | fit of current design | gap |
|---|---|---|
| A — long-form contextual ASR (earnings/conec) | native target | — |
| B — SLU (slurp/speech-massive/minds14; 2.9–9s single utterances → intent/slots) | loop degenerates to single iteration (buffer ≥ clip); VAD trim still useful | output contract (structured JSON vs transcript) + format-repair re-ask trigger |
| C — spoken QA (spoken-squad/heysquad/slue-sqa-5; spoken question + spoken document) | document stream fits the OBS loop | **role-typed dual channels** (question vs document) + **span-addressable observation memory** (time-range → text index built from the OBS trace's per-span records) enabling region re-listen |
| D — tool calling (audio2tool/VAB; short commands; multi-turn tiers) | single-turn ready (P1 scorer landed); correction tier maps onto the re-ask skeleton | **session outer loop**: cross-turn ORG state (rolling state generalized from within-call to across-turns; per-turn audio in chat_history) |
| E — meeting (AMI) | long-form fits | reuses C's span memory; speaker-change as a future VAD-tier upgrade; participant glossary is ConEC-isomorphic |
| F — assistant omnibus (BBA/voicebench/…) | fits; unification bonus below | output contract only (MCQ letter extraction etc.) |

Unification bonus (F): the survey's strongest multi-carrier mechanism signal
— cascade vs direct (BBA 66→~92, AIR-Bench 77.8→87.7, URO +20; FDB-v3
reversal) — IS an architecture ablation of this agent: N1+N2 split = cascade,
N1/N2 fused into one call = direct. R2/R3 probes become the fused-vs-split
knob of the same system.

## The five pluggable seams

1. **Observation channel types**: single utterance / long stream /
   multi-turn session / question+document dual stream. The OBS loop is the
   long-stream instantiation; single-shot is its degenerate case; sessions
   add an outer loop; dual streams are role-typed channels.
2. **Span-addressable observation memory (ORG)**: (time-span, text, hashes)
   tuples plus derived state (glossary, confusable sets, rolling summary).
   Enables region re-listen, cross-segment consistency detection, meeting
   QA. The OBS trace already records per-span offsets — this is an ORG-layer
   organization of records the substrate already emits.
3. **Task/output contracts**: transcript | structured tool call | answer
   span | choice | free text — each with a deterministic parser, a scorer
   binding (registry exists), and a format-repair re-ask trigger.
4. **Knowledge ports** (already designed): N1 boundary knowledge / N2 task
   knowledge × source typing (external-static / external-retrieved /
   self-generated). The R4 dose ladder and T-series analogs instantiate
   these ports per carrier.
5. **Re-ask skeleton × pluggable triggers**: acoustic badness / entity
   suspicion / format failure / answerability doubt — one policy skeleton,
   four trigger types.

## Discipline rules

- **Protocol arms never run through the agent.** Published-protocol
  reproductions (R1 Audio2Tool same-model row, AIR-Bench SLURP-IC rows,
  benchmark harness reruns) stay protocol-faithful bare prompting —
  comparability is their whole value. The agent is always OUR contribution
  arm, run alongside, never instead.
- Build order stands: v1 substrate (A-family long stream, hardest case) →
  phase-2 knowledge/re-ask arms → seams 1/2/3 as the B/C/D probes come up,
  each with its own pre-registration.
- Every seam configuration flows into config_hash → protocol_hash; every
  cross-seam state transition is traced on its owning axis (OBS/ORG/SUPPLY/
  USE), per the consolidated contract.
