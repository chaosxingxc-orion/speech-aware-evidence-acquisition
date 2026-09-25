# VAR-2 revision failure and one-recovery diagnosis

At 2026-09-25 09:49:19 UTC the full VAR-2 attempt aborted after 224 model
contacts and 804.911625 repeated speech seconds. The original four-row proof
completed with 28 contacts. The full run has no sealed manifest, no official
score and no usable partial experiment result. Preserve it. Do not select
completed rows, read partial answers or treat first-visit fragments as a result.

## Named cause and evidence

The failure is at solver_1_input, entering a revision. A knowledge router may
return only values not yet visible. The runner checked that per-visit selection
against the node's cumulative acquired values. An empty increment was therefore
incorrectly compared with a nonempty accumulated history. The original
four-row proof did not exercise this route.

The root reproduced the same failure with the actual OpenJiuwen revision graph
and fake model transport. Two incremental-routing cases failed before the fix;
two repeated-selection controls passed. No real failed response was replayed.

The fix accumulates each arm's own supply history before rendering and before
the independent delivering-arm check. New values append once; a repeated full
selection also works; duplicate ids within one decision still fail. The actual
baseline request remains the ordinary accumulated QueryState rendering.
First visits are unchanged. The side arms keep only their own cumulative
selections in the supply overlay; they do not acquire another arm's answers.
All arms in a visit still share the sealed predecessor; revisits remain
conditioned on the delivering baseline trajectory.

Evidence: 89 focused variant/revision/bundle/scoring tests and 35 ordinary
native/log/status tests pass. This is an engineering correction, not task
quality evidence.

## Separate status-log defect

The failed inspector printed plain text followed by JSON. The batch logger
embedded that output as raw JSON, splitting one event into malformed lines.
The process and attempt records established the real stop independently.

The updated logger serializes every event. The status reader reports an
explicit STOP alongside malformed-history evidence. It never repairs original
history or infers a running experiment from a malformed file. Original status,
STOP, task log and attempt hashes are pinned in the incident receipt.

## Recovery decision

Use the one recovery already permitted by the registered failure policy.
Create fresh generation and tokenizer identities, run the engineering proof,
then the same 625-row full comparison. This is a full recovery, not an
infrastructure resume: the implementation changed. Do not mix old and new
rows or repurpose the original smoke as proof of the fix.

Keep the original actions, ordering, model, prompts, roster, maximum contacts
and primary first-visit question. Record cumulative original and recovery
contact costs. A second failure closes VAR-2; do not create another recovery.
Complete-system verification remains necessary even if local actions improve.
The semantic-delta line and fresh DEV/test boundaries remain unchanged.

Detailed pins: docs/receipts/continuation/2026-09-25-var2-revision-failure.json.
