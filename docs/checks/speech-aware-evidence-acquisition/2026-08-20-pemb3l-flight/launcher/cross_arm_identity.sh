#!/usr/bin/env bash
# STRUCTURAL byte-identity accounting across arms -- the same class of check as
# "78 distinct vector sha256" (the consumed P-EMB-1 receipt's own "did the model
# do something" test). It compares CONTENT HASHES ONLY. No vector component is
# read, no cosine/argmax/ranking/accuracy is computed, and no verdict is formed.
source /mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pemb3l/env.sh
exec > >(tee "$SCRATCH/cross-arm-identity.log") 2>&1
echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
python - "$SPEECHRL_DATA_DIR" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
base = root / "derived" / "embeddings" / "SAEA-PROBE-pemb3l-234"
arms = {}
for arm in ("l1-last-bare", "l2-last-instruct", "l3-mean-instruct"):
    d = json.loads((base / arm / "manifest.json").read_text(encoding="utf-8"))
    arms[arm] = {(e["kind"], e["contact_id"]): e["sha256"] for e in d["entries"]}

names = list(arms)
print("=== per-arm entry counts by kind ===")
for a in names:
    kinds = {}
    for (k, _cid) in arms[a]:
        kinds[k] = kinds.get(k, 0) + 1
    print(f"  {a}: {kinds}")

print()
print("=== pairwise byte identity, SPLIT BY KIND (same contact_id compared) ===")
for i, a in enumerate(names):
    for b in names[i + 1:]:
        same_audio = same_text = tot_audio = tot_text = 0
        for key, ha in arms[a].items():
            hb = arms[b].get(key)
            kind = key[0]
            if kind == "audio":
                tot_audio += 1
                same_audio += (ha == hb)
            else:
                tot_text += 1
                same_text += (ha == hb)
        print(f"  {a}  vs  {b}")
        print(f"    audio vectors byte-identical: {same_audio}/{tot_audio}")
        print(f"    text  vectors byte-identical: {same_text}/{tot_text}")
PY
echo
echo "=== server-log 'not marked as outputs' warning, this sweep vs the consumed P-EMB-1 ==="
RD="$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pemb3l-234"
for f in "$RD"/*/SAEA-PROBE-pemb3l-234.session-*.server.log; do
  [ -f "$f" ] || continue
  echo "  $(basename "$(dirname "$f")")/$(basename "$f"): $(grep -c 'not marked as outputs' "$f") warning line(s)"
  grep -m1 'not marked as outputs' "$f" | sed 's/^/      /'
  echo "      pooling_type line: $(grep -m1 'pooling_type' "$f" | sed 's/^ *//')"
done
P1="$REPO/docs/checks/speech-aware-evidence-acquisition/2026-08-19-pemb1-flight/postflight.log"
if [ -f "$P1" ]; then
  echo "  consumed P-EMB-1 (mean pooling, 60 audio contacts) postflight line:"
  grep -i "not marked as outputs" "$P1" | sed 's/^/      /'
fi
echo "end: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
