#!/usr/bin/env bash
# Archive the P-EMB-3L sweep into the study's check surface. The registered
# sweep spans TWO attempts (attempt 1 aborted in the launcher's own inter-
# session teardown after L1+L2 landed; attempt 2 carried those two arms and
# flew L3), so BOTH attempts' receipts are archived.
# Run ONLY after the launcher has written its flight receipts.
#   archive.sh <attempt-1-id> <attempt-2-id>
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/pemb3l
source "$SDIR/env.sh"

A1="${1:?usage: archive.sh <attempt-1-id> <attempt-2-id>}"
A2="${2:?usage: archive.sh <attempt-1-id> <attempt-2-id>}"
RUN_ID=SAEA-PROBE-pemb3l-234
SLUG=2026-08-20-pemb3l-flight
RD1="$SPEECHRL_DATA_DIR/runs/$RUN_ID/$A1"
RD2="$SPEECHRL_DATA_DIR/runs/$RUN_ID/$A2"
DEST="$REPO/docs/checks/speech-aware-evidence-acquisition/$SLUG"

mkdir -p "$DEST/launcher"

# 1. the launcher chain (every file that produced the run)
for f in env.sh flight_identity.py launch_pemb3l_flight.py preflight.py \
         gguf_verify.sh postflight.sh archive.sh update_ledger.py \
         run_preflight.sh run_flight.sh \
         session_precheck.sh session_run_pytest.sh session_rerun_flake.sh \
         probe_marker.sh wait_for_yield.sh check_preflight_proc.sh \
         check_flight_proc.sh check_partial_state.sh cross_arm_identity.sh \
         syntax_check.sh measure_rate.sh; do
  cp "$SDIR/$f" "$DEST/launcher/$f"
done

# the flight receipt narrative
cp "$SDIR/README.md" "$DEST/README.md"

# 2. health logs (operational/structural only -- never a vector component)
cp "$SDIR/session-precheck.log"        "$DEST/session-precheck.log"
cp "$SDIR/preflight-pytest.log"        "$DEST/preflight-pytest.log"
cp "$SDIR/preflight-pytest-rerun.log"  "$DEST/preflight-pytest-rerun.log"
cp "$SDIR/marker-probe.log"            "$DEST/marker-probe.log"
cp "$SDIR/preflight.log"               "$DEST/preflight.log"
cp "$SDIR/gguf-verify.log"             "$DEST/gguf-verify.log"
cp "$SDIR/flight.log"                  "$DEST/flight.log"
cp "$SDIR/postflight.log"              "$DEST/postflight.log"
# the abort + repair evidence
cp "$SDIR/partial-state.log"           "$DEST/abort-partial-state.log"
cp "$SDIR/syntax-check.log"            "$DEST/abort-repair-proof.log"
cp "$SDIR/cross-arm-identity.log"      "$DEST/cross-arm-identity.log"

# 3. run receipts (identity + cost + contact counts; never a vector)
#    Attempt 2 is the completing attempt and supplies the canonical plan/config
#    (both attempts carry the SAME config_hash and protocol_hash).
cp "$RD2/flight-receipt.json"        "$DEST/flight-receipt.json"
cp "$RD2/$RUN_ID.plan.json"          "$DEST/execution-plan.json"
cp "$RD2/$RUN_ID.config-values.json" "$DEST/config-values.json"
cp "$RD2/contacts.json"              "$DEST/contacts.json"
cp "$SPEECHRL_DATA_DIR/attempts/$RUN_ID/$A2.json" "$DEST/attempt-state.json"

# attempt 1 (ABORTED) -- the partial flight that produced L1 + L2
cp "$RD1/flight-receipt.json"        "$DEST/attempt1-aborted-flight-receipt.json"
cp "$RD1/contacts.json"              "$DEST/attempt1-aborted-contacts.json"
cp "$RD1/$RUN_ID.plan.json"          "$DEST/attempt1-aborted-execution-plan.json"
cp "$SPEECHRL_DATA_DIR/attempts/$RUN_ID/$A1.json" "$DEST/attempt1-aborted-attempt-state.json"

