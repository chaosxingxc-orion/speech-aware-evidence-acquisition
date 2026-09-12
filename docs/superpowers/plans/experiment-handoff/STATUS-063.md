# STATUS-063: Active GPU execution and next speech-tool comparison

Snapshot UTC: 2026-09-12T16:47:20.899425+00:00. Root read process and attempt metadata, not current recovery task outcomes. The receipt is DATA coordination/owner-status-20260912-1646-v1.json (SHA256 3198a8f0df2ecfd5093f55441a7c834d74eff0dc72346d04663384779989567c).

## Current execution

- Audio2Tool DIRECT is FINALIZED with 4000 generation calls.
- Audio2Tool STAGE-CONTROL is FINALIZED with 8000 generation calls.
- Audio2Tool KNOWLEDGE is OPENED with 5319 generation calls toward 8000 planned calls. Calls are not completed final-answer rows.
- Root service PID620 and campaign PID2179 are live in WSL Ubuntu-24.04. The service uses cached features, no mmproj, total context98304, three slots and32768 tokens per slot. Preserve frozen active source22b56d706e2f5601dc79f58a8fad2bb6a9629f51.
- The two finalized arms already have their first complete official scores with per-sample statistics. Keep all recovery quality closed until the third arm seals or an explicit terminal hold. Do not rescore.
- Recent utilization is high and all three slots have been busy. The read-only GPU query also reports software power-cap activity and low SM clocks. Utilization alone does not establish maximum hardware throughput. Diagnose at an experiment boundary without changing the active serving geometry or asserting an unverified hardware cause.

## Completed and in-flight preparation

Control recall now exists for all1000 SLURP rows. Root verified byte-equivalent recalled score mappings and candidate IDs/order against the retained compact-frame preparation. The same ranking/fusion configuration remains in force; final selection still uses legal runtime state. No neural encoding or task-quality read occurred. The final control baseline binds the new receipt. Warm validation and the full3000-request fake shared-executor check are running in the preparation worktree; do not call them complete until their receipt exists.

Whisper large-v3 checkpoint, source, isolated environments, shared producer/consumer and the preparation registration are in place. Freeze the actual producer checkout at f755559a43fa8fddb67438cf258626507cf8ae84. No real dataset ASR forward has occurred. The first admitted window contains1000 clips,125 native batches of8 and2884.7936875 source speech seconds. Treatment recall must bind the actual finalized ASR catalog.

A separate bounded shared saved-score reader compatibility change is in progress. It lets the existing SLURP statistical path consume finalized bundle score attachments without rerunning a scorer or changing the estimator. It does not modify the active A2T source or analysis recipe.

## Scientific interpretation

The retained SLURP exploratory same-roster working baseline improves NEW500 intent73.2 to77.4 percent and official pooled micro SLU F1 36.511 to39.502 percent. Its two-phase system comparison does not isolate a knowledge-content effect. Rich source-span and role-coverage variants remain closed; more value text has not established more benefit.

E21 fresh draft/repair reduces PERSON errors675 to576 and total word errors29216 to29051, while insertions rise10336 to10341. Preserve the original insertion-guard failure. Apply the owner's WER/PERSON-first preference only to future registered experiments. Live targeted review, new tool observations and speaker-context performance are not established.

The only older NEW500 null calibration uses a different single-stage, max64, eight-slot configuration and projected scoring. It is not a matching null for the new three-stage, max256, four-slot raw official SLURP comparison. Treat it as historical context only. The earlier prospective design's retain_aligned_historical_null_calibration field must not transfer numerical noninferiority or equivalence margins. Freeze the new native-metric analysis before reading either new arm; keep intent and pooled micro SLU F1 distinct and report tradeoffs.

## Owner decisions

No immediate owner decision blocks the active campaign or authorized preparation. Retain quality-first offline evaluation, local tools, final frozen-core answer authority, SLURP-first system optimization, task-specific distinguishing knowledge and validated corrective memory. Do not ask the owner to choose an optimizer or extra tool before the system evidence exists.

If a future comparison exposes a concrete task-quality tradeoff that changes which system is retained, present its native metrics, affected strata and proposed prospective rule to the owner. Optional pyannote access remains outside the critical path because local Sortformer artifacts exist.

## Next work

1. Finish the admitted Audio2Tool recovery, register the finalized-manifest analysis bindings and apply its frozen paired decision rule. Preserve all original and recovery contacts. A fresh effectiveness claim needs the declared same-roster reproduction; an uncertain or negative outcome needs named-component attribution.
2. Close the SLURP control preparation and fake wiring. Complete root statistical registration and the minimal shared saved-score compatibility fix.
3. After scientific admission, allocate one exclusive Whisper GPU preprocessing window. Cache source-bound observations, seal them, and restore the decoder-only Qwen geometry.
4. Run two matched full DEV1000 three-phase systems: both plan, solve and revise; only one receives Whisper evidence before revision. Each arm targets3000 Qwen generation calls with max_tokens256 and the same resident process. Retain original speech and compact knowledge.
5. Score each complete manifest once and analyze native quality, corrections, harms, failures and evidence use. This is an evidence-availability comparison; it is not a learned Reviewer trigger.
6. If useful evidence is established, compare problem-targeted supply against matched random supply. Add alignment, conflict localization, VAD or speaker context only for a named limitation.
7. Build source-bound corrective experiences and the reward-to-update-to-freeze-to-evaluate lifecycle for system-level training-free optimization. Seven upstream source audits, historical memory experiments and synthetic runtime integration do not constitute a completed optimizer. Extend a retained system to native Audio2Tool and E21; E22 test remains closed.

The broad goal remains active. Cost and latency are reported without a quality reward penalty. Every new attempt still needs finite prospective accounting. Maintain one root-owned GPU service and shared execution paths.
