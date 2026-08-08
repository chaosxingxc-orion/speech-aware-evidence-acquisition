# Agentic long-form design (owner directives, 2026-08-08; v2)

**v2 (same day, second owner directive + truncation evidence):** the OBS
layer is a **model-driven agent loop**, not fixed pre-sliced windows. The
whole-call protocol is empirically invalid — 7 of 9 "successful" whole-call
transcripts were 2–106 words for 40–75-minute calls (the core transcribes
the opening line and emits EOS); and no reference work loads whole calls
(Earnings-21 scored VAD/streaming pipelines; Whisper's canonical recipe is
30s sliding windows; Siskos/ConEC/CMT-LLM all segment; D/F-family benchmark
clips average 3.6–47s). Fixed windows are kept only as a degenerate config
(ablation arm A) of the loop policy.

**obs-agent-loop (v2 design):** per call, a sliding buffer of
`obs_buffer_seconds` (default 60, configurable) is transcribed by the frozen
core, which also reports a rough end-of-last-complete-sentence boundary;
boundary resolution is three-tier — model estimate → deterministic
silence-snap (±`obs_silence_snap_seconds` RMS minimum) → clamp into
[`obs_min_advance_seconds`, `obs_max_advance_seconds`], with a fixed-advance
+ overlap-text-merge fallback when the estimate is unusable. Accepted spans
concatenate into the call hypothesis; every boundary decision is an OBS
trace record (per the contract's per-axis tracing). Runtime slices are cut
under the attempt run dir and hash-chained to the parent media through an
extended payload-binding rail (fail-closed). Node-1's transcript IS the ASR
output (single pass); Node-2 semantics (evidence injection per iteration)
carry the R4 arms. Rationale guardrail: audio-LLM timestamps are unreliable,
so the model's boundary is advisory, never trusted raw.

**v2 addendum (third owner directive, same day):** speech preprocessing
tools join the OBS toolkit as pinned, logged, tool-level components (no
answer authority): VAD upgrades boundary tier 2 (snap to the nearest
speech/non-speech transition; v1 engines: zero-dependency energy VAD
default, webrtcvad when present, silero as a future pinned-model ablation);
VAD pre-trim skips long non-speech spans (> `obs_vad_trim_min_seconds`,
trimmed audio never metered, every trim an OBS trace record); optional
per-slice RMS loudness normalization (`obs_preprocess`, default off;
denoising deliberately excluded from v1 — future ablation arm). All knobs
flow into config_hash → protocol_hash; all decisions and derived-audio
hashes chain back to the parent media.

Owner directive (session, 2026-08-08, recorded verbatim in intent): long-form
audio must NOT be handled by driving the frozen core once over a whole call;
the study's object is a speech-omni AGENT, so long context is an agent
problem — segmentation, context management, multi-pass inference, context
compression. This supersedes the whole-call request shape that the first
SAEA-E-001 attempts used (their 9/10-sample record stays as the
no-segmentation boundary evidence: ~56k tokens/request, 3600s timeout on the
longest call, RTF ≈ 0.57).

## Mapping onto the four-construct frame (plan §abstraction)

| directive element | construct | concrete v1 |
|---|---|---|
| 断句 segmentation | 1 — agent construction (OBS policy) | 300s fixed windows, 16kHz mono, no overlap; segment-as-sample; window length is the first OBS knob (substrate being built) |
| 上下文管理 context management | 2 — knowledge construction (ORG) | bounded carry-state per call: entity/number/term glossary accumulated from already-produced segment transcripts, capacity-capped |
| 上下文压缩 compression | 2 (ORG policy) | v1 deterministic extraction (pure function, no extra calls); v2 model-made rolling summary via self-cascade (same frozen core) |
| 多段推理 multi-pass | 1 (pass structure) | ordered per-call segment loop threading the carry state |
| 状态注入 | 3 — knowledge use (SUPPLY) | carry state enters the next segment's prompt through the existing `supplied_evidence` field, provenance `self-rolling-v1` — reuses the frozen 12-field arm shape (D2 re-freeze expected unnecessary; verify) |

Key scientific link: a self-built rolling glossary IS a self-generated
contextual-biasing list — the same mechanism family as Siskos/ConEC external
materials, but sourced from the agent's own OBS stream. No published
inference-time precedent exists on any held carrier (mechanism map bucket 3).

## Knowledge routing (fourth owner design question, 2026-08-08)

Both workflow nodes have knowledge slots, of different types and sources:

| node | knowledge | source | axis | precedent |
|---|---|---|---|---|
| Node-1 断句 | rolling tail conditioning (previous ACCEPTED span's tail in the prompt; model output, never gold) | self | ORG→SUPPLY | Whisper condition-on-previous (strong) — **v1, in scope** |
| Node-1 | entity glossary guarding boundaries (never cut inside a name) | external (ConEC participants/bias lists) + self-accumulated | SUPPLY | none (bucket 3) — phase 2 |
| Node-1 | structural priors (call phases, Q&A turn cadence) | external/static | ORG | meeting-ASR adjacent — phase 3 |
| Node-2 任务 | bias/keyword lists injected per iteration | ConEC materials (on disk) | SUPPLY | Siskos — the R4 arms |
| Node-2 | **confusable sets** ("heard form" → phonetically-near entity candidates), dual-sourced: deterministic phonetic keying over ConEC entities AND self-detected cross-segment spelling inconsistencies | external-derived + self | ORG+SUPPLY | RECOVER/DeRAGEC class (R6 in-loop) — phase 2 |
| Node-2.5 | confusable-driven correction re-ask | same | USE | RECOVER-style — phase 2 |

The dual sourcing of confusable knowledge (external-derived vs
self-generated from the agent's own inconsistencies) gives a clean
self-vs-external contrast INSIDE one mechanism class — scoping discipline:
v1 ships tail conditioning only; every phase-2 arm gets its own
pre-registration.

## Arm ladder this enables (extends R4's pre-registered monotonicity)

On the same segmented substrate, per call: `no-carry` (independent segments,
floor) / `self-carry` (rolling compressed state) / `external`
(matched ConEC materials) / `mismatched` (rotated materials). Self- vs
external- vs no-evidence is a dose spectrum; each new arm gets its own
pre-registration before any run reads results.

## Sequencing

1. Segmentation substrate (worktree agent, in flight): segmenter + derived
   manifests + segments receipts + segment loader + `asr-wer-concat` scorer +
   D1 derived-layer amendment path + segmented config fragments.
2. Operator runs: segments build → D1 amendment → gate dry-run → segmented
   E-001 smoke (~134 requests, small each) → segmented R4 mini arms
   (~102 requests/arm).
3. Carry-arm engineering (next agent task after the substrate lands):
   `rolling-context` policy (ordered per-parent loop + deterministic
   compressor v1), tests, pre-registration, then the four-arm ladder run.
4. Fold results into the wiring memo / baselines wiki / umbrella index as
   already planned.