# session receipts + server logs from whichever attempt spawned them
for RD in "$RD1" "$RD2"; do
  for s in last mean; do
    [ -f "$RD/$RUN_ID.session-$s.receipt.json" ] && \
      cp "$RD/$RUN_ID.session-$s.receipt.json" "$DEST/session-receipt-$s.json"
    [ -f "$RD/$RUN_ID.session-$s.server.log" ] && \
      cp "$RD/$RUN_ID.session-$s.server.log" "$DEST/session-$s.server.log"
  done
done

# 4. each arm's embedding manifest STRUCTURAL summary (counts + per-entry
#    sha256/relpath/dims -- the vectors themselves stay on the data root)
python - "$SPEECHRL_DATA_DIR" "$RUN_ID" "$DEST" <<'PY'
import collections
import hashlib
import json
import pathlib
import sys

root, run_id, dest = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
base = root / "derived" / "embeddings" / run_id
arms = {}
for arm_dir in sorted(p for p in base.iterdir() if p.is_dir()):
    mp = arm_dir / "manifest.json"
    d = json.loads(mp.read_text(encoding="utf-8"))
    entries = d.get("entries", [])
    arms[arm_dir.name] = {
        "source_manifest": str(mp),
        "manifest_sha256": hashlib.sha256(mp.read_bytes()).hexdigest(),
        "run_id": d.get("run_id"),
        "dims": d.get("dims"),
        "audio_count": d.get("audio_count"),
        "text_count": d.get("text_count"),
        "entry_count": len(entries),
        "entries_by_kind": dict(sorted(collections.Counter(e["kind"] for e in entries).items())),
        "distinct_vector_sha256": len({e["sha256"] for e in entries}),
        "dim_distribution": dict(sorted(collections.Counter(e["dims"] for e in entries).items())),
        "entries": [
            {"contact_id": e["contact_id"], "kind": e["kind"], "relpath": e["relpath"],
             "dims": e["dims"], "sha256": e["sha256"]}
            for e in sorted(entries, key=lambda e: (e["kind"], e["contact_id"]))
        ],
    }

# Cross-arm byte identity ONLY -- how many vectors are literally the same bytes
# between two constructions, split by kind and keyed on the SAME contact_id.
# This is a structural "did the knob do anything" check of exactly the class
# the consumed P-EMB-1 receipt already performs ("distinct vector sha256").
# It never compares vector VALUES and never produces an accuracy or a verdict.
by_key = {
    name: {(e["kind"], e["contact_id"]): e["sha256"] for e in a["entries"]}
    for name, a in arms.items()
}
names = sorted(arms)
cross = {}
for i, a in enumerate(names):
    for b in names[i + 1:]:
        same = collections.Counter()
        total = collections.Counter()
        for key, ha in by_key[a].items():
            total[key[0]] += 1
            if by_key[b].get(key) == ha:
                same[key[0]] += 1
        cross[f"{a}|{b}"] = {
            kind: {"byte_identical": same[kind], "total": total[kind]} for kind in sorted(total)
        }

summary = {
    "schema": "saea-pemb3l-embedding-manifest-summary-v1",
    "run_id": run_id,
    "arm_count": len(arms),
    "total_entries": sum(a["entry_count"] for a in arms.values()),
    "byte_identical_vectors_between_arms_by_kind": cross,
    "arms": arms,
}
(dest / "embedding-manifest-summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
)
print("embedding manifest summary:", summary["arm_count"], "arms,", summary["total_entries"], "entries")
for name, a in sorted(arms.items()):
    print(f"  {name}: {a['entry_count']} entries, {a['distinct_vector_sha256']} distinct vector hashes")
print("  cross-arm byte identity:", json.dumps(cross, sort_keys=True))
PY

