#!/usr/bin/env bash
set -euo pipefail
REPO="/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
L="$REPO/docs/exposure-ledger.md"
before=$(wc -l < "$L")

cat >> "$L" <<'NOTE'

**2026-08-16 P2 R-ladder block ABORTED AT MANIFEST BIND; the r0bias attempt is sealed unread.** The five-arm block launched 2026-08-16T00:21Z under the four rows above (pre-registration committed `a001a22`) did not fail in science - it failed at manifest bind. The English-only rewrite of `AGENTS.md`/`CLAUDE.md` landed in the working tree mid-flight (file mtime 2026-08-16T01:13:40Z) and `core/bundle/git_commit.py` refuses to bind `study_commit` against a dirty tree, so no COMPLETED manifest could be built. Arm `SAEA-P2-r0bias`, attempt `attempt-20260816T002109Z-4e1f59`, had by then RUN ITS INFERENCE TO COMPLETION - 156 min, **395 metered model calls, 30959.04 speech-audio seconds** (405 MODEL_REQUEST trace records less the 10 terminal stitch requests), all ten replay derivations plus trace, outputs, trace-manifest and server log written - yet its manifest was finalized `status: ABORTED` with `failure_reason` "run succeeded but its COMPLETED manifest could not be built: ... uncommitted changes". Arm `SAEA-P2-r1verify` (attempt `attempt-20260816T025734Z-23a43f`) died identically ~13 min in, and the driver's two-failure rule stopped the sequence at 03:10Z. **No results were read at abort time; `consumed` stays `no`.** The r0bias raw trace is durable and sealed, and its results will be read EXACTLY ONCE from that attempt via offline salvage; the arm is therefore NOT re-flown, because one-shot attempt semantics are preserved by reading the attempt that ran rather than flying a second one. This spend is recorded against the registered 2500 / 170000 / 20.0 cells of the `SAEA-P2-r0bias` row above.

**2026-08-16 four-arm resume - SAME pre-registration, no new registration.** The block resumes with the four un-run arms only - `SAEA-P2-r1verify`, `SAEA-P2-r2draft`, `SAEA-P2-r0wrong`, `SAEA-P2-r1wrong`, in that order - from `docs/arms/p2-rladder-resume.arms`, whose header is copied verbatim from `docs/arms/p2-rladder.arms`: the PRE-REGISTERED READS and the BRANCH RULES are unchanged, as are the split identity hash, the tier fields and the registered budget cells. The four rows above remain the governing registration; **no new registration was created and no new registration ID exists.** `consumed` stays `no` on all four. The resume is launched detached from Windows per plan rule I1, only after the working tree was made clean by the single commit carrying the guide translation, this resume arms file and these two notes - the I2 rule (no commits of any kind during any arm flight) governs the whole block.
NOTE

after=$(wc -l < "$L")
echo "ledger lines: $before -> $after"
echo "=== CRLF check (expect 0) ==="
grep -c $'\r' "$L" || true
echo "=== non-ASCII in the appended tail (expect none) ==="
tail -4 "$L" | grep -P '[^\x00-\x7F]' || echo "  (none)"
echo "=== appended tail ==="
tail -4 "$L"
