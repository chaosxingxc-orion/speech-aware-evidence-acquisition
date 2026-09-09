# Owner decision: small output-budget validation

Decision ID: OWNER-BUDGET-PROBE-004

The owner asked whether chain-of-thought reasoning would improve results and whether a64-token completion ceiling is too small for agentic tasks. When offered unchanged KC-S1b replication, an output-cap audit and a separate capacity comparison before reasoning, the owner requested small-scale validation.

Operational interpretation communicated to the owner: first audit historical metadata, then compare the same four selected SLURP inputs under64 and256 completion-token ceilings. Keep the frozen Instruct weights, service, prompt, schema examples and input packets fixed. Use separate configurations and the shared controller/runtime. Admit at most four generation calls per arm, with separately registered real request-fit contacts. Do not infer effectiveness from this engineering sample or automatically launch a full budget sweep. Preserve the original KC-S1b same-profile repeat.

Keep reasoning as a later separately designed factor. The current model is the locked Qwen3-Omni-30B-A3B-Instruct GGUF. The official Qwen model card distinguishes Instruct and Thinking releases; a template that accepts thinking tags is not evidence that the resident service exposes a verified native thinking switch. Switching weights would change the frozen core and is outside this decision.

Official source: https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Instruct

E21 registered configurations use1024 completion tokens;64 is not a universal system-wide limit. Later live agentic stages need explicit per-stage budgets and complete-system cost accounting.
