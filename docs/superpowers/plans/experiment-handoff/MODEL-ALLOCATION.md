# Cloud model allocation for the continuation

Owner direction, recorded 2026-09-09: balance efficiency and quality. Use different
ChatGPT/OpenAI cloud models for bounded coding and reading work. Keep task
planning, decisions, critical review and reflection with the main agent.

Use the cloud model selection exposed by the current Codex subagent channel.
Do not deploy a local assistant model. This routing does not create an independent
API client or amend the study's zero paid-API-spend rule.

## Assignment rules

- Keep scientific planning, hypothesis selection, protocol interpretation, gate
  decisions, result interpretation, acceptance review, merges, and retrospective
  reflection with the main agent.
- Assign a bounded implementation or test task to GPT-5.6 Luna with medium
  reasoning when requirements and acceptance cases are explicit.
- Assign source extraction, artifact inventories, and factual comparisons to
  GPT-5.6 Luna with low reasoning. Require exact paths, source hashes, and
  unresolved-field markers. Treat the report as evidence for main-agent review.
- Escalate a subtask to the main agent when interfaces or scientific semantics
  are unclear. Do not spend repeated small-model attempts on an unresolved design.
- Supply only the required English context and named files. Avoid full-history
  forks when a concise task contract suffices.
- Require a reviewed patch and appropriate tests for code, and addressable sources
  for reading. Do not interpret a subagent's confidence as verification.
- Preserve useful completed commits before changing assignments. Do not redo
  validated work solely to switch model tiers.
- Keep all repository execution in WSL Ubuntu-24.04.
- Keep the research answering path unchanged: only the frozen Qwen3-Omni core
  answers experimental tasks. Engineering assistants do not supply runtime answers,
  judge study outputs, or become an additional experimental model.

## Current bounded assignments

| Task | Cloud model | Deliverable | Main-agent acceptance |
|---|---|---|---|
| KC-S1b replica and fit configuration | GPT-5.6 Luna, medium | Held configuration fragments and source bindings | Verify identical scientific request semantics; register and admit separately |
| Engineering AST detector | GPT-5.6 Luna, medium | Alias-aware transitive detector and synthetic tests | Review detector scope and historical compatibility before enabling enforcement |
| E21 predecessor receipt inventory | GPT-5.6 Luna, low | Exact configuration, artifact and metadata pointers | Verify sources and design DR/LOOP migration personally |

Model availability is established by the active tool's advertised model choices;
no unverified price or quota saving is claimed. Review the total time and rework,
not just the selected tier.
