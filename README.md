# audio-aware-evidence-acquisition

Reward-guided, training-free audio-aware evidence acquisition over a frozen speech/omni core
(API-only). An external control plane decides between audio re-resolution (OBS) and external
evidence supply (SUPPLY), and controls admission/ordering/use of evidence, without modifying model
parameters or adding a second answering LLM.

- Governance, experiment ledger and data identity live in the umbrella repository
  (`exploring-l4-intelligence`): see `wiki/experiments/audio-aware-evidence-acquisition/README.md`
  and `docs/datasets.lock.json` there.
- Execution authority: owner GO and execution contract, 2026-08-03 (see umbrella
  `wiki/experiments/audio-aware-evidence-acquisition/2026-08-03-owner-go-and-execution-contract.md`).
- Stage-1C source provenance: candidate R2 of campaign `system-first-stage1c-v2` (provenance only;
  not an engineering identity).

## Layout

```text
src/audio_aware_evidence_acquisition/
  data/         lock-key based carrier loaders; no dataset bytes
  models/       frozen-core API adapter (llama.cpp llama-server)
  evidence/     evidence schema, provenance, OBS/SUPPLY separation, admission
  scoring/      registered metrics and scorer adapters
  tracing/      request/tool/response/cost trace
  experiments/  experiment composition, not raw outputs
configs/        model / dataset / baseline / experiment composition
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

This repository currently has **no dependency on `speechrl_common`** (nothing in `src/` imports
it). If a module is ever consumed, it enters via the pin policy in
`docs/migration-manifest.md`: exact umbrella commit pin + `uv.lock`; `../../common` editable
installs are a local development override only.
