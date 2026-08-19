#!/usr/bin/env bash
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pkey2fly/env.sh
cd "$REPO"
python - <<'PY'
import py_compile, sys, pathlib
scratch = pathlib.Path("/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pkey2fly")
for name in ("flight_identity.py", "preflight.py", "probe_d1.py", "launch_pkey_flight.py"):
    py_compile.compile(str(scratch / name), doraise=True)
    print(f"compile OK: {name}")
sys.path.insert(0, str(scratch))
import flight_identity
print("RUN_ID:", flight_identity.RUN_ID)
print("FLIGHT_CONFIG:", flight_identity.FLIGHT_CONFIG_RELPATH)
# import-time guards of the machinery fire here (model-free)
from speech_aware_evidence_acquisition.rails.probes import pkey_flight
print("machinery import OK: pkey_flight arms =", pkey_flight.PKEY_ARMS)
print("machinery split identity pin =", pkey_flight.EXPECTED_SPLIT_IDENTITY_HASH)
import json
cfg = json.loads((pathlib.Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition") / "configs/probes/g0-binding/pkey-flight.json").read_text(encoding="utf-8"))
pkey_flight.assert_pinned_text_matches_config(cfg)
print("config/code parity guard: PASS (model-free)")
values = flight_identity.build_values(pathlib.Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"))
print("build_values OK: keys =", len(values), "arm =", values["arm"], "feat cache =", values["server_env"]["LLAMA_MTMD_FEAT_CACHE_DIR"])
print("config_hash:", flight_identity.config_hash_of(values))
PY
