#!/bin/bash
# The a2t0 consumption-module all-off arm's descriptive form read (model-free; refuses unless the READ row is root
# countersigned). Carrier admission gate, design 2b.3; owner decision 196, direction 205.
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
/home/chao/.venvs/speechrl/bin/python -B "$MAIN/scripts/flights/module/module_alloff_read.py" --carrier a2t "$@"
