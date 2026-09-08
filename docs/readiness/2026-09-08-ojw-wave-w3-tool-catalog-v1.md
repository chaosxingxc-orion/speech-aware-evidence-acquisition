# WAVE W3: the tool catalog (2026-09-08, v1)

Owner Decision 11-B, item #5 of the openJiuwen implementation assessment's ordered change list. Built
model-free, at zero model contacts, on no GPU, in the `wt/ojw-w3` worktree.

The assessment's finding was blunt: **nothing in this repository is registered as a framework tool.
Zero.** `grep -rn "LocalFunction|ToolManager|tool_manager|foundation.tool|intent_toolkits|Toolkit"`
over `src/`, `tests/` and `scripts/` returned no hits, and the only occurrences of `LocalFunction`
and `intent_toolkits` anywhere were in the design note itself. This wave closes that gap for the
first eight tools the design note names.

## 1. The 2026-08-08 ruling is not re-litigated; it is enforced

The adoption memo's rebuild plan did say "DSP functions registered as framework local tools"
(`docs/readiness/2026-08-08-openjiuwen-adoption.md`). The owner **reversed** that the same day:

> `docs/readiness/2026-08-08-ojw-rebuild-notes.md:57`
> "DSP + slice rail | **NOT framework constructs, by design** … (owner ruling: the framework tool
> base is reserved for the phase-2 model-invoked re-ask arm; wrapping pipeline DSP as tools would
> change semantics to model-decided invocation)"

That ruling stands. The object this wave builds is a different one: a **system-invoked** catalog the
Planner reads, not a tool list the core is offered. Nothing here is rendered into a prompt, handed to
the core as a callable function, or selected by model output.

The distinction is machine-enforced, in three places rather than stated in a comment:

- `ToolManifest.system_invoked` must be `True`, and `rails.tools.build_tool_entry` — the ONE
  constructor of a catalog entry — refuses a manifest without it;
- `scripts/checks/tool_catalog_check.py` fails if any `TOOL_CATALOG.register(...)` call takes its
  entry from anything other than `build_tool_entry(...)`, so a hand-built `ToolEntry` cannot be
  slipped past the marker;
- the marker and `"invocation": "system"` ride into every framework `ToolCard`'s `properties`, so a
  reader of the card sees the same claim the code enforces.

A second, related boundary: `LEDGER_ROW_TYPES` has **no `model-contact` value**. The frozen core is
reached through the single door and is never a tool, so no manifest can claim a generation.

## 2. The manifest, exactly the design note's fields

Design note section 7: "id and pinned hash; typed inputs and outputs; side effects (bytes changed ->
derivation record required); cost class (CPU, GPU, contacts); the axis it serves (OBS / ORG / SUPPLY
/ USE); scope (general or carrier); the ledger row type it needs."

| field | meaning | validated |
|---|---|---|
| `tool_id` | catalog identity, `saea-tool-` prefixed | non-empty, prefixed, unique in the registry |
| `pinned_sha256` | sha256 over `inspect.getsource` of the wrapped function | 64 lowercase hex; re-measured by the check |
| `inputs` / `outputs` | typed I/O, as PYTHON type spellings | non-empty mappings of text to text |
| `changes_bytes` + `derivation_record` | side effects | biconditional: bytes changed **iff** a record is named |
| `cost_class` | `cpu` / `gpu` / `contact` | a `contact` may not declare ledger row `none` |
| `axis` | `OBS` / `ORG` / `SUPPLY` / `USE` | one of the four |
| `scope` | `general` or `carrier:<id>` | carrier must be in the owner-locked set |
| `ledger_row_type` | `none` / `tool-contact` / `service-contact` | never `model-contact` |
| `system_invoked` | the 2026-08-08 marker | must be `True` at registration |

`description` and `source_ref` sit beside them: the framework `ToolCard` requires a description, and
without the dotted target the pinned hash is over, the pin is unverifiable. `parallel_safe`,
`stateless` and `idempotent` are `ToolCard`'s own fields, carried so the card is complete.

The typed I/O is deliberately **not** a JSON schema. These tools are system-invoked over native
objects (`bytes`, `array`, dataclasses), never over model-emitted JSON; writing JSON types would
claim a decoding contract that does not exist. `tool_input_params` renders them under a
`python_type` key with `"x-invocation": "system"` inside the schema, so a framework reader cannot
mistake the card for a model-facing function signature.

## 3. The eight tools

