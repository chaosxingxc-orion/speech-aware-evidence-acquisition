# Knowledge-plane baseline — owner rulings, coordinator review, and approved plan (2026-08-23)

Date: 2026-08-23. Authority: owner directive (session, 2026-08-23) restating the study goal and
issuing structural rulings, followed the same day by owner approval of the coordinator's
improvement plan containing the corrections below. This document is the durable record; the
approved plan file is session-local and this document supersedes it as the citable source.

## 1. Owner rulings (2026-08-23, recorded verbatim in intent)

1. **Goal restated**: design a general multimodal-agent scheme on the openJiuwen agentloop
   framework; build a complete task-oriented speech agent over the locally available tasks and
   datasets; this becomes the engineering baseline for later large-scale experiments.
   Progressive scale; no test-set tuning; leave workspace for training-free RL.
2. **Knowledge domain focus**: knowledge CONSTRUCTION, knowledge USE, knowledge OPTIMIZATION.
3. **Q-K-V organization**:
   - **Q is locked**: the speech signal is the primary query; agent intermediate products are
     auxiliary only (consistent with the standing speech-carriage prohibition — no
     transcript-only query).
   - **K is multi-dimensional**: content, speaker, label, and further dimensions; a key must be
     computable against Q and add task information gain; a ranking algorithm, strategy, or
     model integrates retrieved results across dimensions.
   - **V is consumed, never embedded**: directly task-helpful payloads; V carries priors and is
     modeled against the TRAIN set, sample-linked.
4. **Construction/use separation (fatal-flaw diagnosis)**: knowledge construction happens at
   scale on TRAIN and must model the main data distribution — dimension-based sampling, not
   per-label-uniform sampling (which loses knowledge when label vocabularies exceed 100).
   Knowledge USE and agent-space optimization happen on DEV; the owner's 100→500→1000 ladder
   is a DEV-side optimization ladder. TEST is touched once, for final reporting only.
5. **Generality**: do not design for one task; the paradigm must bind at least a second task
   (task-specific structures such as the SLU factor graph are cited as the anti-pattern).
6. **GPU discipline (restated)**: keep the GPU as fully loaded as possible; plan GPU tasks and
   CPU tasks as separate queues so the GPU is never wasted.

## 2. Owner-approved corrections (via plan approval, 2026-08-23)

1. **E108 gate decoupling**: the frozen serving requirement (saturated GPU median/P10 ≥ 95/90%)
   is decoupled from scientific admission. Scientific cells fly on the best-known receipt-bound
   profile with utilization reported descriptively; the 95/90 requirement remains the
   ENGINEERING-baseline acceptance criterion, pursued in parallel (the tail work-stealing
   scheduler hypothesis is the next admissible engineering idea). Rationale: seven-plus
   registered engineering cells (np32, q128, global-branch, n-gram, MoE CUDA-graph, cross-slot
   batching, hot-prefix) failed P10 while mean occupancy measured 94–96%; every remedy class
   was formally closed; the blocked state left the GPU idle — the exact waste the gate exists
   to prevent. Any E108 flight still requires its own execution plan, exposure row, and the
   unchanged runtime-integrity checks; this amendment removes only the P10/95 gate from the
   scientific-admission conjunction.
2. **Ladder disambiguation**: the existing train-side discovery tiers are renamed T108 / T500
   (formerly D108 / D500) — they remain train-only discovery surfaces. T500 (360 memory + 140
   speaker-unseen holdout; capacity audit sha256 `5aff61c8…b20a`, feasible) is approved in
   principle as the action-support densification step; its identity freeze and execution
   contract still land as their own registered artifacts. The owner's DEV-100/500/1000 ladder
   is a separate, new governance object: sampled from SLURP devel excluding the reserved
   FINAL60, used ONLY for agent-space optimization (k, α-blend weight, admission thresholds,
   rerank depth, speaker-λ), with gold scoring-side between iterations and never in runtime.
   TEST remains one-touch under a future registered amendment (see §4.4).
3. **Second surface**: the M11 machinery is carried unchanged to Audio2Tool (152 tools; prompt
   enumeration ≈ 12.7k tokens/request) as the structural-headroom surface, and later to the
   earnings21+ConEC entity layer (true external knowledge). Rationale: all five rejected
   controllers were judged on SLURP 18-scenario routing at 89–95/108 primary accuracy with
   oracle headroom 3–8 — near the task ceiling; the binding constraint was the surface, not
   the controller family.

## 3. Design-queue supersession

The 2026-08-19 scoreboard design queue items P-CORR-R, P-TARGET-P1, and P-STRIP-AUG are
formally PARKED (never registered; superseded by this baseline program). They may be revived
only with a fresh registration justified under the Q-K-V frame. The M4-cascade-on-A2T
successor candidate is absorbed into the Audio2Tool surface work (§2.3).

## 4. Coordinator engineering review (2026-08-23) — accepted findings

Verdict: the shared engineering base (rails/knowledge.py contracts, rails/runner.py,
openJiuwen executor) is architecturally sound; four defects are queued as work item C4 and
land BEFORE the first train-scale snapshot is exercised:

1. `assert_agent_step_binding` / `assert_knowledge_use_binding` recompute the full snapshot
   content hash every wave — O(waves × snapshot bytes) at train scale; accept a precomputed
   hash or cache it on the frozen instance.
2. `_assert_agent_control_excludes_knowledge_payloads` re-materializes the protected-material
   tuple per wave; precompute once per run.
3. External governed knowledge (ConEC context documents) is unrepresentable — facet/value
   `source_sample_ids` must currently be task TRAIN samples; admit an `external-governed`
   source role with its own identity hashing, keeping dev/test refusal intact.
4. There is no legal path for the final one-touch TEST report (`use_partition_role` hard-codes
   `dev`); the amendment path is planned now, in writing, and implemented only under a future
   owner-approved final-report contract.

## 5. Approved workstreams (sequenced; GPU/CPU queues per ruling §1.6)

- **GPU queue** (ready-first): E108 under §2.1; KB-BUILD embedding sidecars (GLAP audio keys +
  qwen3-embedding-0.6b text keys, registered); the Audio2Tool cell; meeting-line G2 / SAER-M
  v1.1 re-score; engineering-baseline profile cells in gaps.
- **CPU queue** (fills alongside): C4 scale fixes → C2 DEV-ladder receipts + fail-closed split
  gate (FINAL60/test refusal) → C1 KB-BUILD v1 (distribution-modeled SLURP-train snapshot;
  datastore size as a reported axis 1k/5k/full; coverage report; decontamination vs dev/test
  identity hashes) → C3 first cross-task policy in the empty registries (multi-dim recall →
  weighted rank fusion → percept-keyed supply filter with coverage layer → discrete α-blend
  consumption) → per-modality mean-centering re-analysis of the landed P-EMB-4R vectors
  (model-free; settles whether the 0.13–0.28 audio cosine is a modality-cone artifact).
- Scheduling rule: before starting any CPU batch, verify the GPU queue head is running or
  blocked on an owner decision — never blocked on the implementer.

## 6. Survey grounding

The 2026-08-23 cross-modal retrieval survey (29 items; text / vision-multimodal / speech) is
recorded in `docs/readiness/2026-08-23-cross-modal-retrieval-survey.md`. Its top-ranked
actionable ideas — Tip-Adapter-style α-blend, speaker-smoothed injection strength λ, multi-dim
recall + frozen-core listwise rerank, per-modality mean-centering, MassiveDS datastore hygiene
— are bound into the C1–C3 designs above.
