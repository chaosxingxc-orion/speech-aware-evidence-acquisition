# R1 re-plan: sampled reproduction plan (PROPOSAL — owner decision pending)

Status: PROPOSAL, 2026-08-07. This document turns the R0.1 survey verdict
into an executable, sampled reproduction plan. It is evidence-derived input
to the owner's pending R1 re-plan decision (HANDOVER.md options 1–4); nothing
here is authorized to run until the owner lands a dated decision record (like
`SAEA-OWNER-AMENDMENT-2026-08-06-BUDGET-CAPS`) and each step's
`contracts.ExecutionPlan` + exposure pre-registration exists. Scope
reduction accepted from the operator: **we reproduce claimed improvements on
sampled subsets, never the papers' full-scale experiments.**

## What "reproduce the claimed improvement" means — three different things

The R0.1 survey (groups 1+2, artifact hunt, mechanism map) forces a
three-way split; conflating these would repeat the mistake framing rule 6
warns about:

1. **Literal reproduction (same model, same protocol, published number).**
   Available exactly once in the entire surveyed literature: Audio2Tool's
   introductory baseline row for Qwen-3-Omni-30B (Tier1 92.4 → Tier3 74.7 →
   Tier8 41.7, deterministic metrics, prompt-only). Reproducing it under our
   GGUF/llama.cpp runtime is a pipeline + quantization-drift calibration
   with zero method-interpretation risk. This is HANDOVER option 2 in its
   strongest form.
2. **Mechanism-delta transfer (their conditions, our core).** The
   "claimed improvement" of every boundary-compatible method line is a
   *delta between conditions*, not an absolute number: Siskos no-context
   35.9 → context 31.1 WER; BBA direct 66 vs cascade ~92; AIR-Bench SLURP-IC
   direct 77.8 vs cascade 87.7; VoiceAgentBench zero-shot → one-shot
   +10–17pp; WCN-ICL 1-best → WCN+1-shot closes 81% of the oracle gap.
   Re-running the *conditions* on our frozen core reproduces the
   **direction and effect size**, never their absolute numbers (different
   backbone). These must be recorded as mechanism-delta transfers, not
   reproductions.
3. **Not reproducible under boundary, by definition.** Every trained-method
   line (UniverSLU, WHISMA, prefix-tuned SLU, SpeechDPR/SpeechRAG, trained
   extractors/summarizers, FlexCTC/TurboBias). Reimplementing them means
   training. Excluded outright; they stay in the structural-gap bucket.

Sampling is statistically sufficient because every targeted delta is large
(4.8 WER pts … 26 acc pts) and every design is **paired** (same items, both
arms): 150–400 items per experiment yields ample power (McNemar /
utterance-bootstrap). All runs are discovery/dev-split only; nothing here
can support a confirmatory claim.

## Compliance constraints designed in from the start

- **No gold in runtime.** Siskos's oracle condition derives keywords from
  reference transcripts — banned here. Replacement: ConEC's *real* context
  materials (slides / press releases / participant lists, on disk, from
  `huangruizhe/ConEC` lineage) serve as the correct-evidence arm;
  another call's materials serve as the mismatched arm. Gold transcripts
  are used only scorer-side, on discovery/dev splits.
