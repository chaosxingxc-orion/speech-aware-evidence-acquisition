# Native completion provenance for the shared agent loop

Status: prerequisite implemented; controller and live tool execution integration remain pending.

The owner requires the frozen core to choose during a task whether to answer or invoke a real tool. Text-only completion discarded the raw native call metadata already returned by the shared adapter. A text heuristic would conflate a predicted Audio2Tool business call with an internal evidence-tool request and could execute the transport's compatibility fallback for malformed arguments.

The shared FrozenCoreClient now provides opt-in complete_with_metadata and complete_prepared_with_metadata methods. Both use the existing request builder, adapter, accounting, and one-use prepared request path. Ordinary complete and complete_prepared still return their historical text and produce unchanged request bytes.

CoreCompletion binds the exact sample, contact, request ID, request hash, response hash, and response-text hash. Native call JSON is held as immutable bytes; reading it returns an independent copy. Malformed argument strings remain malformed. This seam does not interpret calls, supply observations, execute tools, or authorize a flight.

Validation used the real FrozenCoreClient and FrozenCoreAdapter with in-process fake transports: nine focused cases plus adjacent client/native/adapter tests, 169 passed and one skipped. Coverage includes ordinary and prepared wire parity, one-use request consumption, raw native provenance, source binding, no-call responses, concurrent response separation, and unchanged legacy text behavior. Ruff and diff checks passed.

Remaining work: propagate metadata through both shared runner paths into the controller, validate a bounded native answer-or-tool decision, dispatch only registered internal tools, bind their actual observations into successor requests, attach runtime contact custody, and run the prospectively registered engineering proof. A tested prerequisite is not a live agentic baseline or an efficacy result.

No model, tokenizer, speech-tool, GPU, scorer, or dataset-result contact was performed by this change.
