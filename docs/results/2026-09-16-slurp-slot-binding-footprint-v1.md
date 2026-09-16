# SLURP slot-binding footprint and consumption gap

Date: 2026-09-16. Root analysis. Source-only, model-free, no task-quality read.
This is structural evidence for a distinct future system experiment, not a new flight.

## Measurement

The released slot store contains 54 cards, 402 observed intent/slot bindings and
80,049 UTF-8 bytes of full value bodies. All 60 legal candidate IDs in the pinned
Perception catalog match the released relation. The audit uses the actual shared
round-robin selector with per-candidate 16 and total 28 card caps.

Each hypothetical ordered distinct candidate set is enumerated exactly once. Keep
the same selected cards, their order and ALL global extraction, format, missing,
ambiguity and limitation text. Remove only semantic-role binding rows for other
intents. This is an ideal full-body calculation, before derived-view/provenance overhead.

| Distinct candidates | Ordered sets | Pooled body-byte reduction | Median per-set reduction | Full body maximum | Projected body maximum |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 60 | 47.0332% | 47.3191% | 33,226 bytes | 17,959 bytes |
| 2 | 3,540 | 44.6498% | 45.0021% | 43,720 bytes | 25,895 bytes |
| 3 | 205,320 | 42.5421% | 42.7433% | 50,579 bytes | 31,688 bytes |

Maxima in each column may come from different candidate sets. Pooled reduction is
one minus summed projected bytes divided by summed full bytes, not the mean of
per-set percentages. All 208,920 ordered sets were evaluated; none are sampled
experimental utterances. These weights do not represent the campaign's candidate
distribution, speakers, scenarios or quality.

The arithmetic was tested against actual rendering of projected structured rows,
including shared cards, order, caps and preserving all global fields. The real released
source was rebuilt and matched to its snapshot before enumeration. Snapshot content
hashes and physical file hashes are different identity types; the shared loader checks
the former for snapshots and the latter for release/source/catalog files.

Machine-readable measurements and source pins are in
[the receipt](2026-09-16-slurp-slot-binding-footprint-v1.json).

## Root interpretation

The source structure supports a substantial, separable candidate-binding projection.
It is not necessary to rewrite knowledge content to test this first. The opportunity
is about relevance and interpretation, not merely input length. Less cross-intent text
may reduce distraction and make it easier to apply the appropriate semantic role.
It may also remove a useful competing interpretation. That risk is especially relevant
when the correct intent is absent from the initial candidates.

The real interface loss is identifiable in code: the authored semantic-role relation
is collapsed to candidate-to-card IDs before consumption. A shared card is deduplicated
by ID; its first selecting candidate is not its only applicable candidate. Runtime
QueryState retains value IDs, and the renderer re-emits the complete card. The agent
thus has the text but lacks a source-bound view of which binding is relevant now.

This audit does not prove that the extra bindings caused any observed error. It does
not measure token counts, fit margin, model comprehension, latency or task benefit.
The older 525 correct-intent/nonexact-entity result motivates the task hypothesis but
does not attribute those cases to cross-intent interference.

## Source map

- Authored structure and exact complete rendering: rails/semantic_knowledge_build.py,
  _slot and build_slot_contract_snapshot.
- Source pin/rebuild and lossy relation: rails/candidate_semantic_supply.py,
  _released_candidate_index.
- Shared ordered selection: rails/knowledge_provider.py, select_candidate_semantic_values.
- Explicit Reviewer candidate scope: rails/released_target_index.py and
  rails/knowledge_target_lookup.py.
- Full canonical returns and retained QueryState rerender:
  rails/phase_tools.py, native result assembly and render_values.
- Source-bound role-history compilation happens separately in rails/runner.py,
  speech_binding. It currently receives evidence IDs, not structured slot bindings.

All paths above are under src/speech_aware_evidence_acquisition/.
The source map was independently inspected by a bounded reading agent; root owns the
measurement, interpretation and selected next design.

## Reproduce without a model service

From a WSL checkout, with that checkout's absolute src path in PYTHONPATH:

    python -B -m speech_aware_evidence_acquisition.analysis.slurp_slot_binding_footprint \
      --baseline configs/baseline/slurp-native-dual-store-train-fold-a-anchor-recovery-v1.json \
      --data-root "$SPEECHRL_DATA_DIR" \
      --output /tmp/slurp-slot-binding-footprint-new.json

The output must not exist; the command does not overwrite prior analysis. It reads the
specified released knowledge sources and the pinned candidate catalog. It does not load
campaign traces, answers, gold labels, reference transcripts or scorer outputs.

Validation: 30 focused source/analysis tests passed; Ruff and engineering-base checks
passed. Differential unit tests plus the real released-source CLI covered 89% of the
new module (combined statements/branches). A second CLI run reproduced the measurement
document exactly. No runtime experiment
configuration was changed. The failed typed-context recovery remains closed.
