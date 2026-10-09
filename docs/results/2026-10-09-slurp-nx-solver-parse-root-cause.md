# NX R0.3: why the seed's first Solver draft parses 87 / 100 and review-off's 100 / 100 (offline, zero GPU)

**Status: DESCRIPTIVE, root cause identified.** Read id `SAEA-SLURP-NX-SOLVER-PARSE-ROOT-CAUSE-V1`, driver
`scripts/analysis/slurp_nx_solver_parse_root_cause.py`. Programme: `docs/readiness/2026-10-09-slurp-nx-node-extreme-
programme-v1.md` (B W3, C2 R0.3). Author: Claude Opus 5.5 (analysis agent), 2026-10-09.

**Contacts: zero** (no model, server, tokenizer, scorer, network or GPU). Gold is not read. Only counts, lengths,
hashes, key names, tool names and enum values are reported; no utterance, transcript, model output or instruction
text.

## 1. Finding

**All 13 unparsed seed first drafts (and all 10 of the seed A/A) are native tool-call strings: the Solver emitted
`<tool_call>{"name": "saea-tool-knowledge-target-lookup-v1", "arguments": {...}}</tool_call>` as its answer.** The
seed graph renders the Planner's lookup tool into EVERY role's request (Perception, Solver, Reviewer, Planner: one
tool schema, 852 JSON chars, +410 prompt tokens per contact). The Solver contact has `tool_choice: "none"` and no
`response_format`; under llama-server, `tool_choice: "none"` leaves the tools in the chat template (the GGUF
template renders `<tools>...</tools>` and the tool-call convention) but installs no grammar and no tool-call
parser, so a tool-call-shaped completion is returned verbatim as text and `parse_slu_response` rejects it.
Review-off renders no tool schema on any role, and its Solver produced 0 tool-call strings in 100 first drafts.

It is not fenced JSON, prose, truncation, a different max_tokens, or a different contract:

