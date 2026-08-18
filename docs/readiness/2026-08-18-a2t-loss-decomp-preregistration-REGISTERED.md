# A2T selection-loss decomposition — registered model-free re-read — REGISTERED

Date: 2026-08-18. Status: **REGISTERED — executable once the suite extension lands and is
reviewed** (no GPU, no core contact; runs any time). Profile: `model-free-check`. Owner GO:
2026-08-18 ("2) Go"). Parents: the consumed Stage-2b read (`c9ee811`), whose own caveat (3)
records that MISLEAD's mechanism is untested — retention is raw mean tool_accuracy and
cannot say where B2's 21 lost selections went — and the consumed Stage-2c read (`88ebaf5`),
whose C3 arm lost 7.

## 1. Question

When a supply arm loses an already-correct tool selection, where does the selection GO —
dragged to the highlighted/supplied wrong tool, drifted elsewhere in the 152-row registry,
or collapsed into an empty/parse-failed call? This is the baseline-referenced drag measure
the MISLEAD overlay lacked.

## 2. Scope (read-only, over already-consumed attempts; no new model contact)

Classify every lost selection (A0-correct → arm-incorrect) into four mechanical classes —
DRAGGED-TO-SUPPLIED (the arm's highlighted/deranged tool), DRIFTED-OTHER (a different wrong
tool), EMPTY, PARSE-FAIL — for:
- **B2** (Stage-2b, 21 losses; the highlighted wrong tool is the drag target) — the verdict
  carrier;
- **N0r** (Stage-2, 5 losses; zero supply — the DRIFT REFERENCE distribution: with no
  supplied tool, DRAGGED-TO-SUPPLIED is undefined and every loss is drift/empty/parse);
- **C3** (Stage-2c, 7 losses; the appended RIGHT row — drag is undefined; classified for
  the augment-form drift picture) — descriptive;
- **S1'/S2/B1/C1/C2** loss classifications — descriptive completeness (their supplied tool
  IS the correct tool, so DRAGGED-TO-SUPPLIED is structurally impossible; expected classes
  drift/empty/parse only).

## 3. Verdicts (mechanical, on B2 only; descriptive elsewhere)

- **DRAG-CONFIRMED**: ≥ 11/21 of B2's losses are DRAGGED-TO-SUPPLIED — the highlighted
  wrong row actively pulls selection; MISLEAD's mechanism is real even though its pooled
  threshold did not fire.
- **DRIFT-CONFIRMED**: ≤ 5/21 DRAGGED-TO-SUPPLIED AND the B2 class distribution is
  compatible with N0r's reference shape (report side-by-side; no statistical test at n=21
  vs n=5 — stated as a shape comparison, not inference).
- Otherwise **MIXED** (report the full table).

## 4. Discipline

This is a REGISTERED RE-READ of consumed attempts: the original one-shot reads remain
consumed and their verdicts untouched; this read adds a NEW, narrower instrument
(`analysis/a2t_loss_decomp.py` + CLI, extending the consumed suites' parsing primitives
verbatim — tool-selection extraction reused, never reimplemented) over the SAME archived
outputs.jsonl files, hash-verified against their MANIFESTs before reading. Suite built and
coordinator-reviewed BEFORE execution; one execution, idempotence-guarded output dir
`docs/checks/speech-aware-evidence-acquisition/2026-08-18-a2t-loss-decomp/`; exposure row
`SAEA-CHECK-a2t-loss-decomp` appended at registration (consumed=no; flips at the read).
Zero core contact, zero GPU, no attempt-directory mutation. NC license carried on
audio-derived results.

## 5. Amendment 2026-08-18 (pre-read instrument repair; nothing consumed)

The first execution attempt REFUSED at the suite's own three-way reconciliation gate
before writing any output: the suite declared losses on deduplicated distinct-tool
identity, while the parents' `tool_accuracy` is a name-MULTISET comparison — one headroom
sample (`tier3_multi_intent:003994`, a duplicated gold tool name) makes the identity
count exactly one low on every full-headroom arm. No output row was read, no verdict
produced, the idempotence guard did not trip, and the ledger row stays consumed=no.
Repair, registered before any read: (a) the loss definition is aligned to the parents'
multiset comparison verbatim; (b) a fifth class **MULTIPLICITY** (correct tool SET,
wrong multiplicity — structurally neither dragged nor drifted) joins the taxonomy; the
B2 verdict clauses are unchanged and keep counting DRAGGED-TO-SUPPLIED over B2's total
losses (a MULTIPLICITY loss therefore weighs against DRAG-CONFIRMED exactly as EMPTY and
PARSE-FAIL do). The reconciliation gate itself is unchanged — it is the instrument that
caught the defect.
