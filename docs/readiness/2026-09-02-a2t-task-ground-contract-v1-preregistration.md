# A2T Task-Wide Knowledge Ground V1 Contract and Landed-Surface Audit Preregistration

## Decision question

Before candidate pruning or another training-free controller is attempted, determine whether the
current task knowledge is already a usable ground. A usable ground must let the frozen core perform
the complete Audio2Tool task at a high level; merely containing the correct tool somewhere is not
sufficient.

This row is a zero-contact secondary audit of already-sealed aggregate results. The aggregates are
already public inside this repository. The new information is the owner-set qualification contract
and the mechanical consequence of applying it. No per-sample outcome is opened, no policy is fit,
and no threshold, feature, candidate, or knowledge form is searched.

## Ground definition

A task ground is one frozen, English, content-addressed knowledge object that is available to every
query without using the evaluation row's label, reference transcript, annotation, or future turn.
It is task-wide and query-independent at this qualification stage. It must cover the full tool
space and the complete execution semantics needed to produce final calls, including tool-selection
boundaries, argument extraction, multi-call composition, correction handling, and the exact output
envelope.

A registry roster is not automatically a ground. A retriever's top-k candidate set is not a ground.
A gold-conditioned row is not admissible as a runtime ground. Evaluation gold remains scorer-side
after all responses seal.

## Prospective quality contract

The unchanged official Audio2Tool scorer supplies all task metrics. A complete manifest qualifies
only when every minimum gate passes:

| channel | minimum | approximately 104-row count interpretation |
|---|---:|---:|
| exact match | at least 0.90 | at least 94 exact rows |
| tool accuracy | at least 0.95 | at least 99 tool-correct rows |
| slot micro F1 | at least 0.90 | rate gate |
| parse rate | at least 0.99 | at most one parse failure |

Exact match at or above 0.95 is the target, corresponding to at least 99 exact rows at `n=104`.
The approximately-100 flight is a feasibility gate, not a stable population claim. A later
block-disjoint support flight is still required before scale.

## Frozen inputs

| input | SHA-256 |
|---|---|
| A0 full-registry 400 verdict | `8b0e96ca6eac50b75eb07d6f1d05b245c43cc845e877b8f1dd185e4665c7ccff` |
| Stage-2 correct-row verdict | `2377f09ac1138c2648e18fd6ac040465f5d4d11967f4f6479b39ec53bbffa8bf` |
| Stage-2b values-stripped verdict | `ad49af4c73e281b5094aecb917bf59b4b13cf3c7472b54e45947f895a2a86363` |
| Stage-2c augmenting-row verdict | `904b63c1465371f6dcc5c6093cc39153001a32974d06fc83fab357c7a7f75fdc` |
| CPV2 mechanism result | `59b7e91fc2ce47e3f54652e20091228b2c78f970eac85771fe028313e9f13fc1` |
| post-contact headroom result | `a3fc915b945a23e4d265c403235b51e4febd714d03fb4823b6613de067b7b8ac` |
| full knowledge-size receipt | `75f52a23ee86ff00abc2d33bb865fd3a0864dcb77fe7035eece13fbb2e77e081` |
| lexical-ceiling receipt | `624d85f9803291d3f2f8698687bc9c1d0dd43bb49f1bbc8b8948b14b983703fc` |
| frozen tool registry | `7c50b0e8b49f514b169f4040c38ac67ca69ebaf361f754f1f3e994c7cb09d0a4` |

The run must arm the offline connection guard before opening an input, verify every hash, observe a
clean study commit, and report zero frozen-core, retriever, embedding, tokenizer, network, audio,
and GPU contact.

## Mechanical audit

The audit reports only landed aggregates and these fixed classifications:

1. full-registry presence is insufficient if A0 misses either the tool or exact floor;
2. the current top-5 surface is insufficient if its gold-tool coverage or its matched exact score
   misses the exact floor;
3. M0/matched arbitration is insufficient if its descriptive exact oracle misses the floor;
4. the highlighted correct row lacks execution knowledge if conversion misses the exact floor or
   retention misses the tool floor;
5. literal defaults are a copy hazard if any registered induced substitution exists.

All five conditions imply `knowledge expansion required before candidate optimization`. The audit
does not choose the expansion content.

## Consequence

If the current ground fails, suspend candidate pruning and training-free policy work. The next
separately preregistered construction must retain all tools while replacing the flat directory with
an executable handbook: values-stripped schemas, required/optional argument patterns, explicit
copy-only-from-speech rules, tool-selection contrasts, multi-call/correction rules, and a strict
JSON envelope. It must be derived only from the block-disjoint construction partition and governed
registry, never evaluation or test labels.

If that full ground misses the prospective gate on a fresh approximately-100 cohort, use sealed
post-hoc diagnostics to route the next action: expand intent contrasts when tool accuracy binds;
expand argument knowledge when tool accuracy passes but exact/slot quality binds; repair USE/output
contract when parse rate binds; improve OBS when speech observation binds. Do not optimize a
candidate subset until a complete ground qualifies.

Evaluation engineering retains complete-manifest outer parallelism around the unchanged
single-process official scorer. Network jitter, packet loss, injected latency, and network retry
stress are outside the engineering baseline.
