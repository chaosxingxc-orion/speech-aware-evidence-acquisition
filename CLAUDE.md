# CLAUDE.md — speech-aware-evidence-acquisition

Standalone research repository: speech-aware evidence acquisition on a frozen speech-capable omni
core. The object of study is a reward-guided control plane built outside an API-only frozen core
that separately controls speech observation (OBS), knowledge organization (ORG), evidence supply
(SUPPLY), and evidence use (USE), raising speech-domain task capability reliably without changing
parameters or internal structure.

## First principles

These override every other convention in this repository; the umbrella `CLAUDE.md` carries the
full statement.

1. **English before the model.** Everything that enters a model context must be English — owner
   instructions, transcripts, log lines, review comments, dataset cards, pasted files, tool
   output. Translate non-English sources to English first and pass the translation, never the
   original; keep the source addressable so the translation stays auditable, and never drop
   content while translating.
2. **English-only documents.** Every document this repository authors is written in English:
   root Markdown, `docs/`, readiness notes, exposure ledger entries, code comments and
   docstrings, and review submissions. Non-English text in a mutable document is a defect;
   repair it the next time that file is touched. Immutable records and hash-pinned bytes are
   never rewritten in place — supersede them with an English successor instead.
3. **Conventions are executable English.** Rules are stated in English, in the imperative, and
   are preferably enforced by a check rather than by prose alone.

## Research boundary (immutable)

- Human speech and its linguistic content only: ASR, entities, contextual biasing, spoken QA,
  meeting speech understanding.
- WAV/MP3 are carriers of the speech signal; general/environmental audio tasks are out of scope.
  FSD50K, AudioSet, and ESC-50 must never be consumed by this repository's loaders, tests, or
  configs.
- The frozen Qwen3-Omni core is reached only across an API-shaped service boundary; zero-parameter
  training; no task-trained model; no second answering LLM.
- Gold labels, reference transcripts, test annotations, and future turns must never enter runtime;
  discovery and confirmatory stay isolated.
- OBS/ORG/SUPPLY/USE are traced separately; external responses, tool actions, model requests, and
  derivatives are all versioned and hashable.
- A frozen tool-level retriever/judge is allowed only when pinned and logged; final answer
  authority stays with the frozen core.

## Authorization and sequence

This repository is the **Stage-2 study carrier** (umbrella Decision-Log continuation entries
91/92): it ends at one or more qualified paper candidates, not at a finished paper. The only
self-contained contract in force is umbrella
`wiki/experiments/speech-aware-evidence-acquisition/2026-08-04-owner-consolidated-execution-contract.md`;
the entry sequence is umbrella
`docs/superpowers/specs/2026-08-02-speech-aware-evidence-acquisition-stage2a-entry.md`.
The 2026-08-15 owner amendment (umbrella
`wiki/experiments/speech-aware-evidence-acquisition/2026-08-15-owner-go-dual-track-agentic.md`)
approves a single bounded Audio2Tool leverage probe (probe-scoped; the claim surface is unchanged)
and admits SLURP slot-SLU through the entity clause.
Execution profiles accept only `model-free-check` / `baseline-reproduction` /
`bounded-discovery-probe` (`contracts.assert_execution_scope`, fail-closed). Every model contact
must carry a structured `contracts.ExecutionPlan` (split role, split identity hash, budget cap,
protocol hash, exposure pre-registration binding); confirmatory splits and over-budget plans are
rejected without exception.
Before the first model contact, close E0 D1–D4 and land a runtime receipt carrying the llama.cpp
build commit plus per-file GGUF SHA-256. Record every model or tool contact in
`docs/exposure-ledger.md` before reading its result.

## Routing

- Current state: umbrella `wiki/Research-Objective.md`. Experiment ledger:
  `wiki/experiments/speech-aware-evidence-acquisition/README.md`.
- The single live source of dataset identity is umbrella `docs/datasets.lock.json`. Core keys are
  `earnings21-original`, `earnings22-original`, `conec`, and
  `qwen3-omni-30b-a3b-instruct-gguf`; never copy revisions or hashes out of it.
- Large bytes live under `SPEECHRL_DATA_DIR` and never enter Git. D0 receipt:
  `docs/checks/speech-aware-evidence-acquisition/2026-08-02-acquisition/`.
- W1–W4 code enters this repository only through the `docs/migration-manifest.md`
  copy-and-verify registration.

## Environment and checks

- WSL2 `Ubuntu-24.04`; Python 3.12 in `~/.venvs/speechrl`.
- Install: `uv pip install -e ".[dev]"`. Test: `pytest`.
- Hot paths run on Linux-native ext4, never on `/mnt/*` (9p): feature packets, caches, re-pin/flip loops and any git-heavy tooling run from an ext4 worktree or ext4 data path; the `/mnt/d` master is the single writer and takes only fast-forwards from `scripts/flights/batch/flip_in_ext4.sh` (owner 2026-10-12; measured 38 s vs 0.8 s per CLI import, 7.6 s vs 0.4 s per git status).
- Offline gates: `python scripts/checks/engineering_base_check.py`,
  `harness_admission_check.py`, `results_ledger_check.py`, `tool_catalog_check.py`,
  `experiment_handoff_check.py`, `openjiuwen_native_reuse_check.py`,
  `derived_media_confinement_check.py`, `stage3_algorithm_label_check.py` (owner decision 101:
  every Stage-3 cell carries a `stage3_algorithm` label resolving in `core.base.STAGE3_ALGORITHMS`),
  and
  `finite_completion_policy_check.py` -- every live, unflown native cell must declare
  BOTH `native_episode.finite_completion_policy` as `"deliver-latest-or-abstain"` (item E13;
  the B7a recovery arm lost 1,451 contacts to the parser default `"raise"`) and
  `native_episode.react_exhaustion_policy` as `"continue-without-answer"` (item E22, the
  ReAct-exhaustion disposition, not the Earnings-22 carrier; the B8b-anchor arm lost 2,016
  contacts to the same default).
