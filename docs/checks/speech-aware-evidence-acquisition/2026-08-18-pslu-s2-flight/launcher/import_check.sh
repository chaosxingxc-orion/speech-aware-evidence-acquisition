#!/usr/bin/env bash
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pslus2fly/env.sh
cd "$REPO"
python - <<'PY'
import py_compile, sys, pathlib
scratch = pathlib.Path("/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pslus2fly")
for name in ("flight_identity.py", "preflight.py", "probe_d1.py", "launch_pslu_s2_flight.py"):
    py_compile.compile(str(scratch / name), doraise=True)
    print(f"compile OK: {name}")
sys.path.insert(0, str(scratch))
import flight_identity
print("RUN_ID:", flight_identity.RUN_ID)
print("FLIGHT_CONFIG:", flight_identity.FLIGHT_CONFIG_RELPATH)
# import-time guards of the machinery fire here (model-free)
from speech_aware_evidence_acquisition.rails.probes import pslu_s2_flight, pslu_s2_filler
print("machinery import OK: pslu_s2_flight arms =", pslu_s2_flight.PSLU_S2_ARMS)
print("machinery import OK: pslu_s2_filler roster size =", pslu_s2_filler.F1_ROSTER_SIZE, "seed =", pslu_s2_filler.F1_FILLER_SEED)
values = flight_identity.build_values(pathlib.Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"))
print("build_values OK: keys =", len(values), "arm =", values["arm"], "feat cache =", values["server_env"]["LLAMA_MTMD_FEAT_CACHE_DIR"])
print("config_hash:", flight_identity.config_hash_of(values))
PY
