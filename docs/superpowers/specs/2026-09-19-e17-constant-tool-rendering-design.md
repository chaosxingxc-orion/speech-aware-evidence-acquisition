# E17 (2026-09-19): constant native tool-schema rendering, and the live-slot fit gate

Engineering item E17. Author: Fable 5.1 (checker phase). Branch `fable/e17`.
Model-free: zero model, tokenizer, encoder and server contacts; nothing under `SPEECHRL_DATA_DIR`
was written.

Source of the problem and of every measured number below:
`docs/results/2026-09-19-slurp-throughput-root-cause-v1.md` (lever **L1**, sections 3.1, 5.2, 5.3,
6 and 7) and `docs/receipts/slurp-throughput-root-cause-v1.json`.

This item ships the mechanism and its proofs. It registers **no cell**: the efficiency cell EFF-1
is registered separately by the coordinator.

---

## 1. The measured problem

Three facts, all measured over sealed native runs:

1. `task_instruction` is **byte-identical across all four roles** -- one distinct SHA-256 over
   every request of every native SLURP run. The instruction is not what changes.
2. Only the Reviewer carries a native `tool_schemas` entry (the task-contract tool). The
   Qwen3-Omni chat template renders the `tools` array **inside the system message**
   (`<|im_start|>system\n` + content + `\n\n# Tools\n<tools>...`).
3. `decoding_params.id_slot` is `per-sample`, so one row owns one slot for its whole trajectory
   and its five contacts run in the order perception, solver, reviewer, reviewer, planner.

Together: the tools block **toggles on at contact 3 and off at contact 5**, and each toggle
changes the token stream about 2,220 tokens in, which invalidates the whole KV prefix behind it --
including the speech packet, re-decoded on 100 % of first-Reviewer and Planner contacts.

| position | role | tools | prompt (med) | prefilled (med) | cached | char LCP available | packet re-decoded |
|---|---|---|---|---|---|---|---|
| 0 | perception | 0 | 3,597 | 1,373 | 61.8 % | -- | 100 % |
| 1 | solver | 0 | 9,960 | 6,591 | 36.1 % | 0.254 | 0 % |
| 2 | reviewer #1 | **1** | 10,062 | **7,843** | 23.6 % | **0.822** | **100 %** |
| 3 | reviewer #2 | 1 | 11,813 | 1,757 | 83.5 % | 0.617 | 1.4 % |
| 4 | planner | **0** | 11,805 | **9,586** | 19.8 % | **0.849** | **100 %** |

Positions 2 and 4 carry **63.5 % of all prefill work**, and the flights are prefill-bound
(488-536 s per million prefilled tokens across four sealed runs, a spread of 5 %). Position 3 is
the existence proof that nothing about the Reviewer is intrinsically expensive: a *same-tools*
handover realises 83.5 % cache where the character proxy says only 61.7 % is available.

---

## 2. The mechanism

One episode-class switch key, `native_episode.tool_schema_rendering`, on the closed allowlist
`rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS` (its eighth member, and the first admitted for
efficiency rather than for a capability).

* `"per-role"` -- today's behaviour. The null arm is the key's **absence**; writing the default
  out loud composes the same episode, which `rails.config_tables.is_episode_null_arm` reads
  identically.
* `"constant"` -- every role contact of a row carries the **same** `tools` array: the union of the
  tool schemas any role of the episode may call, in one fixed order
  (`NativeEpisodeConfig.constant_tool_names`).

### 2.1 Rendering is not authority

The key changes **what is rendered**, never **what may be called**. Nothing else moves:

* each role's `tool_names` is unchanged, and `tool_choice` is still derived from `tool_names`
  alone -- a role with no authority still sends `tool_choice: "none"`;
* the framework still advertises that role no ability (`NativeRoleNode` builds it with no
  `abilities` and no `tool_allowed`), so the agent cannot dispatch one;
* if the core emits a call anyway, `reproduction.ojw.native_roles._RoleAuthorityRail._assert_allowed`
  still raises `AbortError` with a `PermissionError` cause, the framework hands the role the
  "outside role authority" tool result, and the episode continues. That path is unchanged and is
  re-proved for the armed arm in `tests/unit/test_e17_constant_tool_rendering.py`.

