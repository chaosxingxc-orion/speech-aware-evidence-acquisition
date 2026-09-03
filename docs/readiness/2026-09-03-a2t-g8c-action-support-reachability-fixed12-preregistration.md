# G8C action-support fixed12 preregistration

## Scope and identity

Prepare one official-scoring successor using every one of the 12 untouched identities in the
exact G8B support remainder. Retain source order and read only `key`, `sample_id`, and `tier`.
Do not use G8B recovered response bytes, behavior counts, scores, rewards, task text, or audio to
select, prune, tune, or reorder G8C. The G8C split identity is
`acf2d1e7664987bf7154e2e45ed366b712c11e710910cf94af067e90ba4e1acb`.

This document, receipt, configs, and launcher are preparation only. They authorize no flight and
make no model, scorer, service, audio-byte, gold, reference-transcript, tokenizer, network, test,
or future-turn contact. A separate exact-attempt ExecutionPlan, clean-tree precontact report, and
exposure gate are required before any future model contact.

## Frozen protocol

Reuse the corrected prospective G8B protocol without scientific changes:

- `STOP_M0` reuses the frozen same-row G1 M0 response with zero new contact.
- The three agent branches share one speech OBS and 28 speech EVIDENCE contacts per row.
- `EXHAUSTIVE_G7` and `SUPPORT_ONLY_RESOLVE` each make one final frozen-core resolve.
- `DECOMPOSED_SELECT_BIND_RESOLVE` makes SELECT, makes BIND only for a nonempty valid selection,
  and makes final resolve only while the row remains valid.
- A valid empty selection logs the model-free empty-bind passthrough and proceeds to final resolve.
- Invalid SELECT or BIND bytes become only that row's raw decomposed output; no later row contact,
  retry, repair, resend, fence stripping, substitution, or synthesis is allowed.

The service context remains 32,768 tokens, with a 24,576 operational prompt-plus-completion cap
and at least 8,192 tokens of headroom. Measure the exact serialized request, speech reserve,
special-token reserve, and completion reserve immediately before every actual contact. Refuse on
overflow without trimming or extrapolating from an earlier loop step. Preserve two sample-affine
slots, two concurrent requests, queue depth four, and batch size two. Network-jitter testing is
out of scope.

## Budget and scorer plan

The planned maximum is 408 model contacts. Realized calls must reconcile exactly to
`396 + nonempty_valid_selections - invalid_selects - invalid_binds` and remain in `[384, 408]`.
Frozen G1 metadata gives 76.694 seconds across the roster, so the maximum repeated-speech
reservation is 2,608 seconds. There are zero embedding, tokenizer, paid API, or external network
contacts.

Keep gold, annotations, reference transcripts, and the scorer closed until all four complete
12-row manifests seal. Then run one official scorer process per whole manifest, at most four
independent processes through the outer coordinator. Capture aggregates and per-row detail in that
single invocation. Never shard a manifest, average shard results, or rerun to recover detail.

## Decision rule

Build the frozen post-score branch oracle only after all four branch scores seal. Exact match at
least 11/12 and slot micro-F1 strictly greater than 0.90 must both pass. Passing opens only a
separate approximately-100-row randomized propensity-logged discovery registration using the
pinned open-source Vowpal Wabbit controller. Failure opens no policy fit and instead requires new
knowledge or action construction on a new identity-only roster. Approximately-1,000, test,
confirmation, Stage-3, and paper work remain closed.

## Prepared bindings

- G8C roster SHA-256: `f00ab9486d978c334e14c96231ac45968f24c3bf8792181427703b738260dac0`
- Baseline SHA-256: `1953bcfaeb294dd3f48085e9d24932f18e8cfd2d8ccef98222a78132af26e448`
- Experiment SHA-256: `38f17a3e4b35bdbf9eba081d6a2caa9fae871dd961a4f4e9c7e8b67b5e853a69`
- Composed-config SHA-256: `137f3caab46a5a8818c90bd526d0d7868d2ee386f4c0d5308a12763c0146fc76`
- Protocol SHA-256: `b68f29ac9afffd9bdc4064ce4d2959c8b7b9f54f99fd80842a0496d090672465`
- Protocol-descriptor SHA-256: `fd307e2e74714ac5dc2e89ae2c4d94c033a7546486e848afee9172d8aa0c977e`
- Thin launcher SHA-256: `a82fb1d03336d3c1ca7c4da06833a7a2c9a3ead123978df87b3be0c59d0a799e`
- Corrected G8B parent launcher SHA-256: `65047c7a96dac5601368739944e01921510d302d844e3b28ada2e358b7379229`
