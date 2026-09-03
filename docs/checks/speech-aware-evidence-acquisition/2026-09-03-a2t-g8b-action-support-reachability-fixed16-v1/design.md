# G8B action-support reachability successor design

## Decision

G8B is a new, identity-only fixed16 successor selected from exactly the 28-row G8 support
remainder. It retains two identities from each frozen Audio2Tool tier under its own declared
SHA-256 namespace, leaving 12 support identities. The receipt, baseline, and experiment contract
are prospective only and authorize no model, scorer, network, audio, gold, task-text, output,
score, or reward contact.

## Frozen actions and row handling

The action set is unchanged: `STOP_M0`, `EXHAUSTIVE_G7`, `SUPPORT_ONLY_RESOLVE`, and
`DECOMPOSED_SELECT_BIND_RESOLVE`. STOP reuses exact-identity G1 M0 bytes and creates no new
contact. The three agent branches share one OBS and 28 family EVIDENCE contacts per row.

For a valid empty decomposed selection, the runtime records a model-free `EMPTY_BIND_PASSTHROUGH`
event, seals an empty binding, skips the binding contact, and sends the empty selection and binding
to final resolve. This is neither a fallback nor a repair.

For an invalid selection, or an invalid binding for a nonempty valid selection, preserve the
received raw frozen-core bytes as the row-local invalid branch output. Make no later contact for that row and do
not retry, repair, substitute, or synthesize an answer. Continue all other rows. Every one of the
four branch manifests still contains all 16 identities, so official scoring measures every row.

## Capacity, queueing, and scoring

The maximum is 544 model calls: 16 rows times 29 shared contacts plus at most 80 branch contacts.
Empty-bind passthroughs and row-local terminal invalid outputs can lower actual contacts, never
raise them. Immediately before every actual contact, render and measure its exact serialized
request plus speech, special-token, and completion reserves. Require the frozen 8,192-token
headroom; refuse before contact on overflow.

The existing two-slot, two-request concurrency and queue depth four remain frozen. Network jitter
testing is false. Gold, transcripts, annotations, and the official scorer remain closed until all
four complete 16-row manifests seal. Then run exactly one official scorer invocation per complete
manifest, retaining detailed output from that invocation rather than rerunning a scorer.

## Boundary

G8B is an action-set reachability screen, not policy fitting, confirmation, scale, test, or paper
work. The post-score oracle is gold-informed only after sealing and remains a ceiling, not a
deployable policy result.