# 5. manifest over everything above
cd "$DEST"
rm -f MANIFEST.sha256
find . -type f ! -name MANIFEST.sha256 | sort | xargs sha256sum -b > MANIFEST.sha256
echo "archived $(wc -l < MANIFEST.sha256) files to $DEST"
ls -la "$DEST"
echo
echo "=== leak guard: no vector component and no response text may enter the archive ==="
# A vector would appear as a JSON ARRAY under a "values" key. The bare token
# "values" is deliberately NOT the guard: config-values.json legitimately
# carries a "values" OBJECT (the hashed config bundle), and launcher/ files
# name the field in code and inside this guard's own search strings.
echo "  files carrying a vector ARRAY ('\"values\": ['): $(grep -rl '\"values\": \[' "$DEST" | grep -v '/launcher/' | wc -l) (expect 0)"
echo "  files carrying 'response_text': $(grep -rl 'response_text' "$DEST" | grep -v '/launcher/' | wc -l) (outside launcher/, expect 0)"
echo "  .npy files under the archive: $(find "$DEST" -name '*.npy' | wc -l) (expect 0)"
echo "  vectors-*.jsonl under the archive: $(find "$DEST" -name 'vectors-*.jsonl' | wc -l) (expect 0)"
echo "  largest archived file: $(find "$DEST" -type f -printf '%s %p\n' | sort -rn | sed -n 1p)"
echo
echo "=== read guard: no COMPUTED accuracy, cosine, argmax or verdict may enter this FLIGHT archive ==="
# Three sources legitimately carry one of these tokens and are excluded by
# NAME, so the guard stays a real check rather than a blanket suppression:
#   1. launcher/ and the two narrative files (README.md, cross-arm-identity.log)
#      -- prose that names what was deliberately NOT computed;
#   2. config-values.json -- the CITED constant `cited_mean_bare_accuracy`
#      (0.0500) carried verbatim from the CONSUMED P-EMB-1 read and folded into
#      this run's config identity so the protocol hash names it. It is an input
#      to this flight's identity, never an output of it;
#   3. the two llama-server logs -- llama.cpp's own load_hparams boilerplate
#      ("if you encounter problems with accuracy, try adding --image-min-tokens").
# Anything else matching is a genuine leak of read work into a flight archive.
#   4. the flight commit's own SUBJECT LINE, "build(pemb3l): local construction
#      sweep - last/instruct arms + verdict delta", which the pre-check and
#      post-flight echo verbatim via `git log --oneline -1`. It names the
#      machinery commit, not a computed verdict, so it is stripped from the
#      text before matching rather than whitelisting those two whole logs.
UNEXPECTED=$(for f in $(find "$DEST" -type f ! -name MANIFEST.sha256 \
        | grep -v '/launcher/' \
        | grep -vE 'README\.md|cross-arm-identity\.log|config-values\.json|session-(last|mean)\.server\.log'); do
  if grep -v 'last/instruct arms + verdict delta' "$f" \
     | grep -qiE 'accuracy|cosine|argmax|top-?1|verdict'; then echo "$f"; fi
done)
echo "  unexpected files carrying a read-shaped token: $(printf '%s' "$UNEXPECTED" | grep -c . || true) (expect 0)"
[ -n "$UNEXPECTED" ] && printf '    %s\n' $UNEXPECTED
echo "  the three excluded sources, shown so the exclusion is auditable:"
echo "    config-values.json  : $(grep -o '"cited_mean_bare_accuracy": [0-9.]*' "$DEST/config-values.json")  (CITED from the consumed P-EMB-1, an INPUT to this run's config hash)"
echo "    session logs        : $(grep -ihoE 'if you encounter problems with accuracy[^"]{0,45}' "$DEST/session-mean.server.log" | sort -u | head -1)  (llama.cpp boilerplate)"
echo "  computed-result keys anywhere outside launcher/ (expect none):"
grep -rhoE '"(top1|top_1|argmax|accuracy|cosine)[a-z_]*"[[:space:]]*:' "$DEST" --include='*.json' \
  | grep -v cited_mean_bare_accuracy | sort -u | sed 's/^/    /' || echo "    (none)"
