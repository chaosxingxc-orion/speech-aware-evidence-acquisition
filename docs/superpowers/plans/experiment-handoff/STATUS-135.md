# STATUS-135: primary parameter attribution and identifier evidence gap

Date: 2026-09-15. CPU-only closure. Keep the owner GPU hold, resident memory,
prior generation/scoring/outcome artifacts and held successor configs unchanged.
No new model, actual fit/tokenizer, encoder, runtime analytical-tool, scorer
or service contact occurred.

## New evidence

Implementation commit 8e2c16950b61629362f9d7346d78af3cb2a96814 adds a shared primary-parameter
diagnostic entry and pure helper. All4000 IDs agree with both original first-score
primary parse/name facts, normalized correct/predicted/reference key counts,
parameter exactness and official exactness. The official parser/normalizer are
reused; no scorer or compute_parameter_accuracy is invoked.

In the same2089 rows where both arms select the correct primary tool:

- Official exact rises665->829.
- Wrong-value samples fall950->784; wrong-value keys fall1205->941.
- Extra-key samples fall472->451.
- Missing-key samples rise107->131.
- System deviceId errors account for583/941 remaining wrong keys.

Do not add overlapping error sample counts or generalize conditional results to
a causal component effect. This PRIMARY-call analysis is distinct from the
earlier1250 full-call failures. Preserve natural, equal-tier, equal-domain and
all tier/domain counts. The equal-domain omission direction differs from the
natural/equal-tier direction.

Both existing parsers give identical official-normalized parameter maps for
all2089 common-primary-correct rows and all2337 system-primary-correct rows.
Repo numeric/boolean coercion resolves zero system wrong-value keys. These
narrow formatting diagnostics do not explain the main residual value gap.

A public source audit finds43 tools with a published deviceId default, and zero
of those ID literals in the own parameter card, any parameter card or the complete
compact tool registry. The current value supplies role/type/constraints and
synthetic examples but omits this published value evidence. Of583 common-cohort
system deviceId errors,376 references equal the public default and207 do not.
This is a concrete source-projection gap, not proof that a public default is the
requested device or a valid live-inventory resolution.

## Root decision and boundary

Retain the parameter-meaning direction. A subsequent candidate extension should
investigate source-bound parameter values/identifier evidence and request-to-value
binding, using existing target-knowledge/store seams. Preserve public defaults as
labelled source priors/examples, never a blanket filling rule. Evaluate explicit
omission/default tradeoffs. Inspect permitted construction sources before building
binding rules; evaluation aliases and error pairs never enter runtime memory.

The new evidence does not authorize editing or replacing the frozen scope-tools
pair. Keep the prepared SLURP broad/factored TRAIN-A first after explicit owner
GPU resume, then admit the prepared A2T pair and E21 transfer. Further work must
have clear decision use rather than repeat completed preparation or source audits.

Root analysis:
[primary parameter report](../../../results/2026-09-15-a2t-primary-parameter-attribution-v1.md).
Aggregate:
[diagnostic artifact](../../../results/2026-09-15-a2t-primary-parameter-attribution-v1.json).
All raw parameter/example values remain outside Git and analysis-only.

## Verification and remaining objective

25 new focused tests pass;54 pass including reused source-projection tests.
The pure helper has100% statement coverage. Ruff, engineering-base and whitespace
checks pass; actual full4000 source projection succeeded once. Root verification
SHA-256 bcfd2c34710265f92aeaf50513b0fa69006886d6c01c9f6b017342bd6f747fe9.

Original verdict remains PRIMARY_GAIN_TOOL_GUARD_FAILED_NOT_ADOPTED.
Stable replicated benefit, actual held-flight capacity, E21 transfer and later
algorithmic training-free trajectory optimization remain unproven. This root
engineering/analysis is not RL. Do not mark the research goal complete.
