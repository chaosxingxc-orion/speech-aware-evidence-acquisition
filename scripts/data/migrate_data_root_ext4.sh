#!/bin/bash
# Migrate the data root from the 9p E: original to the ext4 hot root (owner ruling 284, step 2;
# design docs/superpowers/specs/2026-10-12-engineering-base-unification-design.md, section 7).
#
# DRY-RUN BY DEFAULT: prints the plan and the preflight verdict; touches nothing. --execute copies.
# It never deletes, renames or rewrites anything under the source, and never deletes under the target.
#
# Usage:
#   migrate_data_root_ext4.sh [--phase hot|runtime|derived|rest|cold|all] [--subtrees a,b,c]
#                             [--source DIR] [--target DIR] [--receipt-dir DIR] [--jobs N]
#                             [--measure] [--execute]
#   --phase     hot      runs analysis knowledge prepared coordination serving attempts locks (owner order)
#               runtime  the other subtrees the runtime reads (vectors, preparation-runs, ...; manifest migration.runtime_read_subtrees)
#               derived  derived/
#               rest     every remaining top-level entry of the source except datasets/ and models/ (and loose files)
#               cold     datasets models  (only with --target on the cold disk, decision 284 step 3)
#               all      hot, runtime, derived, rest in that order (default)
#   --subtrees  an explicit comma list instead of --phase
#   --source    default: $SAEA_LEGACY_DATA_ROOT from scripts/lib/data_root.sh
#   --target    default: $SAEA_HOT_DATA_ROOT from scripts/lib/data_root.sh (/home/chao/saea-data/speechrl-data, decision 296)
#   --receipt-dir  default: <target>/receipts/migration-ext4 (one directory per run, never overwritten)
#   --jobs      parallel sha256 workers (default 8; the 2026-09-03 rule allows 8 during a campaign, 20 idle)
#   --measure   dry-run only: also run `rsync --dry-run --stats` per subtree (walks 9p: slow)
#   --link-cold DIR  instead of copying: make <target>/datasets and <target>/models symlinks to DIR/datasets and DIR/models
#               (DIR = the legacy root until the cold disk exists, then /mnt/wsl/saea-data-2/speechrl-data). Refuses to
#               replace a real directory; re-pointing an existing symlink is allowed. Honours --execute like the copy.
#
# --execute refuses (exit 3) unless ALL hold: the target is a mounted ext4 (findmnt/stat -f), the target is not
# the live data root (post-cut-over runs are refused: the copy would race live writers), no generation flight is
# alive and no flight.lock exists (serving_lib.sh saea_flight_alive), no flip/re-pin is alive, no serving start/
# monitor/swap is alive or pending, and no llama-server is listening on the GPU serving port (the serving session
# directory moves too). Override for tests only: SAEA_MIGRATE_SKIP_ALIVE_CHECK=1.
#
# Per subtree: rsync -aH --numeric-ids (idempotent: a re-run copies only differences); then a sha256 manifest of
# every regular file on BOTH sides (relative path, size, sha256; sorted), a symlink inventory (absolute targets
# that point into the source root are re-pointed to the target root and listed), and a compare. A subtree is
# VERIFIED only when the two file manifests are byte-identical. The run writes <receipt-dir>/<run-id>/receipt.json
# plus the per-subtree manifests; deletion of the E: originals is a separate owner step after reading them.
# Exit: 0 ok (dry-run, or every subtree verified); 2 usage; 3 preflight refusal; 4 a subtree failed to verify.
set -u
HERE=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
REPO=$(cd "$HERE/../.." && pwd)
source "$REPO/scripts/lib/data_root.sh" || exit 2
SERVING_LIB=$REPO/scripts/flights/batch/serving_lib.sh

PHASE=all SUBTREES="" SOURCE=$SAEA_LEGACY_DATA_ROOT TARGET=$SAEA_HOT_DATA_ROOT RECEIPTS="" JOBS=8 MEASURE=0 EXECUTE=0 LINK_COLD=""
while [ $# -gt 0 ]; do
  case "$1" in
    --phase) PHASE=$2; shift 2 ;;
    --subtrees) SUBTREES=$2; shift 2 ;;
    --source) SOURCE=$2; shift 2 ;;
    --target) TARGET=$2; shift 2 ;;
    --receipt-dir) RECEIPTS=$2; shift 2 ;;
    --jobs) JOBS=$2; shift 2 ;;
    --measure) MEASURE=1; shift ;;
    --link-cold) LINK_COLD=$2; shift 2 ;;
    --execute) EXECUTE=1; shift ;;
    -h|--help) sed -n '2,/^set -u/p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