- **Zero paid API.** No GPT-4o-mini / GPT-4 / Claude judges. Scoring is
  deterministic wherever the carrier allows (Audio2Tool EM/slot-F1;
  AIR-Bench IC closed label set; BBA short answers; VoiceBench MCQ/rule
  tier; WER/E-WER via the frozen scoring package) and otherwise a pinned
  local open judge (VoiceAssistant-Eval's gpt-oss-20b precedent), logged as
  a tool-level component with no answer authority.
- **Per-touch discipline.** Each P1/P2 step needs: profile
  (`baseline-reproduction` for P1, `bounded-discovery-probe` for P2/P3),
  structured ExecutionPlan (split role/identity hash, planned calls/audio
  seconds/GPU hours, protocol hash, exposure pre-registration), and an
  exposure-ledger row before results are read. R0.3 (`SAEA-E-001`) remains
  the first model touch and remains unauthorized today.
- **Success criteria pre-registered** before any result is read; one-shot
  attempt semantics per the consolidated contract.

## The four-construct abstraction frame (owner alignment, 2026-08-07)

The probes are not a flat list of paper deltas; each exercises one or more
of four study-facing constructs, which sit on top of the contract's
OBS/ORG/SUPPLY/USE axes as the working vocabulary for what is being built
and measured:

1. **Agent construction（智能体构建）** — how the inference-time agent is
   assembled around the frozen core: prompt scaffolds, pass structure
   (direct / self-cascade / multi-pass), routing policy, tool wiring,
   output contracts. Primarily OBS plus the control plane itself.
2. **Knowledge construction（知识构建）** — building and organizing the
   evidence store independent of any single query: context materials →
   biasing lists (ConEC), tool-schema registries, exemplar banks,
   retrieval indexes. Primarily ORG.
3. **Knowledge use（知识使用）** — delivering and consuming knowledge at
   inference time: evidence injection and dose control, schema supply,
   uncertainty/n-best surfacing, retrieval-grounded correction. Primarily
   SUPPLY + USE.
4. **Knowledge-utilization-driven agent optimization（基于知识利用优化智能
   体性能）** — the closed loop: measure whether and how supplied knowledge
   changed the answer (per-entity-class deltas, dose–response, attribution),
   then adapt the agent — routing between direct and mediated paths, dose
   selection, re-ask policies — with zero parameter training. Cross-axis;
   this is the study's contribution space (mechanism-map bucket 3) and the
   X probes' target.

Probe ↔ construct map:

| probe | constructs exercised | published anchor it calibrates against |
|---|---|---|
| P1/R1 | 1 (single-pass agent) | Audio2Tool Qwen-3-Omni-30B tier rows |
| R2, R3 | 1 (pass structure: direct vs self-cascade) | BBA 66→~92; AIR-Bench 77.8→87.7 |
| R4 | 2 (materials→evidence prep) + 3 (dose control) | Siskos 35.9→31.1→29.7 |
| R5 | 2 (exemplar bank) + 3 (exemplar use) | VAB one-shot +10–17pp |
| R6 | 3 (retrieval-grounded correction) | RECOVER 8–46% rel E-WER |
| R7 | 3 (uncertainty surfacing) | WCN-ICL 81% gap closure |
| P3/T-series | 2 + 3 (training-free analogs of trained knowledge components) | each analog's trained published row |
| P4 fold-back → X probes | 4 (the optimization loop over 1–3) | — (un-preceded territory) |

## The plan

### P0 — model-free preparation (no authorization beyond normal docs/code work)

1. Reimplement Audio2Tool's three metrics (Tool Accuracy, Exact Match,
   Slot-F1) as a standalone deterministic scorer; unit-test against worked
   examples from the paper text; freeze in the study's scoring surface.
   (Official eval scripts are unreleased — placeholder repo; this is the
   accepted reimplementation risk, mitigated by metric simplicity.)
2. Wrap the on-disk SLURP official scorer and the frozen WER/E-WER scorer
   for post-hoc use (owner framing rule 4).
3. Freeze prompt templates per experiment (task prompt, self-cascade
   two-pass prompts, one-shot exemplar, evidence-injection scaffold);
   protocol-hash them.
