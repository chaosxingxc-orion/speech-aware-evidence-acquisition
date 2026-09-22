import json
import sys

d = json.load(open(sys.argv[1]))
p = d["preflight"]
reg = open(sys.argv[2]).read()
print({k: p.get(k) for k in ("run_id", "config_hash", "protocol_hash", "sample_count", "study_commit")})
print("readiness", d.get("scientific_readiness"), "| registered doc carries runtime protocol hash:", p["protocol_hash"] in reg, "| composed:", p["config_hash"] in reg)
