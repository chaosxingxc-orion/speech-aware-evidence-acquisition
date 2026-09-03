# G8B action-support fixed16 preregistration

## Decision

Authorize one bounded G8B discovery flight only after the exact clean-commit, execution-plan, precontact-report, and exposure-ledger bindings pass. G8B uses a fresh identity-only fixed16 selected from the untouched 28-row G8 support remainder. It makes no test, confirmation, scale, or paper claim.

## Frozen comparison

The four complete branches are `STOP_M0`, `EXHAUSTIVE_G7`, `SUPPORT_ONLY_RESOLVE`, and `DECOMPOSED_SELECT_BIND_RESOLVE`. They share each row's one OBS and 28 family EVIDENCE responses. STOP reuses the frozen same-row G1 M0 output with zero new contact. Gold remains closed until all four 16-row manifests seal.

The decomposed branch makes a strict SELECT, a strict BIND only for a nonempty valid selection, and a final frozen-core resolve. A valid empty selection creates one hashable `EMPTY_BIND_PASSTHROUGH` with no BIND contact, then proceeds to the frozen-core final resolve. An invalid SELECT or nonempty BIND is preserved unchanged as that row's decomposed failure output; no later contact, retry, repair, resend, fence stripping, substitution, or synthesized answer is permitted for that row. Other rows continue.

## Capacity and context

The structured `ExecutionPlan` reserves a 544-contact and 2,578 speech-audio-second maximum. Realized contacts equal `528 + nonempty_valid_selections - invalid_selects - invalid_binds`, between 512 and 544. The client trace must reconcile the realized count exactly.

Every actual request is rendered and measured immediately before contact. The model context is 32,768 tokens, the operational prompt-plus-completion cap is 24,576, and the required remaining headroom is 8,192. The worst preflight envelope is the exhaustive resolve at 24,304 tokens, leaving 8,464. Selection leaves 10,051; maximum BIND leaves 14,051. No fixed-step extrapolation, trimming, or completion-reserve reduction is allowed.

Two sample-affine slots, at most two concurrent model requests, queue depth four, temperature zero, and no network-jitter testing remain frozen.

## Scoring and decision

After four manifests seal, schedule exactly one unchanged official scorer process per whole manifest through four outer workers. Do not shard a manifest or average shard metrics. Persist aggregate and per-row detail from the same invocation. Then create and score one model-free post-score branch-oracle manifest.

Only an oracle with at least 15/16 exact matches and slot micro-F1 strictly above 0.90 may open a separately preregistered approximately-100 randomized, propensity-logged Vowpal Wabbit experiment. Failure requires knowledge or action-set expansion on a new identity-only discovery roster. The post-training-free-RL `>0.90` objective is not an engineering-baseline admission requirement.
