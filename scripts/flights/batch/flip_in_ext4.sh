#!/bin/bash
# Run a model-free flip (re-pin) script inside an ext4 worktree instead of the 9p-mounted master checkout, then fast-forward master.
#
# Why: on this host the flip chains spend 40-80 minutes per package almost entirely in filesystem latency on /mnt/d (the CLI import is
# 38 s cold there against 0.84 s on ext4; `git status` 7.6 s against 0.39 s). The registered hashes are CONTENT hashes of files, so an ext4
# checkout of the same commit yields identical bytes, and every commit made in the worktree keeps its hash when master fast-forwards to it.
#
# Usage:  bash scripts/flights/batch/flip_in_ext4.sh <flip-script> [args...]
#   <flip-script> is repo-relative (scripts/flights/direct/direct_fb_flip.sh) or an absolute path under master; it is run from the
#   WORKTREE copy with SAEA_MAIN (and MAIN) pointing at the worktree, so every `cd $MAIN`, git call, PYTHONPATH and --repo-root in the
#   flip scripts addresses the ext4 tree. Environment (DIRECT_FB_KINDS, TFRL_ITER, TFRL_ONLY, ...) passes through unchanged.
# Examples:
#   DIRECT_FB_KINDS="instruct replicate" bash scripts/flights/batch/flip_in_ext4.sh scripts/flights/direct/direct_fb_flip.sh
#   TFRL_ITER=2 bash scripts/flights/batch/flip_in_ext4.sh scripts/flights/tfrl/tfrl_i1_flip.sh column
# Refuses (exit): 64 the worktree resolves under /mnt/ (SAEA_ALLOW_9P_FLIP=1 overrides); 2 usage / unknown script; 3 a batch driver, flight CLI, or another flip is alive; 4 master tracked tree dirty;
#   5 worktree cannot be fast-forwarded to master HEAD (or is dirty); 6 the flip script failed (master untouched, worktree kept for
#   inspection); 7 master moved while the flip ran (no merge is ever attempted; the flip branch is kept); 8 fast-forward failed.
# Never merges, never pushes. Timings per step go to stdout as `[flip_in_ext4] step=<name> seconds=<n>`.
# Env: SAEA_FLIP_MASTER (default the /mnt/d study path), SAEA_FLIP_WORKTREE (default /home/chao/saea-worktrees/fable-flip),
#      SAEA_FLIP_SKIP_ALIVE_CHECK=1 (tests only).
MASTER=${SAEA_FLIP_MASTER:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
WT=${SAEA_FLIP_WORKTREE:-/home/chao/saea-worktrees/fable-flip}
T0=$(date +%s)
tick() { local n; n=$(date +%s); echo "[flip_in_ext4] step=$1 seconds=$((n - ${TS:-$T0}))"; TS=$n; }
TS=$T0
[ $# -ge 1 ] || { echo "usage: flip_in_ext4.sh <flip-script> [args...]" >&2; exit 2; }
SCRIPT=$1; shift
case "$SCRIPT" in "$MASTER"/*) SCRIPT=${SCRIPT#"$MASTER"/} ;; esac
case "$SCRIPT" in /*) echo "refusing: flip script must be repo-relative or under $MASTER" >&2; exit 2 ;; esac

# (a) refusals
case "$(realpath -m "$WT")" in /mnt/*) [ "$SAEA_ALLOW_9P_FLIP" = 1 ] || { echo "refusing: worktree $WT is on /mnt (9p); use an ext4 path or set SAEA_ALLOW_9P_FLIP=1"; exit 64; } ;; esac
if [ -z "$SAEA_FLIP_SKIP_ALIVE_CHECK" ]; then
  ALIVE=$(pgrep -af 'batch_driver\.sh|core\.flight\.cli|repin_loop_generic\.sh|repin_cell\.py|repin_package_one_pass\.py|scripts/flights/[a-z0-9_/]*(_flip|flip_all|flip_both)[a-z0-9_]*\.sh' | grep -v 'pgrep\|flip_in_ext4' | grep -v "^$$ \|^$PPID ")
  if [ -n "$ALIVE" ]; then echo "refusing: a batch driver, flight CLI or another flip is alive:"; echo "$ALIVE" | head -5 | cut -c1-200; exit 3; fi
fi
DIRT=$(git -C "$MASTER" status --porcelain --untracked-files=no)
if [ -n "$DIRT" ]; then echo "refusing: master has tracked changes:"; echo "$DIRT" | head -5; exit 4; fi
MHEAD=$(git -C "$MASTER" rev-parse HEAD) || exit 4
MBRANCH=$(git -C "$MASTER" symbolic-ref -q --short HEAD) || { echo "refusing: master is on a detached HEAD"; exit 4; }
tick checks

# (b) worktree at master HEAD on a throwaway branch
STAMP=$(date -u +%Y%m%dT%H%M%SZ); BR=flip/$STAMP
if [ -d "$WT/.git" ] || [ -f "$WT/.git" ]; then
  OLD=$(git -C "$WT" rev-parse HEAD) || exit 5
  OLDBR=$(git -C "$WT" symbolic-ref -q --short HEAD)
  if [ -n "$(git -C "$WT" status --porcelain --untracked-files=no)" ]; then echo "refusing: worktree $WT has tracked changes"; exit 5; fi
  if ! git -C "$WT" merge-base --is-ancestor "$OLD" "$MHEAD"; then
    echo "refusing: worktree HEAD ${OLD:0:9} is not an ancestor of master HEAD ${MHEAD:0:9}; cannot fast-forward"; exit 5
  fi
  git -C "$WT" checkout -q -b "$BR" "$MHEAD" || { echo "refusing: cannot move worktree to master HEAD"; exit 5; }
  case "$OLDBR" in flip/*) git -C "$MASTER" branch -D "$OLDBR" >/dev/null 2>&1 ;; esac
else
  git -C "$MASTER" worktree add -q -b "$BR" "$WT" "$MHEAD" || { echo "refusing: cannot create worktree $WT"; exit 5; }
fi
[ "$(git -C "$WT" rev-parse HEAD)" = "$MHEAD" ] || { echo "refusing: worktree HEAD != master HEAD"; exit 5; }
tick worktree
[ -f "$WT/$SCRIPT" ] || { echo "refusing: $SCRIPT is not tracked at master HEAD ${MHEAD:0:9}" >&2; exit 2; }

# (c) run the flip from the worktree copy
MARK=$(mktemp /tmp/flip_in_ext4.mark.XXXXXX)
export SAEA_MAIN=$WT MAIN=$WT
(cd "$WT" && bash "$WT/$SCRIPT" "$@"); RC=$?
tick flip_script
if [ $RC -ne 0 ]; then echo "flip script exited $RC; master untouched; worktree $WT kept on $BR for inspection"; rm -f "$MARK"; exit 6; fi
NEW=$(git -C "$WT" rev-parse HEAD)

# (d) fast-forward master (never a real merge)
if [ "$(git -C "$MASTER" rev-parse HEAD)" != "$MHEAD" ]; then
  echo "refusing: master moved from ${MHEAD:0:9} to $(git -C "$MASTER" rev-parse --short HEAD) during the flip; branch $BR kept"; rm -f "$MARK"; exit 7
fi
if [ "$NEW" != "$MHEAD" ]; then
  if [ -n "$(git -C "$MASTER" status --porcelain --untracked-files=no)" ]; then echo "refusing: master became dirty during the flip; branch $BR kept"; rm -f "$MARK"; exit 7; fi
  git -C "$MASTER" merge --ff-only -q "$BR" || { echo "fast-forward of master failed; branch $BR kept"; rm -f "$MARK"; exit 8; }
fi
FF=$(git -C "$MASTER" rev-parse HEAD)
# flight-commit files written by the flip scripts during this run get the ff'd HEAD (identical to the worktree HEAD by construction)
for f in $(find /home/chao -maxdepth 1 -name '*flight-commit.txt' -newer "$MARK" 2>/dev/null); do
  echo "$FF" > "$f"; echo "[flip_in_ext4] flight-commit file $f = ${FF:0:12}"
done
[ -z "$SAEA_FLIP_COMMIT_FILE" ] || { echo "$FF" > "$SAEA_FLIP_COMMIT_FILE"; echo "[flip_in_ext4] flight-commit file $SAEA_FLIP_COMMIT_FILE = ${FF:0:12}"; }
rm -f "$MARK"
# detach the worktree from the throwaway branch so it can be deleted; the worktree stays at FF for reuse
git -C "$WT" checkout -q --detach "$FF" && git -C "$MASTER" branch -D "$BR" >/dev/null 2>&1
tick fast_forward
echo "[flip_in_ext4] master $MBRANCH: ${MHEAD:0:9} -> ${FF:0:9} (total $(( $(date +%s) - T0 )) s)"
