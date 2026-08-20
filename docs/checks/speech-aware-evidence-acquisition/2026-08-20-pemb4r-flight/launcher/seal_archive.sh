#!/usr/bin/env bash
# Re-run the leak + read guards over the FINAL archive contents (README
# included) and regenerate MANIFEST.sha256. Never deletes anything.
source "$(dirname "$0")/env.sh"
DEST="$REPO/docs/checks/speech-aware-evidence-acquisition/2026-08-20-pemb4r-flight"
cd "$SCRATCH"

echo "--- leak guard ---"
LEAK=$(find "$DEST" \( -name '*.npy' -o -name 'vectors-*.jsonl' -o -name '*jitter-vectors*' \
        -o -name 'retrieval_plan.json' -o -name 'c-decode-outputs.jsonl' -o -name 'c-decode-responses.jsonl' \
        -o -name 'gate-c-*-vector.json' \) || true)
if [ -n "$LEAK" ]; then echo "LEAK GUARD FAILED:"; echo "$LEAK"; exit 3; fi
python - "$DEST" <<'PY'
import json, sys
from pathlib import Path
dest = Path(sys.argv[1])
bad = []
for path in sorted(dest.rglob("*.json")):
    def walk(node, where):
        if isinstance(node, list):
            if len(node) > 64 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in node):
                bad.append(f"{path.name}:{where} -- numeric array of length {len(node)}")
            for i, v in enumerate(node):
                walk(v, f"{where}[{i}]")
        elif isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{where}.{k}")
    try:
        walk(json.loads(path.read_text(encoding="utf-8")), "")
    except Exception:
        continue
if bad:
    print("LEAK GUARD FAILED (raw numeric vector in landed JSON):")
    for line in bad[:20]:
        print("  ", line)
    sys.exit(3)
print("leak guard PASS: no .npy, no vectors-*.jsonl, no retrieval plan body, no C-DECODE response file,")
print("                 and no numeric array longer than 64 anywhere in the landed JSON")
PY

echo "--- read guard ---"
python - "$DEST" <<'PY'
import re, sys
from pathlib import Path
dest = Path(sys.argv[1])
FORBIDDEN = (
    "accuracy", "vote_accuracy", "recall", "recall_at_1", "recall_at_3", "recall_at_5",
    "n_correct", "correct", "is_correct", "gold_label", "gold_scenario", "verdict",
    "predicted_correct", "hit", "precision", "f1", "argmax_stability", "cross_arm_agreement",
)
pattern = re.compile(r'"(' + "|".join(re.escape(k) for k in FORBIDDEN) + r')"\s*:')
hits = []
for path in sorted(dest.rglob("*")):
    if not path.is_file() or path.suffix not in (".json", ".jsonl"):
        continue
    for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for m in pattern.finditer(line):
            hits.append(f"{path.relative_to(dest)}:{n}: {m.group(1)}")
if hits:
    print("READ GUARD FAILED (computed-result key in landed evidence):")
    for line in hits[:30]:
        print("  ", line)
    sys.exit(4)
print(f"read guard PASS: zero computed-result keys ({len(FORBIDDEN)} patterns) in any landed JSON")
PY

cd "$DEST"
rm -f MANIFEST.sha256
find . -type f ! -name MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > MANIFEST.sha256
echo "MANIFEST.sha256: $(wc -l < MANIFEST.sha256) files"
