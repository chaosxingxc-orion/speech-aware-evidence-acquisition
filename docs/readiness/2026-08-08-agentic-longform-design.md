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

## Selective re-observation (fifth owner design question, 2026-08-08)

Noise-segment detection → model invokes a denoising tool → re-listens.
Classification: NOT knowledge-driven — it is **condition-aware
re-observation** (construct 1 acting on OBS; the acoustic sibling of
exploration direction 8). The owner's *selective* framing designs out the
documented failure mode of static denoise front-ends (enhancement artifacts
hurting ASR on clean audio). Phase-2 arm, own pre-registration:

- **Triggers (deterministic only; no logits available)**: per-slice acoustic
  metrics (energy-SNR estimate, clipping rate, spectral flatness — pure
  numpy) + output-pathology metrics (transcript-length ÷ VAD-speech-seconds
  ratio — the cheapest bad-observation signal, handed to us by the
  whole-call truncation finding — plus character-loop and OOV density).
- **Denoiser**: pinned frozen tool-level component, no answer authority
  (v1 pure-numpy spectral subtraction; RNNoise/DeepFilterNet runtime-
  detected, hash-pinned, as tool ablations).
- **Keep rule**: deterministic — adopt the re-listened transcript only if
  the badness metric improves beyond a margin; both output hashes traced.
- **Shared skeleton**: one re-ask policy skeleton serves two triggers —
  acoustic badness (this arm) and entity suspicion (Node-2.5 confusable
  re-ask).

## Arm ladder this enables (extends R4's pre-registered monotonicity)

On the same segmented substrate, per call: `no-carry` (independent segments,
floor) / `self-carry` (rolling compressed state) / `external`
(matched ConEC materials) / `mismatched` (rotated materials). Self- vs
external- vs no-evidence is a dose spectrum; each new arm gets its own
pre-registration before any run reads results.

## Prefix-cache-friendly prompt order (transport engineering, 2026-08-09)

**Rule:** stable content FIRST, variable audio LAST. In the transport's
user-message `content` list, evidence text parts (deterministic, unchanged
formatting) precede the audio part; the system message (task instruction)
already precedes both and is unaffected.

**Measured saving** (ops benchmark on the real server, 8 requests sharing an
identical 23.3 KB evidence block): audio-first (the prior order) processed
11,780 tokens/request with only 26 cached (22,283 ms prefill, 367.8 s total);
evidence-first processed 2,200 tokens/request with 9,607 cached (8,416 ms
prefill, 250.5 s total) — 93% fewer prompt tokens processed, 72% less
prefill, 32% less wall-clock. llama-server only reuses a KV-cache prefix
that is byte-identical AND contiguous from the start of the prompt; content
placed after the audio does not get this benefit.

**Why this matters specifically for the evidence arms (fixed-legal-context,
mismatched-evidence, and the R4 context-dose ladder):** their evidence block
is constant across every slice of one call — the same materials get
re-sent, slice after slice, only the audio and the rolling carry-state
change. With evidence-first ordering, that constant block is cached ONCE per
server slot (after the first slice pays full prefill) and reused for every
later slice of the same call; with audio-first ordering, the identical
evidence text sat behind a per-slice-variable audio blob and could never
form a reusable prefix, so it was fully re-processed on every single slice.
For a long call with many OBS-loop slices, this compounds: the no-evidence
arm (`bare-core`) is unaffected (no evidence block to cache), but every
evidence-bearing arm pays full evidence-token cost on every slice under the
old order and near-zero marginal cost after the first under the new one —
this is a pure transport-efficiency fix, not a change to what evidence is
supplied or how it is scored (D2 `ARM_VISIBLE_FIELDS` and the evidence
formatting string are both untouched).

**Audit signal:** this is a PROTOCOL-AFFECTING change (two runs on the same
config hash differ in wire bytes across this commit) even though it alters
no config value. Verified by tracing the code: `request_sha256` (the
`payload_sha256` traced in `MODEL_REQUEST`, `core/model/adapter.py`) hashes
the canonical `ExecutionPayload` dict *before* the transport ever runs —
that dict has no `content`-array concept at all, so this reorder is NOT
visible there, nor in `protocol_hash`/`config_hash` (both config-value
derived, unaffected). The actual provenance signal is `study_commit` in the
run manifest (`core/bundle/git_commit.py`), which binds the exact git HEAD
of the study repo a run executed against — any run after this commit lands
carries the new `study_commit`, which is how pre/post-reorder runs are
distinguished in the audit trail.

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
