# Required Planner control-format correction

Status: prepared offline, not activated or GPU-verified. Preserve the flown
bundle, its role files, requests, outputs, FIT and score-job specification.

The active seed uses native_episode.planner_output_format = exact-text. Its
Planner instruction says to use the registered format but never specifies the
bytes. The engineering metadata shows JSON action objects, which the existing
strict parser correctly rejects. Keep the parser and answering authority fixed.

For a newly registered successor seed, append this explicit English protocol
instruction to the Planner role text, and bind a fresh content-addressed policy:

> When making a knowledge request, use only the supplied native tool-call
> interface. ACCEPT and REVISE are routing actions, not tools. When you finish
> planning, your final response must be exactly one bare token: ACCEPT or
> REVISE. Do not emit a JSON object, arguments, Markdown, explanation, punctuation
> or extra text in that final response. After receiving a tool result, follow
> the same exact final-response contract. The Solver alone produces the task
> answer.

This fixes an existing interface contract. It does not supply task answers,
labels, sample-specific hints, a new semantic policy or a relaxed parser. Apply
it equally to the initial seed, its A/A and both later search branches before
any scientific generation or proposer contact. Preserve the old seed and link
the prospective new seed in an explicit protocol successor; do not patch frozen
role files in place. Include the correction's provenance in preparation records.

Before any successor contact: register its own identities and contact cap,
compile the new bundle with the existing shared compiler, verify that only the
Planner role text changed, test both ordinary and post-tool final routing, pin
its own supplies, and run the exact runtime readiness check. Complete the
maximum-legal tool-return/handoff/revision FIT separately. Do not interpret
these four engineering rows as capability, benefit, harm or learning feedback.
