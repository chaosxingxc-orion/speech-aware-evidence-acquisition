#!/bin/bash
# Usage: wt_create.sh <name>  -- a fresh worktree fable-<name> on branch fable/<name> from the study HEAD (agents work there, never on master).
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
cd $MAIN || exit 1
for n in "$@"; do git worktree add -q -b fable/$n /home/chao/saea-worktrees/fable-$n HEAD && echo "worktree fable-$n at $(git -C /home/chao/saea-worktrees/fable-$n rev-parse --short HEAD)"; done
