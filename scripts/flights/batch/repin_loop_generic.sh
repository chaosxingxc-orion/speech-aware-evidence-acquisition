#!/bin/bash
# Usage: repin_loop_generic.sh <repin-script> <readiness-dir> <cell> <plan-prefix: smoke-generation|generation> <commit-msg-file>
# Optional env PLAN_REC (e.g. -rec1): the plan file is <plan-prefix>-plan-registered<PLAN_REC>-v1.json (a recovered smoke's plan name).
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
PY=/home/chao/.venvs/speechrl/bin/python
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
SCRIPT=$1; RD=$2; CELL=$3; PLAN=$4; MSG=$5
# Owner 2026-10-12: hot paths never run on /mnt/* (9p). Refuse (64) unless SAEA_ALLOW_9P_FLIP=1.
case "$(realpath -m "$MAIN")" in /mnt/*) [ "$SAEA_ALLOW_9P_FLIP" = 1 ] || { echo "refusing: repo root $MAIN is on /mnt (9p); run via scripts/flights/batch/flip_in_ext4.sh or set SAEA_ALLOW_9P_FLIP=1"; exit 64; } ;; esac
cd $MAIN || exit 1
for pass in 1 2 3 4 5; do
  echo "######## $CELL pass $pass HEAD $(git rev-parse --short HEAD)"
  # 2026-09-29: D3 freeze refuses a __pycache__ entry beside the frozen scoring sources; purge cached
  # bytecode under $MAIN/src before every pass. Only directories literally named __pycache__ are removed.
  if [ -d "$MAIN/src" ]; then find "$MAIN/src" -type d -name __pycache__ -prune -exec rm -rf {} +; fi
  bash $SCRIPT 2>&1 | grep -v "^{'run_id'\|^On branch\|^Your branch\|^  (use\|^nothing to commit\|^COMMIT FAILED" | cut -c1-180
  ERR=$(ls -t /home/chao/*-repin-*.err 2>/dev/null | head -1)
  if grep -q "neither its freshly composed config_hash" "$ERR"; then
    $PY - "$RD" "$PLAN" "$CELL" "$ERR" <<'PY'
import io, json, os, re, sys, glob
rd, plan, cell, errf = sys.argv[1:5]
rec = os.environ.get("PLAN_REC", "")   # optional recovery marker of the plan file name, e.g. -rec1 (smoke-generation-plan-registered-rec1-v1.json)
err = io.open(errf, encoding="utf-8").read()
m = re.search(r"config_hash \(([0-9a-f]{64})\) nor protocol_hash \(([0-9a-f]{64})\)", err); new_c, new_p = m.group(1), m.group(2)
reg = json.load(io.open(f"{rd}/{plan}-plan-registered{rec}-v1.json", encoding="utf-8"))
assert reg["cell"] == cell, (reg["cell"], cell)
old_c = reg["composed_config_hash"]; old_p = reg["execution_plan"]["protocol_hash"]
files = sorted(glob.glob(f"{rd}/*")) + [f"{rd}-preregistration.md"]; total = 0
for f in files:
    s = io.open(f, encoding="utf-8", newline="").read(); n = s.count(old_c) + s.count(old_p)
    if n: io.open(f, "w", encoding="utf-8", newline="").write(s.replace(old_c, new_c).replace(old_p, new_p)); total += n
# the ledger: ONLY the rows whose artifacts column points into this package (item E26: never another cell's row)
L = "docs/exposure-ledger.md"; led = io.open(L, encoding="utf-8", newline="").read(); out = []
for ln in led.split("\n"):
    if ln.startswith("|") and ln.count("|") > 12 and (rd + "/") in ln:
        n = ln.count(old_c) + ln.count(old_p)
        if n: ln = ln.replace(old_c, new_c).replace(old_p, new_p); total += n
    out.append(ln)
io.open(L, "w", encoding="utf-8", newline="").write("\n".join(out))
print("rewrote registered -> fresh:", total, "|", old_c[:8], "->", new_c[:8], "|", old_p[:8], "->", new_p[:8])
PY
    git add "$RD" "$RD-preregistration.md" docs/exposure-ledger.md && git commit -q -F "$MSG" && echo "committed $(git rev-parse --short HEAD)"
    continue
  fi
  if grep -q "has uncommitted changes" "$ERR"; then continue; fi
  if [ -s "$ERR" ] && grep -q '"error"' "$ERR"; then
    echo "REFUSAL:"; $PY -c "import json,io; print(json.load(io.open('$ERR'))['error'][:500])"
    # 2026-09-26: the rewriter above covers the plan documents, the preregistration and the ledger rows
    # whose artifacts column points into this package. It does NOT cover a package file that merely
    # QUOTES a hash as the record of something already done -- a dry-run record is the case seen -- nor a
    # ledger row the E26 scope test excludes. Name the remedy instead of leaving the operator to guess.
    if grep -q "old hash residue remains" "$ERR"; then
      echo "REMEDY: a package file still quotes a superseded hash. Do NOT edit the number inside a record"
      echo "        of something that happened: re-run that record's own producer at the flipped bytes so"
      echo "        the document becomes true (a dry run is model-free and costs zero contacts), then"
      echo "        repair only THIS cell's own ledger rows (item E26: never another cell's row)."
    fi
    exit 4
  fi
  if [ -s "$ERR" ] && grep -q "Traceback" "$ERR"; then echo "REFUSAL (traceback):"; tail -3 "$ERR" | cut -c1-300; exit 4; fi  # 2026-09-23: a raw traceback was misread as satisfied
  echo "satisfied at $(git rev-parse HEAD)"; exit 0
done
echo "did not converge"; exit 5