| id | wrapped body (unchanged) | axis | scope | cost | ledger row | bytes |
|---|---|---|---|---|---|---|
| `saea-tool-diarization-artifact-v1` | `reproduction.diarization:load_diarization` | OBS | general | cpu | tool-contact | no |
| `saea-tool-slice-encode-v1` | `reproduction.obs_audio:encode_slice` | OBS | general | cpu | none | **yes** |
| `saea-tool-speaker-turn-units-v2` | `analysis.e21_speaker_turn_units:plan_units_v2` | OBS | carrier:earnings21 | cpu | none | no |
| `saea-tool-legal-label-projection-v2` | `reproduction.slurp_scoring:project_slu_label_v2` | USE | carrier:slurp | cpu | none | no |
| `saea-tool-repair-alignment-v1` | `core.repair_alignment:accept_entity_repair` | USE | general | cpu | none | no |
| `saea-tool-flagged-spans-v1` | `core.replay_signals:flag_spans` + `core.flag_sources:roster_band_flags` | OBS | general | cpu | none | no |
| `saea-tool-sealed-vector-query-v1` | `rails.phase_supply:load_sealed_vectors` | SUPPLY | general | cpu | tool-contact | no |
| `saea-tool-prompt-fit-tokens-v1` | `core.driver.speech_native:_LoopbackPromptAuditClient.request_json` | USE | general | contact | service-contact | no |

Each wrapper is one module under `rails/tool_wrappers/` holding one body that calls the existing
function unchanged and returns its result inside a `ToolResult`. No argument is renamed, defaulted or
reinterpreted on the way through; the manifests and the registration block live in `rails/tools.py`,
where the engineering base check reads the ids out of source.

Four decisions worth recording:

**The slice encoder is the only byte-changing tool**, so it is the only one that emits a
`DerivationRecord`. It emits one on **every** call, not only when a transform was declared: with
`transforms=()` and `pre_sha256=None` the record honestly says the bytes are the raw cut. Its three
fields are the three `core.model.SliceRegistry.register` already requires, so a record produced here
drops into the payload-binding rail without translation.

**The flagged-span detector is one tool over two bodies**, because the repository already treats
them as one object with several sources (`core/flag_sources.py` is named for the plural). A manifest
carries exactly one `source_ref`, so the second body is pinned by
`ADDITIONAL_PINNED_SOURCES` in the wrapper module and verified by the check identically. Dispatch is
a lookup and fail-closed: an unknown source name refuses rather than silently picking one.

**The diarization tool never runs a model.** The Sortformer pass is a separate, already-ledgered
batch contact (`scripts/e21_diarization_pass.py`); this tool reads and re-derives the sealed
`saea-diarization-v1` artifact that pass produced. Its cost class is therefore plain `cpu` while its
ledger row type is `tool-contact` — a user of the artifact must cite the pinned tool row. It also
accepts `dry_run=True`, returning the read it WOULD perform without touching the filesystem, so the
Planner can price the contact before committing to it.

**The prompt-fit tokenizer is a `service-contact`, and stays one by construction.** Its three
admitted routes (`/props`, `/apply-template`, `/tokenize`) are non-generative; the allow-list refuses
`/completion` and every other generative route, so the single door stays the single door. The client
is duck-typed so the wrapper does not import the 7,000-line driver that owns it, while the manifest
still pins that method's source by hash.

## 4. Equivalence results

The claim a wrapper is entitled to make is that registering a function as a tool changes **who
decides to call it**, never what it does. `tests/unit/test_tool_wrappers.py` asserts
`wrapped(...).result == direct(...)` for every tool, on synthetic inputs, and additionally:

| tool | equivalence evidence |
|---|---|
| diarization | byte-identical `DiarizationArtifact` on a synthetic sealed artifact; separate dry-run test proves the plan path reads nothing; an import scan proves the module cannot reach a diarizer runtime (no `nemo`, `torch`, `sortformer`, `subprocess`, `onnx`) |
| slice encode | equal `(wav_bytes, transforms, pre_sha256)` across four transform combinations (raw / rms-norm / tail 0.5 s / rms-norm + tail 2 s); the untransformed path re-proved byte-identical to `write_wav_bytes`; the derivation record re-checked against the direct call's own hashes |
| speaker-turn units | equal `tuple[UnitV2, ...]` and equal `as_dict()` per unit; a second case proves the three knobs pass through and change the plan |
| legal-label projection | equal `LabelProjection` including `branch`, across already-legal / 4-PROMOTE / 4-FALLBACK / label-free / unparsed; **and on the 18 real source labels the sealed 2026-09-06 projection-v2 receipt recorded** (`docs/checks/.../2026-09-06-slurp-legal-label-projection-v2/result-summary.json`) |
| repair alignment | equal `RepairOutcome` and equal `trace_view()` across substitution / empty predecessor / empty response / unrelated response / identical response; a second case proves the three bounds pass through |
| flagged spans | equal span list on the logprob source; equal `RosterBandFlag` list and spans on the roster-band source; unknown source refuses; the second body's pin re-measured |
| sealed vector query | equal `{id: {dimension: vector}}` mapping including exact float tuples; a wrong sha256 still refuses through the tool |
| prompt-fit tokenizer | the real `request_json` body runs end to end against an in-process fake connection (no socket, no server, no generation) on all three admitted routes; the wire bytes reaching the route are identical wrapped and direct; generative routes and a client without the method both refuse |

The receipt-grounded projection test rebuilds the legal space from the receipt's projection TARGETS
(the real 60-pair TRAIN inventory is built from the pinned corpus and is not committed), so it does
not re-derive the receipt's targets — it asserts the tool and the direct call decide identically on
every source label the flight actually emitted.

