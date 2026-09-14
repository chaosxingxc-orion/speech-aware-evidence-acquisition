# Initial intent support from actual native requests

Date: 2026-09-14. This is an offline source-bound diagnostic, not an experiment,
scorer, optimization reward or launch authorization.

## Decision use

Separate whether the gold intent's authored value was actually supplied to
initial Perception from whether gold entered its C0 shortlist. Report four
mutually exclusive full-cohort cells: supplied-and-covered, supplied-but-missed,
not-supplied-but-covered and neither. Report explicit denominators for the
two conditional coverage rates. An empty condition has a null rate.

This statistic measures the gold intent's own card, not all semantically useful
knowledge. Another intent's card can contain a relevant contrast even when the
gold intent's own card is absent. Do not classify every missing-own-card case
as a retrieval failure.

A supplied value does not prove attention, understanding, semantic use or
causal contribution. Missing supply does not impose an accuracy ceiling: the
frozen model can select a legal label without that particular knowledge value.
The diagnostic therefore informs the choice between retrieval, discriminative
value content and evidence acquisition; it does not by itself choose a winner.

## Source and join

Reuse project_verified_native_candidate_stages to locate C0, the first actual
Perception contact. Read only that manifest-verified request's supplied_evidence.
Validate request/sample identity and canonical payload hash. Require the
declared intent-boundaries store, a value-only Perception supply route and
frozen snapshot/release pins. Map each selected value by the configured exact
qualified store ID and legal intent-ID suffix, never by parsing content prose.

Cross-check complete ordered evidence IDs against the initial QueryState and
its paired ORG/SUPPLY/USE records. Require the C0 query-state hash, the exact
knowledge-snapshot source URI, nonempty content, value role and unique IDs.
Ignore other supplied value stores for intent-support counting, while preserving
the complete source-order check. Do not read future supply or candidate unions.

The offline reference join uses exactly the complete source roster in order.
Persist numeric flags, source hashes and counts, with no gold label/reference
strings or transcripts in the diagnostic output. The parent sidecar retains
the complete official score and reward-source custody.

## Shared configuration

Use analysis.native_train_stage_diagnostics after a finalized source and its
first complete official score are released. Keep the existing native_source,
reward_source and reference_source pins and add both optional fields below:

~~~json
{
  "candidate_stage_projection": {
    "schema": "saea-native-candidate-stage-projection-config-v1",
    "policy_id": "first-perception-and-last-before-delivered-solver-v1",
    "candidate_projection_policy": "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
  },
  "initial_intent_support_projection": {
    "schema": "saea-initial-intent-support-projection-v1",
    "policy_id": "initial-perception-request-intent-value-id-suffix-v1",
    "store_id": "intent-boundaries",
    "value_id_prefix": "intent-boundary:"
  }
}
~~~

The public module uses --config, --config-sha256, --source-repo-root and --output.
The source checkout must remain clean at the generating commit. Pin the
diagnostic implementation separately. Omitted options preserve the existing
C0-only and C0/C1 output paths. The optional support section also binds its
implementation hash in the prepared artifact; warm reuse verifies all inputs.

## Validation and boundaries

Tests were written before implementation. Seventy-eight affected synthetic
tests pass, including actual native stage projection, shared sidecar joins,
source verification and query-state replay. The new support module reaches
95% branch-aware coverage. Ruff and engineering-base checks pass; no exception
list was enlarged. These are engineering checks, not observed TRAIN results.

The installed coverage module measured coverage without installing or changing
dependencies. An initial pytest-cov invocation was rejected because that plugin
is not installed; no test or model contact ran in that rejected invocation.

No active TRAIN outcome, reference or partial score was read to design or test
this projection. No model, tokenizer, ASR, encoder or official scoring contact
is authorized by this document. Keep the running anchor and model service
unchanged. Use one complete scorer pass owned by the existing campaign.
