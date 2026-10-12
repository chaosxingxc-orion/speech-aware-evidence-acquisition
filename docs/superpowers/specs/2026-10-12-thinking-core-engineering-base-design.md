# Thinking-core engineering base: reasoning controls, the no-truncation guarantee, reasoning context policy, per-node thinking and throughput (design for decision 268)

Date 2026-10-12. Author: Claude Opus 5.5 (engineering-analysis agent, coordinator brief by Fable 5.1), worktree
`opus/thinking-core-engineering-design` from master `8a4dbb48b`. Model-free: no model, server, encoder, tokenizer or GPU
was contacted; the resident server was not touched; nothing was written under the data root. Read-only inputs: the pinned
llama.cpp fork source (`/home/chao/llama.cpp-featcache`, HEAD `04ccc72a2`), the two GGUF chat templates (dumped
read-only with the fork's `gguf-py` `GGUFReader`, CPU, metadata only), the THINK serving session records, and the COST /
USE channels of three sealed traces (token counts, latencies and role ids only; no text was read or printed).

Owner directive of 2026-10-12 (registry `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, section
"Owner rulings 2026-10-12"): if the Thinking core's effect stacks on the system, re-base the engineering on Thinking
mode; Thinking must FINISH the task and never be truncated midway; decide whether context engineering carries Thinking's
intermediate results; and say whether llama.cpp can be configured externally so that some nodes think and others do
not, to raise throughput.

Decisions for the owner are numbered **275-283** (274 is the owner's base-unification directive in the registry) (section 7). Unverified statements are marked **[unverified]**.

## 0. Findings in one screen

1. **The pinned build already has every control we need. No rebase is required.** The fork is upstream
   `fdbd6abee` (2026-06-25, #24935) plus 7 speech-feature-cache commits. The fork diff
   (`git diff --stat fdbd6abee 04ccc72a2`) touches only `tools/mtmd/*`, `tools/server/server-common.*`,
   `tools/server/server-context.cpp`, `tests/test-server-tokens.cpp` and CMake. None of its hunks mentions reasoning
   or thinking. The pinned build provides:
   - a server-global `--reasoning-budget N`;
   - a per-request `thinking_budget_tokens`;
   - a budget sampler that forces the think block to close;
   - `--reasoning-budget-message`;
   - per-request `chat_template_kwargs` (including `enable_thinking`);
   - a per-request `reasoning_format`;
   - a mid-generation `POST /v1/chat/completions/control` (`reasoning_end`).
2. **The Thinking GGUF's embedded template honours `enable_thinking: false`.** It pre-fills an empty
   `<think>\n\n</think>\n\n` block. The live THINK session logged `chat template, thinking = 1`, so the server detected
   the reasoning tags, and the budget fields are therefore forwarded to the sampler.
   Caveat: the model card calls this checkpoint "thinking-only". A no-think node on it is out of distribution, so its
   answer quality must be measured.
3. **The guarantee.** A per-node reasoning budget B is enforced by logit forcing of `</think>`
   (`common/reasoning-budget.cpp`). The node's `max_tokens` is set to B + R, where R is an answer reserve. A receipted
   one-shot answer-only fallback covers the residual case. Together these make "an empty answer at max_tokens"
   impossible except as a receipted double failure. At B = 3,072 the budget covers 98.3 % of the naturally finishing
   266-E contacts; the 36 runaway contacts get forced closes instead of empty answers.
4. **The module program makes the runaway worse than it looks today.** If a Thinking Perception contact hits
   `finish_reason = length` with empty content, the whole row abstains. E39 tolerance never applies to empty text, and
   there is no Solver to fall back to (`reproduction/ojw/native_roles.py` `_tolerated_truncation`;
   `reproduction/ojw/native_episode.py` `_finite_terminal_outcome`). Unbounded, about 6.6 % of rows would abstain on the
   delivered path alone (3.3 % per thinking contact on Perception and on the delivering Solver).
5. **Context policy: carry no reasoning across nodes (the status quo, kept as an explicit, hashed knob).** Qwen's
   guidance and the Qwen3-Omni template both drop historical thinking. Our harness already passes only `content`
   between nodes (`state["perception"] = output`), and the OpenJiuwen projection drops `reasoning_content`.
6. **Per-node thinking.** It runs on ONE resident Thinking server and uses per-request fields only. Two resident cores
   cannot fit, and a per-node model swap is not feasible.

   | 268 column shape | GPU-h | wall |
   | --- | ---: | --- |
   | c4 as the loop flew it (P + 3 Solver arms), unbounded cap 8,192 | 9.2 | 10-13 h |
   | c4, budgeted (B = 3,072), all nodes think | 7.9 | 9-11 h |
   | c3 (P + lock + in-row twin), budgeted, all nodes think | 5.9 | 6.6-8.5 h |
   | c3, Solver-only thinking | 4.5 | 4.9-6.4 h |

   Only the c3 shapes reliably fit a working day.

## 1. llama.cpp reasoning controls in the pinned build

Pinned build identity: binary `/home/chao/llama.cpp-featcache/build/bin/llama-server`, `build_info` `b8-04ccc72a2`,
binary sha256 `d0b42ace...` (THINK `session.json`,
`$SPEECHRL_DATA_DIR/serving/serving-slurp-thinking-direct-fold-b-np4-max8192-v1/session.json`). Fork log:
`04ccc72a2`, `9c0659e6e`, `1a3039c77` (2026-08-21, speech packets), `5d9dfcb58`, `1c806481c`, `862effd0f`, `b3dc62149`
(2026-08-11, feature cache), on upstream `fdbd6abee` (2026-06-25).

### 1.1 What exists, with file references (fork HEAD `04ccc72a2`)

| control | scope | where | semantics |
| --- | --- | --- | --- |
| `--reasoning-budget N` (env `LLAMA_ARG_THINK_BUDGET`) | server-global default | `common/arg.cpp` ~3159 | -1 unrestricted (default), 0 immediate end, N > 0 token budget |
| `thinking_budget_tokens` | **per request** (`/v1/chat/completions`) | `tools/server/server-common.cpp` 1509-1520 | -1 (or absent) falls back to the server default; otherwise overrides it for this request. Forwarded ONLY when the template yields a non-empty `thinking_end_tag` |
| `--reasoning-budget-message MSG` | server-global | `common/arg.cpp` ~3167; `server-common.cpp` 1518; `server-schema.cpp` 397-404 | text forced before the end tag when the budget expires; forced sequence = tokenize(MSG + end_tag) |
| `reasoning_control` + `POST /v1/chat/completions/control {"id","action":"reasoning_end"}` | per request, mid-generation | `server-schema.cpp` 375; `server-context.cpp` 2642-2652, 4900-4930; `tools/server/server.cpp` 211; README "POST /v1/chat/completions/control" | arms the budget sampler so a client can force the close at any time |
| `chat_template_kwargs` | per request | `server-common.cpp` 1458-1473 | merged over `--chat-template-kwargs`; a boolean `enable_thinking` sets `inputs.enable_thinking`, and a string-typed value is refused |
| `-rea/--reasoning on/off/auto` | server-global | `common/arg.cpp` 3141-3157 | sets the default `enable_thinking`. The `--chat-template-kwargs enable_thinking` route is deprecated in favour of this flag (`arg.cpp` ~2994) |
| `reasoning_format` | per request or `--reasoning-format` | `server-common.cpp` 1446-1449; `arg.cpp` 3130 | `none`: thoughts stay in `content`; `deepseek`: thoughts go to `message.reasoning_content`; `deepseek-legacy`: both |

The per-request `thinking_budget_tokens` is not described in the server README of this build. It is read from the
request body in code (`server-common.cpp` 1509), and the Anthropic-compatible path maps `thinking.budget_tokens` onto it
(`tools/server/server-chat.cpp` 529-535). Upstream history of the feature: not needed, because it is inside our pinned
base. The fork's own commits do not touch any reasoning code, so **no rebase and no rebuild is required**.

### 1.2 How the budget closes the think block (the "finish" mechanism)

`common/reasoning-budget.cpp` / `.h` implement a sampler with the state machine
IDLE -> COUNTING -> (WAITING_UTF8) -> FORCING -> DONE.
- **IDLE.** The sampler watches for the start-tag token sequence.
- **COUNTING.** It decrements a budget per generated token. A natural `</think>` moves it to DONE.
- **Budget exhausted.** It waits for the current UTF-8 sequence to complete, then enters FORCING. There every logit
  except the next forced token is set to `-inf` (`common_reasoning_budget_apply`). It forces MSG + `</think>` token by
  token.
- **DONE.** Passthrough. This is **the guarantee mechanism**: the close is forced by masking, not merely truncated.
  After the close, the model writes its answer normally until EOS or `max_tokens`.

Interactions that matter for us:
- **Creation.** The sampler is created only when start and end tags exist and one of these holds: a budget >= 0,
  `reasoning_control`, or a lazy grammar (`common/sampling.cpp` 299-311). The generation-prompt prefill tokens are fed
  through it, so a template that pre-opens `<think>` starts in COUNTING.
- **Grammar.** Grammar constraints (`response_format` JSON schema) apply only while the budget sampler is IDLE or DONE
  (`common/sampling.cpp` 436-440). JSON-constrained answers therefore compose with thinking.
- **Re-arming.** In DONE the sampler re-arms on a NEW `<think>` with a fresh budget (`reasoning-budget.cpp`, DONE case:
  "some models emit multiple <think> blocks"). A model that re-opens thinking after a forced close can spend a second
  budget. `max_tokens` = B + R bounds that, and the residual is the fallback of section 2.4.
- **What counts against `max_tokens`.** `n_predict` counts every generated token, including the `<think>` token, the
  forced message and the end tag. R must cover the answer plus those few tokens.
- **Unit test.** The fork carries `tests/test-reasoning-budget.cpp` (budget, clone mid-counting/forcing, manual force,
  UTF-8 boundary). It is not built in `build/bin` today **[unverified on this build; a CPU-only build of that one test
  is a 0-GPU check, section 6]**.

### 1.3 The Thinking GGUF template and `enable_thinking`

Dumped read-only from `/home/chao/models/qwen3-omni-30b-a3b-thinking-gguf-q4km/Qwen3-Omni-30B-A3B-Thinking-Q4_K_M.gguf`
(`tokenizer.chat_template`, 5,715 chars; the same bytes appear as `props.chat_template` in the THINK `session.json`).
Its tail:

```
{%- if add_generation_prompt %}
    {{- '<|im_start|>assistant\n' }}
    {%- if enable_thinking is defined and enable_thinking is false %}{{- '<think>\n\n</think>\n\n' }}{%- endif %}
{%- endif %}
```

- **Thinking on (default).** The generation prompt is plain `<|im_start|>assistant\n`. The model opens `<think>`
  itself, and the budget sampler starts IDLE and activates on that token.
- **`enable_thinking: false`.** An empty think block is pre-filled. The model answers directly, with zero reasoning
  tokens generated.
- **Historical turns.** An assistant message before the last user query is rendered as `content` only: reasoning is
  stripped. Reasoning is re-rendered only for assistant turns AFTER the last user query, i.e. inside one turn's tool
  loop, when `reasoning_content` is present.
- **The Instruct GGUF** (`.../qwen3-omni-30b-a3b-instruct-gguf-q4km/Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf`, 6,519
  chars) has the same tail.
- **Detection by the server.** The server decides template thinking support by rendering a probe
  (`common/chat.cpp` 355-368, `common_chat_templates_support_enable_thinking`) and, for templates without a
  specialised handler, by the differential autoparser (`chat.cpp` ~2585-2595, `thinking_start_tag` / `thinking_end_tag`
  from `autoparser.reasoning`). The THINK server log records `init: chat template, thinking = 1` on every start
  (`$SPEECHRL_DATA_DIR/serving/serving-slurp-thinking-direct-fold-b-np4-max8192-v1/server.log` lines 35 and 414).
  Detection succeeded, and so the per-request budget is forwarded. The exact detected tag strings are not logged at
  INFO **[unverified: expected `<think>` / `</think>`; the first budgeted smoke logs `reasoning-budget: activated` at
  INFO, which proves it]**.
- **Model-card caveat.** Qwen describes Qwen3-Omni-30B-A3B-Thinking as a thinking-only checkpoint
  (https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Thinking). The `enable_thinking` branch is inherited template text.
  How good a no-think answer from this checkpoint is remains **unmeasured** (section 4).

### 1.4 What the OpenAI-compatible endpoint returns

Under `--reasoning-format deepseek`:
- thoughts go to `choices[0].message.reasoning_content`;
- the answer goes to `message.content`;
- `finish_reason` is `stop`, `length` or `tool_calls`.

At `max_tokens` inside an open think block, every generated token is reasoning. `content` is empty and `finish_reason`
is `length`. This is exactly the 266-E failure: 36 of 36 receipts show `finish_reason` length, `completion_tokens`
8,192 and empty content (`docs/results/2026-10-12-slurp-266e-thinking-vs-instruct-bare-core-read.md` section 5).

Our transport:
- never reads `reasoning_content`;
- refuses `<think>` markers in content (`core/model/transport.py` 366-379, 1497-1528);
- forwards `finish_reason` under the guard (1530-1534).

Multi-turn input: the server parses `reasoning_content` on incoming assistant messages, and the template decides
whether to render it (server README "Reasoning support", PR https://github.com/ggml-org/llama.cpp/pull/18994).

## 2. The no-truncation guarantee

### 2.1 Policy

Each node runs in one of two modes.
- **Thinking node.**
  - Request `thinking_budget_tokens = B_node` and `max_tokens = B_node + R`.
  - The server flag `--reasoning-budget-message` carries a fixed close sentence, which marks the close and makes it
    detectable.
  - The Qwen3 technical report describes this halt-and-insert scheme (arXiv:2505.09388, section on the thinking budget;
    its stop sentence is "Considering the limited time by the user, I have to give the solution based on the thinking
    directly now." **[wording from memory; verify against the paper before pinning]**).
- **No-think node.** Request `chat_template_kwargs = {"enable_thinking": false}` and `max_tokens = R`.

Defaults (decision 276):

| knob | value | why |
| --- | ---: | --- |
| B (Perception, Solver) | 3,072 | covers 98.28 % of the 1,044 naturally finishing 266-E contacts and 95.0 % of all 1,080 (table 2.2); adds only ~66 tokens per contact over B = 2,048 |
| R (answer reserve) | 1,024 | the largest answer on the Instruct module column is 158 tokens (Perception) and 105 (Solver) (i2 trace COST, section 4.2); R is 6.5x that, plus the forced tokens |
| `max_tokens` | 4,096 | = B + R; the new model fragment's geometry cap (replaces 8,192) |
| fit `completion_ceiling` | 4,096 | must equal B + R. **At 8,192 the ace arm's fit estimate (2,000 + 63 x 235 + 8,192 = 24,997) exceeds the 24,576-token slot.** At 4,096 the worst arm is 20,901 |

### 2.2 Sizing from the 266-E distribution (COST channel, 1,080 contacts; computed here)

Completion tokens include reasoning and the answer. On the bare form the answer is short, so these are close to
reasoning tokens.

| B | contacts <= B, all 1,080 | contacts <= B, the 1,044 natural finishes | forced closes expected |
| ---: | ---: | ---: | ---: |
| 1,024 | 74.72 % | 77.30 % | 273 (25.3 %) |
| 1,536 | 85.83 % | 88.79 % | 153 |
| 2,048 | 91.11 % | 94.25 % | 96 (8.9 %) |
| 3,072 | 95.00 % | 98.28 % | 54 (5.0 %) |
| 4,096 | 96.20 % | 99.52 % | 41 (3.8 %) |
| 6,144 | 96.57 % | 99.90 % | 37 |

Percentiles:

| subset | p50 | p75 | p90 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| all 1,080 | 584 | 1,034 | 1,898 | 3,000 | 8,192 |
| the 1,044 natural finishes | 558 | 961 | 1,641 | 2,191 | 3,610 (max 7,694) |

The 36 runaway contacts are a separate mass. Each spent exactly 8,192 tokens and holds a slot for 190 s on average:
6,842 s, or 27.8 % of the arm's whole latency sum. Under any budget they become forced closes.

Why they run away is **unverified**. Two facts point at greedy decoding:
- Qwen's guidance for thinking mode is "DO NOT use greedy decoding, as it can lead to performance degradation and
  endless repetitions" (https://huggingface.co/Qwen/Qwen3-8B, best practices).
- The checkpoint's `generation_config.json` sets temperature 0.6, top_k 20, top_p 0.95
  (https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Thinking/raw/main/generation_config.json).

Our fragment decodes at temperature 0. The direct-only arm did not preserve wire bytes (its trace has no
`MODEL_WIRE_RESPONSE` channel), so no repetition statistic can be computed from the sealed records. The module program
sets `preserve_wire_responses: true`, so the 268 column will seal `reasoning_content`. A model-free repetition statistic
(tail compression ratio, periodic tail) then becomes possible on forced-close rows without printing any text.

### 2.3 Interaction with `finite_completion_policy = deliver-latest-or-abstain`

On the native module path:
- A `length` finish raises `FrozenCoreRoleFiniteCompletionError` (`native_roles.py` 496-500).
- E39 tolerance returns the truncated text only for a NON-answering role, and only if that text is non-empty
  (`_tolerated_truncation`, `native_roles.py` 1116-1160). A Thinking runaway has EMPTY content, so tolerance never
  applies.
- The episode's finite outcome delivers `latest_solver` if one exists, else an abstention
  (`native_episode.py` 1218-1314).

Consequences without a budget:
- A runaway **Perception** contact (the first node) abstains the whole row.
- A runaway delivering-Solver contact also abstains, because no earlier Solver exists in the review-off program.

With the budget, `length` can occur only if the answer itself exceeds R after the forced close, or if the model
re-opens a think block. Both are expected to be rare **[unverified until the smoke]**. The policy knob stays
`deliver-latest-or-abstain`, and the `finite_completion_policy_check.py` gate is unchanged. The new fallback (2.4) runs
BEFORE the finite outcome is reached.

### 2.4 The receipted fallback (decision 278)

Trigger: a thinking-node contact returns `finish_reason = length` with empty `content` (the forced close failed or a
second think block ran out).

The harness then makes **one** answer-only re-ask on the same node:
- the same messages, with `chat_template_kwargs = {"enable_thinking": false}` and `max_tokens = R`;
- metered and traced like any contact;
- receipted as `saea-thinking-answer-fallback-v1`, carrying the source contact id, both finish reasons and token counts
  (no text);
- counted in the plan budget;
- the node's contact ceiling rises by 1. The family `phase-native-module-v1-c<n>` already registers c2-c24
  (`rails/controllers.py` 1795-1822).

If the fallback also returns empty content, the existing E13 abstention (decision 199, "empty is legal") applies,
receipted as today. Thinking text from the failed contact is never carried into the fallback request (section 3).

Alternative B: no fallback, receipted abstention only. This is the current behaviour plus the budget.

### 2.5 Per-row cost model

Measured contact latencies:
- **Instruct module (i2 column, 4,320 contacts, COST joined to USE `native-role-contact` by request id).** Perception:
  3,590 prompt tokens mean, 114.8 completion tokens, 5.48 s per contact. Solver: 10,649 prompt tokens, 23.5 completion
  tokens, 7.45 s.
- **Thinking decode increment.** A least-squares fit on the 266-E COST channel at np4 gives
  latency = -0.96 + 0.02298 x completion_tokens, i.e. about 23 ms per generated token per slot (~174 tokens/s
  aggregate over four slots).

Model: thinking contact latency = Instruct-module latency of that role + 0.02298 x E[min(reasoning, B)]. E[min(x, B)]
from the 266-E distribution is 1,032 (unbounded at cap 8,192), 892 (B = 4,096), 848 (3,072), 782 (2,048) and 638 (1,024).

Assumptions **[unverified]**:
- Reasoning length on the module prompts follows the bare-form distribution.
- Per-token decode cost does not grow with the 3-5x longer module prompts. Longer prompts make attention per decoded
  token more expensive, so this likely understates the cost slightly.

## 3. Context policy for reasoning (decision 279)

- **Qwen guidance.** "In multi-turn conversations, the historical model output should only include the final output
  part and does not need to include the thinking content" (https://huggingface.co/Qwen/Qwen3-8B). The Qwen3-Omni
  templates implement this: reasoning is stripped from turns before the last user query and kept only inside a turn's
  tool loop (section 1.3).
- **llama.cpp.** The server accepts `reasoning_content` on assistant history, and the template decides whether to
  render it (README "Reasoning support", PR #18994).
- **Our harness today.**
  - Across nodes, carriage is content only. The Perception node writes `state["perception"] = output`, where `output`
    is the role's `actor_output`, i.e. the delivered content text. Downstream prompts read `state["perception"]` as
    plain text (`reproduction/ojw/native_episode.py` 842-874). The transport builds `actor_output` from
    `message.content` only and never reads `reasoning_content` (`core/model/transport.py` 1496, 577-581).
  - Within a role's tool loop, the OpenJiuwen projection keeps `content`, `tool_calls` and `finish_reason` only
    (`reproduction/ojw/native_roles.py` `project_native_assistant_message`, 518-540). The full wire message is restored
    only for custody validation (`restore_native_assistant_wire_message`, used in `rails/runner.py` ~5285). Whether the
    framework history serialiser could still emit `reasoning_content` is **[unverified; add a test]**.
  - The 268 program (review-off, `phase_tools: {}` in the i3 baseline fragment) has no tool loop. Each role visit is
    one contact.

**Recommendation: carry none (A), as an explicit registered knob.**
- `native_episode.reasoning_context_policy = "drop-reasoning-v1"`. Default for every reasoning fragment; refused on a
  non-reasoning fragment. It is part of the baseline fragment bytes, so it enters the protocol hash and the cell
  identity like every other native-episode knob.
- **Why not carry.**
  1. The Solver already receives Perception's structured output (the hypotheses JSON and the candidate supply built
     from it, `rails/candidate_semantic_supply.py`, `candidate_state_phase perception`).
  2. Carrying ~800-1,000 reasoning tokens per earlier node adds Solver prefill at every arm (3 arms in c4) and eats
     the slot budget the supply frame needs.
  3. Reasoning is not authored to be read by another node, and Qwen does not train the model to consume it.
  4. Carried text would put model-authored non-final material into the knowledge surface, which the ORG/SUPPLY
     separation keeps out.
- **Option B, a bounded summary.** A future, separately measured knob: `"carry-summary-v1"` with a token cap, produced
  by the SAME node's content (for example a `rationale` field in the response format), never by reading
  `reasoning_content`. Not recommended for 268.
- **Option C, carry raw reasoning.** Not recommended. It conflicts with the template's own convention.
- **Within-role tool loops** (relevant to A2T / E21 later, not to 268). Qwen's template re-renders reasoning inside one
  turn's tool loop. A second policy value `"carry-within-role-tool-loop-v1"` can be registered when a tool-bearing node
  flies on Thinking. That is a later measurement.
- **Required test (0 GPU).** On a stub server returning `reasoning_content`, no later request body of the same row
  carries any byte of it.

## 4. Per-node thinking control (decision 280) and throughput

### 4.1 Mechanism

**Recommended (A): one resident Thinking server with per-request fields.**
- A thinking node sends `thinking_budget_tokens = B` (plus `max_tokens = B + R`).
- A no-think node sends `chat_template_kwargs: {"enable_thinking": false}` (plus `max_tokens = R`).
- Both are per request, so serving identity does not move. Only `--reasoning-budget-message` is a server flag, and it
  needs one new fragment and session.

Alternatives:
- **B: a budget-0 node** (`thinking_budget_tokens = 0`). The model emits `<think>`, then the forced close. This costs a
  few generated tokens and keeps the model's own think-open habit. It is a fallback if `enable_thinking: false`
  measures badly on this thinking-only checkpoint.
- **C: two models.** Not possible. Each Q4_K_M decoder is 18.56 GB of weights (18,557,053,248 and 18,557,053,952
  bytes). Two need 37.1 GB before any KV cache. The records call the card 24 GB, and even a 32 GB RTX 5090 cannot hold
  both. A per-node swap costs a model load per contact.

Harness work (model-free; decision 283):
1. Add `thinking_budget_tokens` and a shape-restricted `chat_template_kwargs` (exactly `{"enable_thinking": bool}`) to
   `core/model/request_types.py` `ALLOWED_DECODING_KEYS` (85-130). The transport already forwards allowed keys to the
   body and refuses collisions (`transport.py` 1299-1314). Add both to the encode-only refusal list
   (`rails/encode_only_check.py` ~88).
2. Add a role-level `reasoning` block in `rails/native_episode_config.py` with fields
   `{mode: think|no-think, budget_tokens, answer_reserve_tokens}`. Compose it at the E39 seam
   (`max_completion_tokens`, 161-172; `reproduction/ojw/native_request.py` `MeteredNativeSpeechRequest.prepare`) into
   the per-contact decoding params. The loader refuses:
   - B + R above the geometry `max_tokens`;
   - the block on a fragment without `reasoning_content_guard`;
   - unequal policies across one supply-variant arm group (arms are instruments and must share decoding).
3. Bind the fit `completion_ceiling` to B + R for every `fit_estimate` (`rails/supply_variants.py` 201-205, 433-472).
4. Build the fallback of section 2.4 and its receipt. Emit a per-contact `reasoning` COST sub-record with: budget, mode,
   whether the close was forced (detected by the configured budget message at the end of `reasoning_content`, from
   bytes, never printed), and reasoning character count.
5. Add `reasoning_context_policy` (section 3).

### 4.2 Which nodes need reasoning

- **Solver: yes.** It writes the slots, and slot values are where Thinking's bare gain sits (+11.90 SLU; datetime,
  audio, alarm, transport +23-33 pp, results note section 4).
- **Perception: measure; do not assume no.** Intent is decided at Perception's shortlist rank in this system (study
  memory "node gain ledger 2026-09-28"; the Perception shortlist is the selector). Thinking's bare intent gain (+4.35)
  could live there. Thinking also LOSES intent in general (-15.8) and music (-12.5).
- **Supply / retrieval: no model contact.** They are model-free (sealed vectors, `kb-facet-v1`), so there is nothing
  to gate.
- **Reviewer / Planner.** Off in the review-off program.

For the transfer question 268 asks, the faithful arm is "the system on the Thinking core": every node thinks, budgeted.
The Perception on/off contrast is the first ablation (section 6).

### 4.3 Throughput (per 1,080-row pass, 4 slots)

GPU-h are slot-normalised (latency sum / 4 / 3600). Wall time applies the measured idle factors:
- 1.11 on the direct-only Thinking arm (1.9 h wall over 1.71 slot-normalised);
- about 1.44 on the Instruct module column (about 3 h wall for 2.09 slot-normalised, registry 268 brief).

The higher factor reflects the per-row Perception -> Solver dependency.

| shape | thinking nodes | B | s per row | GPU-h | wall |
| --- | --- | ---: | ---: | ---: | --- |
| c4 (P + 3 S), Instruct core (measured) | none | -- | 27.8 | 2.09 | ~3 h |
| c4 | all | unbounded (cap 8,192) | 122.7 | 9.20 | 10.2-13.3 h |
| c4 | all | 4,096 | 109.8 | 8.24 | 9.1-11.9 h |
| c4 | all | 3,072 | 105.7 | 7.93 | 8.8-11.4 h |
| c4 | all | 2,048 | 99.7 | 7.48 | 8.3-10.8 h |
| c4 | Solver only | 3,072 | 86.3 | 6.47 | 7.2-9.3 h |
| c3 (P + lock + in-row twin) | all | unbounded | 91.5 | 6.86 | 7.6-9.9 h |
| c3 | all | 3,072 | 78.8 | **5.91** | **6.6-8.5 h** |
| c3 | all | 2,048 | 74.3 | 5.57 | 6.2-8.0 h |
| c3 | Solver only | 3,072 | 59.3 | **4.45** | **4.9-6.4 h** |
| c3 | Solver only | 2,048 | 56.3 | 4.22 | 4.7-6.1 h |

- **Registry estimate.** The registry's 14 GPU-h for 268 counts 8,640 contacts (two passes x 4 contacts) at 22.8 s.
  The model above gives 18.4 GPU-h for two unbounded c4 passes, because module prompts add prefill.
- **Owner's bar** (a column within a working day). Two c4 passes cannot meet it on any setting. One c4 pass meets it
  only if budgeted and only at the low end of the factor range.
- **Single-pass c3 meets it.** The loop's c4 already carries the twin in-row: arm `aa` is `replicate_of: lock`
  (i3 baseline fragment, `roles.solver.supply_variants`). Dropping the loop's `ace` comparator arm, which is not part
  of the lock, and keeping `lock` + `aa` gives the in-chain twin in ONE pass.
- **Abstentions.** Every budgeted row removes the unbounded design's expected ~6.6 % delivered-path abstentions
  (section 2.3).

## 5. What to register for decision 268

New model fragment `q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-max4096-v1`:
- the THINK geometry (c 98,304, np 4, q8_0 KV, `--reasoning-format deepseek`, Thinking packet root);
- `max_tokens` 4,096;
- the added server flag `--reasoning-budget-message "<fixed sentence>"`;
- `reasoning_content_guard` kept;
- temperature 0, seed pinned (decision 282).

This needs a new session id, because the server argv changes. Baseline / experiment: the lock v2.2 + v4g module program
as c3, with the knobs below.

| knob | recommended default | validated by |
| --- | --- | --- |
| `roles.perception.reasoning` | think, B 3,072, R 1,024 | stub-server test that the body carries `thinking_budget_tokens` 3072 and `max_tokens` 4096 (0 GPU); smoke: `reasoning-budget: activated` in `server.log` |
| `roles.solver.reasoning` | think, B 3,072, R 1,024, the same for every arm | loader refusal test for unequal arm policies (0 GPU) |
| fallback | answer-only re-ask, one per node, `saea-thinking-answer-fallback-v1` | stub returning `length` + empty content -> exactly one fallback request with `enable_thinking: false`, `max_tokens` R, a receipt, and the contact counted (0 GPU) |
| `reasoning_context_policy` | `drop-reasoning-v1` | stub returning `reasoning_content` -> no later request carries its bytes (0 GPU) |
| fit `completion_ceiling` | 4,096 | loader refuses a mismatch with B + R; the existing fit gate on the real supply (0 GPU) |
| `finite_completion_policy` / `react_exhaustion_policy` | unchanged (`deliver-latest-or-abstain` / `continue-without-answer`) | existing gates |
| geometry cap | 4,096 | flight registration check |
| smoke | 32 rows (not 4: the 266-E smoke overstated cost 1.8x with one runaway in four) | forced-close rate, fallback count (expected about 0), empty deliveries (expected 0), s per contact vs table 4.3 |
| plan | 1,080 x 3 contacts + at most 2 fallbacks per row as the ceiling; about 5.9 GPU-h expected, 8 GPU-h ceiling | `flight_registration_check.py` (row GPU vs plan) |

Read: c3 lock arm vs the Instruct lock column (64.34 / 82.41, cross-flight bar 2.5 pp), with the in-row twin as the
A/A. Per-stratum table, as required. Also: forced-close rows reported separately (descriptive), and the full roster as
the preregistered number.

## 6. After 268, if the gain stacks: the re-base path (one experiment in flight at a time)

1. **T1, Perception thinking on/off.** Same-flight Perception branches (the phase-2 `perception_branches`
   instrument). Arms: think vs `enable_thinking: false` (and budget-0 if the no-think arm degrades). It decides the
   per-node policy and saves about 1.5 GPU-h per column if Perception can go no-think.
2. **T2, Solver budget sweep.** B in {1,024, 2,048, 3,072} as Solver arms. This needs a new arm kind "decoding
   variant" beside supply variants: model-free engineering first. The quality per forced close sets B.
3. **T3, sampled vs greedy decoding.** Qwen's temperature 0.6 / top_p 0.95 / top_k 20 vs temperature 0, on the
   runaway / forced-close rate and on accuracy (seeded; the twin then measures sampling variance, so read with care).
4. **T4, serving geometry.** At B + R = 4,096 the worst Solver prompt (15,065 measured) needs 19,161 tokens, so np5
   (19,660 tokens per slot at c 98,304) fits. Measure aggregate decode tokens/s at np4 vs np5. The decode-bound
   Thinking workload is the case where more slots pay.
5. **T5, supply re-sizing for Thinking.** The Solver prefill (10.6k tokens mean) dominates the Instruct contact. With
   reasoning, fewer supplied items may suffice. A width sweep on the existing supply-variant instrument.
6. **T6, re-tune the Solver contract.** The Instruct-tuned Solver instruction may fight the reasoning (intent losses in
   general / music).
7. **T7, carriers on Thinking.** A2T / E21 / E22 base runs after the SLURP lock moves to the Thinking core (decision
   272 waits for 268). A2T is tool-bearing, so it needs the within-role tool-loop context decision (section 3).

0-GPU checks to run before 268 registration:
- (a) build and run `tests/test-reasoning-budget` CPU-only from the pinned source (it loads no model);
- (b) the stub-server tests above;
- (c) the fit loader tests;
- (d) confirm the Qwen3 report's stop sentence verbatim.

## 7. Decisions for the owner (proposed, numbered for the registry)

- **275 Mechanism.** A = per-request `thinking_budget_tokens` / `chat_template_kwargs` on one resident Thinking server
  (recommended; no rebase, no rebuild); B = server-global `--reasoning-budget` only (one budget for every node);
  C = no budget (today).
- **276 Budget and reserve.** A = B 3,072, R 1,024, `max_tokens` 4,096 (recommended); B = B 2,048 / R 1,024
  (cheaper by about 0.3 GPU-h per c3 pass, 8.9 % forced closes); C = B 4,096 / R 1,024 (3.8 % forced closes, about
  +0.2 GPU-h).
- **277 Forced-close marker.** A = `--reasoning-budget-message` with a fixed sentence (Qwen3-report style; a new
  fragment and session; gives a detectable forced-close receipt) (recommended); B = bare `</think>` (no server flag
  change; forced closes not detectable from bytes).
- **278 Fallback.** A = one receipted answer-only re-ask (`enable_thinking: false`, `max_tokens` R) per node,
  counted, then E13 abstention (recommended; the owner's "finish the task"); B = receipted abstention only.
- **279 Reasoning context.** A = `drop-reasoning-v1` across nodes (recommended; Qwen guidance and the template
  default); B = a bounded content-side summary (later, measured); C = carry raw reasoning (not recommended).
- **280 Per-node policy for 268.** A = every node thinks, budgeted (recommended for the transfer read); B = Solver-only
  thinking (cheaper, but confounds transfer with a node policy); then T1 decides the production policy.
- **281 Column shape.** A = one pass of c3 (Perception + lock + in-row twin `aa`), dropping the loop's `ace`
  comparator (recommended; 5.9 GPU-h, 6.6-8.5 h wall); B = c4 as the loop flew it (7.9 GPU-h, 9-11 h); C = two passes
  (about 16-18 GPU-h).
- **282 Decoding.** A = temperature 0 as in 266-E (recommended for comparability and the A/A twin); B = Qwen's
  sampled settings (T3 measures it later).
- **283 Engineering before registration.** A = implement section 4.1 items 1-5 with the 0-GPU tests on a branch
  (model-free code agent; no GPU; outside a campaign window) (recommended); B = register 268 with the server-global
  budget only (decision 275-B) and skip the harness knobs.

## 8. Sources

- Pinned llama.cpp source at `/home/chao/llama.cpp-featcache` (HEAD `04ccc72a2`): `common/arg.cpp`,
  `common/reasoning-budget.{h,cpp}`, `common/sampling.cpp`, `common/chat.cpp`, `tools/server/server-common.cpp`,
  `tools/server/server-schema.cpp`, `tools/server/server-context.cpp`, `tools/server/server-chat.cpp`,
  `tools/server/server.cpp`, `tools/server/README.md`, `tests/test-reasoning-budget.cpp`.
- GGUF templates: the two Q4_K_M files under `/home/chao/models/` (read-only, metadata).
- THINK session: `$SPEECHRL_DATA_DIR/serving/serving-slurp-thinking-direct-fold-b-np4-max8192-v1/{session.json,server.log}`.
- Sealed traces (COST / USE channels only): `runs/SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-V1/...-rec1-v1`,
  `runs/SAEA-SLURP-STAGE3-TFRL-LOOP-I2-FOLD-B-V1/...-generation-v1`.
- Study code: `core/model/transport.py`, `core/model/request_types.py`, `reproduction/ojw/native_roles.py`,
  `reproduction/ojw/native_episode.py`, `rails/runner.py`, `rails/controllers.py`, `rails/native_episode_config.py`,
  `rails/supply_variants.py`, `rails/candidate_semantic_supply.py`.
- Study configs: `configs/model/q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max8192-v1.json`,
  `configs/{baseline,experiment}/slurp-native-stage3-tfrl-loop-i3-fold-b-*.json`.
- Records: `docs/results/2026-10-12-slurp-266e-thinking-vs-instruct-bare-core-read.md`; the registry
  `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md` (266-E, 268, owner rulings 2026-10-12).
- External: https://huggingface.co/Qwen/Qwen3-8B (best practices); https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Thinking;
  https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Thinking/raw/main/generation_config.json;
  https://github.com/ggml-org/llama.cpp/pull/18994; Qwen3 Technical Report arXiv:2505.09388.
