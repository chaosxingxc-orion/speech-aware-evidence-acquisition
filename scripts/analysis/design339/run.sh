#!/bin/bash
# Model-free reproduction of the 339 bounds (WSL, CPU only; about 10 min in total). Aggregates only.
S=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/analysis/design339
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4
export SPEECHRL_DATA_DIR=/home/chao/saea-data/speechrl-data
PY=/home/chao/.venvs/speechrl/bin/python
cd $S
$PY -B $S/asr_trigger_bound.py --out $S/bound339.json
$PY -B $S/whisper_wer.py $S/whisper_wer.json
$PY -B $S/exposure.py $S/exposure.json
