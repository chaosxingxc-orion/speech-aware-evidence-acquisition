# Reviewer and Planner: the global state they receive, and what is missing (2026-09-26)

Owner ruling (2026-09-26, translated): *"I think Reviewer and Planner are the two that need GLOBAL
information, not local input, in order to make their decision — including the state of past errors
and corrections."*

That closes the per-node supply-scope direction the same day's dedup measurement opened
(`2026-09-26-slurp-supply-dedup-and-rerank-measurement.md`, section 6): the 67.8 % re-render at
those two nodes is not waste, because they retrieve nothing of their own precisely in order to judge
and to route over the whole picture, and a re-render is the only way the whole picture reaches a
stateless single-turn core. **No reduction was built, no arm was registered, no exposure row was
written and no receipt was minted.** This note audits SUFFICIENCY instead: what those two nodes
receive, whether the state of past errors and corrections is in it, and what is not.

**Method.** Model-free and local. Reproducer:
`scripts/analysis/slurp_reviewer_planner_global_state_audit.py`; two consecutive passes produce
reports differing in exactly one field, `tokenizer.invocations` (how many counts the sha256-keyed
cache did not serve), and in no measured number. Sources, all read-only: the sealed run traces of
five arms under `$SPEECHRL_DATA_DIR/runs/`, the committed `configs/` fragments, and the rendering
code. Tokens come from the local `llama-tokenize` binary at
`/home/chao/llama.cpp/build/bin/llama-tokenize` loading the pinned
`models/qwen3-omni-30b-a3b-instruct-gguf-q4km/Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf` vocab in a
local process (3,140 distinct texts, 4 workers) — no server, no port, no GPU, no encoder, no scorer,
**zero model contacts**. Ids, kinds, counts, token counts and hashes only; no utterance, transcript,
gold label, model output, knowledge body or rendered instruction is printed or persisted.

## 1. What a contact is, and therefore what "global" can mean here

One native-role contact is exactly **two messages**, one system and one user. The adapter
(`reproduction/ojw/native_request.py`) refuses any other shape, stores no conversation history and
executes no tool backend, so the frozen core carries nothing at all between contacts. Every later
node's global picture is re-rendered from the episode's accumulated state, once per contact, or it
does not exist.

Those two messages decompose into exactly these classes, each produced by a named function:

| class | where its bytes come from |
|---|---|
| system: task contract | `rails/runner.py::_agent_messages` (adapter system text + `"\n\nTask contract:\n"` + contract), sealed as `payload.task_instruction` |
| user: speech query packet | the one `input_speech_features` part; `speech-query-prefix-v2` places it first |
| user: supply bodies | `core/model/transport.py:896` — `[evidence <evidence_id>] <content>`, one text part per visible value |
| user: earlier role responses | `core/model/transport.py:352` — `[agent state <state_id> kind=<state_kind>] <content>`, one per exposed state |
| user: this node's instruction | the `rails/phase_material.py` template, appended LAST by `core/model/native_framework_history.py:313` |
| user: episode limits (control) | `rails/runner.py:2543` — `"\n\nNative episode limits: " + json.dumps(limits)` |
| tool schemas | `payload.tool_schemas` — **0 in every one of the lock arm's 2,590 contacts** |

Which states are exposed is decided by `select_native_role_history`
(`rails/native_episode_config.py:282`). The locked v2.0 plan
(`configs/baseline/slurp-native-stage3-var1-plan-r01c-baseline-v1.json`, the PLAN fragment as flown)
declares **no `history_scope`, no `context_policy`, no `reviewer_audit`, no `role_context`, no
`knowledge_index` and no `phase_tools`** — so `history_scope` is its default `"full"`
(`rails/native_episode_config.py:37`) for every role, and the exposed set is the episode's entire
monotone state chain.

