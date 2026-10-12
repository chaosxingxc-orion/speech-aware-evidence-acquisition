"""After the readiness flip the composed config hash moves: recompute per cell and rewrite old -> new in the plans, the six E35 ledger rows and the receipt."""
import io, json, sys, hashlib, re
from pathlib import Path
REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"); DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
sys.path.insert(0, str(REPO / "src"))
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
RD = "docs/readiness/2026-09-22-e21-native-window-flightruntime-e35-v1"
CELLS = [("four-row-direct", "e21-native-window-four-row-direct-vs-system-v1", "e21-native-window-direct-four-row-v1"),
         ("four-row-system", "e21-native-window-four-row-direct-vs-system-v1", "e21-native-window-system-four-row-v1"),
         ("sub10-direct", "e21-native-window-sub10-direct-vs-system-v1", "e21-native-window-direct-sub10-v1"),
         ("sub10-system", "e21-native-window-sub10-direct-vs-system-v1", "e21-native-window-system-sub10-v1")]
def rd(p): return io.open(p, encoding="utf-8", newline="").read()
def wr(p, s): io.open(p, "w", encoding="utf-8", newline="\n").write(s)
import os; os.chdir(REPO)
mapping = {}
for stem, experiment, cell_id in CELLS:
    exp = json.load(io.open(f"configs/experiment/{experiment}.json", encoding="utf-8")); cell = next(c for c in exp["cells"] if c["cell_id"] == cell_id)
    composed = compose(REPO, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)
    plan = json.loads(rd(f"{RD}/{stem}-plan-v1.json")); old_c = plan["composed_config_hash"]; old_p = plan["execution_plan"]["protocol_hash"]
    new_c = composed.config_hash; new_p = protocol_hash(new_c, composed.values.get("arm"), plan["execution_plan"]["split_identity_hash"])
    if old_c != new_c: mapping[old_c] = new_c
    if old_p != new_p: mapping[old_p] = new_p
    print(stem, "config", old_c[:8], "->", new_c[:8], "| protocol", old_p[:8], "->", new_p[:8])
if not mapping:
    print("no hash moved"); sys.exit(0)
for stem, _, _ in CELLS:
    p = f"{RD}/{stem}-plan-v1.json"; s = rd(p)
    for a, b in mapping.items(): s = s.replace(a, b)
    wr(p, s)
# receipt
rp = DATA / "coordination/e21-native-window-flightruntime-e35-v1/root-admission-v1.json"; s = rd(rp)
for a, b in mapping.items(): s = s.replace(a, b)
# plan sha pins inside the receipt antecedents are now stale: recompute
d = json.loads(s)
for stem, _, _ in CELLS:
    d["antecedents"]["plans"][stem]["sha256"] = hashlib.sha256(io.open(f"{RD}/{stem}-plan-v1.json", "rb").read()).hexdigest()
wr(rp, json.dumps(d, indent=2) + "\n")
# ledger: only the six E35 rows (by run id prefix), rewrite hashes and Plan SHA256
L = "docs/exposure-ledger.md"; lines = rd(L).split("\n"); n = 0
for i, ln in enumerate(lines):
    if ln.startswith("|") and ln.count("|") > 12 and "SAEA-E21-NATIVE-WINDOW-" in ln.split("|")[2] and ("FOUR-ROW" in ln or "SUB10" in ln):
        for a, b in mapping.items(): ln = ln.replace(a, b)
        c = ln.split("|"); plan_rel = c[14].strip()
        if os.path.exists(plan_rel):
            c[15] = re.sub(r"Plan SHA256 [0-9a-f]{64}", "Plan SHA256 " + hashlib.sha256(io.open(plan_rel, "rb").read()).hexdigest(), c[15])
        lines[i] = "|".join(c); n += 1
wr(L, "\n".join(lines)); print("ledger rows rewritten", n)
