# speech-aware-evidence-acquisition

Reward-guided, training-free evidence acquisition for speech-domain tasks over a frozen,
speech-capable omni core (API-only). The external control plane separates four interventions:
speech observation (`OBS`), knowledge organization (`ORG`), evidence supply (`SUPPLY`) and evidence
use/control (`USE`). It modifies no model parameter and adds no second answering LLM.

This is a **speech-only** study. WAV/MP3 files may carry speech signals, but environmental/general
audio classification and QA are outside scope. FSD50K, AudioSet and ESC-50 remain governed local
assets in the umbrella lock and are never loaded by this repository.

- Governance, experiment ledger and data identity live in the umbrella repository
  (`exploring-l4-intelligence`): see
  `wiki/experiments/speech-aware-evidence-acquisition/README.md` and `docs/datasets.lock.json`.
- Current execution authority: the single self-contained consolidated owner contract, 2026-08-04
  (`wiki/experiments/speech-aware-evidence-acquisition/2026-08-04-owner-consolidated-execution-contract.md`).
- **Stage boundary (umbrella Decision-Log 续91/续92):** this is a Stage-2 study carrier. Its
  endpoint is one or more qualified paper candidates. Production-scale confirmatory campaigns,
  final superiority claims, manuscripts and publication belong to a separately admitted
  `papers/<slug>` repository via `OWNER_GO_AND_PAPER_EXECUTION_CONTRACT` — this repository never
  accepts a `paper-scale-confirmatory` execution profile
  (fail-closed: `contracts.assert_execution_scope`).
- Stage-1C source provenance: candidate R2 of campaign `system-first-stage1c-v2` (audit provenance
  only, never an engineering identity).

## Layout

```text
src/speech_aware_evidence_acquisition/
  contracts.py  fail-closed E0 engineering contracts: information boundary,
                OBS/ORG/SUPPLY/USE trace separation, exposure-claim schema,
                Stage-2 execution-scope guard + ExecutionPlan, carrier/
                general-audio denylist, frozen-core entry gate
                (FrozenCoreGate) -- load-bearing, referenced throughout
                docs/engineering.md
  core/         ONE foundation package (owner direction 2026-08-05):
                  base.py       Registry mechanism (CARRIERS, EVIDENCE_SOURCES,
                                 TRANSPORTS, POLICIES, SCORERS seams) + core errors
                  model.py      FrozenCoreAdapter: gate-bound request path
                  session.py    runtime session attestation (process/socket binding)
                  carriers.py   registered speech-carrier loaders
                  evidence.py   ORG/SUPPLY/USE schema, provenance and admission
                  tracing.py    OBS/ORG/SUPPLY/USE trace sink (append-only)
                  policies.py   arm policies (only `fixed` implemented at R0)
                  scorers.py    registered scoring adapters (only scoring-side
                                 reference importer)
                  attempts.py   one-time attempt accounting / state machine
                  bundle.py     atomic run bundle + finalizer (verify -> score ->
                                 re-verify -> upload -> ledger row -> FINALIZED)
                  driver.py     single experiment driver + CLI (`saea-driver`)
                  resources.py  injectable GPU/CPU cost-sampling seam (I8)
                  tracking.py   lazy MLflow linkage + umbrella ledger-row renderer
                  config.py     deterministic four-fragment JSON config composer
                  split_receipt.py  split-identity receipt binding
  data/         lock-key based speech-carrier loaders and splits; no dataset bytes
                  identity.py     cross-layer sample/segment identity (E0 D1)
                  lock.py         umbrella-lock resolution: the only live
                                   authority for asset identity
                  loader.py       deterministic, boundary-safe carrier sample
                                   loading (never reads transcript/context content)
                  splits.py       frozen discovery/dev/confirmatory partitions
                  references.py   scoring-side reference reader (only
                                   core/scorers.py may import it; AST-enforced)
  scoring/      frozen scoring stack: wer.py, entity.py, qa.py, normalize.py,
                transitions.py (hash-pinned by the D3 E0 closure receipt)
  e0/           E0 model-free closure generators (D1-D4 + runtime receipt;
                CLOSED 2026-08-04, out of scope for further edits this campaign)
configs/        model / speech dataset / baseline / experiment composition (JSON
                fragments only, see configs/baseline/README.md)
scripts/        reproduce.sh, evaluate.sh
tests/          unit / integration / contract
docs/           engineering.md, migration-manifest.md, exposure-ledger.md
```

## Setup

```bash
# WSL2 Ubuntu-24.04, ~/.venvs/speechrl (Python 3.12)
uv pip install -e ".[dev]"
pytest
```

This repository currently has no dependency on `speechrl_common`. If shared code is later consumed,
it enters through `docs/migration-manifest.md`: exact umbrella commit pin plus `uv.lock`;
`../../common` editable installs are a local development override only.