The pinned llama.cpp build supports this exactly: `tools` reaches the Jinja template whenever the
array is non-empty (`common/chat.cpp`, `common_chat_template_direct_apply_impl`), while
`tool_choice: "none"` only suppresses the tool-call grammar and parser. A tool-free role therefore
renders the identical system message and is still never steered to call.

### 2.2 The fail-closed admission rule

`load_native_episode_config` refuses `"constant"` when

* **no** role holds tool authority -- it would be a second spelling of `"per-role"`, and two
  spellings of one thing is how a cell acquires two identities; or
* two tool-bearing roles declare **different** ordered `tool_names`.

The second rule is custody, not taste. `rails.native_tool_authority.select_completion_tool_schemas`
re-derives a request's schema array from the names the model actually called and compares its
digest to that request's own `tool_schemas_sha256`; that only holds while a caller's rendered array
is exactly its own authority. With every tool-bearing role declaring one ordered array, the union
**is** each of their arrays, so a tool-bearing role's request is byte-identical to the `per-role`
arm's and only the tool-free roles gain the block. Today's SLURP episode satisfies this trivially:
the Reviewer is the only role with tools.

### 2.3 Where it is implemented

| file | change |
|---|---|
| `rails/config_tables.py` | the eighth episode-class key and its `"per-role"` null arm |
| `rails/native_episode_config.py` | `tool_schema_rendering`, `constant_tool_names`, the two refusals |
| `rails/runner.py` | binds `rendered_tool_names` on every contact; collects the per-contact evidence; seals the receipt block |
| `reproduction/ojw/native_request.py` | `NativeRoleSpeechBinding.rendered_tool_names`; rendering scope versus authority scope at `prepare`; `_assert_framework_schemas` (exact per role, containment under constant) |

### 2.4 The receipt

An armed episode seals one block per row under the native-episode receipt:

```
"tool_schema_rendering": {
  "schema": "saea-native-tool-schema-rendering-v1",
  "mode": "constant",
  "rendered_tool_names": [...],
  "contacts": [{contact_id, role_id, authority_tool_names, rendered_tool_names,
                tool_schemas_sha256}, ...],
  "distinct_tool_schemas_sha256": 1
}
```

`tool_schemas_sha256` is the digest of the `tool_schemas` array **that request actually carried**
(`rails.core_client.FrozenCoreClient._completion_metadata`), so
`distinct_tool_schemas_sha256 == 1` over a row *is* the constancy claim, and
`authority_tool_names` beside it is the visible proof that authority was not widened.

The OFF arm seals **no** block, exactly as E11/E12/E14's OFF arms seal none: the null arm must be
byte-identical to the pre-key tree, receipt included. The per-role digests of the sealed anchor are
not lost -- every run already records `tool_schemas_sha256` and `tool_names` per request in
`rails.core_client.RequestTiming`, which is what a verdict reads for the comparator side.

---

## 3. Expected saving

Setting positions 2 and 4 to their measured available reuse
((1 - 0.822) x 10,062 = 1,791 and (1 - 0.849) x 11,805 = 1,783):

| quantity | today | after L1 |
|---|---|---|
| prefilled tokens / row | 26,197 | **~13,065** (-50.1 %) |
| GPU-h / 1,080 rows | 3.837 | **~1.92** |
| 13,078-row test read | 46.5 h | **~23.2 h** |
| speech-packet re-decode share | ~80 % | <= 25 % (pass criterion) |

The bound is conservative: position 3 realises 83.5 % where the character proxy predicts 61.7 %.

Request bytes move on three of five contacts, so `config_hash` and `protocol_hash` change. Nothing
else does: no change to knowledge, roster, split, serving geometry, scorers, contact count, or any
role's authority.

---

## 4. Admission form

E17 ships the mechanism. Admission is a separate, one-factor **efficiency cell (EFF-1)**, registered
by the coordinator, on the current anchor base:

