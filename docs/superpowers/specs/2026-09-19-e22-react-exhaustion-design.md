# Item E22 (the ReAct-exhaustion disposition, not the Earnings-22 carrier): design

Date: 2026-09-19. Branch `fable/e22`, off `master` `01c73225`. Zero model, tokenizer, encoder,
ASR, scorer and server contacts; nothing under `SPEECHRL_DATA_DIR/runs` was written and the
resident llama-server was not touched.

Written in the form of E13 (`scripts/checks/finite_completion_policy_check.py`'s own docstring) and
E20 (section 20 of `docs/superpowers/specs/2026-09-17-node-context-policy-design.md`): the failure,
the key, the disposition, the receipts, the gate, the tests, and what this does not authorise.

---

## 1. The failure

Cell B8b-anchor — the Reviewer slot-audit attachment on the sealed anchor — run
`SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1`, attempt
`attempt-slurp-native-reviewer-audit-anchor-train-fold-a-generation-v1`, flight worktree
`/home/chao/saea-worktrees/fable-b8ba-flight` at `c905ddf0`, campaign log
`/home/chao/b8ba-campaign-20260919T205944Z.log` (55,674 lines).

**What the log says**, re-verified for this note:

| fact | evidence |
| --- | --- |
| 2,016 model contacts spent | 2,016 `[LLM] >>> request` lines; 2,016 `MODEL_REQUEST` records in the sealed trace |
| about 400 of 1,080 rows | 410 Reviewer visits opened (`ReAct iteration 1/3`) |
| 5 `workflow_execute_error` events | lines 20887, 22523, 29313, 54169, 55275 |
| 3 of them are the E13 class | the paired `graph_vertex_ability_error` at lines 20880, 22516, 29306, each `"exception": "metered completion is non-authoritative because finish_reason is 'length'"`, at nodes `reviewer_1_role`, `reviewer_0_role`, `reviewer_1_role` |
| those 3 rows were RETAINED | the flight ran on for another 45 minutes, and the sealed trace carries exactly 3 `finite_completion` terminal dispositions (USE records 5108, 5536, 6997) — the armed `finite_completion_policy` did its job |
| 2 of them are the NEW class | lines 54162 and 55268, both `"exception": "review node did not return an answer"`, both at node **`reviewer_1_state`** (the `_ApplyRole` of the revision-1 Reviewer), at 15:13:24 and 15:15:46 local |
| the Reviewer's loop spent every iteration on tool calls | iteration tally over the whole log: 410 at `1/3`, 409 at `2/3`, **2** at `3/3`. The second exhaustion's window (lines 55250–55262) is cleanly attributable: `2/3` → `content_len=0, tool_call_count=1` → `Executing tool` → `3/3` → `content_len=0, tool_call_count=1` → `Executing tool` → error |
| every call was the same call | 413 of 413 `Executing tool` lines are `Executing tool: saea-tool-task-contract-v1 with args: {}` — one tool, one empty argument object, no variation anywhere in the arm |
| the comparator never reaches 3/3 | the B1r arm log `/home/chao/b1r-campaign-20260919T164911Z.log`: 1,092 visits at `1/3`, 1,088 at `2/3`, **0** at `3/3` |

The log interleaves concurrent rows (one line per event, no row id), so line adjacency is not
attribution; the per-visit facts above are taken from the tallies and from the two error events'
own `node_id`, not from neighbouring lines.

**Why it died.** `openjiuwen.core.single_agent.agents.react_agent`, at the `else:` of its iteration
`for`, returns its own literal when the budget is spent:

```python
result = {"output": "Max iterations reached without completion", "result_type": "error"}
```

`reproduction.ojw.native_roles.NativeRoleNode._run` passes that through unchanged, and
`reproduction.ojw.native_episode._ApplyRole.invoke` refused it, because the only thing it has ever
accepted is `result_type == "answer"`:

```
NativeEpisodeError: review node did not return an answer
```

Nothing was broken. The Reviewer asked to read the task contract three times, the framework ran out
of turns, and a graph that has no word for "the reviewer found nothing" called it a flight failure.

## 2. How the runtime treated the FIRST exhausted row

Not in `core/flight/runtime.py` at all. The tolerance is in
**`src/speech_aware_evidence_acquisition/reproduction/ojw/runner.py`**, inside
`execute_speech_agent_workflows._run_all`:

* **`admission_worker`**, lines 620–631: `await one(state)` is wrapped in
  `except BaseException as error:` (line 628), which records `failures[index] = error` (line 630)
  and **returns** — that one worker stops, and the exception is not re-raised there.
* **`next_admission`**, lines 611–618: `if failures or next_index >= len(ordered_states): return
  None`, so once any row has failed **no new row is admitted**. Workers already inside a row run to
  the end of it.
* **line 638**, `await asyncio.gather(*admission_workers)`: the flight drains.
* **line 648**, `raise failures[min(failures)]`: the lowest split-index failure is raised and the
  campaign dies.

So the first exhausted row was **neither dropped, nor marked partial, nor retried**. Its
`_ContactAgentState.final_outcome` stayed `None`, its exception went into `failures`, admission
stopped instantly, and the flight drained until the last in-flight worker finished — which is why
the log shows 29 further `1/1` role iterations and 16 further Reviewer visits after 15:13:24, and
why the second exhaustion at 15:15:46 is the last thing in it. Had `gather` not raised,
`rails/runner.py` line 3885 would have raised
`RailsRunnerError("native graph ended without an accepted Solver outcome")` for the same rows.

This is a drain-and-die tolerance, not a row tolerance. There is no place in the current runtime
where a row whose graph raised is retained.

## 3. The key

`native_episode.react_exhaustion_policy` — the **twelfth** member of
`rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS`, and the **third failure-mode** key after E13's
`finite_completion_policy` and E20's `context_fit_policy`.

| value | behaviour |
| --- | --- |
| `"raise"` (default) | exactly today's: `_ApplyRole` refuses the non-answer and the flight dies at that row |
| `"continue-without-answer"` | the exhausted visit ends with **no finding**; the row continues and delivers |

**Null arm**, exactly E13's and E20's shape: the key's ABSENCE *or* the literal `"raise"`, which
`rails.native_episode_config.load_native_episode_config` reads identically
(`rails.config_tables.is_episode_null_arm`). Any other value is refused by the parser
(`"native episode react exhaustion policy is invalid"`) and by
`reproduction.ojw.native_episode.NativeEpisodeSpec.__post_init__`
(`"react_exhaustion_policy is invalid"`) before any contact is made.

**Which stages may take it.** `REACT_EXHAUSTION_STAGES` is `{"review"}` and nothing else. A Solver
visit owes a **draft** (an empty one is not delivery-eligible and the row would have nothing to
deliver) and a Planner visit owes a **route** (with no action the conditional graph has no branch
to take), so for those two an exhausted visit keeps its pre-E22 raise. Perception carries no tool
authority at all — `native_roles._TOOL_FREE_ROLE_KINDS` — and cannot reach this class. This is
narrower than "any tool role", deliberately: the repair is for the failure that happened, and
inventing a behaviour for a node whose output is load-bearing would be a second factor.

**Recognising the class.** Four conditions, all required
(`native_roles.NativeRoleNode._react_exhaustion`, line 1042): the role has an advertised ability, the
result is `result_type == "error"` with `actor_output == REACT_EXHAUSTION_OUTPUT` (the framework
literal, pinned as a constant at `native_roles.py:66`), at least one tool call was recorded, and the
model contacts of the visit equal the role's declared `max_iterations`. `result_type == "error"` is
also what the framework returns for `"No query provided"` and for `str(exception)`; those are not
this class and still raise.

## 4. The disposition

Under the armed policy, `_ApplyRole._retained_exhaustion` (`native_episode.py:530`):

1. **Custody is kept.** The visit is appended to `role_visits` exactly as an answering visit is,
   with its full `execution_receipt` — its contacts were made, metered and traced, and pretending
   otherwise would lose them.
2. **The finding is empty.** `state["review"]` becomes `""` — the state the graph would hold if the
   Reviewer had reviewed and found nothing. It is **not** the framework's sentence: a test asserts
   that `"Max iterations reached without completion"` never appears in any rendered request of the
   row.
3. **The Planner routes normally.** No branch, no action and no delivery rule changes.
4. **Nothing is retried.** No extra contact is spent, and no prompt byte of any other contact moves.
5. A `react_exhaustion` record is appended to the episode state, modelled on E8c's
   `planner_action_illegal` mark.

What one exhausted visit records — tool ids and digests, never an argument value and never an
observation's text:

```json
{
  "schema": "saea-native-react-exhaustion-v1",
  "count": 1,
  "visits": [{
    "role_id": "reviewer",
    "stage": "review",
    "role_visit_index": 2,
    "revision_count": 0,
    "iterations_used": 3,
    "max_iterations": 3,
    "identical_calls": true,
    "calls": [{"tool_id": "saea-tool-task-contract-v1", "arguments_sha256": "<64 hex>"}, "..."],
    "last_observation_sha256": "<64 hex or null>"
  }]
}
```

`identical_calls` is "every call of this loop had the same tool id and the same arguments digest",
which is vacuously true for a single call. The per-call log is captured by the node's own
invocation-local recorder (`NativeRoleNode._record_tool_call`, line 899, a `ContextVar` built
exactly as `FrozenCoreRoleModel._receipt_contacts` is) through `_InstanceOwnedAbility` (line 763),
which already wraps every ability the node advertises. No framework rail hook was added and no
framework callback registration changed.

## 5. Receipts

**Per row.** `rails/runner.py` copies `react_exhaustion` into the sealed
`native_episode_receipt` beside `planner_action_illegal`, present only when a visit took it.
The row's `terminal_disposition` is **not** touched: the exhaustion is a VISIT-level disposition
and the row delivers through whichever kind it would have taken anyway (an ordinary `accepted`, in
the proof).

**Validation.** `rails.native_episode_receipt._validate_react_exhaustion` (line 120) shape-checks
the block and **binds every record to a real visit**: `role_visit_index` must address a
`role_visits` entry whose `stage` and `role_id` are the record's own, no index twice, the stage must
be admissible, `iterations_used == max_iterations >= 1`, every `arguments_sha256` and the optional
`last_observation_sha256` must be lowercase 64-hex, and `identical_calls` must agree with the calls
it sits beside. `NativeEpisodeDelivery` gains a `react_exhaustion` field, declared last and
defaulted, so every positional construction and every pre-E22 reader composes what it did.

**Prospective configuration.** `validate_native_episode_terminal_policy` checks the block FIRST and
for EVERY delivery kind — including `accepted`, which returns early on everything else — and
refuses it unless `react_exhaustion_policy == "continue-without-answer"`
(`"ReAct exhaustion recorded without its declared policy"`). The keyword defaults to `"raise"`, so a
reader written before E22 that never passes it still refuses an undeclared block. Both callers pass
the composed fragment's own value: `rails/runner.py` at seal time and
`core/flight/runtime.py` at the flight seal (`raw_native.get("react_exhaustion_policy", "raise")`).

**Per run.** `core.flight.runtime.FlightRuntime._episode_disposition_counts` gains
`react_exhaustion_rows` and `react_exhaustion_visits` (lines 7234, 7272, 7278) — different numbers,
because one row may exhaust more than one visit. They are **added** only when at least one row
sealed the block, exactly as E21w added its four, so an unarmed dispatch's manifest reports exactly
the four counters it reported before E22.

## 6. The gate

`scripts/checks/finite_completion_policy_check.py` keeps its name and its scope rule (ledger row
`consumed = no` AND `readiness.state` in `ready`/`held`) and now demands **both** failure-mode keys
of every live, unflown native cell:

* `finite_completion_policy == "deliver-latest-or-abstain"` (E13), and
* `react_exhaustion_policy == "continue-without-answer"` (E22).

Each key is its own finding, named by key, so a cell that arms one and not the other is told which
one is missing. Rule 2 — no committed baseline anywhere declares a third value, including the abort
default written out loud — applies to both. The result schema moves to
`saea-finite-completion-policy-check-v2` and the PASS/FAIL line names both keys.

On the tree at `01c73225` the gate **FAILS with 10 findings**, all of them the new key absent, on
8 live unflown baselines — among them both B8b-anchor plans
(`docs/readiness/2026-09-19-slurp-b8b-anchor-reviewer-audit-v1/generation-plan-v1.json` and
`generation-plan-registered-v1.json`, baseline `slurp-native-anchor-reviewer-audit-train-fold-a-v1`).
That is the point of the item. **No readiness package, ledger row or config was edited here**; the
re-registration is the coordinator's job, through `scripts/flights/repin_cell.py`.

## 7. Tests

`tests/unit/test_e22_react_exhaustion.py` (36 tests), all against the fake transport of
`test_native_episode_runner` and in-memory role nodes:

1. the key parses, defaults to `"raise"`, refuses every third value, and resolves in the closed
   12-member episode allowlist with the absence/`"raise"` null arm;
2. `_InstanceOwnedAbility` records the tool id and the exact argument and observation digests, and
   `_canonical_sha256` is order-insensitive for objects and byte-exact for strings;
3. the node recognises the framework's literal, records three identical calls and NOTHING else (no
   argument value, no observation text in the block); an answering role's result dict is byte-for-byte
   its pre-E22 self; a tool-free role can never reach the class;
