# Node-template variant instrument: design

Author: engineering agent (Sonnet), 2026-10-09, branch `fable/nx-harness`. Status: IMPLEMENTED, offline only
(no model, server, tokenizer, GPU or network contact). Authority: the NX programme
(`docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`, principle C0.2 and deliverables E1/E2).
Companion: `docs/readiness/2026-10-09-slurp-nx-template-variant-instrument-v1/README.md` (usage, example, proof).

## 1. What it is, and what it reuses

Item E42 (`docs/superpowers/specs/2026-09-27-same-flight-supply-variant-instrument-design.md`) contacts ONE node
K times over the SAME `QueryState`, each arm with a different declared knowledge-SUPPLY selection; the delivering
arm is LAST and carries no override, so the delivered request is the locked plan's request byte for byte (I7) and
the K contacts are one `action_alternatives` batch bound by invariant I7v.

The node-template kind moves the varied axis from SUPPLY to the node's INSTRUCTION TEMPLATE. Each non-delivering,
non-twin arm overrides exactly ONE thing: `phase_material.<role>.instruction_template`, a path under `probes/`
(spelled with or without the `configs/` prefix), hash-pinned by sha256. Nothing else is addressable: no supply knob,
no release swap, no decoding parameter, no response format, no tool authority, no per-arm supply bound.

It is NOT a second mechanism. A `template_variants` block parses (`rails.supply_variants.parse_template_variants`)
into the SAME `SupplyVariantGroup` the supply form uses, with `kind = "template"` and `arm_visits = "first"`. The
runner's arm fan-out, the single contact batch, the settle rule (only the delivering arm registers state), the
contact ceiling term `base + (K - 1)`, the bundle invariant I7v and the downstream arm-column scorers are therefore
the supply form's own. What differs is exactly: how an arm's instruction is composed, one receipt field, and the
absence of per-arm supply routers.

## 2. Declaration