- Exposure-ledger closure gate (2026-10-11): `ledger_consumed_check.py` fails when a flight sealed on disk still has
  its ledger row at `consumed = no`; close rows with `scripts/flights/batch/ledger_mark_consumed.py --apply`
  (data-root mode is the gate; the results-notes fallback used when the data root is absent is advisory).
- Stage-3 measurement gates (2026-09-26): `stage3_effect_floor_check.py` refuses a cell whose
  declared `stage3_measurement` block is missing, whose design is a cross-flight contrast without an
  in-chain A/A replicate, or whose expected effect sits under the measured floor of its design
  (`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`); a batch under 200 rows is
  a form proof and must not claim benefit. `handoff_freshness_check.py` fails when a result or a
  results-ledger entry is newer than the refresh stamp of `docs/handoff/HANDOFF-TO-CHATGPT.md`.
- Inference: llama.cpp llama-server. Reproduction entry point: `bash scripts/reproduce.sh`
  (active from R0 onward).
- This repository currently declares no `speechrl_common` dependency; first consumption must pin
  exactly as the migration manifest requires.

## Prohibited

- **Paper-scale work**: the `paper-scale-confirmatory` profile, production-scale method
  implementations, large-scale confirmatory campaigns, final superiority or generalization
  conclusions, and manuscript/submission/publication. These belong to Stage-3 and must be promoted
  through `OWNER_GO_AND_PAPER_EXECUTION_CONTRACT` into a standalone `papers/<slug>` repository;
  this repository never accepts them (machine-enforced: `contracts.assert_execution_scope`).
- Paid API spend (= 0, still in force). The numeric budget caps (formerly ≤3000 calls / ≤40 GPU-h
  / ≤20h audio) were retired by the 2026-08-06 owner amendment and must not be reintroduced
  unilaterally by the implementer; exposure pre-registration and one-shot attempt semantics remain
  mandatory.
- Committing data, weights, speech files, or raw traces; moving code in around the migration
  manifest.
- Writing candidate IDs such as R2 into package names, MLflow namespaces, or formal experiment IDs.
- Publishing a wiki mirror or a public release without owner authorization.

## Engineering base and experiment rules (owner, 2026-09-03)

Owner directives of 2026-09-03 (recovery plan after the September Audio2Tool sprint); they
restate the 2026-08-23 rulings and are enforced by `scripts/checks/engineering_base_check.py`.

- **One base, thin derivations.** `rails.task_adapter.TaskAdapter`, `rails.knowledge_provider.
  KnowledgeProvider`, `rails.controllers.EvidenceAgentController`, and `core.flight.FlightRuntime`
  are the bases; a carrier adds one `data.carriers` descriptor, one adapter under
  `rails/adapters/`, one scorer registration, and config fragments. No new module under
  `rails/probes/`, no `TaskAdapter` or controller subclass elsewhere, no `launcher/` directory
  under `docs/checks/`. Every `policy`, `evidence_source`, and `scorers` value in `configs/`
  must resolve in a `core.base` registry.
- **Same harness for every arm.** The direct baseline is the `direct-only` phase program of the
  shared controller through the same `FlightRuntime` and the same OpenJiuwen executor; a
  separate code path for a baseline is a defect.
- **Standard scoring.** The paper-facing number comes from the dataset's standard scorer
  (SLURP official `evaluate.py` from the pinned local clone; Audio2Tool `a2t-toolcall`
  calibrated to arXiv:2604.22821 Table 3; Earnings WER with the Whisper normalizer beside
  `saea-scoring-v1`), run once per complete manifest through `core.scoring_batch`, never sharded.
- **Carriers.** Locked to Earnings21+ConEC, SLURP, Audio2Tool until the owner expands the set.
- **Power and rosters.** Paired effectiveness claims need n >= 400 (Audio2Tool frozen 400 split,
  SLURP DEV-500 or larger, Earnings full discovery). No fixed-8/12/16 screens. Replicate on the
  same roster before drawing a fresh one; report natural-mixture and equal-stratum weightings.
- **Iteration.** One experiment in flight. A new mechanism is admitted only after its predecessor
  is replicated or root-caused to a named component. At most one recovery re-registration per
  flight; a second failure stops the flight and the fix is proven on a 4-row dry run.
- **Reporting.** Every verdict carries the per-stratum table; Audio2Tool tables carry the paper
  column beside the repo column. Gates are set relative to the published ceiling, never above it.
- **Pipeline.** CPU packet preprocessing runs in parallel (20 workers idle, 8 during a campaign)
  and overlaps model load; one resident server per serving geometry; ready flights are queued by
  geometry so the GPU never idles; official scoring overlaps the next flight.
