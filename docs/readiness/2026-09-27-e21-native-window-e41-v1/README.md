# Item E41: the bounded Perception note on the Earnings21 + ConEC system form (launch runbook)

Registered 2026-09-27, before any contact, in the worktree `/home/chao/saea-worktrees/fable-e41` (branch `fable/e41`,
base commit `a50a0d1c`). Authority: owner decisions 103 (E41 defined) and 158 (E41 judged unfinished Stage-2
engineering base: carry it out after COMP-1). Model-free registration: zero model, server, encoder and scorer contacts;
one local vocab-only tokenizer process measured the token cost.

**Question:** with nothing else moved, does bounding the Perception note remove the Perception length-truncation mode
the E35 sub10 read (75 / 342 at 1,024), the E39 dry run (4 / 4 at 320) and the E39b dry run (2 / 4 at 640) recorded?
**It does not ask** whether anything improves: no score, comparison or effectiveness claim is made by either cell.

## The one pin

`phase_material.perception.instruction_template`: `probes/e21_native_window_system_perception_v1.txt` -> `probes/e21_native_window_system_perception_v2.txt`. The v2 note is a numbered list of at most 5 lines, at most 20 words
per line, `N. KIND near S s: reading A or reading B` with KIND in NAME / NUMBER / BOUNDARY / MISSING and at most 4
quoted spoken words per reading; never a repeated line; `1. NONE` when nothing is uncertain; and explicitly not a
transcript (the Perception contact's system message is the Solver's task instruction, which orders a transcript).
Everything else is the sealed E39b dry run's form (base lock v3.1): scope answering-node, caps 640 / 640, Reviewer
probe v2, `deliver-latest-or-abstain`, `continue-without-answer`, the E21 geometry. Composed diff:
`composed-config-diff-v1.json` -- dry run vs E39b: 26 differing leaves,
exactly one pin; sub10 vs the sealed E35 sub10 system arm: 61 differing leaves (the pin, the
v3.1 leaves the dry runs proved, and bookkeeping).

## Token cost (`instruction-token-measurement-v1.json`)

- Prompt side: the instruction grows 75 -> 173 tokens;
  as the wire renders it (with the native-episode limits) 145 -> 243,
  i.e. +98 tokens per Perception contact (one per window): +392 on the dry run,
  +33516 on the sub10 re-read (E35 sub10 system prompt total 4,016,159).
- Completion side: a typical compliant note is 75 tokens; the digit-dense worst case
  (every reading four 12-character numerals) is 574 tokens, 66 under the 640 cap;
  the ratio bound 5 x 20 x 2.7162 (the maximum tokens per word observed) is 271.6.
  The v1 notes ran median 324 / p95 821 tokens (E35 sub10).

## The model-free truncation argument (`perception-trace-read-v1.json`, counts only)

All 354 sealed Perception contacts of the Earnings system form (E35 sub10, E35 four-row, E39,
E39b) were joined to their wire finish_reason; 82 were length-truncated. Mode by a fixed rule:
{"ENUMERATION": 12, "LOOP": 60, "PROSE": 5, "TRANSCRIPT": 5}. **None of the 82 truncated notes fits the E41 bound**
(0 within), and none of the 272 naturally stopped v1 notes does either
(0): the v1 instruction never produced a bounded note, so v2 is a real change of form.

- LOOP (the 1,024 mode, 59 of 75 on E35 sub10): the repeated unit has a period of median
  26 words (about one list item) repeated to the cap -- an open list with no terminator.
  v2 closes the list (numbered, at most 5 lines, 'Never repeat a line', 'Stop after line 5'). Residual risk, named:
  27 of 59 loops began within the first 100 words, so length alone does not
  exclude a loop; the form does, if the core complies -- which the dry run's R3 measures.
- ENUMERATION (the 320 / 640 mode): 14-64 lines at 1,024, 6-10 at 320, 19-21 at 640. v2: at most 5 lines.
- TRANSCRIPT: the note re-emits at least half of the window's direct-arm transcript 4-grams. v2 forbids
  transcription and caps quoting at 4 words per reading; on E35 sub10 36 of 267 STOPPED v1 notes also re-emitted at
  least half the window -- transcript tokens in a NON-answering node's intermediate state, which the 2026-09-06
  owner ruling (no transcript or ASR state; only the Solver's draft answer, the carrier's deliverable, is a
  transcript) does not admit; v2 removes them.