**One class is sealed and never sent.** `history[-1]` is a control record whose content is the
framework envelope, a JSON document that re-embeds the whole message array
(`core/model/native_framework_history.py::framework_contact_instruction`). The wire renderer rebuilds
the user turn from `history[:-1]` (`:298`) and appends only `framework[1]["content"]` — the role query
— at `:313`. So that envelope is custody, not prompt: **2,599.6 tokens' worth of bytes per Reviewer
contact and 2,553.6 per Planner contact are sealed and never reach the model.** It is measured
separately below so the difference between sealed and sent is a number rather than a claim.

**The accounting closes.** Summing the classes above and subtracting from the sealed
`COST.prompt_tokens` leaves 75.6 / 76.6 / 76.8 / 77.0 tokens at Perception / Solver / Reviewer /
Planner on a first pass and 80.2 / 80.3 / 80.9 on a second — the speech packet plus the chat-template
frame, constant across roles as it must be, since every contact of a row carries the same single
packet. The class breakdown therefore accounts for 99.2 % of each prompt.

## 2. The per-node baseline, extended with the content-class breakdown

First, the dedup note's per-node table, re-derived here over **all** contacts from the sealed `COST`
and `MODEL_REQUEST` records rather than a sample — it reproduces exactly, and adds the state count:

| | Perception | Solver | Reviewer | Planner |
|---|---|---|---|---|
| store supplying it | `intent-boundaries` (k=8) | `train-exemplars` + `slot-contracts` | none | none |
| contacts | 625 | 657 | 657 | 651 |
| supplied items (mean) | 7.97 | 40.14 | 40.14 | 40.14 |
| **exposed earlier role states (mean)** | **0.00** | **1.15** | **2.15** | **3.14** |
| prompt tokens (mean, sealed COST) | 3,615.5 | 9,967.6 | 9,945.2 | 10,082.0 |

The two corroborating arms agree: PLANR 3,615.5 / 9,917.9 / 9,895.8 / 10,036.0 with 0.00 / 1.14 /
2.14 / 3.14 states, ROLL-1 3,615.5 / 9,935.2 / 9,924.5 / 10,059.3 with 0.00 / 1.22 / 2.22 / 3.22.

Now the class breakdown, on the lock arm `SAEA-SLURP-STAGE3-VAR1-PLAN-R01C-V1`, over a sample of 57
episodes (a deterministic 25-row stride plus all 32 revised rows, so the second-pass stratum is
complete). Tokens, mean per contact. The two strata are separated because a contact composed before
any Planner route cannot carry a correction, and one composed after always does.

### Table 1 — first pass (no Planner route has happened yet)

| content class | Perception (n=57) | Solver (n=57) | Reviewer (n=57) | Planner (n=56) |
|---|---|---|---|---|
| task contract (system message) | 2,217.0 | 2,217.0 | 2,217.0 | 2,217.0 |
| supply bodies: `intent-boundaries` | 1,090.1 | 1,090.1 | 1,090.1 | 1,090.3 |
| supply bodies: `slot-contracts` | — | 5,263.8 | 5,263.8 | 5,239.4 |
| supply bodies: `train-exemplars` | — | 715.8 | 715.8 | 717.0 |
| *of which `[evidence <id>] ` labels, all stores* | *118.0* | *586.2* | *586.2* | *585.2* |
| earlier response: Perception candidates | 0.0 | 193.7 | 193.7 | 194.2 |
| earlier response: Solver draft | 0.0 | 0.0 | 103.7 | 103.7 |
| earlier response: Reviewer findings | 0.0 | 0.0 | 0.0 | 216.8 |
| earlier response: Planner route | 0.0 | 0.0 | 0.0 | 0.0 |
| this node's own instruction | 188.0 | 208.0 | 82.0 | 36.0 |
| episode limits (control) | 50.0 | 50.0 | 49.0 | 49.0 |
| **all text classes** | **3,545.1** | **9,738.5** | **9,715.1** | **9,863.4** |
| speech packet + template frame (residual) | 75.6 | 76.6 | 76.8 | 77.0 |
| **sealed COST prompt tokens** | **3,620.8** | **9,815.1** | **9,791.9** | **9,940.4** |
| supply bodies, share of prompt | 30.1 % | 72.0 % | **72.2 %** | **70.9 %** |
| earlier role responses, share of prompt | 0.0 % | 2.0 % | **3.0 %** | **5.2 %** |
| task contract, share of prompt | 61.2 % | 22.6 % | 22.6 % | 22.3 % |