* **one factor** -- `native_episode.tool_schema_rendering` `"per-role"` -> `"constant"`, and
  nothing else, against the sealed anchor bytes;
* **effectiveness read: NEUTRAL, required.** Official pooled SLU micro F1 and intent accuracy at
  **n = 1,080** (TRAIN Fold A), scored once per complete manifest through `core.scoring_batch` with
  the SLURP official `evaluate.py`, under the existing own-null margins
  (intent half-width 0.92, SLU-F1 micro 1.18). A cell that is not NEUTRAL is not admitted, whatever
  it saves;
* **efficiency read: measured, not modelled.** Prefilled tokens per row, wall seconds per row,
  aggregate prefill tok/s, per-position cache shares and speech-packet re-decode share, all read
  from the serving session's `server.log` and the flight receipt, joined per slot exactly as the
  throughput report joins them. Plus GPU-hours per 1,080 rows against the anchor's 3.837;
* **the per-row constancy table** from the sealed receipt
  (`distinct_tool_schemas_sha256 == 1` on every row);
* **order.** L1 is evaluated **before** L2 (drop the Planner) and before L3 (shrink the evidence
  block), because four fifths of the Planner's apparent cost is this toggle and evaluating L2 first
  would credit it with L1's gain.

A cheap model-free precursor remains available and is not superseded by this item: re-render the
20 contacts of four sealed rows through the production transport with the key armed and emit the
predicted prefilled-token counts (report section 8, Probe A). The unit proofs in section 5 below
already establish the byte-level half of that claim.

---

## 5. What is NOT claimed

* **No effectiveness claim.** E17 asserts nothing about SLU F1, intent accuracy or any quality
  metric. The cell must read NEUTRAL; it is not expected to improve anything.
* **No measured token-level gain.** 50.1 % is derived from character-level longest-common-prefix
  proxies over sealed requests plus llama.cpp's common-prefix rule. Token-level realisation can
  only be confirmed on a live cell. Re-tokenising here would have been a tokenizer contact.
* **No claim about other carriers.** The measurement is SLURP native, np4, ctx24k, `id_slot`
  per-sample. Earnings and Audio2Tool are not addressed.
* **No claim that the Planner or the Reviewer is expensive.** Their neighbours' tools shape is.
* **No geometry change.** np6/np8 and `-ub` remain out of scope (report L8 and L5(b)); they become
  interesting only after the row is no longer prefill-bound.
* **The fit-gate repair below is not a lever.** It changes no request byte and saves no time.

---

## 6. The latent fit-gate defect, repaired

**The defect.** `core.flight.runtime.FlightRuntime._assess_prompt_budget` budgeted a preflight
prompt estimate against `rails.context_budget.PER_SLOT_LIMIT_TOKENS` -- a fixed 32,768 -- whenever
a fragment declared no `context_budget_limits` block. Every committed SLURP fragment is such a
fragment and every one of them serves **24,576-token** slots, so the gate reasoned against a slot
33 % wider than the one it guards (report section 4, "one latent inconsistency"). Nothing was
harmed: the widest prompt ever observed was 18,110 tokens. But a gate that budgets against a slot
the session does not have is not a gate.

**The repair.** `_assess_prompt_budget` now reads the live per-slot limit from the adapter's own
serving geometry -- the same number `serve()` turns into `-c` and `-np` -- and passes it to
`assess_context_budget(..., serving_slot_limit_tokens=...)`. Three budgets now exist, in
decreasing order of specificity:

1. a declared `context_budget_limits` block: unchanged, including its opt-in three-quarter
   occupancy rule;
2. **the live serving slot** (new): the slot limit is `min(live_slot, PER_SLOT_LIMIT_TOKENS)`, and
   the decision rule is the legacy one -- only the limit moves;
3. neither: the registered default, unchanged.

Two deliberate properties:

* **The live slot lowers the budget and never raises it.** The registered 32,768 stays the ceiling
  on an *undeclared* budget; raising it is exactly what the explicit block is for, and that block
  brings the stricter occupancy rule with it. A 49,152-token live slot therefore still budgets
  against 32,768.
