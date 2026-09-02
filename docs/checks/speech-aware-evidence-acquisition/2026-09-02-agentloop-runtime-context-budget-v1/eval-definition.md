# Evaluation definition — AgentLoop runtime context budget v1

## Purpose and scope

Define the fail-closed context rail required before any future multi-contact speech AgentLoop
flight. This is a `model-free-check`: it authorizes no model, tokenizer, scorer, retriever, network,
gold, reference, or test contact. It does not alter the separately registered one-contact
executable-ground qualification.

The receipt-pinned decoder GGUF declares 65,536 context tokens. The current server allocates the
same 65,536 total tokens across two request slots, so the enforceable per-contact slot width is
32,768 tokens. Never treat the server-wide allocation as a per-contact allowance.

## Runtime accounting contract

Before every future AgentLoop model contact, materialize the exact final payload after the proposed
state transition and measure these components with the receipt-bound chat template and tokenizer:

1. rendered text tokens for the complete task contract, all currently visible facet/value text,
   selected Agent-state text, and the current control instruction;
2. the exact token counts from every referenced speech-feature packet;
3. the registered two-token special-token reserve; and
4. the contact's registered completion-token ceiling.

The required window is the sum of all four components. The admission relation is:

`required_window_tokens + 8192 <= 32768`.

The 8,192-token reserve is an operational headroom floor, not output capacity and not evidence that
the model can use a tightly packed window. A zero or negative component, missing packet count,
template/hash drift, tokenizer failure, unrecognized content part, arithmetic overflow, or
non-integer count refuses admission.

## Bounded compaction contract

If the exact proposed payload does not clear the headroom floor, return `COMPACT_REQUIRED` without
contacting the model. The controller may make at most two deterministic, traced compaction passes.
Each pass must name exactly which Agent-state, facet, or value identifiers it drops, rebuild the
complete payload, and remeasure it. It must never drop or shorten the task contract, original query
speech packet, output schema, current control instruction, or registered completion ceiling.

If the second compaction pass still does not clear the floor, return `REFUSE`. Never ask the server
to truncate, never silently reduce `max_tokens`, and never turn a refused contact into a retry.
Previously generated raw responses are not retained by the current AgentLoop renderer; only the
selected structured Agent states and visible knowledge can enter this compaction surface.

## Capability evals

1. Distinguish the 65,536-token GGUF declaration, the 65,536-token server-wide allocation, and the
   32,768-token per-slot limit.
2. Admit the exact ground envelope requiring 15,090 tokens and report a 17,678-token physical
   margin plus a 9,486-token margin above the operational reserve.
3. Admit a request exactly at 24,576 required tokens and return `COMPACT_REQUIRED` at 24,577.
4. Return `REFUSE` after two failed deterministic compaction passes.
5. Permit a smaller successor payload after a prior larger step; loop step alone must not determine
   admission.
6. Refuse missing, negative, Boolean, non-integral, or inconsistent component counts.
7. Produce a hashable receipt containing the exact breakdown, payload hash, decision, physical
   margin, operational margin, compaction pass, and dropped identifiers.

## Regression evals

1. The registered one-contact ground qualification remains unchanged and carries zero tokenizer
   contacts.
2. Existing AgentLoop payload ordering remains unchanged.
3. No raw prior response text is introduced into model context.
4. Network jitter, server retry behavior, gold, references, and test annotations remain outside the
   engineering gate.

## Implementation and integration gates

- Write unit tests before the pure rail implementation.
- Reach at least 80% statement and branch coverage for the new module.
- Keep the module model-free and transport-independent.
- Do not authorize a multi-contact flight until a later integration binds the pure rail to the
  receipt-pinned exact tokenizer immediately before every model contact and traces every decision.
- A pure-module pass is necessary but not sufficient evidence that runtime integration is complete.
