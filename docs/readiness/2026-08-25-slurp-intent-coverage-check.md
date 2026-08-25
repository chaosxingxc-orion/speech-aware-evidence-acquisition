# SLURP intent-coverage check — the docstring was wrong, the KB is not

Exposure row `SAEA-SN-MF-SLURP-INTENT-COVERAGE-CHECK` (`model-free-check`), registered at commit
`8c1aa59e` **before any computation**. Module
`src/speech_aware_evidence_acquisition/analysis/slurp_intent_coverage_check.py`; receipt
`docs/checks/speech-aware-evidence-acquisition/2026-08-25-slurp-intent-coverage/intent-coverage-report.json`
(sha256 `de1e9778795fc6b0d02445a53c45dedf060f483978e542e0f354003545d52750`).

**Zero contacts.** `analysis.dev100_reviewer_audit.arm_offline_guard()` was armed before the first
input was opened and recorded **0 outbound connection attempts against 0 targets**. No model, tool,
embedding, tokenizer or socket contact; 0 audio seconds; 0.0 GPU hours. The resident np8
llama-server (pid 38623, port 8090) was not contacted, probed, reconfigured or stopped. Nothing
hash-pinned moved: the pinned snapshot was opened read-only and re-hashed to
`e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57`. No snapshot was rebuilt, no
knob changed, nothing written under `configs/` or `core/`. SLURP `test.jsonl` was not opened.

**Headline.** The KB models every intent the task is defined over. The `91` in
`rails/knowledge_build.py`'s docstring was a miscount of SLURP's own inconsistent `intent` field,
not evidence of lost knowledge — and that docstring has been corrected. The real finding is
narrower and lives in Q4: `intent_coverage` is computed over a **TRAIN-derived** denominator, and
on the tier that actually flew it is **1.0 by construction**, so it cannot detect the failure it
exists to detect. On this corpus that blind spot is not exercised.

---

## Q1 — how many intents actually exist

Counted directly out of the governed bytes, two ways, because the two ways disagree.

| governed file | sha256 (first 16) | rows | scenarios | actions | distinct `intent` field | distinct `f"{scenario}_{action}"` |
|---|---|---|---|---|---|---|
| `train.jsonl` | `4a05a3de6c7f028a` | 11,514 | 18 | 46 | **91** | **60** |
| `devel.jsonl` | `00d346b183ecc2d1` | 2,033 | 18 | 45 | 71 | 59 |
| `train_synthetic.jsonl` | `8394ac2573e1d72b` | 19,711 | 18 | 54 | 98 | 69 |

`test.jsonl` was not opened, loaded or enumerated.

**The 91 is an aliasing artifact, and this is measured, not argued.** The 60 `scenario_action`
strings are a strict subset of the 91 `intent` strings; the 31 extras are prefix-stripped spellings
of intents already counted. Row form histogram over `train.jsonl`: **11,352 rows (98.59 %) carry
`intent == f"{scenario}_{action}"`, 162 rows (1.41 %) carry `intent == action` with the scenario
prefix dropped, and 0 rows carry any third form.** Consequently **40 of the 60 (scenario, action)
pairs carry two different `intent` strings** (`calendar_query` also appears as `query`,
`email_addcontact` also as `addcontact`, …), and 2 of the bare-action strings span several pairs
(`query` covers 9 pairs, `remove` covers 2). SLURP's `intent` field is therefore *neither* a
function of `(scenario, action)` *nor* injective into it. The genuine train intent inventory is
**60**.

**The label space the task is defined over.** Union of train and devel on the builder's key:
**60** — `devel_scenario_action_absent_from_train` is the **empty set**. Devel introduces exactly
one new raw `intent` string (`likeness`), and it is an alias, not a new intent. `train_synthetic`
does carry 9 `scenario_action` values absent from train (`general_affirm`, `general_commandstop`,
`general_confirm`, `general_dontcare`, `general_explain`, `general_negate`, `general_praise`,
`general_repeat`, `qa_query`), but `train_synthetic` is TTS audio, is excluded from every legal-tier
roster by the 2026-08-17 finding, and is not part of this task's evaluation surface.

