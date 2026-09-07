# KU-S3 wire checks — receipt (2026-09-07)

Preregistration `docs/readiness/2026-09-07-slurp-consumption-ku-s3-v1-preregistration.md`,
section 7. Three arms, four DEV-1000 rows each, driven through the REAL
`core.flight.FlightRuntime.wire_check` path against `WireCheckGate` and
`WireCheckTransport`: **zero sockets, zero model contacts, zero GPU.**

What was real: the composed fragments, the label-free roster with every media file re-hashed, the
frozen snapshot load and hash verification, the `phase_supply` spec resolution, the sealed vector
load and re-hash, the `kb-facet-v1` construction, the pre-flight bootstrap selection, the request
build and the transport seam. What was fake: the gate and the transport, so nothing could reach a
server.

| arm | contacts | config hash | system message sha256 | query / facet rows | modality |
|---|---|---|---|---|---|
| `speech-wire-check.json` | 0 | `af0dfedeb836c6a8…` | `4073f79ef25c4796…` | 1000 / 11514 | `speech` |
| `twin-wire-check.json` | 0 | `ec55b6af1e8fd602…` | `4073f79ef25c4796…` | 1000 / 11514 | `speech` |
| `speech-state-wire-check.json` | 0 | `4018c16042cecd0f…` | `4073f79ef25c4796…` | 1000 / 11514 | `speech+state` |

The system message resolves to `4073f79e…37db` on every arm — **byte-identical to KC-S1b's**, which
is what makes the contrast against KC-S1b's sealed rows a one-factor contrast. The config hashes
differ per arm because the query source rides the hash, so no two of these cells can be flown as
each other.

**These were run from the worktree `wt-kus3`, so the SEAL half is SKIPPED**:
`scripts/flights/run_slurp_closed_list_cell.py` pins `REPO` to the main checkout by design and
refuses to import anywhere else. The seal half runs on master before takeoff, per section 9 of the
preregistration.

**What the first attempt caught.** Before the knobs were corrected, the harness refused the check
with "this cell declares phase_supply but not one request carried a typed knowledge block; the
supply never reached the wire" — the DEV-1000 BLEND lock's `tau 0.65` admits 0 of 100 cross-modal
top-5 candidates, so the cell would have supplied nothing on every row and done so lawfully and
silently. That refusal is why these receipts exist.
