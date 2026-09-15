# On-demand target knowledge in the shared native agent framework

Date: 2026-09-15. Status: CPU-verified implementation; no experiment enabled and no model contact authorized. The owner GPU hold remains active.

## Purpose and interpretation

Expose saea-tool-knowledge-target-lookup-v1 to a configured Reviewer or Planner. The frozen core names a knowledge store, competing task targets and a concrete unresolved distinction. The shared tool returns bounded values from the already loaded, source-pinned store. The calling role receives the actual tool return; a later Solver revision consumes the same evidence and retains sole answer authority.

This extends the existing native role graph, tool registry, knowledge-store binding, shared candidate round-robin selector, PhaseSupply, QueryState and OpenJiuwen tool loop. It introduces no new controller, private experiment runner, model service or answering model. The opt-in capability table is [task-toolkits-v4-target-knowledge-v1.json](../../configs/toolkit/task-toolkits-v4-target-knowledge-v1.json); historical tables and the default remain unchanged. Catalog membership alone executes nothing.

The completed Audio2Tool attribution gives separate reasons to work on candidate inclusion and downstream resolution. Primary target inclusion is 72.05%; all 8,883 unique candidate observations map to parameter values. Exact target lookup can help inspect a known competing action or its parameter meaning. It cannot discover an unknown missing candidate by itself, establish that the stored content is sufficient, or prove a task improvement.

## Runtime contract

The action has exactly four arguments:

    {
      "store_id": "tool-activation",
      "view": "text",
      "candidate_ids": ["candidate-alpha", "candidate-beta"],
      "distinction": "Resolve whether the operation affects one item or the complete collection."
    }

The candidate names above are illustrative. Supply actual legal target IDs from the bound registry at runtime. The distinction records the model's reason for lookup; the current deterministic selector matches explicit ValueBundle.task_target, not semantic similarity to this free-text reason.

Configure each admitted role under phase_tools with mode=native-tools, exact source_authority_role, the tool allowlist, knowledge_views=[text], named knowledge_store_ids, and explicit candidate_limit, knowledge_values_per_candidate and knowledge_value_limit in 1..32. The same tool name must expose identical schema fields across roles. Select per-role iteration/contact limits through the existing native_episode and policy configuration. Only Reviewer and Planner may hold analytical tool authority; Perception and Solver consume evidence.

Preserve the two-store distinction. Use activation knowledge for conditions and near-neighbor exclusions. Use parameter-meaning knowledge for field semantics, units, ranges, references, defaults and extraction requirements. Knowledge does not establish that an action or argument was spoken.

Selection follows ordered unique targets, sorts each target's value IDs and reuses the shared bounded round-robin policy. Complete the capped selection before removing already visible values; do not refill the freed positions. Return explicit missing-target entries. A wholly repeated lookup returns no new supply. An absent mapping returns no fabricated value. Keep the full selection and the newly supplied subset separate in the receipt.

Pin every result to the store release, local snapshot, composite identity, source query state and originating native tool call. Preserve the request reason, per-target mapping/cap exclusions and deterministic selection hash internally. Return only necessary store identity, selected values, missing targets and disposition to the model. Preserve the existing evidence renderer and sealed tool-history equality checks. Repeated history references do not duplicate already returned text.

## Integration correction and verification

Native role programs may list Planner last; the Audio2Tool program instead lists Solver last. The old phase-tool bridge excluded the final listed phase when loading tools and building schemas, then unconditionally indexed a sequential successor during dispatch. Native tool calls return inside the calling role's node loop. The shared bridge now includes native roles and handles a last-role call without indexing a nonexistent successor. Legacy sequential programs retain their previous nonfinal-phase and successor behavior.

The real OpenJiuwen workflow test covers Reviewer and Planner independently, each querying activation and parameter-meaning stores across two synthetic samples. Selected values appear in the calling role's next request and in Solver's subsequent revision. The test uses the same named-store renderer wiring as the shared phase runner; the sealed-return equality check is retained. Fake transports and synthetic packets create no model or GPU contact.

The 460-test focused regression covers ordinary phase tools, native role routing, actual workflow execution, authority, history, local tool scheduling, FlightRuntime dispatch, named stores, candidate supply and catalog checks. The complete receipt is coordination/native-target-knowledge-tool-v1/verification-v1.json under SPEECHRL_DATA_DIR. Its source hashes identify the tested implementation. This is engineering evidence, not a scientific comparison or observed task gain.

## Prospective adoption and remaining work

Keep the already registered SLURP broad/factored TRAIN-A flight first after explicit GPU resume, using its frozen worktree. It currently exposes the task-contract Reviewer tool only; do not silently enable this new capability or the separately prepared refresh/Whisper configuration.

A future Audio2Tool version may reuse the frozen tool-activation and parameter-meaning store releases if their bytes remain unchanged. It needs distinct baseline, policy, experiment and attempt identities, appropriate prompts, newly bound prepared supply and an actual fit receipt. The inherited Planner prompt prohibits tools and must be replaced in the new version; the inherited one-iteration Planner cannot perform a tool call and a final routing report. With the inherited one revision, Reviewer limit 3 and Planner limit 2, the graph ceiling would be 13 contacts per sample. This arithmetic is a design constraint, not a new approved generation budget.

Preserve candidate formation, ordered action identity and final resolution as separate analysis surfaces. A broader legal overview and candidate reconsideration address inclusion; targeted values and acoustic tools address the evidence needed for selection or arguments. Use observable ambiguity or conflicting speech support as runtime triggers. Keep evaluation gold and error labels outside runtime knowledge and memory.

No successor fit, tokenizer call, generation, encoding or service restart has occurred. A useful replicated task-agent system remains necessary before defining trajectory-sampling and training-free RL updates. This shared tool expands the controllable action workspace; it is not an RL algorithm.


A subsequent actual Audio2Tool integration also removed the mandatory automatic-supply requirement for explicitly target-tool-owned stores and added source-bound analysis of refreshed candidates. See [the CPU implementation and value review](2026-09-15-a2t-candidate-recovery-cpu-v1.md). This extends dormant on-demand routing; it does not claim the historical Audio2Tool program suffered from a last-listed Planner.
