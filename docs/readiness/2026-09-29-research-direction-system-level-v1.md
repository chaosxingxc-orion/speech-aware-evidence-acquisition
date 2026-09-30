# Research direction: system-level optimisation with model-initiated tools (v1)

Date 2026-09-29. Readiness note, docs only; it grants no contact and admits nothing.

## Owner directives (verbatim, with English glosses)

The two quotes below are owner-record text kept verbatim, as the decision registry keeps owner rulings; the English
gloss beside each is the working text.

1. 「我们调整下课题方向，0906的时候还是聚焦在如何用好主模型，现在调整为如何搭建系统并进行系统级优化」
   -- "We are adjusting the research direction: on 09-06 the focus was still on how to make good use of the main
   model; it now becomes how to build the system and optimise it at system level."
2. 「工具应该是模型主动发起调用，而不是系统默认调用，否则就会陷入到自证陷阱，为什么不是ASR+LLM的组合来完成任务，而得用omni agent system！」
   -- "Tools should be invoked by the model on its own initiative, not called by the system by default; otherwise we
   fall into the self-proof trap -- why would the task not be done by an ASR + LLM combination, and why would it need
   an omni agent system!"

## What changes

- **Tools are system components.** A pinned, logged tool (for example the pinned Whisper ASR of E5) is a legitimate
  part of the system under test; the 2026-09-06 "no transcript tokens anywhere" direction is superseded to that extent
  (decision 201's scope).
- **The object optimised is the model's control decisions through the control plane** -- what to supply, what to
  present, when to consult a tool -- read with the sealed-credit inner loop and same-flight columns, not the core's raw
  capability.
- **Tool use is model-initiated.** The system OFFERS a tool at one node; the model decides to call it; the decision is
  receipted and read (call rate, decision precision/recall against an offline oracle, conversion). A system-applied
  tool step is not a runtime candidate. Deterministic form normalisers (delivered-row normaliser, scope rule) remain
  the one class of system-default action because they change form, not evidence
  (`docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md` section 2d).

## What does not change

- The immutable research boundary of the study `CLAUDE.md`: human speech and its linguistic content only; no
  FSD50K/AudioSet/ESC-50; the frozen Qwen3-Omni core reached only across an API-shaped boundary with zero-parameter
  training, no task-trained model and no second answering LLM; final answer authority stays with the frozen core; gold
  labels, reference transcripts, test annotations and future turns never enter runtime; discovery and confirmatory stay
  isolated; OBS/ORG/SUPPLY/USE traced separately and every tool action versioned and hashable; a frozen tool is
  allowed only when pinned and logged.
- Decision 187: the GPU stays on SLURP until the SLURP lock.
- Decision 196: after stable SLURP gains, the module transfers to Audio2Tool, Earnings-21 and Earnings-22 through its
  carrier profile, each component re-read on each carrier.

## Decision rows this maps to

| row | subject | effect of this note |
| --- | --- | --- |
| 201 | E5 frozen tool-level ASR route (proposed) | its runtime form is the model-initiated offer; E5-0/E5-1 are oracles; E5-2a withdrawn (E5 spec addendum) |
| 205 | research direction: build the system and optimise at system level | this note is its readiness statement |
| 206 | tools are model-initiated, never system-default | module design section 2d; first offer `tool-offer:asr-slot-value` |

Rows 205 and 206 are numbered as the coordinator assigns them; they are not yet in the registry file on this branch.
