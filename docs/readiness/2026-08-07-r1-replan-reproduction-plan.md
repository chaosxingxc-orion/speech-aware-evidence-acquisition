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

### P3 — fold-back

Consolidate P1/P2 outcomes into the R1 decision record: which deltas
transferred, which didn't, calibrated pipeline receipts — the evidence base
for freezing R1 (or formally replacing it with protocol-reproduction +
ladder, HANDOVER options 2+3) and for designing the X-probe arms from
bucket-1 mechanisms.

## Explicit non-goals

No trained-method reimplementation; no absolute-number chasing across
different backbones; no full test sets; no confirmatory splits; no paid
judges; no new carriers. P2d and anything beyond stays out unless the
earlier steps earn it.

## Decision points for the owner

1. Land the R1 re-plan decision record (this plan = concrete form of
   options 2+3; options 1/4 remain open).
2. Approve the ConEC-materials replacement for Siskos's oracle arm (gold
   stays out of runtime) — or grant a scoped allowance.
3. Resolve the Audio2Tool license contradiction (paper CC-BY-4.0 vs disk
   CC-BY-NC-4.0) before its data drives any recorded result.
4. Confirm sampled-subset identities (P0.4) and the e22-subset10 reuse in
   P2b.
5. Authorize P1 as the first model touch (supersedes/absorbs the R0.3
   `SAEA-E-001` slot or schedules after it — owner's call).
6. **P0 finding (2026-08-07): the AIR-Bench SLURP-IC subset is not on disk**
   — R3 is blocked until the asset enters via the umbrella's formal
   acquisition path (`docs/datasets.lock.json` + fetch scripts;
   distribution channel is a GitHub-issue link, itself a weak-channel flag).
   R2 (Big Bench Audio, on disk) carries the cascade-vs-direct probe until
   then; the probe manifest marks R3 `BLOCKED`.
