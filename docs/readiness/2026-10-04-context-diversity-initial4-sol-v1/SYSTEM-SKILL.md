# Versioned four-node spoken-language system skill

Version: initial4-sol-v1. Status: prospective draft, not runtime admitted or selected by reward.
Author: GPT-6.1 Sol, through the human-authorized engineering subagent. This is a system-context
package consumed through the existing policy compiler; it is not an installed Codex skill.

The trainable document surface is the full independent Perception, Solver, Reviewer and Planner
instruction set together with implemented assembly options. Preserve the frozen answering core,
original legal output schemas, tools, one-lookup/one-revision controls, knowledge, dataset and
Solver final-answer authority. Treat each complete system version as immutable during evaluation.
Record its ancestry, rationale, rejected alternatives and any later acceptance decision explicitly.

Microsoft SkillOpt treats structured natural-language skill documents as the editable state and
applies candidate changes through a validation gate. This package borrows coherent document
organization, explicit edits and retained history; it does not implement or replicate SkillOpt's
optimizer and adds no third algorithm comparison. See the official
[skill-document guide](https://github.com/microsoft/SkillOpt/blob/main/docs/guide/skill-document.md).

## Four complete prospective systems

The candidate index pins each complete bundle, assembly choice, compiled baseline and all four
content-addressed role texts. Every role is a full replacement, not a prefix/suffix patch. Review
the actual text files linked below before publication. The four systems are distinct hypotheses;
their ordering does not encode a measured rank.

| System | Coherent edit rationale | Placement | Tool presentation | Reviewer history |
| --- | --- | --- | --- | --- |
| speech-evidence | Align intent, extraction and review with concrete speech-supported uncertainty; keep local review focused on the current draft. | before-speech-v1 | per-role | latest-solver-and-local-tools |
| coverage-ledger | Check both emitted-entity support and missing-mention coverage; preserve completed checks separately from unresolved findings. | historical | constant | full |
| counterexample-check | Test an anchored alternative explanation before revision; avoid cascading historical criticism. | before-speech-v1 | constant | latest-solver-and-local-tools |
| semantic-frame | Resolve intent and entity roles as one request frame; use history to track which semantic doubt is already resolved. | historical | per-role | full |

Each Perception retains one to three legal scenario_action candidates using the exact registered
compact JSON. Each Solver chooses among those original candidates and emits the exact task JSON.
Each Reviewer uses exactly findings/checked with the registered fields, kinds and list limits.
Each Planner uses the native tool interface and ends with exactly ACCEPT or REVISE. Examples and
knowledge associations never establish speech presence. Tools cannot answer the task or change
the final-answer authority.

Read all node texts for each system:

- speech-evidence: [Perception](../../../configs/probes/system-text-policy/3de7e312b42632f7358f381bb27072459d4d19754f2c5bf73a341c667a686303/perception.txt), [Solver](../../../configs/probes/system-text-policy/3de7e312b42632f7358f381bb27072459d4d19754f2c5bf73a341c667a686303/solver.txt), [Reviewer](../../../configs/probes/system-text-policy/3de7e312b42632f7358f381bb27072459d4d19754f2c5bf73a341c667a686303/reviewer.txt), [Planner](../../../configs/probes/system-text-policy/3de7e312b42632f7358f381bb27072459d4d19754f2c5bf73a341c667a686303/planner.txt).
- coverage-ledger: [Perception](../../../configs/probes/system-text-policy/929b0e7ccbebebca16c968d8a20782a790cae547077870657c085d702379eb4f/perception.txt), [Solver](../../../configs/probes/system-text-policy/929b0e7ccbebebca16c968d8a20782a790cae547077870657c085d702379eb4f/solver.txt), [Reviewer](../../../configs/probes/system-text-policy/929b0e7ccbebebca16c968d8a20782a790cae547077870657c085d702379eb4f/reviewer.txt), [Planner](../../../configs/probes/system-text-policy/929b0e7ccbebebca16c968d8a20782a790cae547077870657c085d702379eb4f/planner.txt).
- counterexample-check: [Perception](../../../configs/probes/system-text-policy/fd9183d44243005bf027af8b14316a5a2111fece88cd1838fde1ec2564bf2e09/perception.txt), [Solver](../../../configs/probes/system-text-policy/fd9183d44243005bf027af8b14316a5a2111fece88cd1838fde1ec2564bf2e09/solver.txt), [Reviewer](../../../configs/probes/system-text-policy/fd9183d44243005bf027af8b14316a5a2111fece88cd1838fde1ec2564bf2e09/reviewer.txt), [Planner](../../../configs/probes/system-text-policy/fd9183d44243005bf027af8b14316a5a2111fece88cd1838fde1ec2564bf2e09/planner.txt).
- semantic-frame: [Perception](../../../configs/probes/system-text-policy/612d7cc4ba6b46d145e3e20ce9e4afd0185617f622604c04099d13dc7a75e091/perception.txt), [Solver](../../../configs/probes/system-text-policy/612d7cc4ba6b46d145e3e20ce9e4afd0185617f622604c04099d13dc7a75e091/solver.txt), [Reviewer](../../../configs/probes/system-text-policy/612d7cc4ba6b46d145e3e20ce9e4afd0185617f622604c04099d13dc7a75e091/reviewer.txt), [Planner](../../../configs/probes/system-text-policy/612d7cc4ba6b46d145e3e20ce9e4afd0185617f622604c04099d13dc7a75e091/planner.txt).

## Deterministic rollout mapping

N is the number of distinct inputs. K is the number of distinct complete prompt/assembly systems
run on each input. M is four nodes within each system. Initial N20/K4/M4 means 80 complete system
trajectories and at least 320 initial node visits if every trajectory completes. Legal revisions,
tool use and internal steps add work; M is not a maximum contact count. A failed trajectory can
end before its planned node visits and must still remain in the accounting denominator.

Map rollout indices 0/1/2/3 to speech-evidence/coverage-ledger/counterexample-check/semantic-frame
respectively for every input in the first20 of the same UPDATE2 ordered400 pool. Freeze each
bundle version within the run. K already counts the distinct candidate systems in an iteration;
never multiply by candidate count again. Separate algorithms, iterations and control trajectories
need their own additional accounting. Preserve temperature0 and seed20260913. Context variation supplies the exploration;
do not silently enable stochastic sampling. The requested distinct-input ladder is
20,80,160 then50,200,400 on the same pool, with K separate and each stage reviewed independently.
No larger stage is admitted here, and human review before8x400 remains in force.

Record every cold/warm/unknown cache condition and every failure. Report actual all-sample and
non-first sample latency without trimming slow rows, alongside official whole-system quality,
intent protection and reliable completion. Keep preparation, FIT, persistence and official scoring
costs explicit, without double-counting FIT already inside settled-workflow timing. No latency,
quality, formal budget admission or benefit has been observed in this package.

## Algorithm adapters and source fidelity

Training-Free GRPO's original method samples multiple rollouts under the same policy and E,
summarizes them, extracts semantic advantage only for groups with clear winners/losers, and
updates E with add/delete/modify/keep operations. K distinct deterministic context systems are
an adaptation, not exact same-policy reproduction. A future semantic adapter must preserve
terminal-reward custody and experience-version identity; existing numerical standardized
feedback is not that learner. See [the original paper, section2](https://arxiv.org/html/2510.08191v1).

GEPA's prospective adapter needs reflective component mutation and per-example candidate Pareto
selection, using the full role texts and supported assembly fields as editable components. It
must retain trial history and rejected candidates rather than relabeling a numerical GRPO
statistic as reflection. No such learner is implemented by this package. Root is separately
pinning [the official implementation](https://github.com/gepa-ai/gepa).

The existing optimizer_experience list is provenance metadata; the current compiler does not
automatically render it into a role context. Any experience insertion must become explicit,
versioned full role text through a reviewed adapter. Compression and progressive loading are
unsupported future changes; do not advertise them as implemented assembly choices.

## Publication and review boundary

The new data-root metadata archive `system-text-search/context-diversity-initial4-sol-v1`
contains four draft bundles and two byte-preserved seed/ancestor copies so the shared archive
loader can verify complete ancestry. Large ancestry stays outside Git. The compact
candidate-edits-v1.json contains all16 full texts and exact edit/seed/archive identities for review
and reconstruction. Its data-root binding pins are verified metadata, not runtime admission.
Earlier independent root verification used repository staging; the final data-root verification is
recorded separately and root must repeat it before integrating the execution materials.

Four compiled baseline fragments and 16 content-addressed role text files are ready for review.
The baseline fragments are policy-compilation templates, not UPDATE2 execution configurations.
They intentionally preserve the interface seed's legacy R01C query/supply fields, inherited
prepared_phase_supply/FIT identities and historical what_this_is text for compiler roundtrip
verification. These inherited identities are not N20 supply readiness or current runtime evidence.
Per-member execution preparation must bind the current UPDATE2 queries and each system's own
immutable warm-verified supply, supersede stale FIT/supply identities and verify the actual composed
four-slot/queue4 configuration. This package builds no supply and admits no runtime cell.
No new experiment cell, exposure entry, registered recipe, proposal slot, archive panel freeze,
model/tokenizer/scorer call, service or queue operation is created. The old Astra proposals and
the paused round9 six-member comparison remain unchanged. Root must review, reconcile the
adapted baseline protocol, supply/geometry bindings, actual request FIT and structural proof
before any contact. Do not select a best skill until qualified evidence exists.

See candidate-edits-v1.json, candidate-index-v1.json, initial20-budget-draft-v1.json,
history-v1.json and audit-v1.json.