`native_episode.roles.solver.template_variants` (Solver first; the parser, the materials builder and the arm record
are keyed on the node's `phase_id`, and `TEMPLATE_VARIANT_NODES` is the one tuple that admits another node):

```json
{"node": "solver",
 "arms": [
   {"arm_id": "t1", "instruction_template": {"relpath": "configs/probes/nx/solver-t1.txt", "sha256": "<64 hex>"},
    "template_tokens": 410},
   {"arm_id": "t2", "instruction_template": {"relpath": "configs/probes/nx/solver-t2.txt", "sha256": "<64 hex>"},
    "template_tokens": 395},
   {"arm_id": "aa", "replicate_of": "lock"},
   {"arm_id": "lock", "deliver": true, "template_tokens": 380}],
 "max_supplied_items": 48,
 "fit_estimate": {"slot_tokens": 24576, "completion_ceiling": 640,
                  "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120}}
```

* 1 to 6 candidate arms, plus the delivering arm (LAST) and at most one twin (`replicate_of` the delivering arm,
  the A/A of the read). With both, the group spans at most `MAX_SUPPLY_VARIANT_ARMS` = 8 contacts.
* `max_supplied_items` is ONE bound for every arm (the supply is unvaried). `template_tokens` is the measured token
  count of the template an arm renders; `fit_estimate.base_prompt_tokens` EXCLUDES the instruction template.
* The consumption module compiles a `columns` entry of kind `template` to this block (section 6).

## 3. Refusals (all before any contact, all by name)

| Refusal | Raised by |
| --- | --- |
| block not exactly `node, arms, max_supplied_items, fit_estimate` | `parse_template_variants` |
| `node` differs from the role the block sits on; role outside `TEMPLATE_VARIANT_NODES` | `parse_template_variants`, loader (`roles.<kind>.template_variants is refused`) |
| candidate arms outside 1..6; two twins | `parse_template_variants` |
| `overrides`, `release_swap`, `knobs`, a per-arm `max_supplied_items`; any unknown key | `parse_template_variants` |
| candidate without `instruction_template`; delivering arm or twin WITH one | `parse_template_variants` |
| template not exactly `{relpath, sha256}`; digest not lowercase 64-hex | `parse_template_variants` |
| path outside `probes/`, absolute, `..`, backslash, drive letter | `parse_template_variants` |
| missing or non-positive `template_tokens` (non-twin); `template_tokens` on a twin | `parse_template_variants` |
| duplicate arm id; zero or several delivering arms; delivering arm not last; twin of another arm | `parse_template_variants` |
| two arms naming the same template path or digest; a candidate equal to the node's locked template | `parse_template_variants`, loader (passes `locked_template`) |
| estimated prompt over the live slot with the registered reserve | `parse_template_variants` (`SupplyVariantFitEstimate`) |
| `template_variants` beside `supply_variants` on one node; beside `native_episode.knowledge_index` | loader |
| program ceiling differs from `base + (K - 1)` | loader (program contact ceiling must equal the bounded graph ceiling) |
| a pinned template whose bytes hash to another digest, or whose file is missing | `FlightRuntime._template_variant_materials` |
| a rendered template that embeds frozen knowledge payloads | `FlightRuntime._template_variant_materials` |
| builders missing, extra, or bound with no group; a resolver beside a template group | `rails.runner` binding check |
| an arm material whose response format differs from the node's | `rails.runner.template_arm_instruction` |
| a sealed receipt whose templates differ from the declared ones | `rails.runner` seal; `validate_supply_variant_receipt` (v4) |

## 4. Runtime contract

* **Evidence is unvaried.** Every arm renders `base_messages(ctx)` over the row's own `QueryState`. The settle step
  resolves no per-arm supply for a template group; the flight builds no per-arm router
  (`_supply_variant_binding` returns `None`).
* **Instruction composition.** The flight publishes, from `_default_phase_program_binding`, the node's specs, the
  protected-knowledge list and `material_with_static_text(overrides)` (the SAME `build_material_for_phase` call with
  only the named phases' static text replaced). `_template_variant_materials` verifies each pin, renders the arm's
  template through the node's own `instruction_fill` and `fill_params`, and returns one builder per template arm.
  `rails.runner.template_arm_instruction` calls a builder with the SAME `(context, sealed predecessor)` the visit's
  delivering material was built from, then appends the visit's own bounded "Native episode limits" suffix. The node
  asks for this string as the arm's framework query (`SupplyVariantRoleNode(query_for_arm=...)`); the binding
  provider asks for it again as the contact instruction. The two are the same cached string, so the framework check
  `framework[1] == role_query` holds.
* **The delivering arm and the twin** carry no template: their instruction and query are the visit's own, untouched.
  A test compares the delivering arm's request to an UNARMED run of the same row at the same program ceiling (the
  ceiling is part of the plan: the limits text states the contacts still allowed) and finds every wire field, the
  history and the control turn equal up to the contact id.
* **Revisits.** `arm_visits` is forced `first`: arms fan out at the first Solver visit only; every later visit
  contacts the delivering arm alone. This is the VAR-2 fix and keeps the fit bound to one visit.
* **Cited-answer contract.** The existing refusal (a cited-answer Solver does not compose with variant arms) is
  unchanged. The NX base is the uncited review-off graph.

## 5. Custody

Receipt schema `saea-supply-variant-arms-v4` = v3 plus `instruction_template` on every arm row: `null` for the
delivering arm and the twin, the declared `{relpath, sha256}` otherwise. The validator additionally requires: no
knob, no release swap, every arm supplying exactly the delivering arm's ids, distinct templates. v1 to v3 receipts
validate unchanged. Request, response text and contact identity of every arm are the supply form's: the arm's
`contact_id` binds its trace pair, `request_sha256` binds the rendered request (which contains the template text),
and invariant I7v already walks every arm contact. The parse result is not a sealed field: it is a deterministic
function of the sealed response text, computed by the reader (section 7) through the governed parser.

## 6. Consumption module

A `columns` entry `{"column_id", "kind": "template", "node", "template": {relpath, sha256}, "template_tokens"}` is one
arm named `column_id`. The block-level `template_frame` carries the shared numbers (`max_supplied_items`,
`delivering_template_tokens`, `twin`, `fit_estimate`) because they are measured by the cell author. The carrier hook
`template_variant_frame` names the block path, the node and the delivering and twin arm ids. The compiler builds the
whole block (columns in order, twin, delivering arm last), runs `parse_template_variants` on it, adds K - 1 to the
ceiling and selects `phase-native-module-v1-c<ceiling>` (the family now covers c2 to c24). Template columns are
admitted under the review-off profile and refused beside Perception-branch columns. `verify_declared_module` holds a
declared config to exactly the compiled block.

## 7. Measurement

* `scripts/checks/stage3_effect_floor_check.py`: `measurement_design` `same-flight-node-column`, read at the
  same-flight contrast floor (per metric, BORROWED from `same-flight-supply-variant`: intent 0.65, SLU 1.49 at
  n = 1,080 until a node-column cell measures its own twin null), with a shape-checked `template_variants` summary
  `{node, candidate_arms, twin}`.
* `scripts/analysis/slurp_nx_solver_column_read.py` (E2): per arm, paired per row against the delivering arm: raw
  parse validity, raw first-answer entity exact-set, empty-gold false fill, non-empty exact, per-slot-type counts;
  paired Wilson of the discordant rows and a whole-utterance cluster bootstrap CI95 (10,000 draws, seed 20260915) of
  the per-row differences. Gold through the governed loaders; no text is printed.

## 8. Rejected alternatives

* A parallel `template_variants` custody channel with its own node, receipt key and bundle verifier: duplicates the
  five seams the supply form already crosses and forks every downstream reader.
* Re-flying the node per candidate (cross-flight): reintroduces the flight offset the programme exists to remove.
* Putting the template in a knob tail of `SUPPLY_VARIANT_KNOB_TAILS`: the knob parser is integer-valued and the
  design (E42) deliberately keeps it unable to reach anything but a supply selection.

## 9. Open questions

See the README. In short: the candidate bound (6 plus lock plus twin) is the programme's C0.5 read as "candidates";
the Reviewer and Planner wiring is config-only for the parser but not yet for the node class; the borrowed floor is
provisional; `flight_registration_check.py` has no node-column registration findings yet.

## 10. The decoding kind (NX-T R4, owner rulings 329 A and 332 A, 2026-10-18)

A sibling kind of the template kind: a same-flight column whose arms differ ONLY in the sampling parameters of the Solver's
own contact. Everything section 1 says the template kind reuses, the decoding kind reuses with the template axis removed.

**Declaration.** `roles.solver.decoding_variants`, exactly `{node, arms, max_supplied_items, fit_estimate, template_tokens}`
(`template_tokens` is the node's LOCKED template token count, shared by every arm; it enters only the fit estimate). An arm is
`{arm_id, deliver?, replicate_of?, decoding?}`. A candidate arm carries `decoding`, a non-empty object over the closed set
`rails.native_episode_receipt.DECODING_VARIANT_KNOBS`:

| parameter | kind | bounds |
| --- | --- | --- |
| `temperature` | number | [0, 1.5] |
| `top_p` | number | (0, 1] |
| `top_k` | integer | [1, 200] |
| `presence_penalty` | number | [0, 2] |

`min_p` and `frequency_penalty` are deliberately NOT admitted (add one to the table only when a round needs it). The delivering
arm is LAST and the twin (`replicate_of` the delivering arm) is optional; both declare no `decoding`, so their requests are the
locked plan's byte for byte. Candidates 1..6 (plus the delivering arm and at most one twin), `arm_visits` fixed `first`.

**Refusals (before any contact, by name).** Everything in section 3 that is not about a template, plus: an arm naming a
parameter another axis owns -- the request `seed` ("the request seed is the lock's for every arm"), `max_tokens`,
`thinking_budget_tokens`, `chat_template_kwargs` (the thinking-budget axis), `response_format`, `tool_choice`,
`parallel_tool_calls` (the node's own), `id_slot` (serving geometry), `min_p`, `frequency_penalty`, `logprobs` -- is refused
with the owning axis in the message; an unknown parameter, a mistyped value (boolean, string, non-integer `top_k`), a
non-finite value, an out-of-bounds value, an empty or non-object `decoding`; a template or supply knob on an arm
(`instruction_template`, `template_tokens`, `overrides`, `release_swap`, `knobs`, a per-arm `max_supplied_items`); an override
that sets every named parameter to the lock's own value (compared with the cell's effective request decoding, so such an arm
would be a second spelling of the delivering arm); two arms with the same override; the fit overrun of section 3 (its
estimate has no template term beyond the shared locked-template count).

**Runtime contract.** The runner treats the decoding group in template mode (`SupplyVariantGroup.unvaried_evidence`): every
arm's two messages come from the one `base_messages(ctx)`, no per-arm supply is resolved, no per-arm material builder exists
(`binding.template_variant_materials` must be empty). The override is applied at ONE seam,
`MeteredNativeSpeechRequest.prepare`: after the role-level completion cap and thinking policy and before the answer-only
re-ask, on the contacts of the Solver role whose `variant_arm_id` names a candidate arm, as `decoding.update(override)`. The
template, evidence, response format, thinking budget and cap, seed and tool authority are not touched. The delivering arm and
the twin have no map entry, so an armed adapter's requests for them (and for every Perception contact) are byte-identical to an
unarmed adapter's (unit-tested at the request level and in the live harness against an UNARMED run). The answer-only fallback
re-ask of a candidate contact (decision 278) is derived from the arm's own decoding, so it keeps the arm's sampling.

**Wire.** `core.model.request_types.ALLOWED_DECODING_KEYS` already admits `temperature`, `top_p`, `top_k` and
`presence_penalty`; `core.model.transport` moves every `decoding_params` key it does not own to the top level of the
OpenAI-compatible request body unchanged, which is where llama.cpp's server reads each of them (read from source; no server
was contacted). Stochastic sampling at a fixed request `seed` is reproducible only up to the serving geometry's batching
nondeterminism (the R2b analysis measured 25 % forced-status flips between two greedy arms at 4 slots), so a sampling arm's
discordance against the delivering arm is reported beside the twin's.

**Custody.** `decoding_params` is part of the request payload, so the override is covered by the trace's `payload_sha256`; the
arm identity (`variant_arm_id`) is already in the role custody document; the receipt `saea-supply-variant-arms-v6` (v3 arm rows
plus `decoding_override`, `None` for the delivering arm and the twin, the declared `{name: value}` for every other arm) states
each arm's override and the runner and the flight re-check the sealed rows against the declaration. A v6 receipt requires
every arm to supply exactly the delivering arm's ids and distinct overrides, and validates under the same
`validate_supply_variant_receipt`. Receipts v1 to v5 validate unchanged. The effect-floor gate keeps the
`same-flight-node-column` design and its `template_variants` summary key `{node, candidate_arms, twin}` for this kind (the key
names the node-column summary, not the template axis).

**Consumption module.** A column of kind `decoding` is one arm of the block:
`{column_id, kind: "decoding", node: "solver", decoding: {...}}`, with one block-level `decoding_frame`
`{max_supplied_items, template_tokens, twin, fit_estimate}`; the carrier hook `decoding_variant_frame` names the block path,
the node and the delivering (`lock`) and twin (`aa`) arm ids. The compiler builds the block, parses it with
`parse_decoding_variants`, adds K - 1 to the ceiling and selects `phase-native-module-v1-c<ceiling>`. Decoding columns are
admitted under the review-off profile and refused beside any other column kind.

**Tests.** `tests/unit/test_decoding_variants.py` (parser, receipt, loader, compiler) and
`tests/unit/test_decoding_variants_live.py` (request seam, live harness).