**Official ontology: unavailable offline, and therefore not quoted.** Neither the governed label
side (`datasets/slurp/metadata`) nor the pinned upstream checkout (`repos/slurp`) ships any file
enumerating the intent vocabulary — the corpus carries the label only per utterance. The published
SLURP intent count could not be verified from the governed bytes and no number for it is asserted
here.

## Q2 — what the pinned snapshot models

Read from the pinned snapshot bytes, three quantities counted separately because they *could*
differ. They do not.

| quantity | count |
|---|---|
| `facet:label:intent:` facets | **60** |
| `facet:prior:` facets | **60** |
| distinct `ValueBundle.task_target` values | **60** |
| `facet:label:scenario:` facets | 18 |
| `facet:label:action:` facets | 60 |
| values with no `task_target` | 0 |

The three intent-bearing counts agree **as sets**, not merely in size. Total facets 11,863 = 11,514
content + 151 speaker + 18 scenario + 60 action + 60 intent + 60 prior; 11,514 values.

## Q3 — where intents are lost: nowhere

| stage | function | utterances | distinct intents |
|---|---|---|---|
| 1 row loading | `load_slurp_train_material` → `slurp_kb_rows` | 11,514 | **60** |
| 2 datastore selection | `distribution_sample(rows, size=None, seed=20260823)` | 11,514 | **60** |
| 3 facet emission | `_build_facets_and_values` (pinned snapshot, read from disk) | — | **60** |

`intents_lost_here` is empty at both boundaries. `train.jsonl` has 11,514 rows and the loader
returned 11,514 rows — and it could not have silently dropped any, because
`load_slurp_train_material` raises `LoaderError` on a malformed row rather than skipping it. **No
intent is lost at any stage inside the builder.** The 60/91 gap is entirely upstream of the builder,
in how SLURP spells its own label.

## Q4 — what denominator `intent_coverage` divides by