4. through the ACTUAL runner, with a Reviewer that answers with a tool call on all three iterations:
   under `"raise"` the flown sentence verbatim (`NativeEpisodeError: review node did not return an
   answer`), under the armed policy a retained row that delivers the Solver's own draft, keeps all
   three Reviewer contacts in `role_visits`, seals the block, routes the Planner on `ACCEPT`, and
   spends exactly 6 contacts;
5. the framework's exhaustion literal never appears in any rendered request;
6. the receipt validator binds every record to a real visit and refuses twelve malformed shapes;
   `validate_native_episode_terminal_policy` accepts only under the declared policy;
7. the run-level counters appear only when a row sealed the block;
8. arming the key on a row whose roles all answer composes **byte-identical requests** and
   **identical receipts** on both arms;
9. the gate demands both keys, names the missing one, and refuses the abort default written out
   loud.

Two existing assertions were updated because the contract they pin changed, not because they broke:
`test_config_table_module_switches.py`'s closed-allowlist enumeration (now 12 keys) and
`test_e20_context_fit_policy.py`'s "the spec's own field is LAST" (now the last **two** fields, in
order). `test_finite_completion_policy_check.py`'s fixtures now arm both keys and vary one at a
time.

Gate and suite results are in the item's report.

## 8. What this does not authorise

* **No cell.** This item registers no experiment, opens no readiness package and writes no ledger
  row.
* **No recovery registration.** The one-experiment rule allows exactly one recovery
  re-registration of the B8b-anchor flight; making it, and re-pinning the plans the gate now
  refuses, is the coordinator's job.
* **No contact.** Zero model, tokenizer, encoder, ASR, scorer and server contacts were made here,
  and arming the key spends none: nothing is retried.
* **No second factor.** No repeated-tool-call guard, no change to the Reviewer's prompt, tools,
  `max_iterations` or routing. A cell that wants the Reviewer to stop asking the same question is a
  different cell.
* **No result.** Retaining a row whose Reviewer found nothing is not evidence that the row is as
  good as one whose Reviewer reviewed. A cell that arms the key must report
  `react_exhaustion_rows` and `react_exhaustion_visits` as diagnostics beside its primary number.
* **No change to E13, E17, E18, E20 or E21** with the key absent, proved by the byte-identity
  falsifier above.
