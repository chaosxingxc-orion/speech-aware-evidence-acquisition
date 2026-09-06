# EVO-A1 decontamination — the gate the proposer's candidates are validated against

Model-free, zero contacts, no GPU. Exposure row `SAEA-A2T-MF-EVO-DECONTAMINATION-V1`. Generator
`scripts/build_a2t_evo_decontamination.py`. Outbound connection attempts: **0**.

Authority:
`docs/readiness/2026-09-06-a2t-evo-a1-description-evolution-v1-preregistration.md` section 8 and
section 12 item 7, which require this row to exist **before the first candidate is validated**.

## The two artifacts

| artifact | what it is | committed |
|---|---|---|
| `decontamination.json` | the evaluation 6-gram set's SIZE and its **set pin** — one SHA-256 over the LF-joined sorted grams | the pin, never the grams |
| `registry-6grams.json` | `A_0`'s exemption list: all 2,005 word 6-grams of the released compact registry | verbatim, all 2,005 |

**Why the evaluation grams are pinned and not listed.** A word 6-gram is six verbatim words of an
evaluation query. A committed list of 77,899 of them would be exactly the leak this gate exists to
prevent, so the artifact records the set's size and a digest that any re-derivation reproduces, and
`scripts/build_a2t_evo_decontamination.py::evaluation_invocation_texts` is the single function every
later caller re-derives the set from. The gate that flies and the gate audited here therefore cannot
drift.

**Why the registry grams are listed.** The compact registry is public released text of the
Audio2Tool distribution, not evaluation speech, and it is the *legal* source of shared phrasing: the
refusal rule is `illegal = (candidate & evaluation) - registry`, so a reviewer has to be able to see
exactly which overlaps are forgiven. **14** of the 2,005 registry grams already occur in the
evaluation set; those 14 are the whole practical content of the exemption.

## Measured

| quantity | value | pin |
|---|---:|---|
| population | `A2T-ORG1-UNION-4000`, 4,000 rows, 500 per tier | receipt sha256 `e5a81b71…857b8736` |
| invocation texts | 9,930 | — |
| evaluation word 6-grams (**the gate set**) | **77,899** | `a98d5dd093571f3a63d58d91ab25dcc5ce04cc2a2ba201bbf4f56e96e00c44e9` |
| evaluation word 6-grams, speaker-only | 68,647 | `496ddfb907af2ec3f57bc157e205723a5a329e9cdee948726c65e3729ff160fc` |
| registry word 6-grams (`A_0`'s exemption) | 2,005 | `6ac2aeeceadb20552c3e2972813ec7e3e966e454df5b6b01e7324b3801d3dcf9` |
| `A_0` rendered block | 15,854 chars, 152 lines | `752dd381a02028dc7345a6ac826109bdcc879d82547a9029a43d559d0de8a605` |

## Four identity anchors, reproduced rather than asserted

The builder refuses with `SystemExit` **before a byte is written** unless all four hold: `A_0`
renders to 15,854 characters over 152 lines and hashes to `752dd381…0de8a605` (the value the
preregistration's section 3 pins); the population yields 9,930 invocation texts and 77,899 word
6-grams, and the registry 2,005 — the three counts `SAEA-A2T-MF-KC-A1-DECONTAMINATION-V1` and
`SAEA-A2T-MF-KC-A1C-DECONTAMINATION-V2` recorded on this same population on 2026-09-06. All four
reproduced.

## A defect in the inherited rule, recorded rather than silently fixed

KC-A1's gate collected **every string value** of a `chat_history` turn, which is the turn's
`content` plus its wav `path` and its `role`. **9,252 of the 77,899 grams therefore come from path
and role strings** rather than from anything a speaker said; the speaker-only core is 68,647.

The inherited superset is **kept as the gate set**, for two reasons. It is strictly *stricter* — a
larger refusal set can only cause a refusal, never admit a candidate the speaker-only set would
refuse — and keeping it is what lets KC-A1's anchors reproduce exactly. It does not touch KC-A1's
verdict either: both arms passed with **zero** shared grams, and a strictly larger refusal set
cannot turn that into a different pass. The speaker-only pin is recorded beside it so a later cell
can narrow the rule knowingly rather than by accident.

## How the gate is actually run

```
rails.proposer.validate_candidate_artifact(
    candidate,
    registry_rows=...,
    token_counter=<the resident server's /tokenize route>,   # the ONLY part needing a server
    compact_baseline_tokens=3581,
    evaluation_query_texts=evaluation_invocation_texts(lock, root, population_ids(repo)),
    registry_text=render_registry_compact(lock, root),
    exemplar_texts=<the construction rows that draw showed>,
)
```

Candidate *pricing* needs the serving tokenizer and is therefore a separate
`bounded-discovery-probe` row (preregistration section 12 item 9); everything this row covers is
model-free. Per candidate the round receipt records `candidate_id`, family, round, target, `k`, the
exemplar ids shown, the six-gram verdict, the exemplar overlap count, the rendered token count and
the per-description character counts.

## Boundary

A pure text pass over the released tier manifests' invocation fields and `tools_registry.csv`. No
frozen core, tokenizer, embedder, retriever, scorer, network, audio decode, GPU or paid API; no
audio file is opened at all. **No gold**: the fields opened are `query`, `user_request` and the
`chat_history` turns; `tool_name`, `expected_tool_call`, `extracted_params`,
`additional_tool_calls`, `reasoning`, `tool_id`, `functions`, `instruction`, `original_tool_call`,
`background_tool_call` and `background_tool_name` are never opened for an evaluation row.
`CUDA_VISIBLE_DEVICES` empty throughout; `arm_offline_guard()` armed before the first input was
opened and recorded 0 outbound connection attempts against 0 targets.
