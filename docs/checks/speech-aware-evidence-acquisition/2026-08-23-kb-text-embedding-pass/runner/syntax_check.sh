#!/usr/bin/env bash
source "$(dirname "$0")/env.sh"

python -m py_compile "$SCRATCH/run_kb_text_embedding_pass.py" && echo "SYNTAX OK"
rm -rf "$SCRATCH/__pycache__"

python - <<'PY'
from pathlib import Path
import os
from speech_aware_evidence_acquisition.rails.encode_only_check import (
    assert_module_never_imports_generation_client,
    assert_source_has_no_forbidden_endpoint_strings,
    run_encode_only_machine_check,
)
import speech_aware_evidence_acquisition as pkg
print("package __file__:", pkg.__file__)
report = run_encode_only_machine_check()
print("pinned-module sweep PASS:", list(report.checked_modules))
p = Path(os.environ["SCRATCH"]) / "run_kb_text_embedding_pass.py"
assert_module_never_imports_generation_client(p)
assert_source_has_no_forbidden_endpoint_strings(p)
print("ENCODE-ONLY GUARDS 1+2 PASS on the runner source")
PY