SOURCE=${SOURCE%/}; TARGET=${TARGET%/}
RECEIPTS=${RECEIPTS:-$TARGET/receipts/migration-ext4}
case "$JOBS" in ''|*[!0-9]*) echo "--jobs must be a positive integer" >&2; exit 2 ;; esac
[ -d "$SOURCE" ] || { echo "source $SOURCE is not a directory" >&2; exit 2; }

HOT="runs analysis knowledge prepared coordination serving attempts locks"
RUNTIME="vectors preparation-runs system-text-search provisional receipts trace-intermediates wire-check official-evaluator-source-bundles references manifests environments repos"
DERIVED="derived"
COLD="datasets models"
rest_entries() {
  local name skip
  for path in "$SOURCE"/* "$SOURCE"/.[!.]*; do
    [ -e "$path" ] || [ -L "$path" ] || continue
    name=$(basename "$path"); skip=0
    for s in $HOT $RUNTIME $DERIVED $COLD; do [ "$name" = "$s" ] && skip=1; done
    [ $skip = 0 ] && echo "$name"
  done
}
if [ -n "$SUBTREES" ]; then
  LIST=$(echo "$SUBTREES" | tr ',' ' ')
else
  case "$PHASE" in
    hot) LIST=$HOT ;;
    runtime) LIST=$RUNTIME ;;
    derived) LIST=$DERIVED ;;
    rest) LIST=$(rest_entries | tr '\n' ' ') ;;
    cold) LIST=$COLD ;;
    all) LIST="$HOT $RUNTIME $DERIVED $(rest_entries | tr '\n' ' ')" ;;
    *) echo "unknown --phase $PHASE" >&2; exit 2 ;;
  esac
fi
for name in $LIST; do
  case "$name" in */*|..|.|'') echo "subtree names are top-level entries of the source, got '$name'" >&2; exit 2 ;; esac
done

# ---- preflight -------------------------------------------------------------------------------------------------
REFUSALS=()
target_fs=$( [ -d "$TARGET" ] && saea_fs_type "$(readlink -f "$TARGET")" )
[ -d "$TARGET" ] || REFUSALS+=("target $TARGET does not exist (is the VHDX mounted? run the SAEA-Mount-Data1 task)")
[ -d "$TARGET" ] && [ "$target_fs" != ext4 ] && REFUSALS+=("target $TARGET resolves to filesystem '${target_fs:-unknown}', not ext4")
[ "$(readlink -f "$TARGET")" = "$(readlink -f "$SOURCE")" ] && REFUSALS+=("source and target are the same directory")
LIVE_ROOT_REFUSAL=""
[ "${SAEA_DATA_ROOT_DEFAULT%/}" = "$TARGET" ] && LIVE_ROOT_REFUSAL="the target is already the live data root (post-cut-over): copying into it would race live writers"
if [ "${SAEA_MIGRATE_SKIP_ALIVE_CHECK:-0}" != 1 ]; then
  SAEA_DATA=$SOURCE; source "$SERVING_LIB"   # saea_flight_alive reads $SAEA_DATA/locks/flight.lock
  if out=$(saea_flight_alive); then REFUSALS+=("a flight is alive or a flight.lock exists: $(echo "$out" | head -n 2 | tr '\n' ' ')"); fi
  flips=$(pgrep -af -- '[f]lip_in_ext4\.sh|[f]lip_package_ext4\.sh|[o]nepass_flip\.sh|[r]epin_cell|[r]epin_package_one_pass|_flip(_all|_loop)?\.sh' 2>/dev/null | grep -v migrate_data_root || true)
  [ -n "$flips" ] && REFUSALS+=("a flip or re-pin is alive: $(echo "$flips" | head -n 1 | cut -c1-160)")
  serving=$(pgrep -af -- '[s]erving_task_entry|[s]erving_monitor_start|[s]erving_swap\.sh|[c]ore\.session\.serving (start|monitor)' 2>/dev/null || true)
  [ -n "$serving" ] && REFUSALS+=("a serving start, monitor or swap is alive: $(echo "$serving" | head -n 1 | cut -c1-160)")
  if out=$(saea_swap_pending); then REFUSALS+=("a serving swap is pending"); fi
  [ -n "$(saea_port_server_pids)" ] && REFUSALS+=("a llama-server is listening on port $SAEA_SERVING_PORT (stop the resident session first: its directory moves)")
