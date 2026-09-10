# E21 DR saved-score analysis admission

This note registers the analysis route before reading any outcome from the two
current DR generation parents. It authorizes no model, encoder, tokenizer, or
additional official scorer contact. Read and verify each complete manifest once
through the existing scoring batch entry, retaining per-sample statistics on
that first score. The current unit parent is running; the self parent is READY.
Both parents use the same formal-packet decoder-only service and frozen inference
checkout. Preserve that checkout until their generation and scoring are closed.

## Complete result set and provenance

Report all four predeclared deliveries: unit constrained, unit free, self
constrained, and self free. Preserve both raw generation parents. Charge each
parent once and label its two deliveries as correlated deterministic derivatives.
Do not select a delivery for reporting after seeing its score.

Use the existing complete-score receipt to bind the manifest, output, scorer
set, full 44-call coverage, and result bytes. The additive
saea-conec-alignment-v1 per-sample payload saves the exact normalized reference
and hypothesis words, operations, transferred owners, and entity types already
computed by the ConEC scorer. It changes no metric. These large artifacts remain
outside Git, under the study data root.

Recover derived windows with the shared delivery rule and the derivative's
verified terminal-window provenance. Do not interpret the parent's constrained
text as a free-delivery result. Partition the saved official alignment through
analysis.e21_window_pairing, verify whole-call stitch identity and every pooled
ConEC bucket, and require exactly 1,593 windows and 44 calls. This analysis opens
no reference layer and invokes no official scorer.

Whole-call numeric bag matching remains authoritative. Report window matching
only as a stricter descriptive decomposition and retain its measured shortfall.
Semantic high-impact rates retain their frozen taxonomy and remain advisory.

## Estimators and inherited decision rules

Preserve the inherited pairing: fixed windows paired across results, calls as
bootstrap clusters, seed 20260903, 10,000 replicates, CI90. Report natural pooled
ratios, equal-call means, equal-sector and equal-sample-rate weighting, and
descriptive strata.
Do not present 1,593 windows as 1,593 independent calls. The construction34 and
evaluation10 reporting slices remain separate; evaluation10 is descriptive and
does not receive an effectiveness interval. Keep the OBS harm-stratum reports
descriptive. Empty denominator strata are unavailable, not perfect scores.

Use a common positive-gain convention: for error rates, gain is comparator
minus cell; for numeric accuracy, gain is cell minus comparator. The original
DR configuration's PERSON phrase LB(cell - comparator) is a sign transcription
defect: the pre-registration explicitly defines positive as fewer errors in
section6, and section6.1 gives LB(delta PERSON) >= -0.25009. Preserve the original
file and use that explicit definition. This correction is made before reading
the current results; it changes neither margin nor decision intent.

For each delivery versus the sealed comparator, report the inherited rule:

- Admit the observe-plus-refresh module only when the call-clustered corpus-WER
  gain lower bound is strictly greater than zero, PERSON gain lower bound is at
  least -0.25009 percentage points, and all applicable guards pass.
- Add the PERSON-improvement conclusion only when its gain lower bound exceeds
  zero.
- Require non-entity gain lower bound at least -0.06475 points, numeric-accuracy
  gain lower bound at least -0.15651 points, and insertion-rate increase upper
  bound at most +0.02218 points.
- Verify delivery integrity for both constrained derivatives and complete
  window coverage for every derivative. Free delivery has no substitution-only
  integrity guarantee; deletions and insertions remain measured outcomes.
- Treat an interval including zero as no demonstrated gain; report a wholly
  negative corpus-WER interval as directional harm, not an affirmative null.

The short-unit-draft attribution leg is unit versus self under the same delivery
rule, requiring positive lower bounds for the named corpus-WER and PERSON gains
to attribute the benefit to draft source. Lack of that evidence does not erase
a separately admitted refresh result. Report comparisons with OBS-E1 and
KC-E1f as inherited secondary analyses.

Historical raw-audio comparators and current formal-packet parents have distinct
protocol identities. Preserve this limitation in every interpretation; the
four-window bridge proves engineering connectivity, not full quality
equivalence. The matched current unit/self contrast isolates draft source within
the current route. If a named protocol mismatch would change the decision,
identify the minimum useful matching control before adding generation.

## Execution boundary

Use configuration plus the shared analysis entry points. Root owns analysis
configuration, gate interpretation, and the final verdict. Complete official
score jobs run one at a time and may overlap the next eligible generation.
Do not mutate the active inference checkout, rescore incomplete manifests,
rewrite historical outputs, or expand the model experiment to keep the GPU busy.

