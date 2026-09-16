# Candidate-bound slot-view proof: terminal report and repair handoff

Author: Codex, root scientific coordinator. Date: 2026-09-16.
This report supersedes pre-proof "HELD/no live contact" statements in the v2 handoff.
It records engineering evidence only. No task-quality output was read.

## What was actually attempted

The proof isolated one new candidate-bound view on the older useful dual-store SLURP agent.
Keep the original role prompts, K8 intent supply, maximum-three candidate rules, slot card
selection/order, task-contract tool, revision bound, decoder and delivery unchanged.
Do not include typed-context compilation, target lookup, reference deduplication, ASR,
candidate refresh or newly authored knowledge in this intervention.

Baseline/experiment/cell: slurp-candidate-slot-view-proof4-v1.
Run: SAEA-SLURP-CANDIDATE-SLOT-VIEW-PROOF4-V1.
Attempt: attempt-slurp-candidate-slot-view-proof4-generation-v1.
FIT run: SAEA-SLURP-CANDIDATE-SLOT-VIEW-PROOF4-FIT-V1.
Frozen source: 3c14a0b0780967a5d224c573e8a991c0fd255607.

The four already-exposed TRAIN rows were:
- slurp:train:000007:audio--1504197557
- slurp:train:000009:audio-1497557594-headset
- slurp:train:000015:audio-1488524781
- slurp:train:000023:audio-1490956038

Their split hash is 4e3413fe64a51cea597bbd1de5c1b4bb5ac5194969a8522d7f3173b6c4b969cb.
Generation and FIT plans, protocol and preregistration are in
[the registered readiness directory](../../readiness/2026-09-16-slurp-candidate-slot-view-proof4-v1/README.md).

The finalized program permits one initial Perception and at most two Solver/Reviewer/Planner
visits. Reviewer has three tool-visible iterations; there is no reserve-final-report
modification. The maximum per row is 1 + 2*(1+3+1) = 11 generation contacts.
The prospective envelope was 44 generation, 176 FIT endpoints, 24 analytical tool invocations,
117 repeated speech seconds and one shared FIT-inclusive GPU hour. Zero ASR/encoder/scorer
calls were admitted. Ceilings were not targets.

The draft tool cap of 16 was corrected to 24 before any contact. Preparation v1/v2 were
model-free administrative artifacts; final phase-supply-v3.json bound the finalized settings,
with identical selected values/order. Those revisions are not failed model attempts.

## Observed terminal facts

| Item | Observed value |
| --- | --- |
| Worker | PID 467880; exit 1 at 2026-09-16T19:12:06.532151+00:00 |
| Root closure | 2026-09-16T19:15:00.251142+00:00 |
| Final attempt state | ABORTED |
| Generation contacts | 4, all Perception |
| Repeated speech exposure | 10.5955625 seconds |
| FIT | 4 receipts; 16 endpoints: 4 props, 4 apply-template, 8 tokenize |
| FIT result | All recorded requests passed; minimum margin 20,417 tokens |
| Failure | FrozenCoreError: native slot view source: target slot full content differs |
| Stage | Entry to solver_0_role, before Solver generation |
| Complete manifest / official score | Absent |
| Quality read | None |
| Root terminal decision | STOPPED_ENGINEERING_SOURCE_CONTENT_MISMATCH_NO_RETRY_UNDER_THIS_PROOF |

The large recorded FIT margin is for Perception requests only. It does not validate any
unexecuted Solver/Reviewer request or demonstrate whole-episode capacity. The failure was
an exact source-content mismatch, not evidence of OOM, reboot, insufficient context or a
bad task answer.

After proving worker absence and four idle slots, root marked the still-open attempt
ABORTED and released the foreground exclusive worker lease. The resident decoder was not
restarted or unloaded. The new snapshot records file/process observations after release.
No automatic retry, partial scoring or replacement answer was attempted.

## Root source-level diagnosis

The projector assumes every target body has the named-store wrapper, but the retained
legacy task-contract-only program legitimately supplies unwrapped canonical content.

The source route at canonical 854e3d2b is:

1. The proof's phase_tools grants only saea-tool-task-contract-v1 and no knowledge_store_ids.
2. core/flight/runtime.py::_build_phase_tool_dispatcher (lines 4678-4704) detects no
   named-store tool authority. It deliberately passes knowledge_stores=None to the
   dispatcher. Automatic knowledge supply has its own store binding.