fi

if [ -n "$LINK_COLD" ]; then
  LINK_COLD=${LINK_COLD%/}
  echo "migrate_data_root_ext4: link-cold $( [ $EXECUTE = 1 ] && echo EXECUTE || echo DRY-RUN ) $TARGET/{datasets,models} -> $LINK_COLD/{datasets,models}"
  rc=0
  for name in $COLD; do
    if [ ! -d "$LINK_COLD/$name" ]; then echo "  REFUSED: $LINK_COLD/$name is not a directory"; rc=3; continue; fi
    if [ -e "$TARGET/$name" ] && [ ! -L "$TARGET/$name" ]; then echo "  REFUSED: $TARGET/$name is a real directory (copy or move it, never shadow it)"; rc=3; continue; fi
    echo "  link  $TARGET/$name -> $LINK_COLD/$name (now: $(readlink "$TARGET/$name" 2>/dev/null || echo absent))"
    if [ $EXECUTE = 1 ]; then
      if [ ${#REFUSALS[@]} -gt 0 ]; then for r in "${REFUSALS[@]}"; do echo "  REFUSED: $r"; done; rc=3; break; fi
      ln -sfn "$LINK_COLD/$name" "$TARGET/$name" || rc=3
    fi
  done
  exit $rc
fi
echo "migrate_data_root_ext4: $( [ $EXECUTE = 1 ] && echo EXECUTE || echo DRY-RUN ) $(date -u +%FT%TZ)"
echo "  source  $SOURCE ($(saea_fs_type "$SOURCE"))"
echo "  target  $TARGET -> $(readlink -f "$TARGET" 2>/dev/null) (${target_fs:-absent})"
echo "  receipts $RECEIPTS"
echo "  subtrees ($(echo $LIST | wc -w)): $LIST"
[ -n "$LIVE_ROOT_REFUSAL" ] && REFUSALS+=("$LIVE_ROOT_REFUSAL")
for r in "${REFUSALS[@]}"; do echo "  REFUSED: $r"; done
if [ $EXECUTE = 0 ]; then
  for name in $LIST; do
    if [ -e "$SOURCE/$name" ] || [ -L "$SOURCE/$name" ]; then
      state=absent; [ -e "$TARGET/$name" ] && state=present
      line="  plan  $name (target $state)"
      if [ $MEASURE = 1 ]; then
        line="$line $(rsync -aH --dry-run --stats "$SOURCE/$name" "$TARGET/" 2>/dev/null | grep -E 'Number of regular files transferred|Total transferred file size' | tr -s ' ' | tr '\n' ';')"
      fi
      echo "$line"
    else
      echo "  skip  $name (not in the source)"
    fi
  done
  [ ${#REFUSALS[@]} -gt 0 ] && echo "  preflight: --execute would be REFUSED" || echo "  preflight: --execute would proceed"
  exit 0
fi
[ ${#REFUSALS[@]} -gt 0 ] && exit 3

# ---- execute ---------------------------------------------------------------------------------------------------
RUN_ID=run-$(date -u +%Y%m%dT%H%M%SZ)-$$
OUT=$RECEIPTS/$RUN_ID
mkdir -p "$OUT" || exit 3
STATUS=$OUT/subtrees.tsv
: > "$STATUS"

file_manifest() {  # <root> <name> <out>: "relpath<TAB>size<TAB>sha256" per regular file, sorted, relative to <root>
  ( cd "$1" && find "$2" -type f -print0 | sort -z |
      xargs -0 -r -n 64 -P "$JOBS" sh -c 'for f do printf "%s\t%s\t%s\n" "$f" "$(stat -c %s "$f")" "$(sha256sum "$f" | cut -d" " -f1)"; done' sh ) |
    LC_ALL=C sort > "$3"
}
symlink_inventory() {  # <root> <name> <out>: "relpath<TAB>target" per symlink
  ( cd "$1" && find "$2" -type l -print0 | sort -z | xargs -0 -r -n 256 sh -c 'for f do printf "%s\t%s\n" "$f" "$(readlink "$f")"; done' sh ) |
    LC_ALL=C sort > "$3"
}
failed=0
for name in $LIST; do
  [ -e "$SOURCE/$name" ] || [ -L "$SOURCE/$name" ] || { printf '%s\tskipped-absent\n' "$name" >> "$STATUS"; continue; }
  t0=$(date +%s)
  echo "== $name: rsync $(date -u +%T)"
  if [ -d "$SOURCE/$name" ] && [ ! -L "$SOURCE/$name" ]; then
    rsync -aH --numeric-ids "$SOURCE/$name/" "$TARGET/$name/" > "$OUT/$name.rsync.log" 2>&1; rc=$?
  else
    rsync -aH --numeric-ids "$SOURCE/$name" "$TARGET/" > "$OUT/$name.rsync.log" 2>&1; rc=$?
  fi
  [ $rc != 0 ] && { echo "   rsync rc=$rc (see $OUT/$name.rsync.log)"; printf '%s\trsync-failed-%s\n' "$name" "$rc" >> "$STATUS"; failed=1; continue; }
  # Absolute symlinks into the source root would resolve back to 9p (and fail confinement) after the cut-over.
  symlink_inventory "$TARGET" "$name" "$OUT/$name.symlinks.tsv"
  : > "$OUT/$name.symlinks-repointed.tsv"
  while IFS=$'\t' read -r rel dest; do
    case "$dest" in
      "$SOURCE"/*) new=$TARGET/${dest#"$SOURCE"/}; ln -sfn "$new" "$TARGET/$rel" && printf '%s\t%s\t%s\n' "$rel" "$dest" "$new" >> "$OUT/$name.symlinks-repointed.tsv" ;;
    esac
  done < "$OUT/$name.symlinks.tsv"
  echo "   hashing source and target $(date -u +%T)"
  file_manifest "$SOURCE" "$name" "$OUT/$name.source.sha256.tsv" &
  sp=$!
  file_manifest "$TARGET" "$name" "$OUT/$name.target.sha256.tsv"
  wait $sp
  files=$(wc -l < "$OUT/$name.source.sha256.tsv")
  bytes=$(awk -F'\t' '{s+=$2} END {printf "%d", s}' "$OUT/$name.source.sha256.tsv")
  if cmp -s "$OUT/$name.source.sha256.tsv" "$OUT/$name.target.sha256.tsv"; then
    verdict=verified
  else
    verdict=MISMATCH; failed=1
    LC_ALL=C comm -3 "$OUT/$name.source.sha256.tsv" "$OUT/$name.target.sha256.tsv" | head -n 50 > "$OUT/$name.difference.tsv"
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$verdict" "$files" "$bytes" \
    "$(sha256sum < "$OUT/$name.source.sha256.tsv" | cut -d' ' -f1)" "$(wc -l < "$OUT/$name.symlinks-repointed.tsv")" "$(( $(date +%s) - t0 ))" >> "$STATUS"
  echo "   $verdict: $files files, $bytes bytes, $(( $(date +%s) - t0 )) s"
done

python3 - "$OUT" "$SOURCE" "$TARGET" "$RUN_ID" <<'PY'
import json, sys, pathlib, datetime
out, source, target, run_id = pathlib.Path(sys.argv[1]), *sys.argv[2:5]
rows = []
for line in (out / "subtrees.tsv").read_text(encoding="utf-8").splitlines():
    parts = line.split("\t")
    row = {"subtree": parts[0], "verdict": parts[1]}
    if len(parts) == 7:
        row.update(files=int(parts[2]), bytes=int(parts[3]), manifest_sha256=parts[4],
                   symlinks_repointed=int(parts[5]), seconds=int(parts[6]))
    rows.append(row)
receipt = {
    "schema": "saea-data-root-migration-receipt-v1",
    "run_id": run_id,
    "written_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source": source, "target": target,
    "subtrees": rows,
    "all_verified": all(r["verdict"] in ("verified", "skipped-absent") for r in rows),
    "note": "Per-subtree <name>.source.sha256.tsv and <name>.target.sha256.tsv are the verification manifests the owner reads before any E: deletion (decision 284 step 3). The source was never modified.",
}
(out / "receipt.json").write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
print(f"receipt: {out / 'receipt.json'} all_verified={receipt['all_verified']}")
PY
[ $failed = 0 ] || exit 4
exit 0