4. Build sample-identity lists + split-identity hashes for every sampled
   subset below; record power notes (paired designs, target deltas).
   **DONE 2026-08-07** — receipts under `docs/receipts/probe-samples/`:
   R1 400 items/8 tiers (`e1d751e6…`), R2 200/4 categories (`c602bd7e…`),
   R5 140 EN-complex (parallel 50 original_english + multi_turn 50 english
   + seqdep_tool 40 english, whole stratum; `7205f865…`). R4 starts from
   the frozen dev subset10 identity; R3 blocked on data acquisition.
   **Sample-once policy (owner alignment 2026-08-07): sampling is unified
   through the probe manifest** — `configs/probes/manifest.json` binds every
   probe to its verified receipt (split hash recomputed fail-closed at
   manifest build); each carrier is sampled exactly once and every later
   experiment on that carrier resolves items through this binding, never a
   fresh draw; new carriers (e.g. T-series) enter by the same script +
   manifest regeneration. Manifest anchor after binding: `c5130274…`
   (LF-byte discipline enforced by test).
5. Verify the local judge candidate (gpt-oss-20b) runs under the WSL2 stack
   if any non-deterministic scoring is retained; pin weights hash.

### P1 — literal same-model protocol reproduction (Audio2Tool) — first model touch after authorization

- Sample: 50 items × 8 tiers = 400 items, stratified, pre-registered.
- Arms: 1 (direct prompting with full tool schema, per paper protocol).
- Metrics: the P0-reimplemented deterministic trio.
- Pre-registered success: (i) tier rank-order preserved (the published
  92.4 → 74.7 → 41.7 monotone structure); (ii) per-tier |Δ| ≤ 5pp vs
  published Qwen-3-Omni-30B numbers; a miss is itself a finding
  (quantization/runtime drift or prompt-fidelity gap — the paper's exact
  prompts may differ until their code release; recorded as the known
  fidelity risk).
- Checkpoint: if P1 fails badly, stop and fix the pipeline before any
  mechanism work; if it passes, the pipeline is calibrated against a
  published same-model number.

### P2 — mechanism-delta transfers (priority order; each paired, sampled)

- **P2a. Transcript self-mediation (cascade vs direct).** BBA: 200/1000
  stratified over the 4 BBH categories; AIR-Bench SLURP-IC: 200/1k. Two
  arms each: direct audio answer vs self-cascade (core transcribes, then
  answers from its own transcript; no second LLM). Deterministic scoring.
  Success: cascade > direct, paired-significant; published deltas are
  +26pt (BBA, cross-model) and +9.9pt (AIR-Bench). Rationale for priority:
  the mechanism map's strongest multi-carrier signal, cheapest to run
  (~800 calls total), and it directly instantiates an OBS/USE-axis arm.
- **P2b. Evidence-injection dose-response (Siskos-style) + degradation
  ladder (HANDOVER option 3), merged.** Carrier: conec/e21 sampled calls
  (candidate start: the already-enumerated e22 subset10 identity, dev
  role, from the E0 closure — extended with an e21 sample if the owner
  agrees). Three arms: no-context / matched ConEC materials / mismatched
  materials. Metric: WER + per-entity-class WER via the frozen scorer.
  Success: monotone movement with evidence quality (Siskos direction),
  which simultaneously proves metric sensitivity — option 3's purpose.
- **P2c. One-shot exemplar prompting (VoiceAgentBench).** 150 EN
  complex-task items (seqdep/multi-turn strata), zero-shot vs one-shot,
  deterministic Tool-Selection/structure metrics (PF semantics via pinned
  local judge only if unavoidable). Success: positive delta; published
  claim +10–17pp.
- **P2d (conditional, only if P2a/P2b are positive).** RECOVER-style
  retrieval-grounded entity correction on e21 (labeled RECOVER-*style*:
  unreviewed preprint, no artifact, real interpretation risk); sampled
  n-best-in-prompt (WCN-ICL analog — sampled hypotheses, since a chat
  endpoint exposes no lattice).

### P3 — training-free analog track (T-series; owner alignment 2026-08-07)

For reference works classified "cannot reproduce" because their knowledge
component is *trained*, we do not stop at the structural-gap record: we
design a **training-free analog** under our boundary — same carrier, same
scorer, modern frozen model selection (our core as the sole answering
model; pinned deterministic tool-level retrievers allowed per contract) —
and test whether the analog reaches, tracks, or beats the published
trained number. Constructs 2+3 territory. Gated post-P2 (each is a
`bounded-discovery-probe` with its own ExecutionPlan); carriers not yet
sampled enter through the sample-once manifest process first.