## 5. Toolkits per task type

`configs/toolkit/task-toolkits-v1.json`, loaded by `rails.tools.load_toolkit_table`:

| task type (carriers) | planner | observer | reviewer |
|---|---|---|---|
| `meeting` (earnings21, earnings22, conec) | prompt-fit-tokens | diarization-artifact, speaker-turn-units-v2, slice-encode, flagged-spans | flagged-spans, repair-alignment |
| `command` (slurp) | prompt-fit-tokens | slice-encode, sealed-vector-query | legal-label-projection-v2 |
| `tool-call` (audio2tool) | prompt-fit-tokens | slice-encode, sealed-vector-query | *(empty)* |

This follows the framework's own `core/controller/modules/intent_toolkits` pattern — a table of tool
schemas plus a subset selector — with two differences. The subset is chosen by task type and agent
role from config, never by a model, so a change to a carrier's toolkit rides in the composed config
hash. And it is **fail-closed**: an unknown task type, an unknown role, a missing role, an unknown or
repeated tool id, and a carrier-scoped tool offered to the wrong carrier's task type all refuse. That
last rule is why the SLURP legality judge cannot end up in the meeting toolkit by a copy-paste.

The framework's own `IntentToolkits.get_openai_tool_schemas(choices)` **ignores its `choices`
argument and returns everything** (installed `openjiuwen==0.1.16.post2`, last three lines of that
module). A toolkit whose selector does not select is not a toolkit, so a test pins that
`ToolkitTable.cards_for` really does select.

There is no `solver` row. The Solver is the frozen core behind the single door and calls no tool, so
the role does not exist to be declared. The Audio2Tool reviewer row is deliberately empty — a
statement that no deterministic judge is admitted for that carrier yet, not an omission.

## 6. Gates

- `scripts/checks/tool_catalog_check.py` — **PASS** (8 tools, 1 extra pin, 10 modules clean of
  framework clients). It proves manifest completeness, every pinned hash against the wrapped
  function's re-measured source, that no catalog module imports a framework LLM client / MCP tool /
  RESTful tool, that `openjiuwen` is imported only inside `to_tool_card` / `to_local_function` (the
  D2 zero-dependency gate: the module must import with the framework absent), that every
  registration passes through the marker-enforcing constructor with a string-literal id, and that
  the committed toolkit table loads with every catalog tool offered somewhere. Its own 14 tests
  include a negative control per rule.
- `scripts/checks/engineering_base_check.py` — **PASS**. One clearly-named WAVE W3 block:
  `rails/tools.py` joins `CANONICAL_REGISTRY_FILES`, and every `tools` LIST under `configs/` must
  resolve in `TOOL_CATALOG`. Verified live: the rule finds the table, resolves all eight ids, zero
  offenders. List-shaped deliberately — `configs/knowledge/a2t-kc-a1/targets-*.json` already carry a
  `tools` OBJECT of Audio2Tool function names, which is carrier payload and not catalog ids, and
  flagging it would be checking the wrong object (the same reasoning the existing
  `decoding_params.max_tokens.policy` rule records for matching by path).
- `ruff` — clean on every file this wave touched. (30 findings elsewhere in the tree are
  pre-existing and untouched.)
- Tests — 107 new, all green: `test_tool_catalog.py` 30, `test_tool_wrappers.py` 41,
  `test_tool_toolkits.py` 22, `test_tool_catalog_check.py` 14. The nine wrapped modules' own suites
  still green (321 passed).

## 7. What this wave did not do

- **No tool is wired into a running loop.** The catalog is a declaration plus a call path; no
  controller, policy or phase program calls `ToolEntry.call` yet. Wiring belongs to the wave that
  owns `rails/controllers.py`.
- **No framework `ToolMgr` registration at runtime.** `to_local_function` builds the object;
  nothing installs it into a session yet. Note for whoever does: the framework's
  `LocalFunction.invoke` coerces inputs through `SchemaUtils.format_with_schema` (jsonschema
  validation plus a pydantic round trip), which would destroy the `bytes` and `array` payloads half
  of these tools carry. The system call path is `ToolEntry.call`, and that is what every
  equivalence test pins.
- **`TOOL_CATALOG` lives in `rails/tools.py`, not `core/base.py`** — the same admitted stopgap
  `rails.knowledge_provider.KNOWLEDGE_PROVIDERS` used before E6 moved it. `core/base.py` is owned by
  a sibling wave this cycle. The engineering base check reads the registered set from source, so the
  object can move later without moving a single `TOOL_CATALOG.register` call.
- **The design note's named-but-unbuilt tools stay unbuilt**: the pinned local enhancer, the
  same-speaker exemplar index, the brief-name near-miss detector, decode-confidence signals from the
  trace, the acoustic re-check through a pinned embedder, and the per-episode core-call budget.
- **No admission receipt is claimed for any tool.** Section 8 of the design note requires a
  per-carrier ON/OFF contrast at n >= 400 before a module enters a default plan. Registering a tool
  is not admitting it, and this note claims no gain of any kind.
