# Bounded review-driven phase decisions

Date: 2026-09-11 UTC. Scope: shared implementation and model-free verification.
This work does not register a scientific flight, change an active flight, or
establish an E21 effectiveness result.

## Behavior and configuration

The shared FlightRuntime now resolves phase_planner from the composed
configuration. It binds the declared Reviewer to EvidenceAgentController's
existing stop_policy through run_continuous_program and the existing
OpenJiuwen executor. There is no new controller subclass or experiment runner.

The registered continue-on-flag-v1 rule continues to the next declared phase
when a selected judge emits a flag at or above minimum_severity. Otherwise it
stops and retains the current frozen-core answer. The Planner returns only a
boolean decision. The Reviewer returns typed criticism. Only a core contact
can produce the next answer.

Use the new optional two-phase program phase-reviewed-repair-v1. It declares
draft and revise with a ceiling of two contacts. Existing phase-draft-revise-v1
retains its always-run-full-program identity. A minimal configuration addition is:

```json
{
  "policy": "phase-reviewed-repair-v1",
  "phase_review": {
    "draft": {
      "judges": ["earnings-numeric-format-flag-v1"]
    }
  },
  "phase_planner": {
    "draft": {
      "planner_policy_id": "continue-on-flag-v1",
      "judges": ["earnings-numeric-format-flag-v1"],
      "minimum_severity": "warn"
    }
  }
}
```

This is a configuration example, not an executable experiment registration.
Combine it with the normal model, dataset, phase_material, knowledge snapshot,
validated packet, execution plan, exposure and fit bindings. Do not change a
running or hash-pinned experiment to use it.

Missing, null or empty phase_planner preserves the historical execution and
receipt shape. Nonempty configuration requires an optional early-exit program
and a reviewed, non-final phase. Unknown rules, duplicate/unreviewed judges,
invalid severity and unknown keys refuse before preparation or model contact.
Nested planner_policy_id values are checked against core.base.PHASE_PLANNERS
by the existing engineering-base check; its exception list is unchanged.

## Binding, tracing and cost

The Planner reads the review verdict and response hash atomically. It verifies
the sample, phase, producer program, query-state hash, raw response hash and
declared judge configuration against the just-sealed runtime state. Parallel
sample decisions are independent. Repeating the same decision is idempotent;
a conflicting source cannot overwrite it.

USE records carry the rule, selected judges, severity, source-response hash,
verdict hash, decision and flag count. They contain no replacement answer.
Reviewer records remain on REVIEW. A per-phase runner emits only that phase's
review records, fixing duplicate emission from a shared multi-phase collector.
Completed reviews and Planner decisions are preserved when a later stage fails.

Receipts separate the per-sample contact ceiling from realized trajectory
counts. The public wire check verifies the actual per-sample request counts
and full output roster, including early exits. It no longer assumes that every
configured sample must spend its full ceiling.

For whole-roster phase barriers, the live fit gate derives the active next-phase
roster from this same Planner collector. Missing prior decisions or a changed
roster refuse before tokenizer calls. Each actual request still uses the common
builder and fit implementation. The registered full-program tokenizer cap
remains the ceiling; skipped trajectories spend no successor tokenizer contacts.
A fit artifact additionally binds its active sample IDs.

## Verification

All implementation and checks ran in WSL Ubuntu-24.04 with the existing Python
3.12 environment and explicit checkout PYTHONPATH. No environment installation,
external service, paid API, neural judge, encoding or model generation was used.

Tests were written and observed failing before the corresponding implementation.
The verification uses real shared Reviewer, controller, request builder and
OpenJiuwen execution with synthetic media and in-process transport.

- Mixed two-sample execution spends three requests: the flagged draft continues
  and the clean draft stops. The successor reads the actual sealed draft.
- Both continuous and whole-roster execution preserve that behavior. Prepared
  requests and sent requests have the same common boundary identity.
- Public FlightRuntime wire checks spend four synthetic requests at warn,
  two at block, and four with the Planner disabled. All retain zero real model
  contacts; empty configuration keeps the old receipt keys.
- Live fitting checks two draft requests and one selected successor: 11 actual
  tokenizer endpoints under the unchanged ceiling of 14, zero generation.
- Stale/cross-sample bindings, missing reviews, conflicting decisions, malformed
  configuration, unsupported OBS/window paths and nested unregistered rules
  refuse. Later-stage failure retains completed review evidence.
- Targeted tests, the engineering-base check and source lint are recorded in
  STATUS-027. The new Planner module measured 93 percent branch-aware coverage.

## Scientific limits and next dependency

This proves bounded continuation to an existing phase. It does not yet implement
judge-selected new audio cuts, an E21 multi-phase window controller, diarization
memory, dynamic summaries, or a live Reviewer-to-Planner-to-new-observation
system. The direct-only window bridge explicitly refuses phase_planner.

The active E21 direct-to-KC-E1f pair remains frozen and uses its existing
precomputed exact windows. It must complete before its full-system quality and
cost can be assessed. Later observation work must use the same shared seams,
qualify its selected-cut feature preparation and actual fit, and receive its
own bounded registration before any contact.

Under OWNER-DATASET-TASKS-010, any later context or summary method is judged on
the existing dataset task. A new summary/minutes evaluator is not an acceptance
requirement. No scientific admission or new GPU work follows from these tests.