| id | trained reference (published row) | training-free analog design | comparability caveat |
|---|---|---|---|
| T1 | SpeechDPR (slue-sqa-5): Top-20 19.73, OpenSQA frame-F1 0.558 — trained speech bi-encoder | core transcribes question + a pre-registered bounded document pool; pinned lexical retriever (BM25) over core transcripts; core answers from retrieved doc | bounded pool ≠ their full-corpus retrieval — published row is a direction reference, not an equal-footing target; new sample receipt required |
| T2 | SpeechRAG (spoken-squad): claim "speech retrieval does not degrade vs text" — trained speech retriever/adapter | passage retrieval over core-transcribed spoken passages (pinned BM25/embedder as tool); arms: closed-book / retrieved / oracle-passage — doubles as Family C's missing SUPPLY-sensitivity ladder | claim-level comparison (degrade-or-not), not number-level; new sample receipt required |
| T3 | zero-shot SLURP slot filling line (ZS-Whisper-SLU 50.0 → WHISMA 63.3 SLU-F1 — all trained adapters) | prompt-only slot filling on SLURP with the on-disk official scorer — the literature's first zero-training number on this carrier | same carrier + official scorer → directly positionable against the published zero-shot line; new sample receipt required |
| T4 | FlexCTC/TurboBias (earnings21): decoder-level bias-phrase boosting | prompt-level bias-list injection using ConEC's shipped biasing lists — implemented as the entity-class-scoped extension of R4, not a separate probe | mechanism analog only; decode-score-level recall numbers are not reproducible by construction |

Success framing per analog: (i) direction/claim reproduced or refuted under
our boundary; (ii) gap to the trained published row quantified — a small
gap is evidence that training was not the load-bearing ingredient, a large
gap is sharpened structural-gap evidence. Either outcome feeds construct 4.

### P4 — fold-back

Consolidate P1/P2/P3 outcomes into the R1 decision record: which deltas
transferred, which analogs closed their gaps, calibrated pipeline receipts —
the evidence base for freezing R1 (or formally replacing it with
protocol-reproduction + ladder, HANDOVER options 2+3) and for designing the
X-probe arms (construct 4) from bucket-1 mechanisms plus the analog results.

## Explicit non-goals

No trained-method reimplementation; no absolute-number chasing across
different backbones; no full test sets; no confirmatory splits; no paid
judges; no new carrier *acquisitions* (T-series uses already-held carriers;
R3's acquisition is a separate owner decision). P2d and the T-series stay
out unless the earlier steps earn them.

## Decision points for the owner

1. Land the R1 re-plan decision record (this plan = concrete form of
   options 2+3; options 1/4 remain open).
2. Approve the ConEC-materials replacement for Siskos's oracle arm (gold
   stays out of runtime) — or grant a scoped allowance.
3. Resolve the Audio2Tool license contradiction (paper CC-BY-4.0 vs disk
   CC-BY-NC-4.0) before its data drives any recorded result.
4. Confirm sampled-subset identities (P0.4) and the e22-subset10 reuse in
   P2b; when the T-series is reached, approve the T1/T2/T3 sample receipts
   (slue-sqa-5, spoken-squad, slurp) added through the same sample-once
   manifest process.
5. Authorize P1 as the first model touch (supersedes/absorbs the R0.3
   `SAEA-E-001` slot or schedules after it — owner's call).
6. **P0 finding (2026-08-07): the AIR-Bench SLURP-IC subset is not on disk**
   — R3 is blocked until the asset enters via the umbrella's formal
   acquisition path (`docs/datasets.lock.json` + fetch scripts;
   distribution channel is a GitHub-issue link, itself a weak-channel flag).
   R2 (Big Bench Audio, on disk) carries the cascade-vs-direct probe until
   then; the probe manifest marks R3 `BLOCKED`.