### Table 2 — second pass (after a Planner REVISE)

| content class | Solver (n=32) | Reviewer (n=32) | Planner (n=31) |
|---|---|---|---|
| task contract (system message) | 2,217.0 | 2,217.0 | 2,217.0 |
| supply bodies: `intent-boundaries` | 1,082.9 | 1,082.9 | 1,083.4 |
| supply bodies: `slot-contracts` | 5,123.7 | 5,123.7 | 5,100.3 |
| supply bodies: `train-exemplars` | 699.2 | 699.2 | 698.3 |
| *of which `[evidence <id>] ` labels, all stores* | *581.1* | *581.1* | *580.4* |
| earlier response: Perception candidates | 193.7 | 193.7 | 192.9 |
| earlier response: Solver drafts (**both**) | 102.6 | 206.5 | 205.9 |
| earlier response: Reviewer findings | 244.3 | 244.3 | 495.9 (**both**) |
| earlier response: Planner route (**its own**) | 82.5 | 82.5 | 82.4 |
| this node's own instruction | 208.0 | 82.0 | 36.0 |
| episode limits (control) | 45.0 | 45.0 | 45.0 |
| **all text classes** | **9,998.9** | **9,976.9** | **10,157.1** |
| speech packet + template frame (residual) | 80.2 | 80.3 | 80.9 |
| **sealed COST prompt tokens** | **10,079.1** | **10,057.2** | **10,238.0** |
| supply bodies, share of prompt | 68.5 % | **68.7 %** | **67.2 %** |
| earlier role responses, share of prompt | 6.2 % | **7.2 %** | **9.5 %** |

So the picture of "global" as it actually is: the Reviewer's global state is **297.4 tokens (3.0 %)**
on a first pass and **727.0 (7.2 %)** on a second; the Planner's is **514.7 (5.2 %)** and **977.1
(9.5 %)**. Against that, re-rendered knowledge bodies are 67–72 % of both prompts and the constant
task contract is 22 %. The two nodes that most need global state spend the smallest share of their
prompt on it.

## 3. Is the state of past errors and corrections in it?

**Yes — completely, verbatim, and with nothing dropped.** This is the owner's load-bearing claim and
it holds on the evidence, stated as plainly as the evidence allows.

PLAN's 625 episodes take four shapes: 588 rows walk perception → solver → reviewer → planner once;
**32 rows revise** (31 walk the full second pass solver → reviewer → planner, 1 stops after the
second Reviewer); 5 rows never reach the Planner.

| what the owner asked for | which rendered class carries it |
|---|---|
| what the Reviewer had objected to | its own earlier response, `kind=phase:reviewer`, 244.3 tokens |
| what changed in response | **both** Solver drafts, `kind=phase:solver`, in order, 206.5 tokens |
| which route was already tried | the Planner's own earlier action token, `kind=phase:planner`, 82.4 tokens |
| the candidate state both drafts answered from | `kind=phase:perception`, 193.7 tokens |
| where the episode stands in its revision budget | `revision_index`, `max_revisions`, `remaining_model_contacts`, `role_max_iterations` in the `Native episode limits:` JSON — one key set across all 2,590 contacts |
| which routes are still open | `available_planner_actions` in the same JSON, and it rides the **Reviewer's** limits too, so the judge knows what the router may do. Measured: 2 actions on 620 Planner contacts, 1 on the 31 second-pass contacts where the revision budget is spent |

Counted over every revised row of the lock arm:

