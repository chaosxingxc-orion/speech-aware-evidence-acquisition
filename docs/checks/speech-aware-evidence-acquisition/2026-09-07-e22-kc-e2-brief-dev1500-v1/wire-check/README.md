# KC-E2 / KU-E2c — zero-contact wire check, request half

**PASS on the request half, for both cells. The seal-and-score half was REFUSED, correctly, by a
lock that belongs to another flight — see §3.**

`scripts/flights/run_e22_esb_cell.py --wire-check` on the committed tree at study commit
`b94c7d3c`, experiment `e22-kc-e2-brief-dev1500-v1`. **Zero model contacts, zero servers started,
zero sockets opened**: the only fakes are `core.flight.runtime.WireCheckGate` and
`WireCheckTransport`, which never opens a socket. The resident serving session was neither started,
stopped nor attached.

## 1. What passed, per cell

| | E22-KC-E2-BRIEF | E22-KU-E2C-PLACEBO |
|---|---|---|
| receipt | `E22-KC-E2-BRIEF-wire-check.json` (sha256 `f1708089…`) | `E22-KU-E2C-PLACEBO-wire-check.json` (sha256 `c6772717…`) |
| contacts driven | 1,500 | 1,500 |
| model contacts / servers | 0 / 0 | 0 / 0 |
| `payload_keys_equal_arm_visible_fields` | **true** | **true** |
| payload keys | the ten `ARM_VISIBLE_FIELDS["bare-core"]` fields, the sealed comparator's own | identical |
| `tool_schemas_count` | 0 | 0 |
| policy / policy_kind | `fixed` / `direct` | `fixed` / `direct` |
| split identity | `8dc9d6a0…`, equal to the dataset fragment's | identical |
| config hash | `d5e01c0b…` | `7af9cac8…` |
| protocol hash | `cdae8a37…` | `5d3f9286…` |
| dispatch | concurrent over 8 slots, 1 contact per sample | identical |
| audio seconds accounted | 12,948.983 | 12,948.983 |

The two cells' config and protocol hashes differ, which is the point: they differ in exactly the keys
`evidence_source` and the twin's own `evidence_brief_derangement` pin, and in nothing else.

## 2. The evidence rail, driven end to end

| | KC-E2 | KU-E2c |
|---|---|---|
| `evidence_source` | `e22-metadata-brief` | `e22-metadata-brief-deranged` |
| items resolved | 1,500 (one per clip) | 1,500 |
| samples with evidence | 1,500 of 1,500 | 1,500 of 1,500 |
| **derivation records re-verified** | **1,500** | **1,500** |
| transforms | `e22-metadata-brief@v1` | `e22-metadata-brief-deranged@v1` |
| `carrier_bound` | `[false]` — honest, and §1.1 of the preregistration says why | `[false]` |
| block digest set | `c05ac7d4…` | `6f3ccf60…` |

Every one of the 3,000 records was re-derived by `core.evidence_derivation.DerivedEvidenceRegistry`
from the call's own two-line metadata source slice, against the params
`core.evidence.resolve_declared_transform_params` reads from that cell's composed config — the same
rail `core.driver.run_experiment` runs — **before** the request path was driven. The pinned metadata
table was re-hashed on every one of those reads and matched `52dbda11…` every time.

The two arms' block digest sets differ, as they must: the twin renders another call's brief. Blocks
are distinct per clip rather than per call because the evidence id is minted as
`<transform>/<sample_id>` and the sample id is the clip; the brief CONTENT is per call, ten distinct
texts per arm.

## 3. Why the seal-and-score half was refused, and why that is correct

```
BundleError: study repo .../wt-kce2 HEAD moved during the flight: the flight lock recorded
study_head 'bfab2b16...' at launch, HEAD is now 'b94c7d3c...'
```

`$SPEECHRL_DATA_DIR/locks/flight.lock` is **held by another flight**: run id
`SAEA-E21-KC-E1-BRIEF-44-V1`, pid 10701, started 2026-09-07T17:12:38Z, recording the main checkout's
HEAD `bfab2b16`. `core.bundle.git_commit` cross-checks that recorded head against the study repo's
current HEAD before binding a COMPLETED manifest, and this worktree's HEAD is its own.

**The lock was not touched, and must not be**: it belongs to a live Earnings-21 flight in the main
checkout. The refusal is the guard working — a COMPLETED manifest may never bind a commit the flight
never ran under — and it is a property of running a wire check in a worktree while another flight
holds the shared lock, not a property of these two cells.

**What that leaves unproven here**, stated rather than glossed: the manifest builder, the bundle
verifier and the four registered scorers (`asr-wer-esb-whisper`, `asr-wer-esb`,
`brief-term-recall-v1`, `cost`) were not driven over the canned responses. The flight agent re-runs
the wire check with `seal_and_score` reached once the shared lock is free, and the request half above
does not need re-proving when it does.

## 4. Boundary

No media byte was decoded; the 1,500 WAVs were re-hashed against the frozen roster receipt before any
sample was built, as `roster_samples` always does. No reference, transcript, segment table or
annotation byte was opened by either cell. `test_split_read: false` — the six calibration-exposed ESB
test calls are not named by any fragment this check composed, and the 109 confirmatory calls are not
loaded.

Nothing here is an authorization. Both cells still need the two preconditions of the
preregistration's §8, their own exposure rows, and the owner's GO.
