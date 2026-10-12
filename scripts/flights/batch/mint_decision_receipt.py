"""Mint a cell's root-admission decision receipt on the data root by id substitution from a sealed sibling's receipt.

Generalised from the 2026-09-22 mint step of plan_gates_mint_0922.sh (R-PRIM from B1-notool). The template receipt's ids
(cell slug, run-id tag, readiness dir, coordination dir, decision id) are replaced, the decision / authorisation texts are
set, every referenced repo file is re-hashed, and the receipt is written under
``$SPEECHRL_DATA_DIR/coordination/slurp-<name>-v1/root-admission-v1.json``. WSL Python from the study root.

    python scripts/flights/batch/mint_decision_receipt.py --from review-primitives --from-tag REVIEW-PRIMITIVES \
        --from-date 2026-09-22 --name prune-reviewer1 --tag PRUNE-REVIEWER1 --date 2026-09-22 \
        --decision "..." --authority "..." --claim-boundary "..." [--expected-contacts 4320 --expected-gpu-hours 1.7]
"""
import os
import argparse
import hashlib
import io
import json
import os
from datetime import datetime, timezone

DATA = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ROOT = os.environ.get("SAEA_STUDY_ROOT", "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition") + "/"


def rehash(x):
    if isinstance(x, dict):
        if "path" in x and isinstance(x["path"], str) and os.path.exists(ROOT + x["path"]):
            x["sha256"] = hashlib.sha256(io.open(ROOT + x["path"], "rb").read()).hexdigest()
        for v in x.values():
            rehash(v)
    elif isinstance(x, list):
        for v in x:
            rehash(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", required=True, help="template cell slug, e.g. review-primitives")
    ap.add_argument("--from-tag", required=True, help="template run-id tag, e.g. REVIEW-PRIMITIVES")
    ap.add_argument("--from-date", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--decision", required=True)
    ap.add_argument("--authority", required=True)
    ap.add_argument("--claim-boundary", required=True)
    ap.add_argument("--expected-contacts", type=int, default=None)
    ap.add_argument("--expected-gpu-hours", type=float, default=None)
    ap.add_argument("--out-name", default="root-admission-v1.json", help="receipt file name inside coordination/slurp-<name>-v1/ (2026-09-24: a cell that shares its coordination directory with a sibling receipt names its own, e.g. cell-admission-v1.json)")
    ap.add_argument("--replace", action="append", default=[], help="extra OLD=NEW substitutions applied AFTER the id substitutions (e.g. run ids without the NATIVE infix, attempt ids without the roster slug)")
    a = ap.parse_args()
    src = f"{DATA}/coordination/slurp-{a.src}-v1/root-admission-v1.json"
    s = io.open(src, encoding="utf-8").read()
    for old, new in [
        (f"slurp-{a.src}-admission-v1", f"slurp-{a.name}-admission-v1"),
        (f"SAEA-SLURP-NATIVE-{a.from_tag}-", f"SAEA-SLURP-NATIVE-{a.tag}-"),
        (f"slurp-native-{a.src}-", f"slurp-native-{a.name}-"),
        (f"docs/readiness/{a.from_date}-slurp-{a.src}-v1", f"docs/readiness/{a.date}-slurp-{a.name}-v1"),
        (f"coordination/slurp-{a.src}-v1", f"coordination/slurp-{a.name}-v1"),
    ]:
        s = s.replace(old, new)
    for pair in a.replace:
        old, new = pair.split("=", 1)
        s = s.replace(old, new)
    n = json.loads(s)
    assert n.get("decision_id") == f"slurp-{a.name}-admission-v1", n.get("decision_id")
    n["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    n["decision"] = a.decision
    n["authorization_basis"] = a.authority
    n["claim_boundary"] = a.claim_boundary
    n["minted_from"] = {"template_receipt": src.replace(DATA, "$SPEECHRL_DATA_DIR"), "tool": "scripts/flights/batch/mint_decision_receipt.py"}
    rehash(n)
    if isinstance(n.get("budget"), dict) and isinstance(n["budget"].get("arm"), dict):
        if a.expected_contacts is not None:
            n["budget"]["arm"]["expected_contacts"] = a.expected_contacts
        if a.expected_gpu_hours is not None:
            n["budget"]["arm"]["expected_gpu_hours"] = a.expected_gpu_hours
    out_dir = f"{DATA}/coordination/slurp-{a.name}-v1"
    os.makedirs(out_dir, exist_ok=True)
    out = f"{out_dir}/{a.out_name}"
    if os.path.exists(out):
        raise SystemExit(f"refusing to overwrite an existing receipt: {out} (pass --out-name for a sibling receipt)")
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(n, indent=2) + "\n")
    print("minted", out, "| decision_id", n.get("decision_id"), "| eligible", n.get("eligible_run_ids"))


if __name__ == "__main__":
    main()