- **second-pass Reviewer: 32 contacts, each rendering 5 of the 5 states sealed before it. Every one
  carries its own earlier review, both Solver drafts and the Planner's route. Earlier steps dropped:
  0.**
- **second-pass Planner: 31 contacts, each rendering 6 of the 6 states sealed before it. Every one
  carries its own earlier route, both Reviewer verdicts and both Solver drafts. Earlier steps
  dropped: 0.**

"Dropped" is measured, not assumed: for each contact the audit compares how many role states the
episode had sealed before that contact was composed against how many its prompt actually renders.
The two are equal at every contact of every arm. That is what `history_scope: "full"` means, made
concrete.

## 4. What is absent

Five absences. Each names the missing content class, the code path that would have to carry it, and
what carrying it costs. None is a design.

### G1. No state says which evidence it used

`cited_value_ids` is a field on every sealed role state, and it is empty in **all 4,209 rendered
states of all 2,590 contacts**: the native episode seals with `seal_phase_response_state(...)` and
never passes it (`rails/runner.py:2777`; the parameter defaults to `()` at
`rails/controllers.py:562`, `:585`). Even populated it would not be sent — the wire renderer prints
only `[agent state <id> kind=<kind>] <content>` (`core/model/transport.py:352`).

So the Reviewer cannot tell which of the 40 supplied bodies the draft rested on, and the Planner
cannot tell which body a finding disputes. Both must re-read the whole block and infer.

**Cost: almost nothing, because the addressing is already paid for.** Every body already arrives
labelled with its own id (`[evidence <id>] `), at **586.2 tokens per later contact — 6.0 % of the
Reviewer's prompt**, about 14.6 tokens per item. The model can already name any body. A citation
therefore costs only the ids a state chooses to name, about 11.6 tokens each; the upper bound, a
state citing its row's entire supplied set, is **466.0 tokens (4.8 % of the prompt)**. The code paths
are `rails.controllers.seal_phase_response_state`'s existing `cited_value_ids` argument and one added
field in `core.model.transport._speech_history_texts`' render.

### G2. The Reviewer's verdict is free text, not a typed finding with evidence links

`phase_material.reviewer.response_format_id` is `null` in the locked plan, so the Reviewer answers
prose and its 216.8-token state is prose. A typed form already exists —
`rails/review_findings.py`'s `saea-review-findings-v1`, whose every finding carries a `dimension`, a
`rationale` and **`evidence_ids`** — armed only in the NCP-L1 reviewer-format arms
(`configs/policy/phase-native-candidates-review-revise-findings-v1.json`,
`configs/probes/slurp_native_role_reviewer_findings_v1.txt`), never in the plan.

**Cost, measured on the arms that flew it, and it is not a budget question.** The typed findings
state costs 276.0 tokens (n=3, the 4-row smoke `…REVIEWER-FORMAT-ANCHOR-SMOKE-4-V1` — a sample far
too small to lean on, flagged as such), i.e. +59 tokens against the plan's 216.8. The one
large-sample structured Reviewer form in the tree is *cheaper*: 114.0 tokens over 535 states
(`…REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1`), −103 tokens. So a typed verdict costs between −103 and
+59 tokens per state, at most 0.6 % of a Reviewer prompt in either direction. The larger price is the
instruction: the findings template is **541 tokens against the plan's 82**, +459 per Reviewer
contact (4.7 % of the prompt).

### G3. Nothing labels the order of the attempts, and nothing states an outcome

The second-pass Planner is handed two Solver drafts and two Reviewer verdicts, and nothing in their
rendered text says which came first. The ordinal exists in custody — `history[].turn`, set at
`rails/core_client.py:1376` for a state and `:1401` for the control record — and the wire render
never prints it (`core/model/transport.py:352` renders id, kind and content only). Order survives
solely as the order of the user-turn parts, and the Planner is asked to decide whether its own
earlier objection was met from that alone. There is no field anywhere stating the OUTCOME of the
route already taken: the state chain is a list, never a diff.

