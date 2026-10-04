# External callback handoff for the existing baseline learner

This is a thin local file adapter for `ContextLearningCallbacks`. It connects an original live learning worker to separately admitted GPT-6.1 Sol subagent work and the root-owned GPU evaluator. It neither contacts a model nor starts a flight. The original TF/GEPA algorithm, selection, accounting, proposal validator and complete-family evaluator remain unchanged.

`run_external_context_iteration` freshly qualifies the complete source family and original TRAIN reference, checks the exact registered iteration plan and callback quotas, and only then creates the exchange. It calls the existing `run_context_learning_iteration` once. A real launch still requires exact external contact admission, frozen source, Windows-owned worker receipts and separate input directories. No real learning request is admitted by this engineering package. Keep the initial family READ unsigned until all six members independently qualify.

## Live handoff

Each reserved algorithm callback publishes one immutable English request with its stage, ordinal, task bytes/hash, optimizer input identity, actor label and exact plan hash. The original worker waits for the corresponding response until its prospectively configured finite deadline. Root can inspect the request and live process identity without substituting another iteration or rerunning earlier calls. The callback invocation is still one opportunity while waiting.

`submit_response(request_path, envelope, actor=...)` atomically publishes one response using a create-only link after complete bytes are flushed. It preserves the external `{value, provenance, usage}` envelope; provenance must address the original subagent or complete-family response, not a root rewrite of it. The waiting adapter checks exact request/actor identity, bounds, English-script validation and usage. Actor labels are routing metadata, not authentication or independent proof of actual provider version. Root retains the actual configured model, isolated task/input manifest and original response evidence separately.

Usage fields are `provider_contacts`, `input_tokens`, `output_tokens`, each measured nonnegative integer or null. Unknown remains unknown through the original learner. Callback counts, bytes and elapsed time do not establish token counts or total compute matching. Byte limits are transport bounds, not actual model-request FIT or server-enforced token limits. Separately register any model/request/token limits before contacts; no paid API spend is introduced here.

Evaluation responses can return only `{bindings, recipe_pin}`. The original learner freshly verifies the separate trial's registration, READ, full six-member seals, unique scores, policy identity, cohort and original TRAIN reference. The exchange cannot certify those sources, return a reward, sign READ or dispatch a GPU job. Preparing a trial is a root task at that boundary.

## Failure and isolation

Timeout, malformed output, mismatched identity, changed scope, quota exhaustion or read failure preserves the original request/response and fails the exchange. Later callbacks refuse. Recreating an existing exchange directory also refuses. This adapter has no restart, response repair, slot replacement or dead-worker resume. Root must inspect the actual process handle and preserve/diagnose any terminal failure under owner227 before a prospective disposition.

Use independent algorithm exchange directories and isolated subagent inputs. Do not send the root conversation, earlier incidental log exposure, historical B outcomes or milestone/test feedback. Only registered complete-family evidence and permitted references enter the respective learner. Successful I/O transport is not scientific adoption, a learning result or release of any held carrier.

## Validation

The synthetic tests run both original baseline iteration functions through real file waits and source-bound response publication. They cover retention and original accounting while separate existing tests cover the underlying READ/score/runtime custody. The new adapter has135 statements and12 branches, all covered;120 focused tests pass. These are model-free engineering proofs, not real GPT-6.1 proposals or GPU learning results. See `validation-v1.json` for hashes and boundaries.
