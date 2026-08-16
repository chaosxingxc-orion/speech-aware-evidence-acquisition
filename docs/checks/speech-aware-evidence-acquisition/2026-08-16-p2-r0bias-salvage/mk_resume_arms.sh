#!/usr/bin/env bash
# Build docs/arms/p2-rladder-resume.arms by VERBATIM slicing of the original,
# so the pre-registered reads and BRANCH RULES cannot be altered by retyping.
set -euo pipefail
REPO="/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
SRC="$REPO/docs/arms/p2-rladder.arms"
DST="$REPO/docs/arms/p2-rladder-resume.arms"

# lines 1-26 = the full header comment block (pre-registered reads + BRANCH
# RULES + the run_id:baseline_fragment legend), byte-verbatim.
sed -n '1,26p' "$SRC" > "$DST"

cat >> "$DST" <<'NOTE'
# ---------------------------------------------------------------------------
# RESUME (2026-08-16). The block launched 2026-08-16T00:21Z died at MANIFEST
# BIND, not in science: the English-only rewrite of AGENTS.md/CLAUDE.md landed
# in the working tree mid-flight, and a COMPLETED manifest refuses a dirty tree.
# Arm SAEA-P2-r0bias, attempt-20260816T002109Z-4e1f59, had already FINISHED its
# inference - 395 metered model calls, 30959.04 speech-audio seconds, all ten
# replay derivations written - and its raw trace is sealed and UNREAD. That
# attempt is being salvaged offline, so r0bias is NOT re-flown: one-shot attempt
# semantics are preserved by reading that attempt, never a second one. This file
# therefore carries the FOUR un-run arms only. The header above is copied
# verbatim from docs/arms/p2-rladder.arms; the reads and BRANCH RULES are
# unchanged, and this resume flies under the SAME pre-registration (ledger rows
# committed at a001a22). No new registration was created.
# ---------------------------------------------------------------------------
NOTE

# lines 28-31 = the four un-run arms, already in the required resume order
# (r1verify, r2draft, r0wrong, r1wrong); line 27 (r0bias) is dropped.
sed -n '28,31p' "$SRC" >> "$DST"

echo "=== written: $DST ==="
cat -A "$DST" | sed -n '1,5p'
echo "..."
echo "=== verbatim proof: header 1-26 and arms 28-31 vs original ==="
diff <(sed -n '1,26p' "$SRC") <(sed -n '1,26p' "$DST") && echo "HEADER 1-26 IDENTICAL"
diff <(sed -n '28,31p' "$SRC") <(tail -4 "$DST") && echo "FOUR ARM LINES IDENTICAL"
echo "=== CRLF check (expect 0) ==="
grep -c $'\r' "$DST" || true
echo "=== final file ==="
cat "$DST"
