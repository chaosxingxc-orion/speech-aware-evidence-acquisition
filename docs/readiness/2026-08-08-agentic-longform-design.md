# Agentic long-form design (owner directive, 2026-08-08)

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