3. rails/phase_runner.py (lines 704-707) passes this dispatcher's render_values callback.
   Thus the live route has a renderer; it is not simply the no-renderer branch.
4. rails/phase_tools.py::render_values uses the shared value renderer and
   _model_knowledge_blocks. With knowledge_stores=None, _model_knowledge_blocks
   (lines 1422-1424) preserves the plain canonical blocks.
5. rails/slot_binding_view.py::project_slot_value (lines 557-563) constructs expected
   content with knowledge_binding.model_evidence_block and requires exact equality.
   That helper inserts "[knowledge store=... role=...] " before the canonical body.
6. A legitimate plain body therefore fails the projector's expected prefixed-body check.

The no-renderer path in rails/runner.py::_agent_messages (lines 1262-1274) also uses plain
canonical values and needs coverage, but it is not the primary route identified above.

This diagnosis is supported by registered configuration, source inspection and the narrow
terminal exception. Root did not inspect raw failed answers or reconstruct the failed
payload from campaign logs. A CPU reproduction through the actual shared dispatcher remains
the first repair step; no repaired end-to-end execution is claimed.

## Why the model-free acceptance missed it

The new slot-view fixtures construct target bodies through model_evidence_block.
They exercise the named-prefixed representation. The real source-binding smoke verified
the 54 cards, 402 bindings and 60 legal intents, but did not exercise this legacy plain
rendering route into the projector.

The prior 248 passing tests, one platform skip and 83% combined coverage are preserved.
They establish the checked behaviors, not coverage of every actual program configuration.
The specific acceptance gap is representation-path mismatch. More generic test volume
without this path would not resolve it.

## Narrow repair contract for the successor

Use a NEW isolated worktree. Keep both failed sources and original artifacts immutable.

- Reproduce with the exact task-contract-only dispatcher, shared render_values and
  candidate-bound projector, using released source knowledge and synthetic valid role states.
  Demonstrate the present failure before changing code.
- Accept only exact source-bound canonical representations that the shared renderer actually
  emits. A plausible fix handles plain canonical and named-prefixed canonical content as
  explicit representation identities and emits the derived view in that same representation.
  Root must choose and review the final shared abstraction.
- Preserve exact ID, source URI, store/snapshot/content binding and complete source body.
  Do not strip arbitrary prefixes/whitespace or accept substring matches.
- Do not grant the tool named-store authority or add prefixes to the old baseline merely to
  satisfy the projector; that would change the retained method's requests.
- Preserve all global rules and applicable candidate/draft bindings. Missing or malformed
  scope, no applicable binding and other registered fallback cases retain full content.
- Test plain and prefixed paths, stale/mismatched source rejection, projection-off byte
  identity, actual shared request-builder FIT/dispatch equality, and raw/feature rendering.
  Record source representation, source/view hashes and actual selected/excluded fields.
- Run focused meaningful WSL tests and existing engineering checks; avoid a new runner or
  open-ended framework redesign.

After CPU acceptance, produce a concrete fresh proof proposal. The closed proof allows no
retry under its identity. A fresh admission must explicitly resolve that condition; renaming
a replay is not a solution. A proof must exercise changed Solver and Reviewer views and
preserve all evidence. Four rows establish engineering only, never effectiveness.

## Authoritative local artifacts

DATA means /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data.

| Artifact under DATA | SHA-256 |
| --- | --- |
| coordination/slurp-candidate-slot-view-proof4-v1/root-closure-v1.json | 4348d68adfb9527d4bb92715cc66cb25b9febd598cda5495a1b44716a655bdde |
| coordination/slurp-candidate-slot-view-proof4-v1/worker-terminal-v1.json | 2e84618578fce1b9b21e58bd4704c1c04529b3b59393ed8e1129b515c017bc10 |
| attempts/SAEA-SLURP-CANDIDATE-SLOT-VIEW-PROOF4-V1/attempt-slurp-candidate-slot-view-proof4-generation-v1.json | 7440804b4a63ec93f23da825edd6b6d3fb59e341a2b442d584affaab6f327946 |
| prepared/SAEA-SLURP-CANDIDATE-SLOT-VIEW-PROOF4-V1/phase-supply-v3.json | 7ae22c4f29af17702e51e58e8d73d46246734d3b4fc4f2b897e43cde35fbcdd0 |

The preparation output hash is 512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733.
Do not publish raw logs, transcripts, credentials or the archived flight-lock contents.
The handoff manifest binds safe closure metadata rather than copying raw traces into Git.
