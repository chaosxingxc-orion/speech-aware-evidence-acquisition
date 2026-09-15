# E21 governed context: constructed stores and verified consumption

This CPU checkpoint changes no GPU authorization or scientific verdict. Read the owner
GPU hold and current canonical experiment handoff before dispatch.

## Root design

Use two independently pinned external-governed stores for the 44 ConEC/Earnings21 calls.
The participant-roster value preserves all listed full names, source order and explicit
roles, including names without a role. The document-lexicon value carries lexical forms
only. Its frozen source-only policy, source-order-letter-bearing-case-first-v1, requires a
letter, deduplicates exact forms, prefers purely alphabetic forms containing uppercase,
preserves source order within both buckets and retains at most 128 forms. This heuristic
is neither proper-name recognition nor a proven quality improvement.

The sources are Name - Role files and token/count rows. Do not infer pronunciations,
financial facts, aliases, speaker identity, relationships or spoken occurrence. A listed
name is spelling/role evidence, not proof of an utterance. Counts and adjacency do not
establish facts. Numeric-only lexical rows are excluded; numbers in the audio remain
the source for transcription.

Route by the original parent call ID. This is exact source-scope selection, not semantic
or acoustic nearest-neighbor retrieval. Separate execution windows retain independent
speech/query identities while accessing the same legal parent context. First supply
both stores to Solver; Perception receives no automatic context in this version.
Reviewer and Planner retain the resulting trajectory evidence. Solver alone delivers
the transcript. Revisited Solver phases preserve existing evidence rather than acquiring
duplicate values.

## Actual preparation

Construction commit: 6e9ff08e. Reviewed consumption code: bf5a4744236830324744afd0144a2d672bcd981f.
Both stores were built once and then verified warm through the existing public driver:

    python -m speech_aware_evidence_acquisition.core.driver prepare-semantic-knowledge
      --registration configs/preparation/e21-governed-participant-roster-v1.json
      --repo-root /home/chao/saea-worktrees/e21-native-window-runtime-v1
      --data-root /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data

Join the displayed command lines when invoking the shell. Use the corresponding
e21-governed-document-lexicon-v1.json registration for the second store. Both registrations
pin the live umbrella lock and original E0/D1 authority; participant names additionally
pin the evidence supplement. Preparation verifies source files and the exact consumed
bytes, then uses existing publication/concurrency/collision checks. Warm calls return
the identical release.

Source consumption was 15,067 participant bytes and 358,266 lexical-source bytes.
Each store has 44 values. Participant values total 27,099 UTF-8 bytes (median 611,
maximum 1,068 per call); lexical values total 66,953 bytes (median 1,527.5, maximum 1,678).
These are byte counts, not token measurements or capacity proofs.

The exact reusable knowledge_stores mapping is
[the binding fragment](2026-09-15-e21-governed-context-binding-v1.json).
It is a verified routing fragment, not a complete experiment registration.

## Root verification and limits

The actual pinned 1,593-window inventory and packet metadata all select exactly the
two values belonging to each window's parent. Perception receives no context; reentry
selects zero new values after both are visible. The audit uses public named-store
loading and routing with verified source/release pins. It does not repeat packet-byte
validation or construct actual model requests.

The configured synthetic lifecycle combines the pure shared store builder, both named
stores, real configuration resolution, FlightRuntime, FrozenCoreClient,
LlamaServerTransport rendering and the OpenJiuwen role workflow. It covers two windows,
Reviewer-selected speech spans, Planner-requested revision, Solver consumption of both
context stores and tool evidence, ordered parent delivery, trace checks and one complete
scoring handoff. Other-call values are absent from all rendered requests. Equivalent
direct and native configurations without context remain in the same fixture.

Root repaired the composite supply occupying the packet argument, preserved the original
candidate-only automatic callback, and prevented revised Solver visits from reacquiring
visible values. Registered rank/fuse factories perform actual composition. Scope
compatibility is checked when constructing routes.

The final focused regression passed 106 tests with three existing dependency warnings.
Ruff, engineering-base and diff checks passed. The first final-suite command named a
nonexistent test file and collected no tests; its log is retained, and v2 is the
successful run. Earlier narrower counts overlap this evidence and must not be added.

Service responses, neural ASR, capacity endpoints, the synthetic packet artifact loader,
manifest builder and final bundle/scorer boundaries remain simulated in the lifecycle
fixture. There were zero new frozen-core, ASR, tokenizer, encoding or scoring contacts.
This proves preparation and shared consumption, not live fit, tool-selection quality,
a finalized scientific bundle or task benefit.

## Remaining finite work

Freeze complete matching direct/system fragments, exact role prompts, local tool
inventory/protocol and per-unit model/tool/fit plans. Evaluate the existing task using
overall WER, PERSON, non-entity/numeric and insertion analysis. Preserve the owner rule
that small insertion increases are analyzed rather than automatically vetoing future
candidates. The new context value policy remains prospective until task evaluation.

This preparation/consumption step is complete; do not add generic execution abstractions
to close it. Integrate reviewed commits at the permitted flight boundary. Actual GPU
fit, encoding, ASR and experiments remain held after the current A2T task stops until
explicit owner resumption. Do not unload resident model memory.

## Evidence

External paths are relative to SPEECHRL_DATA_DIR.

- coordination/e21-native-window-bridge-v1/root-governed-context-checkpoint-v1.json;
  SHA256 4207e46fcc63e40b1c565e1a829a06b993f4918e514fe17ce722710896fb0ec4.
- coordination/e21-native-window-bridge-v1/governed-context-routing-full1593-v1.json;
  SHA256 2ee7b5d77dce31abc9744db5b75110d2ab52cadf08191708b9334948fa6fe5fe.
- coordination/e21-native-window-bridge-v1/root-governed-context-regression-v2.log;
  SHA256 0a47467db9194d875e36c09f048eeee6a56dc9755ac850acfac44f4520f72bc0.
- knowledge/e21/governed/participant-roster-v1/completion.json;
  SHA256 05709c71e9a571d7ede5935da15f0b82e8ecbddd1691acd8057c038e1aa9aad9.
- knowledge/e21/governed/document-lexicon-v1/completion.json;
  SHA256 e73e451e1337b748094b63e1675faff0bdb348114e697db8d971d3ea516db176.
