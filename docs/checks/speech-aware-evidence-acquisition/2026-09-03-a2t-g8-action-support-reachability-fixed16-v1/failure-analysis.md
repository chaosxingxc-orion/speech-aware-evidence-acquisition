# G8 fixed16 terminal-flight analysis

## Outcome

The only authorized G8 flight terminated after 76 of at most 544 frozen-core contacts. It consumed 142.145 speech-audio seconds, emitted no branch manifest, opened no gold, and made zero scorer contacts. The local llama.cpp service stopped cleanly. The original experiment identity and attempt are permanently closed.

## Direct cause

The terminal contact was `g8fixed16-0076`, the `DECOMPOSED_BIND` stage for `tier1_direct:000167`. Its upstream SELECT was the valid sealed value `[]`, so the only cardinality-preserving binding was also `[]`. The BIND request explicitly required that value and allowed 12,288 completion tokens. The response used 22 tokens, was complete and non-truncated, but returned a fenced JSON array containing one invented call whose name echoed the agent-control suffix.

This is not a context-window, completion-budget, network, dispatcher, or parser-strictness failure. The request used 479 prompt tokens, the response used 22 completion tokens, and the maximum preflight BIND envelope retained 14,038 tokens of context margin. Removing the fence would still leave the wrong cardinality and an unregistered tool name.

## Engineering root cause

The protocol asked the model to perform an information-free empty binding and made any structured-stage violation terminal for the entire cohort. One sample-level schema failure therefore discarded all cohort-level measurements. Two rows had already reached the branch stages and a third was in evidence acquisition, but the preregistered failure policy correctly prohibited partial manifests and post-failure scoring.

The strict parser did its job. The defect is the experiment topology: a deterministic empty transition was unnecessarily delegated to the model, and row-level execution reliability was coupled to cohort-level evaluability.

## Prospective correction

A successor must use a new identity-only fixed16 roster from the untouched G8 support remainder. It must not reuse or repair the failed bytes.

The successor will:

1. Seal an empty binding as the explicit model-free identity transition `EMPTY_BIND_PASSTHROUGH` when the frozen core selects `[]`; make no BIND contact; then let the frozen core author the final response.
2. Preserve strict parsing for every nonempty BIND.
3. Treat an invalid SELECT or nonempty BIND as the affected decomposed branch's raw frozen-core failure output, record the failed stage, and make no later contact for that row. Other rows continue without retry, repair, resend, or substitution.
4. Keep exhaustive and support-only outputs for every row and emit complete four-branch manifests only after all 16 row outcomes are sealed.
5. Reserve the 544-contact maximum while reconciling the realized dynamic count and speech cost from actual transitions.

This correction changes execution reliability, not the knowledge ground, branch comparator, scorer, reachability gate, or frozen-core answer authority. It therefore remains a bounded engineering-discovery step before any approximately-100 training-free policy experiment.

## Sealed evidence

- Attempt record SHA-256: `14aa53e9c345bd4cea4aedbf719069a26ac5a636eb0549bd7c33a9c2fc945cfb`
- Failure receipt SHA-256: `46d5d17780f508d9a8bfd60e10ff647c7a14bd20c38aaab99a0e6c74048ba697`
- Transport trace SHA-256: `a932cd86e40d218af76a3683a520d9fbc9e02242e8f14368fa4fbdc192bab5cc`
- Transport trace manifest SHA-256: `650d3c02d666204a6c938fb65ef0b82be17c57dd5b320320508cfb4f87ae64f2`

External root: `$SPEECHRL_DATA_DIR/runs/SAEA-A2T-G8-ACTION-SUPPORT-REACHABILITY-FIXED16-V1/flight-20260903T020018Z/`.
