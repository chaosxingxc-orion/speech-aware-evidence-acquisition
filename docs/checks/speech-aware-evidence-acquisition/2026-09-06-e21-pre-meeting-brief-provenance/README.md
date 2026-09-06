# The Earnings-21 pre-meeting brief — per-call provenance

E5 deliverable 3. For all 44 `earnings21-original` discovery calls, the two ConEC files
`conec-class-lists` reads, their sha256s, the transform applied to each, the sha256 of the rendered
half, and the brief's whitespace-token cost — with the construction/evaluation roster label beside
every row.

**Zero contacts of every kind** — model, GPU, tool, embedding, network, audio — and **no gold or
reference read**. The two files per call are ConEC CONTEXT, classified `runtime-legal-input` by
`docs/readiness/2026-09-03-information-audit-earnings21-conec.md`: the pre-existing press release,
slides and participant roster a human reads before joining the call. No reference transcript, no
timestamp file, no `wer_tags` sidecar and no bias list is opened; `tests/unit/test_class_lists.py::
test_the_renderer_opens_no_reference_path` records every path the renderer touches and asserts each
one lives under `contexts/`.

## The separation, asserted over the real 44

The generator refuses to write anything unless, for every call:

* the call's two source relpaths each carry that call's OWN sample id, and
* no source file is shared with any other call — **88 distinct files for 44 calls**.

So an evaluation call's brief is built from that call's own ConEC context and from nothing another
call's files carry, which is the benchmark's intended use of the context layer, and the property is
re-derived from the real paths every time this receipt is rebuilt rather than asserted once.

| | |
|---|---:|
| calls | 44 |
| construction (`kb-construction`) / evaluation (`r4-e21-sub10`) | 34 / 10 |
| distinct ConEC source files | 88 |
| brief whitespace tokens — min / median / max | 263 / 969 / 2,565 |
| placebo matches the brief's token count on every call | yes |

**The maximum matters for the flight.** 2,565 whitespace tokens is the largest brief in the set, and
the sealed full-44 geometry serves 6,144 tokens per slot against a certified 2,258-token worst
request. A whole-brief arm therefore has to be measured on the FLIGHT tokenizer before takeoff, and
capped through `brief_max_entries_per_class` if it does not fit — the preregistration
(`docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v1-preregistration.md`) makes that the
flight agent's first gate. Whitespace tokens are a lower bound on model tokens and are reported here
only to size the problem; this receipt deliberately does not guess the tokenizer's count.

## Files

| file | what it holds |
|---|---|
| `brief-provenance.json` | the whole record: per call, the roster label, both source relpaths with their sha256s, the transform names, the derived sha256 of each rendered half and of its placebo twin, and the token counts; plus the summary and the zero-contact block |
| `per-call-sources.md` | the same 44 rows as a table: call, roster, the two source hashes (12-character prefixes), brief tokens |
| `example-brief.json` | the complete rendered brief and its complete placebo twin for one CONSTRUCTION call, 4320211 — the artifact itself, not only its shape. A construction call by choice: an evaluation call's brief is the thing under test |
