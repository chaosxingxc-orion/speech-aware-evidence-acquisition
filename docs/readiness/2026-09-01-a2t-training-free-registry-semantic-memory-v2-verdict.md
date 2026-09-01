# Audio2Tool registry-semantic memory v2 — semantic state remains reward-inseparable

Date: 2026-09-01. Status: **RETROSPECTIVE SCREEN FAILED; STATIC SURFACE CLOSED**.
Experiment: `SAEA-A2T-MF-TFRL-REGISTRY-SEMANTIC-MEMORY-V2`. Artifact:
`docs/checks/speech-aware-evidence-acquisition/2026-09-01-training-free-a2t-registry-semantic-memory/policy-v2.json`.
Artifact self-hash: `a7fab72e77a60d047b2c222fbbbdd9866cf81a45350c89cbd0de09039b909583`.
File SHA-256: `a3458db3a5427fc746049c964bcde011c40f64a25eb7c2cef3f168caafee68e8`.

## Verdict

Adding the selected registry row's deployment-visible `domain/category` pair did not make safe
supply identifiable. Both registered candidates chose `STOP_DIRECT` on all 217 samples, saved zero
of the eight known conversions, harmed zero samples, issued zero second contacts, and produced zero
exact-match gain with grouped CI90 `[0.0, 0.0]`. Every fold had zero gain and the conjunctive
promotion screen failed. No prospective approximately-100-sample run, baseline change, G2 opening,
model contact, FINAL60 access, test access, Stage-3 activity, or paper-scale claim is authorized.

The state was live and materially different from v1. The coarse representation had 62 classes,
13 at the minimum support of five, with maximum support 18 and dominant share 0.0830. The detailed
representation had 83 classes, 11 at minimum support, with maximum support 17 and dominant share
0.0783. The semantic-state identity hash was
`e84edaa48db42829ae4c4f17e203c61b60e4d5bd19ec851516177b71d23bdfbe`.
The unchanged all-stop decision therefore reflects reward inseparability, not dead state.

## Why no cell was actionable

The strongest coarse cell, `smart_home/maintenance`, contained four saves and five harms in 13
samples. Its detailed one-key refinement contained the same four saves but still three harms in
seven samples. `smart_home/status` contained two saves and five harms in 11 samples. The remaining
positive cells were too sparse and retained fewer than two saves: detailed `smart_home/energy`
contained one save and zero harms in two samples, while unresolved `wearables/health_activity`
contained one save and zero harms in four samples. No cell simultaneously met support at least
five, saves at least two, and harms zero.

Relaxing support, save, or harm thresholds after seeing these returns would tune to this fully
adaptive discovery surface. Splitting by tool identity or another categorical registry field would
continue the same post-result search. The registered terminal rule therefore applies: categorical
and threshold search on these 217 logged rows is closed. A successor must obtain a genuinely new,
prospective runtime observation, such as a pre-answer self-consistency signal, under a new
ExecutionPlan and exposure registration before any core contact.

## Fidelity and evaluation efficiency

The v2 replay preserved the exact v1 217-row outcomes, five query-group folds, supply renderer,
actions, rewards, thresholds, and promotion gates. Source hashes and the predecessor self-hash all
matched. The final committed replay completed in 10.4 seconds; the focused suite passes 12 tests,
static checks pass, and the v2 core plus runner has 81% targeted line coverage.

Official scoring remains an indivisible per-run operation. When several complete runs require
scoring, `scripts/evaluate_parallel.sh` schedules those full official-scorer invocations in
parallel at the outer layer. It never shards one run and never averages shard scores. This replay
had only one complete run, so additional worker processes would add overhead without independent
jobs to schedule.

No model, embedding, tokenizer, HTTP, socket, audio, or GPU contact occurred. The 183
tool-selection failures, every unexposed Audio2Tool population, FINAL60, test annotations, and
future turns remain closed.
