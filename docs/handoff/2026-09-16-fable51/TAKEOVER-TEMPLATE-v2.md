# Fable5.1 takeover reply template v2

This is an unfilled template, not a takeover receipt or execution authorization.
Create a new TAKEOVER-FABLE51-<UTC>.md file alongside it. Do not overwrite historical replies.

- Recorded at UTC: <actual timestamp>
- Responding coordinator: <identity>
- Read handoff: HANDOFF-v4.md
- Read package manifest: HANDOFF-MANIFEST-v4.json, SHA-256 <verified hash>
- Observed canonical branch/commit: <actual values>
- Current coordination generation: <actual value>
- Candidate proof state/source: <verified values>
- Typed-context closed-flight state/source: <verified values>
- Resident service identity and actual lease owner: <verified metadata; never paste tokens>
- Another coordinator/worker active: <observation and evidence>
- Frozen failed sources preserved: <checks>
- Held direct quality and Fold B remain unread: <confirmation of own actions>
- Selected next action: <normally resolve the already pending fresh proof admission; CPU repair/preparation are done>
- Ownership/coordination contract reconciliation: <completed change or still pending>
- New model-contact admission: <none, or exact independently admitted plan>
- Questions requiring owner input: <specific remaining uncertainty, if any>

Separate what you observed from what you assume. Do not copy old PIDs as evidence of current
liveness. CPU review can proceed without pretending a GPU lease has transferred.
The existing checker pins Codex in its legacy mode; reconcile takeover explicitly rather
than fabricating RESPONSE-001.md or bypassing per-flight gates.