- PROSE: long free text. v2: at most 20 words per line.

A note that obeys v2 is at most 574 tokens, so it cannot reach the 640 cap: under v2 every
length-truncated Perception contact is a NON-compliant note by construction. The argument is conditional on
compliance; the dry run's R3 (Perception truncation rate, target zero) is the measurement of compliance.

## The two cells (both HELD)

| item | dry run | sub10 re-read |
| --- | --- | --- |
| cell | `e21-native-window-system-four-row-e41-v1` | `e21-native-window-system-sub10-e41-v1` |
| experiment | `e21-native-window-four-row-e41-dry-run-v1` | `e21-native-window-sub10-e41-v1` |
| baseline | `e21-native-window-system-four-row-e41-v1` | `e21-native-window-system-sub10-e41-v1` |
| dataset | `e21-native-window-four-row-v1` | `e21-native-window-sub10-v1` |
| generation run | SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1 (44 calls) | SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-E41-V1 (3762 calls) |
| fit run | SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1-FIT-V1 (176) | SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-E41-V1-FIT-V1 (15048) |
| repeated speech s / GPU-h | 3960 / 0.5 | 334477 / 12.0 |
| roster | 4 windows of call 4320211 (E35 / E39 / E39b roster) | 10 calls, 342 windows (the E35 sub10 roster) |
| comparator | sealed E39b dry run (receipts) + E35 four-row direct | sealed E35 sub10 direct arm, bound per window (+ E35 system arm, structural) |
| read | receipts only: R1, R2, R3 (Perception truncation rate, target zero) | descriptive structural read S1-S5 + standard scorer and agentic metrics, no claim |
| stage3_measurement | form-proof, rows 1, claims_benefit false | form-proof, rows 10, claims_benefit false |
| decision | `e21-native-window-e41-dry-run-admission-v1` | `e21-native-window-e41-sub10-admission-v1 (minted only after the dry-run read)` |

Both cells declare `native_episode.finite_completion_policy = deliver-latest-or-abstain` and
`native_episode.react_exhaustion_policy = continue-without-answer` (`scripts/checks/finite_completion_policy_check.py`),
`finite_completion_scope = answering-node`, and `stage3_algorithm` `none` with its reason in the experiment fragment.

## Mint, re-pin, switch, fly (root)

1. Countersign the DRAFT exposure rows of the E41 section of `docs/exposure-ledger.md`.
2. Mint the dry-run receipt: `python scripts/flights/e41/e41_mint_receipt.py --which dry-run`.
3. Flip: `bash scripts/flights/e41/e41_flip_dryrun.sh` (the per-cell `repin_loop_generic.sh` cycle; records
   `/home/chao/e41-dryrun-flight-commit.txt`).
4. After COMP-1 seals (row 158): stop the SLURP np4 session (`scripts/flights/batch/serving_switch_to_e21.sh`), start
   the E21 session (`SAEA-Serving-E21` -> `serving_task_entry_e21.sh`), then run
   `bash scripts/flights/e41/batch_chain_e41_dryrun.sh` (refuses unless the E21 session is resident and the SLURP one is not).
5. Read the dry run by `dry-run-analysis-recipe-v1.json`. Only on PASS: fill the sub10 draft's `dry_run_read`
   antecedent, mint `--which sub10`, flip with `e41_flip_sub10.sh`, fly with `batch_chain_e41_sub10.sh` (same
   serving preconditions), read by `sub10-analysis-recipe-v1.json`. Return the SLURP geometry after each seal.

## Files

`protocol-registered-v1.json` (shared; quotes no cell hash), `dry-run-*` and `sub10-*` plans and recipes, `registered-facts-v1.json`
(stage3_measurement keyed by run id), `composed-config-diff-v1.json`, `perception-trace-read-v1.json`,
`instruction-token-measurement-v1.json`, `sub10-comparator-binding-v1.json`, two root-admission drafts. Proofs:
`tests/unit/test_e41_bounded_perception_note.py`. Generator: `scripts/flights/write_e21_e41_registration.py`.

## Not authorised by this package

No flight before the receipt is minted and the cell flipped; the sub10 flip never before the dry-run read holds; no
contact by this registration; no re-flying or re-scoring of a sealed arm; no change beyond the one pin; no claim.
