# E21 DR shared two-generation successor

Status: held. This configuration is a successor; preserve the original three-generation configuration and sealed artifacts.

Two generation parents consume the sealed short-unit draft and sealed long-window self-draft respectively. Each covers 1,593 windows and 44 discovery calls with raw audio and a 1,024-token output cap. Each parent has predeclared constrained and free deterministic deliveries, for four correlated results and only two groups of generation contacts.

Two explicit OJW baseline fragments preserve the original prompts, postprocessors and all other request fields. Their differences from the legacy baselines are the registered `obs-repair-loop-ojw` policy, the workflow timeout, and explicit `obs_controller_program=phase-direct-only-v1`. The latter routes each window through EvidenceAgentController; selecting an OJW policy alone does not establish that binding. This remains a single-phase compatibility bridge. Shared composition resolves successfully without a runtime policy substitution.

Each generation ceiling is 1,750 calls, 150,000 speech seconds and 1.2 GPU-hours; the two-parent family ceiling is twice that. A full fit uses one GET /props and 1,593 POST /v1/chat/completions/input_tokens contacts, or 1,594 per parent. These tokenizer contacts require separate registration. They are not model-free preparation.

The provisional geometry is six slots at 6,144 tokens each, with a whole-group fallback to four slots at 9,216 tokens each. Retain the required capacity margin and output cap when selecting the geometry. No service or generation is admitted by this note.

Source receipt hashes and OJW baseline hashes are verified in the successor's source_pins. The short-unit receipt is `docs/receipts/e21-unit-draft-obs-e1-speaker-turn-units-v1.json`; the self-draft receipt is `docs/receipts/e21-predecessor-full44-direct-baseline-v2.json`. Use those files as the source of truth.

All four fit/generation cells remain held with pending attempt IDs and no preparation pins. Before advancing, complete current shared-executor live bridge evidence, actual request preparation and full-window fit, exposure registration, source verification and root admission. The historical KC-E1f constrained replay has exact parity for all 1,593 windows and 44 calls; it does not establish new DR performance or current live execution.