## Prepared executable inputs

The full44 metadata preparation receipt is external at
/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-E21-DR-PACKETS-SAVED-SCORE-ANALYSIS-V1/metadata-preparation-receipt.json.
It binds the registered44-call roster and the existing comparator window roster.
Window metadata SHA256: 1c5a7c34e208a4148aa1d2d92f97f2116667285cd77dccdaa5ac990335046e75.
Call metadata SHA256: 5631d6fee9ba032f95abdabf2f9ec9e7fc680b6fe9deb48cc37e50d72a12af23.

configs/experiment/e21-dr-packets-window-contrasts-v1.json freezes the complete
contrast list and metric definitions. Its four future input hashes intentionally
remain null while generation is incomplete; the hash-pinned shared reader refuses
them. Bind measured saved-statistics hashes after each complete score and do not
change the contrast list from the observed outcomes. The entry is
python -m speech_aware_evidence_acquisition.analysis.pooled_ratio_compare CONFIG OUTPUT.
The window-statistics preparation entry is
python -m speech_aware_evidence_acquisition.analysis.e21_score_window_read --config CONFIG --output OUTPUT.

The generic ratio reader supports a summed numerator over existing nested count
fields, preserving the historical entity-class row bytes. Undefined pooled
bootstrap draws produce an unavailable interval without redrawing or substituting
a value. A single zero-denominator call does not disable all otherwise-defined
pooled draws.

Whole-call companion configurations are now prepared as
configs/experiment/e21-dr-packets-call-numeric-contrasts-v1.json and
configs/experiment/e21-dr-packets-call-error-contrasts-v1.json. They bind existing
complete44-call comparator, OBS-E1 and KC-E1f score reads without rerunning a
scorer. The numeric guard uses whole-call matched/expected counts. Error-rate
call contrasts provide the secondary OBS-E1 read and the mathematically
equivalent pooled call-cluster check beside the fixed-window report. Save
ConEC per-call counts in the window-statistics artifact, excluding the large
alignment word arrays; the original score receipt remains their source.
All four current input hashes remain unbound until their actual full scores exist.


## Root clarification before current score access: inherited equal-call reading

The DR pre-registration section 5 inherits the KC-E1f estimator without moving
it. The historical implementation in scripts/e21_kc_e1f_verdict_read.py,
_equal_stratum_statistic, means equal weight per call with a positive metric
denominator in both arms. It resamples the complete call roster and retains the
multiplicity of each drawn call. Sector and sample-rate equal weighting are
additional descriptive sensitivities; they do not replace this inherited
equal-call reading.

The shared pooled-ratio configuration now explicitly enables
include_equal_cluster_mean. It aggregates each metric inside a call before
averaging call rates, reports excluded zero-denominator calls, and uses the
same complete roster, seed and draws as the natural call-cluster bootstrap.
A realized draw containing no eligible call produces an unavailable interval,
rather than a fabricated zero. A synthetic unequal-window-count comparison
matches the historical estimator's point estimate, interval and standard
deviation. No current DR quality outcome was read to choose this method.

Read the E21-specific natural-mixture primary literally, as stated in the
KC-E1f v2 redecision section 4. Report the same numerical guard checks for the
equal-call sensitivity beside it; do not invent new equal-call margins or
require a second positive confidence lower bound that the primary does not
name. Retain the broader program's sign-agreement requirement: a positive
natural-mixture primary with an opposite equal-call point estimate does not
support an unqualified admitted effectiveness claim. Label such a conflict
explicitly rather than silently selecting a weighting. If a guard changes
pass/fail by weighting, preserve the natural primary result and name the
sensitivity before choosing any downstream component. Root owns that review.
This clarification changes neither generation, roster, budget, nor thresholds.


## Bounded parallel execution of unchanged contrasts

A model-free synthetic timing measured 99.665 seconds for one metric across
1,593 rows, 44 uneven call clusters, both descriptive groupings and 10,000
replicates. The 60 declared window-metric comparisons would take approximately
100 minutes serially on that measurement. The window comparison configuration
therefore requests four worker processes for independent complete contrasts.
Each contrast retains its original inputs, estimator, seed and replicate count.
The shared entry preserves declaration order and records requested/effective
concurrency. A serial-versus-two-process fixture produces identical contrast
results. This changes computation scheduling only.

During a GPU campaign, reserve four workers for window comparisons, at most one
for the sequential call-level comparison jobs, and at most three for any
overlapping preparation. Their total does not exceed the owner's global eight
worker limit. Full official scoring remains one job at a time; it is not sharded.
