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
  data/         lock-key based speech-carrier loaders; no dataset bytes
  models/       frozen-core API adapter (llama.cpp llama-server)
  evidence/     ORG/SUPPLY/USE schema, provenance and admission
  scoring/      registered task, entity, evidence and cost metrics
  tracing/      OBS/ORG/SUPPLY/USE plus request/tool/response/cost trace
  experiments/  experiment composition, not raw outputs
configs/        model / speech dataset / baseline / experiment composition
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
