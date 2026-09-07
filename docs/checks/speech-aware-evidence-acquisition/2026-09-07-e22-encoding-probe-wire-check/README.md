# Zero-contact wire checks — the three Earnings-22 encoding probe cells

**ALL SIX CELLS ARE GREEN. Zero model contacts, zero servers, zero sockets.** Six
`core.flight.FlightRuntime.wire_check` runs — the three flight cells at 1,500 rows and their three
4-row smokes — drove the whole request path against `WireCheckGate` and `WireCheckTransport`
(which never opens a socket), and every one reached `seal_and_score: OK`, meaning the run manifest
was written, verified and scored through the **real** registered scorers over the transport's canned
response.

Run under the model-free rows `SAEA-E22-MF-SHORT-CLIP-ENCODING-AUDIT-V1` and
`SAEA-SN-MF-E22-DEV1500-ENCODING-VARIANTS-V1`. No cell is authorized; see
`docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-preregistration.md`.

## What passed

| receipt | run id | rows | contacts | model contacts | servers | payload keys = arm-visible fields | `seal_and_score` |
|---|---|---:|---:|---:|---:|---|---|
| `bx-smoke4-wire-check.json` | `SAEA-E22-DEV-ESB-BX-SMOKE-V1` | 4 | 4 | **0** | **0** | yes (10) | **OK** |
| `bx-full-wire-check.json` | `SAEA-E22-DEV-ESB-BX-V1` | 1,500 | 1,500 | **0** | **0** | yes (10) | **OK** |
| `tail2s-smoke4-wire-check.json` | `SAEA-E22-DEV-ESB-TAIL2S-SMOKE-V1` | 4 | 4 | **0** | **0** | yes (10) | **OK** |
| `tail2s-full-wire-check.json` | `SAEA-E22-DEV-ESB-TAIL2S-V1` | 1,500 | 1,500 | **0** | **0** | yes (10) | **OK** |
| `pad30s-smoke4-wire-check.json` | `SAEA-E22-DEV-ESB-PAD30S-SMOKE-V1` | 4 | 4 | **0** | **0** | yes (10) | **OK** |
| `pad30s-full-wire-check.json` | `SAEA-E22-DEV-ESB-PAD30S-V1` | 1,500 | 1,500 | **0** | **0** | yes (10) | **OK** |

| cell | split id | split identity (flight-computed) | config hash | protocol hash | audio seconds |
|---|---|---|---|---|---:|
| `E22-DEV-ESB-BX` | `E22-ESB-DEV1500-BX-UTTERANCES` | `87d0cc654b05…` | `ffe614090105…` | `dd0be6a78c3d…` | 9,783.571 |
| `E22-DEV-ESB-BX-SMOKE-4` | `E22-ESB-DEV1500-BX1-SMOKE-4` | `0bf6c232bed4…` | `b00e60d8fd36…` | `6ee19994081b…` | 51.260 |
| `E22-DEV-ESB-TAIL2S` | `E22-ESB-DEV1500-TAIL2S-UTTERANCES` | `8dc9d6a04c40…` | `17358fc3f6c4…` | `0fd0d434a166…` | 12,948.983 |
| `E22-DEV-ESB-TAIL2S-SMOKE-4` | `E22-ESB-DEV1500-TS2-SMOKE-4` | `672a0630141e…` | `c7c5dd63dc28…` | `fc6e31915aed…` | 59.701 |
| `E22-DEV-ESB-PAD30S` | `E22-ESB-DEV1500-PAD30S-UTTERANCES` | `2c13bf01e8a4…` | `fa2d6deb021e…` | `c7f6bd149ca9…` | 45,002.880 |
| `E22-DEV-ESB-PAD30S-SMOKE-4` | `E22-ESB-DEV1500-P30-SMOKE-4` | `cfb1a9d55ff1…` | `ec8ea8660516…` | `a38bc34869fc…` | 122.880 |

**Every flight-computed split identity equals the one its dataset fragment declares**, and all six
differ from the sealed dev-v1 population's `c626e62f…`, which is the identity separation
`D-ENC-1` exists to guarantee.

**Three things this proves that the arithmetic could not.** (1) The `@`-suffixed sample ids survive
the whole path: roster hydration, media-path confinement to each variant's own derived root, the
transport payload, the run manifest, and — through
`reproduction.esb_reference.published_segment_key` — the **reference lookup**, on all 1,500 rows of
each variant. (2) `max_tokens` is 1024 with no per-sample cap and no stop string, i.e. the comparator's
decoding params, on every cell. (3) The dispatch pins eight slots on a flight and four on a smoke,
which is the comparator's geometry.

## What the REAL gate does, and why that is also correct

`--dry-run` (the real `contracts.FrozenCoreGate`) was run on all three flight cells. It passes config
composition, roster hydration with a per-file SHA-256 re-hash of all 1,500 media, media-path
confinement, the count check, `ExecutionPlan` construction, the execution-profile check and the WSL
environment assertion, and then **refuses**:

```
GateClosed: model touch refused: run 'SAEA-E22-DEV-ESB-<VARIANT>-V1' has no pre-registered
exposure row in docs/exposure-ledger.md (rows are written before results are read)
```

That is the correct state. These cells are preregistered and **not authorized**; the gate refuses
exactly where an unauthorized cell should be stopped, and everything after that point (E0 closure,
the runtime receipt and GGUF digests, the D1 media-identity rail) is deliberately not exercised
because exercising it would mean pre-registering an exposure row for a cell with no owner GO.

## One operational note worth keeping

`core.scorers._assert_scoring_entry_gate` calls `require_clean_study_repo`, and **that gate refuses
on ANY untracked or modified path, not only the load-bearing surface** — an earlier pass of these
same checks reported `SCORING_FAILED` purely because the wire-check receipts were being written into
this untracked directory while the next check ran. The receipts here were produced with the tree
clean and copied in afterwards. A flight agent writing receipts into the repository mid-campaign will
hit the same wall.
