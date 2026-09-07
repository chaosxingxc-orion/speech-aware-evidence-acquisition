# `e21_participant_names` is a D1 evidence layer — KC-E1's hard gate is closed

Exposure row `SAEA-SN-MF-E21-PARTICIPANT-NAMES-D1-V1` (`model-free-check`), registered and committed
before the first file was hashed. **Zero contacts of every kind** — model, GPU, tool, embedder,
tokenizer, network, audio decode, paid API. Only ConEC CONTEXT bytes and committed receipts are
opened; no reference transcript, timestamp file, `wer_tags` sidecar or bias list is read, and nothing
here writes roster CONTENT — sample ids, byte sizes and digests only.

## 1. The gap

`docs/receipts/artifacts/d1-identity.json` records four ConEC layers — `e21_contexts`,
`e21_nlp_references`, `e21_timestamps`, `e21_wer_tags` — and `e21_contexts`'s own
`excluded_non_layer_files` lists `participant_names` as **outside** it. Since the 2026-08-13
`conec-names` incident, `contracts.gate_evidence_identity._route_evidence_layer_key` has been able to
**name** the layer a `contexts/participant_names/<call>.names.txt` relpath belongs to and unable to
**resolve** it. Any run whose evidence source reads a call's participant roster — `conec-names`, and
through it E5's `conec-class-lists` / `conec-class-lists-placebo` pre-meeting brief — therefore fails
closed at the evidence-identity rail. That is precondition 1 of
`docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v1-preregistration.md`, and it is a hard gate.

## 2. The fix: additive, never a rewrite

The immutable E0 D1 artifact is never rewritten in place, so the layer arrives the way a bounded media
slice already does (`gate_media_identity._d1_media_supplement_records`): as one additive, hash-pinned
successor document, schema **`saea-d1-evidence-supplement-v1`**, declaring exactly one D1 layer key.

| | |
|---|---|
| artifact | `docs/receipts/artifacts/d1-e21-participant-names.json` |
| sha256 | `313da4c48acf7403207e2a45c28f90262a94adfaa42873a0c9f251fc9d6bfd83` |
| declared layer | `e21_participant_names` (carrier `conec`) |
| calls | **44** |
| total bytes | 15,067 |
| `ids_sha256` | `81236a165bc5a7bea24b7a9e04ce7a7a4dcfd74a04ee2ae08e7686e3abeb51d6` |
| `manifest_sha256` | `6934e2fa0a136000ffa3c626ac5dfc4b1479cddc93724428dd44d11fbd9aa158` |
| `parent_d1_sha256` | `9c10fad1e5b625f977a5bdc71ed0c782e5d5c76c7a13af11ce811c5e152d35e3` |
| `source_binding_sha256` | `81236a16…b51d6` — the carrier's own `e21_contexts` `ids_sha256` |
| excluded non-layer files | `names.txt` — ConEC's stray aggregate roster, recorded, never a sample |
| builder | `scripts/build_e21_participant_names_d1_supplement.py` |

**The layer's own facts are produced by the production code path, not re-derived.** The builder calls
`scripts.freeze_participant_names_layer.build_participant_names_layer`, which calls
`data.identity._dir_layer` and `.layer_report` — the same two functions `e0.d1_identity.build_d1`
calls for every other D1 layer, including the sibling `e21_contexts` layer this one sits beside. The
gate then **recomputes** both digests from the manifest it reads
(`gate_evidence_identity._layer_ids_sha256` / `_layer_manifest_sha256`, the same
`"\n".join(...)` recipes `data.identity.Layer` uses) rather than trusting the claim.

**The sample universe cannot widen.** `ids_sha256` equals the carrier's own `e21_contexts`
`ids_sha256` to the digit — the same frozen 44 calls, split identity `fcc1b0bc…d69e` — and the gate
refuses a supplement whose ids do not.

**One supplement per gate.** `contracts.FrozenCoreGate.__post_init__` refuses a gate carrying both a
media supplement and an evidence supplement. **The KC-E1 flight carries this evidence supplement and
no other**, through the new dataset fragment `configs/dataset/earnings21-discovery-conec-names.json`,
which `configs/experiment/e21-kc-e1-brief-44-v1.json` now composes for all three of its fragments. It
needs no media supplement: all 44 `earnings21-original` media entries are already inside the
immutable D1 closure.

## 3. Verified offline, through the production rail

`scripts/verify_e21_participant_names_d1_supplement.py` →
`evidence-identity-verification.json`. Six checks, all through
`FrozenCoreGate.verify_evidence_identity` / `verify_evidence_content_identity`, never a
re-implementation:

| # | check | result |
|---|---|---|
| 1 | a gate with NO supplement, on an evaluation call's roster relpath | **refused** — "carrier 'conec' lacks a 'e21_participant_names' manifest, and no D1 evidence supplement declares that layer" |
| 2 | the same gate WITH the supplement, file rail | **44 of 44 resolved** |
| 3 | the same 44 rosters' already-read bytes, content rail | **44 of 44 resolved** |
| 4 | `conec-class-lists` on evaluation call `4330115` | its **two** items route to **two** layers — the roster half to `e21_participant_names`, the document half to `e21_contexts` — and both pass both rails |
| 5 | one byte appended to a roster's content | **refused** — "evidence content identity drift … 416 bytes / 08840410… → 417 bytes / 54e0c14d…" |
| 6 | a sample id outside the frozen 44 | **refused** — "no D1-recorded evidence identity" |

The probe call is drawn from the frozen `r4-e21-sub10` **evaluation** roster
(`docs/receipts/probe-samples/r4-e21-sub10-sample.json`, split identity `fa1d2982…4cc2`): the roster
half of an evaluation call's brief is exactly what the gate has to resolve before KC-E1 can fly.

## 4. Tests

* `tests/contract/test_d1_evidence_supplement.py` — the refusal matrix on a synthetic world:
  resolves both rails, a context relpath still answers from the base D1, a supplement for another
  layer does not answer this one, and eleven refusals (shadowing a base layer, hash drift, wrong
  parent D1, wrong carrier, wrong source binding, a widened sample universe, either wrong digest,
  wrong `total_bytes`, wrong schema, an extra or missing key, an unpaired digest) plus the
  two-supplement refusal.
* `tests/unit/test_e21_participant_names_supplement_document.py` — the COMMITTED document against
  the COMMITTED base D1, repository bytes only: digests recompute, parent binding names the live D1,
  the universe is the carrier's own, the declared layer is genuinely absent from the base artifact,
  and the dataset fragment pins this exact file.

## 5. What this does and does not authorize

It closes **one** KC-E1 precondition. Precondition 2 — the brief's prompt fit on the flight
tokenizer — is unmeasured and is still the flight agent's first gate. Nothing here is an
authorization to fly, a mechanism result, or a claim of any kind.

## Files

| file | what it holds |
|---|---|
| `evidence-identity-verification.json` | the six checks above with their exact refusal messages, the supplement's own facts, and the evaluation roster |
| `MANIFEST.sha256` | this directory's own byte manifest |