Read out of `rails/knowledge_build.py` (sha256
`259d39ae1388e24ea20b4bd2f1be9a1c77699c3e9980247dd9068f7253a97c4a` at measurement time, before this
mission's docstring correction), not inferred:

```python
"intent_coverage": _coverage_pct(train_intent_counts, selected_intent_counts),

def _coverage_pct(train_counts, selected_counts) -> float:
    if not train_counts:
        return 1.0
    covered = sum(1 for key in train_counts if selected_counts.get(key, 0) > 0)
    return covered / len(train_counts)
```

with `train_intent_counts = Counter(row.intent for row in rows)`.

**The denominator is `len(train_intent_counts)` — the distinct intents present in the TRAIN rows the
caller passes in.** Measured: **60**. Three consequences, stated separately because they are not the
same statement.

1. It is **not** computed over the sampled rows. The numerator is the selection, the denominator is
   the full TRAIN population, so on a *sub-sampled* tier (`size=1000`, `size=5000`) the metric can
   genuinely detect a sampler that drops an intent. To that extent the metric is real.
2. **On the tier that actually flew it is 1.0 by construction.** The landed build used
   `datastore_size=None`; `distribution_sample` returns the whole pool unchanged for `size=None`, so
   `selected == rows` identically and *every* coverage figure in
   `docs/receipts/knowledge/slurp-kb-size-full.json` — `intent_coverage`, `scenario_coverage`,
   `action_coverage`, `entity_type_coverage`, both long-tail coverages, `cluster_coverage_proxy`,
   and `kl = 0.0` — is 1.0/0.0 with probability one, whatever the data says. The receipt's
   `intent_coverage = 1.0` **carries no information about coverage.** This read reproduced the
   landed `coverage_report` exactly (`counts` identical, `intent_coverage` 1.0), which is precisely
   how it is known to be vacuous rather than confirmatory.
3. **The denominator is TRAIN-derived at every tier.** `coverage_report` never consults devel, never
   consults an ontology, and never sees a task-target vocabulary. A target that the task requires
   but TRAIN does not contain is invisible to `intent_coverage` at *any* datastore size — it cannot
   appear in the denominator, so it cannot lower the ratio. The
   `docs/readiness/2026-08-08-unified-agent-abstraction.md` clause the metric exists to enforce is
   about **task** targets ("the support of every task target"); the metric measures **train**
   targets. **As a detector for the contract clause it is written against, it is self-fulfilling and
   cannot fail.**

Measured here, that blind spot is **not exercised**: devel's 59 intents are a subset of train's 60,
so the train-derived denominator happens to equal the task vocabulary (60 = 60) on this corpus. The
metric is uninformative, not wrong-answered.

On the clause's own threshold: SLURP's label vocabulary is 60 intents + 55 entity types = 115
entries, which exceeds 100 in aggregate, though the intent vocabulary alone does not. The question
is moot for correctness — `distribution_sample`'s two hard floors are applied **unconditionally**
and are not gated on any vocabulary size — so the build satisfies the long-tail clause under either
reading. Entity types were confirmed at **55**, exactly as the docstring said.

## Q5 — consequence (SECONDARY READING; revises nothing)

> **The SLURP unexposed 500 inside DEV-1000 is the LOCKED baseline's own population. Every number in
> this section is a secondary, descriptive reading over already-sealed records and must NOT be used
> to revise, re-tune or restate the 2026-08-25 baseline lock.**

Fidelity first: this read reproduced the sealed lock read's own pooled accuracies exactly — M0 536,
BLEND 757 over 1,000 — against `read-verdict.json` sha256 `2f8e2958…a581`, from the hash-verified
sealed arms `attempt-20260825T053342Z-dev1000m0` and `attempt-20260825T054707Z-dev1000blend`.

**DEV-1000 carries 59 distinct gold intents. All 59 are modeled by the pinned snapshot. The number
of DEV-1000 samples carrying an intent the KB does not model is 0 — 0 in the exposed 500 and 0 in
the unexposed 500.** There is therefore no dispatched-but-unmodeled slice and no correctness slice
to report: the "unmodeled" population is empty, and the "modeled" slice is the whole 1,000 (340
BLEND-dispatched = 326 dead-direct + 14 override, 536 M0-correct, 757 BLEND-correct).

**The conservative consequence of the intent question is nil.** No landed number is revised, no
sample is reclassified, and the lock is untouched.

## Verdict, and what was changed

**This is a negative result and it is reported as one.** The KB models everything the SLURP task
needs: 60 intents in train, 60 modeled, 59 exercised by DEV-1000, 0 samples affected. The mission's
suspicion of a coverage gap is refuted.

Two things were nonetheless true and are recorded rather than dressed up:

1. **The docstring was wrong and is corrected** (separate commit). `rails/knowledge_build.py`'s
   parenthetical "SLURP train: 91 intents, 55 entity types" asserted a vocabulary of 91 for exactly
   the sampler whose strata are the 60 `scenario_action` keys. It now states the measured 60, why
   the 91 arose (162 prefix-stripped rows, 31 alias strings, 40 double-spelled pairs), and that the
   floors are unconditional. This is the **only** code-adjacent edit this mission made; no
   behaviour, no knob, nothing under `configs/`, `rails/` (beyond that docstring) or `core/`.
2. **`intent_coverage` cannot detect its own failure mode**, for the two independent reasons in Q4
   (degenerate at `size=None`; TRAIN-derived denominator at every size). **No fix is proposed here**
   — a coverage metric denominated on the task's target vocabulary, and a non-vacuous statement of
   coverage for the full tier, would be a separately registered design step, and this mission
   deliberately does not take it.

## Not verified

- The **officially published** SLURP intent count. No offline governed or pinned-reference byte
  enumerates the intent ontology, so the published figure is unverifiable here and is not quoted.
- Anything about `test.jsonl`. It was not opened, and the test-side intent inventory is therefore
  unknown to this check by design.
