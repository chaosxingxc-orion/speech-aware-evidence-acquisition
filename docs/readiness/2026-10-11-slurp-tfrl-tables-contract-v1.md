# SLURP TFRL contrast tables: input contract v1 (E-T3)

Date: 2026-10-11. Owner decision 263 A. Design:
`docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md` sections 3.3, 3.4,
4.1-4.2. Producers: `scripts/analysis/tfrl_contrast_tables.py` (tables) and `scripts/analysis/tfrl_delivery_fit.py`
(cross-fitted delivery thresholds). Consumers: E-T1 (`rails/tfrl_typed_proposer.py`, the renderer) and E-T2
(`rails/tfrl_ace_material.py`, the ACE material). This note is the interface; the module docstring of the producer
is the long form.

## 1. What is produced

One file per sealed column, `tables-v1.json`, schema `saea-tfrl-contrast-tables-v1`, under
`$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-TFRL-TABLES-DEV-V1/<run_id>/` (never Git). Its last key `tables_sha256` is the
sha256 of the canonical document (sorted keys, indent 2) without that key; the next proposer fragment pins it. No
clock is written, so a re-run on the same bytes is byte-identical. The input is one sealed, officially scored column:
run id, attempt id, an arm label (recorded only), the scorer block key, the gold split (`train` or `devel`) and the
roster size. Gold is used offline on TRAIN / DEV rows only; the test split is refused.

## 2. Content rules (enforced by the script, not by prose)

- Counts, rates, ids, slot-type names, scenario names and token counts only.
- The self-check fails the script if any key equals `text`, `transcript`, `gold`, `value_text`, `utterance` or
  `answer` (case-insensitive) or any string value exceeds 200 characters.
- Every count of 1 or 2 is the string `"<3"`; 0 and counts of 3 or more are integers. A rate is `null` when its
  denominator is below 3.

## 3. Tables

| key | name | columns / shape |
| --- | --- | --- |
| `table_a` | failure cube | `columns` = `class`, `slot_type`, `scenario`, `in_supply`, `in_store_not_delivered`, `in_train_not_in_store`, `nowhere`, `total`; one row per non-empty cell; `marginals.class_x_state`, `marginals.class_x_scenario` |
| `table_b` | empty-gold false fill | `per_scenario[s]` = `empty_gold_rows`, `false_fill_rows`, `false_fill_rate_pct`, `spurious_entities`; `spurious_types_by_scenario[s][type]` (empty-gold rows); `spurious_types_all_rows_by_scenario`; `overall` |
| `table_c` | intent | `per_scenario[s]` = `rows`, `intent_wrong_rows`, `gold_on_shortlist_rows`, `gold_on_shortlist_rate_pct`, `wrong_rows_gold_on_shortlist`, `wrong_rank_histogram` (bins `1`, `2`, `3`, `4-5`, `6-10`, `11+`, `off-list`, `no-shortlist`, on intent-wrong rows); `overall` |
| `table_d` | supply structure | `overall` and `per_scenario[s]` = `rows`, `exemplars`, `cards`, `supplied_tokens`, each `{n, mean, p50, p99}` (nearest-rank percentiles); `supplied_tokens` is the first Solver contact's realised prompt tokens, null if the trace pass is skipped |
| `table_e` | exchange rates | copied from the pinned note `docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md` section 4 (report sha256 recorded): per pool `comp1b_fold_a` and `a2`, `analytic_rates_pp`, `empirical_rates_pp`, `node_rates`; never recomputed |
| `table_f` | refused-candidate buffer | `columns` = `candidate_id`, `operator_class`, `predicted_pp`, `measured_pp`, `verdict`; `rows` is `[]` as written; the DRIVER appends |
| `table_g` | item credit (ACE) | `items[]` = `item_id`, `rendered_rows`, `helpful`, `harmful`, `neutral`; empty without a playbook |

`table_a` classes are the `entity_states.entity_items` kinds: SPURIOUS, MISSING, WRONG-TYPE, BOUNDARY, NEAR,
WRONG-VALUE, FORMAT. The four supply states partition `total` and are judged on the gold value (gold-side classes)
or the predicted value (SPURIOUS), in this priority: `in_supply` (printed by a supplied exemplar under the same or
another type, or named by a supplied slot card), `in_store_not_delivered` (in the exemplar store or any slot card),
`in_train_not_in_store` (in TRAIN gold of another utterance), `nowhere`.

## 4. `item_credit` (E-T2)

Behind `--playbook-release <path>` and the lock column (`--lock-run-id`, `--lock-attempt`, optional
`--lock-scorer`). The release is a JSON snapshot (`values[].value_id`) or `items[].item_id`; only ids are read. For
each item id: `rendered_rows` = rows of the column whose sealed phase record names the item among its supplied value
ids; among those rows, `helpful` / `harmful` / `neutral` = the column's official per-row SLU-F1 (`slu_f1_f1` of the
scorer block) above / below / equal to the same row in the lock column. The script never reads item text and never
asks a model. With no `--playbook-release` the table is `{"playbook_release": null, "items": []}`.

## 5. Cross-fitted delivery thresholds (`tfrl_delivery_fit.py`)

Families of the v4g grammar, each with one threshold: `ee` (explicit-empty, Wilson-guarded), `ti` (type-by-intent,
pool-size-guarded), `article` (leading-determiner strip). Seed 20260915. Utterance clusters are split into two
halves; the threshold fitted on each half is applied to the other; the cross-fitted column's pooled SLU-F1 delta
over the sealed column and its whole-utterance cluster-bootstrap CI95 (10,000 draws) is the predicted effect. A rule
whose cross-fitted CI lower bound is not above 0 is refused: exit status 3, `refused: true`, `rule_table: null`. The
point floor of 0.67 pp is reported as `meets_point_floor` and left to the driver's selection rule (design section 5.3).
Output: `fit-report-<family>-v1.json` with `report_sha256`.
