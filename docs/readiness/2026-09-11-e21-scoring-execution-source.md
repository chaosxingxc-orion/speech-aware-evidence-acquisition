# E21 post-seal scoring execution source

Use the unchanged shared scoring and analysis definitions from frozen /home/chao/saea-worktrees/e21-offline-repair-generation at commit 64440737a401b80805cfdd4f09d5a04748a3aad7. The older preparation v2 named a checkout path whose HEAD later advanced; preserve that preparation and use the additive execution-source handoff.

DATA/coordination/e21-offline-score-comparison-execution-source-v1.json has SHA-256 265476f1431d5c6c4beb7e639eabcccff589a3cca91ebe9022fbac3d9601fa9a. Root independently verified all eleven implementation bindings and both score-job hashes. The seven sources pinned by preparation v2 remain byte-identical; four execution dependencies are additionally pinned. No incompatibility was found.

The handoff provides exact existing-API commands and separate seal, score, saved-read, comparison and formal-hold prerequisites. Both manifests must seal before the root quality-read release, unless a formal hold closes the comparison. The repair manifest hash remains pending and must be measured after seal. Run complete scores sequentially, preserve per-sample statistics on the first score, then use the frozen whole-call primary and guards. Do not finalize attempts until complete score and cost receipts are available.

This source binding executes no scorer, model, tokenizer or encoder and reads no reference or hypothesis.