**Cost:** rendering the already-sealed `turn` is a few tokens per state (four to six at today's
sizes, under 0.3 % of the prompt). An explicit outcome record would need a new state kind through
`rails.controllers.advance_phase_response_state`, priced at one more Reviewer-sized state per
revision, about 217–244 tokens.

### G4. No error state survives the row

Only four state kinds are ever rendered — `phase:perception` (1,965), `phase:solver` (1,403),
`phase:reviewer` (746), `phase:planner` (95) — and all four are this row's own. No tool record, no
acquired-evidence state, no delivery event, and nothing at all from an earlier ROW. "The state of
past errors and corrections" is therefore complete within an episode and empty across episodes. The
machinery exists and is unarmed here: `rails/candidate_experience_memory.py` ("source-attested
provisional corrective memory"), armed only in the Stage-3 system-memory family.

**Cost:** one retained earlier row is one Reviewer verdict plus one Solver draft, about **321 tokens
per retained row** at today's sizes — 3.3 % of a Reviewer prompt each, so a memory of three earlier
rows costs about a tenth of the prompt.

### G5. The affordance the Reviewer's own instruction presumes is gone

`configs/probes/slurp_native_role_reviewer_v1.txt` opens by ordering the Reviewer to call a
task-contract tool "exactly once through its native function schema" and to "use only its returned
source-bound result". That toolkit was **RETIRED** — item E25, harness-admission switch class
`phase_tools`, after the B1-notool read (`docs/results/2026-09-20-slurp-b1-notool-verdict.md`,
decisions 55 and 56) — and this audit confirms **0 tool schemas in all 2,590 contacts of the lock
arm**. So **52 of the Reviewer's 82 instruction tokens (63 %) order an action it cannot perform**,
and the grounding it is told to review against does not exist. The same day's system-summary
diagnostic records the downstream consequence from the other end: summaries "treat a Reviewer's
textual tool-result claims as actual tool execution" while "the complete actor tool event list is
empty" (`docs/results/2026-09-26-system-summary001-fidelity-and-feedback-diagnostic.md`).

**Cost: negative.** Deleting the two stale sentences frees 52 tokens per Reviewer contact and removes
a standing instruction to fabricate. What is genuinely absent is the grounding affordance those
sentences presume — a way for the judge to check a draft against something other than the same
40 bodies the Solver already had.

## Verdict

The owner's reading is confirmed and the direction it closes was the right one to close. The Reviewer
and the Planner receive the episode's entire monotone state chain — every earlier role response
verbatim, with **0 earlier steps dropped at any contact of any arm**, on all 32 revised rows of the
v2.0 lock arm — plus the revision counters and the routes still open. The state of past errors and
corrections IS in their prompt: the Reviewer sees its own earlier objection beside both drafts, the
Planner sees its own earlier route beside both verdicts. A per-node supply scope that narrowed this
would have removed exactly the thing these two nodes exist to read.

What the measurement adds is proportion, and it points the opposite way from the dedup note. The
global picture is 297.4 tokens of the Reviewer's 9,791.9-token prompt (3.0 %) and 514.7 of the
Planner's 9,940.4 (5.2 %), rising to 7.2 % and 9.5 % once a revision has actually happened, while
re-rendered knowledge bodies take 67–72 % and the constant task contract 22 %. The two nodes that
most need global state spend the least of their prompt on it, and every one of the five named gaps is
on that side of the ledger: a judge that cannot cite the evidence it is looking at (G1, already
addressable at 11.6 tokens an id because the labels are on the wire), a verdict with no typed
evidence link (G2, between −103 and +59 tokens), attempts with no ordinal and no stated outcome (G3,
a few tokens for the ordinal the payload already seals), no memory past the row (G4, 321 tokens per
retained row), and an instruction ordering a tool retired six days ago (G5, −52 tokens). None of
these is blocked by budget. They are blocked by nobody having asked the nodes to say what they used.
