# SAEA-E21-MF-SEMANTIC-IMPACT-BASELINE-V1 — receipts

The fourth agentic metric the 2026-09-06 Earnings comparator left blank, filled from the same sealed
bytes by one more `core.scoring_batch` job. Note:
`docs/readiness/2026-09-06-earnings-agentic-metric-baseline-v1.md` §9. Taxonomy receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-semantic-impact-taxonomy/`.

**Zero model, GPU, tool, embedding, network and audio contact**, and no Earnings-22 read. The ledger
row was registered and committed before the scorer touched a reference. Source:
`SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338`, study commit
`44db2e9d` — all 44 `earnings21-original` discovery calls, split identity `fcc1b0bc…d69e`. One
complete verified manifest, one process, never sharded; 1 of 1 succeeded in 568.1 s.

## The result

| roster | calls | reference words | negation-critical HIGH % | HIGH words | LOW % | NONE % | unclassified |
|---|---:|---:|---:|---:|---:|---:|---:|
| **all 44** | 44 | 359,765 | **0.0278** | 100 | 3.272 | 1.926 | 0 |
| construction 34 | 34 | 284,014 | 0.0303 | 86 | 3.384 | 2.027 | 0 |
| evaluation 10 | 10 | 75,751 | 0.0185 | 14 | 2.853 | 1.547 | 0 |

**The decomposition is exact and it closes on a number the sealed verdict already published.** The
three levels partition the substitution-plus-deletion reference-word mass and nothing else: 100 +
11,771 + 6,928 = 18,799 = the sealed S 13,098 + D 5,701, and 5.226 % against the 5.225 % the
comparator note computes as this arm's own `(S + D) / reference words`. Zero reference words reached
`__UNCLASSIFIED__`, so the taxonomy is total over what this corpus actually contains.

## What this number is, and what it is not

Under the landed taxonomy the HIGH tier is the Earnings-22 scan's **negation trigger alone**. The
scan's other two HIGH triggers — a digit-bearing token and a call-inventory named entity — are not
expressible as exact-word taxonomy keys and were left out rather than approximated (the taxonomy
receipt has the reasoning). So:

* **this is the negation-critical error rate**, and it is a strict LOWER BOUND on the scan's own
  content-impact HIGH rate. It must never be quoted as the scan's 1.92 % agentic error rate, which
  is a different quantity on a different corpus with two more triggers and a category ruling this
  key shape cannot carry;
* on Earnings-21 the two missing triggers are already carried, on **gold annotations rather than
  heuristics**, by `numeric-value-accuracy-v1` (90.73 % over 9,734 digit-bearing values) and
  `conec-entity-wer-official` (ConEC's own `wer_tags`, PERSON 22.5 / ORG 17.2), both landed by the
  2026-09-06 agentic-metric row;
* an INSERTED function word is reported `LOW` here where the scan says `NONE`. Insertions carry zero
  reference-word mass, so no rate moves; the 10,700 insertions are reported in their own
  `insertions_by_level` map, of which **56 are negation-critical**.

**It is a weak guard on its own, and the preregistration says so.** 100 HIGH reference words on all
44 calls and **14 on the evaluation ten**, with **15 of the 44 calls carrying none at all**. A
mechanism cell can move this number by a handful of words; the Earnings harm guards that carry real
power are corpus WER non-inferiority and numeric-value accuracy.

## Files

| file | what it holds |
|---|---|
| `scoring/rescore-bundles.json` | the bundle: each sealed artifact's path, its byte-identical copy's path, and the sha256 they share. The manifest differs from the sealed one only in artifact paths and the `scorers` list, so `core.bundle.verify_bundle` re-derives split identity, protocol hash and the outputs↔split↔trace binding and gets the sealed values. The sealed attempt directory was never written to |
| `scoring/jobs.jsonl`, `scoring/batch-summary.json` | the `core.scoring_batch` job table and summary: 1 of 1 succeeded, `max_workers` 1, 568.1 s |
| `verdict/result-summary.json` | the taxonomy id, the pooled figures on all 44 and on both halves of the E5 split, the level and rule breakdowns, and the per-call rows |
| `verdict/per-call-table.md` | all 44 calls: reference words, negation-critical rate, the NONE/LOW split, unclassified residue and negation-critical insertions |