| feature of the 13 (seed) / 10 (seed A/A) unparsed first drafts | seed | seed A/A |
| --- | ---: | ---: |
| leading character `<`, starts with the `<tool_call>` tag (nothing before it) | 13 | 10 |
| closing `</tool_call>` present | 13 | 10 |
| tag body is JSON naming `saea-tool-knowledge-target-lookup-v1` (the rendered tool) | 13 | 10 |
| argument keys exactly `candidate_ids, distinction, store_id, view` (the tool's schema) | 13 | 10 |
| text after the closing tag: none / non-blank but not an SLU answer | 9 / 4 | 7 / 3 |
| any text after the tag that `parse_slu_response` accepts | 0 | 0 |
| code fence | 0 | 0 |
| finish_reason `stop` (no truncation) | 13 | 10 |
| completion tokens < 100 / 100-199 / at the 512 cap | 9 / 4 / 0 | 7 / 3 / 0 |
| later revised by the Reviewer -> Planner REVISE path | 13 | 10 |
| last Solver draft of the row parses | 13 | 10 |

The tool-call string occurs only at the FIRST Solver visit: 13 / 100 first visits vs 0 / 70 revision visits
(seed), 10 / 100 vs 0 / 64 (A/A). Roles under a `json_schema` response format (Perception, Reviewer) carry the same
tool array and produced 0 tool-call strings in 270 contacts (seed) / 264 (A/A): grammar-constrained decoding
excludes the tag. The Planner (`tool_choice: "auto"`) produced 0 tool calls in 334 contacts.

This is the same mechanism EFF-1 measured on 2026-09-19 with a different tool
(`docs/results/2026-09-19-slurp-eff1-tool-constant-verdict.md`: constant tool rendering, 145 / 1,092 Solver
completions returned as `<tool_call>` strings naming `saea-tool-task-contract-v1`, 13 %). The rate here (13 % and
10 %) is the same. On the tool-free COMP-1b graph the Solver's raw first-draft parse failure is 1 / 1,080 (Fold A)
and 1 / 1,000 (DEV-2000-ADDED), neither a tool-call string (`2026-10-09-slurp-nx-exchange-rates-offline.md`
section 3).

## 2. Request structure: seed vs review-off (same 100 inputs)

Per role (all contacts):

| role | member | contacts | response_format | tool_choice | max_tokens | tool schemas | prompt tokens mean | completion tokens mean | tool-call strings |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Perception | seed | 100 | json_schema | none | 512 | 1 | 4,003.1 | 112.9 | 0 |
| Perception | review-off | 100 | json_schema | none | 512 | 0 | 3,593.1 | 117.7 | 0 |
| Solver | seed | 170 | none | none | 512 | 1 | 11,086.3 | 29.7 | 13 |
| Solver | review-off | 100 | none | none | 512 | 0 | 10,405.6 | 23.8 | 0 |
| Reviewer | seed | 170 | json_schema | none | 512 | 1 | 11,168.7 | 155.1 | 0 |
| Planner | seed | 170 | none | auto | 512 | 1 | 11,499.5 | 2.8 | 0 |

Every contact on every role ends with finish_reason `stop`; temperature 0 and seed 20260913 everywhere; the request
field set is identical across members (same keys).

Paired first-contact comparison on the same 100 inputs (seed minus review-off):

| field | Perception | first Solver |
| --- | --- | --- |
| decoding_params (excluding `id_slot`) | equal 100 / 100 | equal 100 / 100 |
| task_instruction, audio, speech features, sample | equal 100 / 100 | equal 100 / 100 |
| tool_schemas | differ 100 / 100 (1 vs 0) | differ 100 / 100 (1 vs 0) |
| control message (role instruction) | differs by one constant edit: 9 chars removed, 33 added (graph id string, route enum gains `"REVISE"`) | one constant edit: 8 removed, 32 added (same) |
| supplied evidence | same ids in the same order; every item carries a constant 59-char store tag `[knowledge store=... role=...]` in the seed | ids equal on 50 / 100 rows (different Perception notes select different exemplars), tag as Perception |
| prompt tokens | +410 on every row | mean +518 (range -3,440 .. +3,633; the supply differs) |
| response text equal | 6 / 100 | 64 / 100 |

So the seed's first Solver request differs from review-off's in exactly three ways: (1) the rendered tool array,
(2) the per-item store tag in the evidence rendering, and (3) a 24-character net change of the role instruction
(graph id and the `REVISE` route value). No instruction section, history length (2 entries: Perception note +
control), response_format, tool_choice or max_tokens differs. The emitted strings call the rendered tool with its
own argument schema, which only (1) can supply; (2) and (3) are formally confounded in this pair but carry no tool
syntax. The causal claim rests on (a) the content of the failures, (b) the grammar-constrained roles' immunity with
the same tool array, (c) the tool-free graphs' 0 tool strings in 2,180 first drafts (review-off 100, COMP-1b 2,080),
and (d) EFF-1's independent reproduction with another tool.

**Side effect for R0.1 (base unification).** The tool array and store tag also change Perception's output on 94 /
100 rows (seed vs review-off), and through it the Solver's exemplar selection on 50 / 100 rows. Any seed-vs-
review-off contrast is therefore a contrast of the whole rendering, not of the Reviewer loop alone; and 13 of the
seed's 70 Solver revisions (18.6 %) exist only to recover from the tool-call artefact.

**solver-lookup (context).** Its Solver carries the tool with `tool_choice: "auto"`; 16 of its first-visit contacts
end with finish_reason `tool_calls` (the server parses the call), and the visit continues to a parsed answer. Per
contact the first response is 84 / 100 parsed; per visit (the member reader's definition, which takes the visit's
answer after within-visit tools) 100 / 100, as the N100 family note reports. Not a defect.

## 3. Candidate fixes for R1 (each a Solver-template / request candidate, none flown)

| # | fix | mechanism | expected effect | cost / risk |
| --- | --- | --- | --- | --- |
| F1 | **Render tools per role: no `tool_schemas` on any contact whose `tool_choice` is `none`** (Solver, Perception, Reviewer); only a role allowed to call a tool sees it | removes the template's tool convention from the Solver prompt | parse 100 / 100 (review-off and COMP-1b evidence: 0 tool strings in 2,180 first drafts); -410 prompt tokens per non-tool contact | breaks EFF-1's constant prefix across roles (prefix-cache efficiency) where a tool role exists; on the review-off base (section F amendment) there is no tool role, so F1 is free |
| F2 | **Give the Solver a `response_format` (`json_schema` of the SLU answer object)** when a tool array must stay rendered | grammar-constrained decoding cannot emit `<tool_call>` (Perception / Reviewer: 0 in 534 contacts with the tool rendered) | parse ~100 %; also removes the 1 / 1,080 non-tool parse failure | changes the Solver's decoding; needs its own A/A / same-flight column; incompatible with a Solver that may call the tool (`tool_choice: auto`) |
| F3 | per-role `logit_bias` ban of the `<tool_call>` token on tool-free roles (EFF-1 repair A) | decode-time veto, prompt unchanged | parse ~100 % with the constant prefix kept | needs the token id pinned per GGUF; transport passes the key through; add a receipt counter of tool-call-shaped completions on unauthorised roles |
| F4 | contract wording ("never call a tool; answer only with the JSON object") | instruction-level | uncertain; the failing drafts are not instruction-ambiguity errors, and wording does not remove the template's tool section | weakest; only as a co-candidate |
| -- | max_tokens | not binding: 0 completions at the 512 cap, failing drafts are 50-200 tokens with finish `stop` | none | do not change |
| -- | parser salvage (strip the tag and parse the rest) | 0 / 13 and 0 / 10 failing drafts contain any parsable answer | none | not a fix |

Recommendation: on the review-off base, F1 holds by construction (no role renders tools) and the parse defect does
not exist; R1 needs no parse candidate. If R3 keeps a model-initiated tool line (decision 206) with a tool visible to
the Solver, pair it with F2 (if the Solver is not the caller) or with `tool_choice: "auto"` plus the within-visit
tool loop (the solver-lookup form, 100 / 100 per visit). Add the unauthorised-role tool-call counter (F3's receipt
half) to the E2 Solver reader in any case.

## 4. Sources and commands

| member | run id | attempt | trace sha256 |
| --- | --- | --- | --- |
| seed | `SAEA-SLURP-SIMPLE-CONSUMPTION-SEED-N100-AUDIO-RECOVERY1-ENTRY2-V1` | `attempt-slurp-native-stage3-simple-consumption-seed-n100-audio-recovery1-entry2-v1-generation` | `73401a893c797314c1c67afd59cafd22fb1d5135874d290d9d4486c2d6f70b66` |
| seed A/A | `SAEA-SLURP-SIMPLE-CONSUMPTION-SEED-AA-N100-AUDIO-RECOVERY1-ENTRY2-V1` | `attempt-slurp-native-stage3-simple-consumption-seed-aa-n100-audio-recovery1-entry2-v1-generation` | `4ce4412764ad0e783376285726bb0f4542eeadb1359880db3122ecfb286a12f5` |
| review-off | `SAEA-SLURP-SIMPLE-CONSUMPTION-REVIEW-OFF-N100-AUDIO-RECOVERY1-ENTRY2-V1` | `attempt-slurp-native-stage3-simple-consumption-review-off-n100-audio-recovery1-entry2-v1-generation` | `02d94555ca56a9d7197bff00e4930c26420593065f879d25ce02580511bf20e6` |
| solver-lookup | `SAEA-SLURP-SIMPLE-CONSUMPTION-SOLVER-LOOKUP-N100-AUDIO-RECOVERY1-ENTRY2-V1` | `attempt-slurp-native-stage3-simple-consumption-solver-lookup-n100-audio-recovery1-entry2-v1-generation` | `776885da21584a234bc41dfe67a2be317a53dbf5f06aa7731ac92fddb5d046de` |

Family custody: `docs/results/2026-10-08-simple-consumption-n100-complete-family.md` and
`docs/receipts/continuation/2026-10-08-simple-consumption-n100-complete-family-read-v1.json`. "First raw parse"
follows the member reader (`analysis/slurp_solver_stage_attribution.py`: `parse_slu_response` on the first Solver
visit's response). Output: `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NX-SOLVER-PARSE-ROOT-CAUSE-V1/report.json`
(content sha256 without `generated_at`: `1c87f0db6fed4fd4d87ea7bd850a397baecb51d3a7aed35f6807cf8ac408d790`).

```bash
cd /home/chao/saea-worktrees/fable-nx-exchange
source ~/.venvs/speechrl/bin/activate
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_solver_parse_root_cause.py --data-root "$SPEECHRL_DATA_DIR"
PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_solver_parse_root_cause.py --data-root "$SPEECHRL_DATA_DIR" --check
# -> check: IDENTICAL apart from generated_at
```

The store-tag and control-message characterisations (constant across all items / rows) were measured with the same
trace bytes by `difflib` opcodes; only lengths are persisted by the driver, the constant tag text is quoted here
because it is template text identical on all 800 Perception evidence items.
