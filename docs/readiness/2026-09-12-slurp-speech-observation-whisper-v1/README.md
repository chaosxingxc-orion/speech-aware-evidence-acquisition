# SLURP cached Whisper treatment configuration template

These templates freeze the matched treatment while the registered Whisper recovery is pending. They stay outside configs because the catalog SHA-256 is the sole unresolved configuration binding and the shared loader must reject the placeholder.

The recovery producer identities are final:

- run: SAEA-SLURP-WHISPER-OBSERVATIONS-RECOVERY-V1
- attempt: attempt-slurp-whisper-observations-recovery-v1
- catalog ID: slurp-dev1000-whisper-large-v3-full-utterance-recovery-v1
- catalog relpath: prepared/SAEA-SLURP-WHISPER-OBSERVATIONS-RECOVERY-V1/attempt-slurp-whisper-observations-recovery-v1/catalog.json

The original preparation aborted after eight charged contacts and produced no catalog. Those contacts remain counted under its original registration. Recovery contacts remain counted under the recovery registration. Both preparations are outside the paired Qwen family caps. Never bind an artifact from the aborted attempt.

## Compatibility checks after the recovery seals

Before materializing the templates, hash the catalog as a stable file. Require its schema and catalog ID, recovery producer run and attempt IDs, DEV-1000 split identity, 1,000 unique observations, and complete source-bound roster. The shared catalog loader must validate its execution-plan pin, protocol hash, exposure-ledger row, finalized attempt, audio-source bindings and observation artifact hashes.

After materialization, compose through the shared registry. Compare the treatment with the control across every retained field listed in audit-checklist.json. Only the recovery preparation metadata, prepared observation pin, fixed solve OBS action, treatment identities, purpose and readiness prose may differ. The treatment remains preparation-pending.

## Root-only materialization after catalog seal

Use the literal WSL checkout and no editable install. This command performs no model or speech-tool contact. It refuses to overwrite an existing final config.

~~~bash
TREATMENT_REPO=/home/chao/saea-worktrees/slurp-speech-tool-treatment-prepare-v1
SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
CATALOG_REL=prepared/SAEA-SLURP-WHISPER-OBSERVATIONS-RECOVERY-V1/attempt-slurp-whisper-observations-recovery-v1/catalog.json
CATALOG_PATH="$SPEECHRL_DATA_DIR/$CATALOG_REL"
PYTHON=/home/chao/.venvs/speechrl/bin/python
export TREATMENT_REPO SPEECHRL_DATA_DIR CATALOG_REL CATALOG_PATH PYTHON
export PYTHONPATH="$TREATMENT_REPO/src"
export PYTHONDONTWRITEBYTECODE=1

"$PYTHON" - <<'PY'
import hashlib
import json
import os
from pathlib import Path

repo = Path(os.environ["TREATMENT_REPO"])
catalog_path = Path(os.environ["CATALOG_PATH"])
catalog_rel = os.environ["CATALOG_REL"]
catalog_bytes = catalog_path.read_bytes()
catalog_sha = hashlib.sha256(catalog_bytes).hexdigest()
catalog = json.loads(catalog_bytes)

assert catalog["schema"] == "saea-prepared-speech-observation-catalog-v1"
assert catalog["catalog_id"] == "slurp-dev1000-whisper-large-v3-full-utterance-recovery-v1"
assert catalog["use_split_identity_hash"] == "8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84"
assert catalog["producer"]["run_id"] == "SAEA-SLURP-WHISPER-OBSERVATIONS-RECOVERY-V1"
assert catalog["producer"]["attempt_id"] == "attempt-slurp-whisper-observations-recovery-v1"
observations = catalog["observations"]
assert len(observations) == 1000
assert len({row["sample_id"] for row in observations}) == 1000

template_dir = repo / "docs/readiness/2026-09-12-slurp-speech-observation-whisper-v1"
baseline = json.loads((template_dir / "baseline-template.json").read_text(encoding="utf-8"))
pin = baseline["prepared_speech_observations"]
assert pin == {
    "relpath": catalog_rel,
    "sha256": "UNRESOLVED_UNTIL_RECOVERY_CATALOG_SEALS",
}
pin["sha256"] = catalog_sha
experiment = json.loads((template_dir / "experiment-template.json").read_text(encoding="utf-8"))

outputs = {
    repo / "configs/baseline/slurp-speech-observation-whisper-v1.json": baseline,
    repo / "configs/experiment/slurp-speech-observation-whisper-v1.json": experiment,
}
for path, document in outputs.items():
    with path.open("x", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
print(catalog_sha)
PY
~~~

The shared runtime performs the deeper catalog and roster validation when it composes the treatment. Do not prepare recall if that validation fails.

## Root-only solve recall preparation

Prepare only after the final catalog SHA-256 is in the materialized baseline. This uses the common model-free phase-recall entry point and the frozen solve supply. It must not run through a private launcher.

~~~bash
DATASET_LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
RECALL_DIR="$SPEECHRL_DATA_DIR/prepared/SAEA-SLURP-SPEECH-OBSERVATION-WHISPER-PREPARE-V1"
mkdir -p "$RECALL_DIR"

"$PYTHON" "$TREATMENT_REPO/scripts/flights/run_campaign.py" prepare-phase-recall \
  --repo-root "$TREATMENT_REPO" \
  --data-root "$SPEECHRL_DATA_DIR" \
  --runtime-root /home/chao \
  --lock-path "$DATASET_LOCK" \
  --experiment slurp-speech-observation-whisper-v1 \
  --cell slurp-speech-observation-whisper-v1 \
  --phase solve \
  --workers 20 \
  --output "$RECALL_DIR/recall.json"
~~~

Require 1,000 recall rows. Compare every selected value ID and serialized order with docs/readiness/2026-09-12-slurp-speech-observation-control-recall-equality-v1.json and its retained control artifact. Then insert the returned relpath and SHA-256 as prepared_phase_recall.solve. The catalog pin, OBS action, allowed stages, IDs, budgets, service, decoding, prompts, packets, knowledge and shared implementation must remain unchanged after recall preparation.

Scientific admission, immutable generation and fit registrations, service admission, live-phase fitting, generation and scoring remain root-owned and pending. These files and commands authorize no model, speech tool, tokenizer, GPU or scorer contact.