* **The reserve stays proportionate.** `OPERATIONAL_RESERVE_TOKENS` is 8,192 -- a quarter of the
  registered slot. `serving_bound_reserve_tokens` keeps that number but never lets it take more
  than half the slot, because this study has actually flown 8,192-token slots (the np8 sessions),
  where an absolute 8,192-token reserve would refuse every prompt. The clamp is inert at 32,768
  and at 24,576; it binds only at or below 16,384.

**Bit-for-bit at 32,768.** At a live slot of exactly `PER_SLOT_LIMIT_TOKENS` the serving-bound
receipt equals the legacy one field for field, down to the pinned
`receipt_sha256` `1507f91e...0daf` that `tests/unit/test_agentloop_context_budget.py` already
guards. At 24,576 the same request is budgeted against 24,576 - 8,192 = 16,384 tokens instead of
32,768 - 8,192 = 24,576.

---

## 7. The measured render result

One row of the production harness (real OpenJiuwen role graph, real `rails.runner`, real
`LlamaServerTransport.render_request`, fake transport), five contacts on one pinned slot --
perception, solver, reviewer x2, planner:

| arm | distinct `messages[0]` | distinct rendered system prefix (`messages[0]` + `tools`) | contacts carrying `tools` |
|---|---|---|---|
| `per-role` | **1** | **2** | reviewer #1, reviewer #2 |
| `constant` | **1** | **1** | all five |

So the repository reproduces the report's premise exactly: the task instruction alone is already
constant, and the *tools array* is the whole toggle. Armed, the toggle is gone.

Byte-level delta, armed versus OFF, same row:

* **reviewer #1, reviewer #2: no change at all** -- identical request bodies, `tool_choice` `auto`;
* **perception, solver, planner: one added key, `tools`, and nothing else**
  (`{k: v for k, v in on.items() if k != "tools"} == off`), `tool_choice` still `none` on all three.

Sealed receipt for that row: `mode` `constant`, `rendered_tool_names`
`["saea-tool-task-contract-v1"]`, 5 contact rows, `distinct_tool_schemas_sha256` **1**, and
`authority_tool_names` `[]` for perception/solver/planner against
`["saea-tool-task-contract-v1"]` for the two Reviewer contacts -- rendering widened, authority not.

---

## 8. Proofs

| proof | file |
|---|---|
| the key resolves in the episode class; `"per-role"` is its null arm; the closed-allowlist ratchet | `tests/unit/test_e17_constant_tool_rendering.py`, `tests/unit/test_config_table_module_switches.py` |
| the loader's default, its armed value, and its two refusals | `tests/unit/test_e17_constant_tool_rendering.py` |
| rendered names must contain the authority names; the exact-versus-containment schema cross-check | `tests/unit/test_e17_constant_tool_rendering.py` |
| a role without authority that emits a call is still refused, under the armed arm | `tests/unit/test_e17_constant_tool_rendering.py` |
| per-role renders two system prefixes per row, constant renders one | `tests/unit/test_e17_constant_tool_rendering.py` |
| the tool-bearing role's bytes do not move; the three tool-free contacts differ in exactly the added array; `tool_choice` unchanged | `tests/unit/test_e17_constant_tool_rendering.py` |
| the receipt proves the constancy and records authority beside rendering | `tests/unit/test_e17_constant_tool_rendering.py` |
| the OFF arm is the key's absence down to the byte, receipt included | `tests/unit/test_e17_constant_tool_rendering.py` |
| the live-slot gate: bit-for-bit at 32,768, tightened at 24,576, never raised, proportionate reserve, forged receipts refused | `tests/unit/test_agentloop_context_budget.py` |

One pre-existing test defect was repaired in passing, because E17 lands in exactly its blast
radius: `tests/unit/test_feature_execution_unit_runtime.py` monkey-patched
`assess_context_budget` with a wrapper that accepted the candidate alone, so it raised `TypeError`
the moment the runtime named `limits=`. The wrapper now forwards keywords.
