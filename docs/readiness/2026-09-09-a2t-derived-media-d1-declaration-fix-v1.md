# The A2T derived-media cells declared D1 where the gate does not look

**Model-free repair. Zero model contacts, zero sockets, zero servers, zero GPU. No exposure row is
due for this repair.** Branch `wt/a2t-d1fix` off `173425fc`; commits `ed68ae45` (the declaration)
and `fc2c18d4` (the missing stage). Re-runnable, contactless:

```
python scripts/a2t_input_rate_16k_wire_check.py        # no --write
python scripts/cross_carrier_tail2s_wire_check.py      # no --write
```

---

## 1. The defect

Found by the `@16k` flight agent on 2026-09-09 at its **first real request**, with **zero contacts
spent**. The cell composed, the roster hydrated, the payload bound, the plan validated — and
`contracts/gate_media_identity.py` then refused the very first row:

```
sample 'tier1_direct:000045@16k' (carrier 'audio2tool') has no D1-recorded media identity;
a sample outside D1's identity closure can never be sent to the frozen core
```

The supplement artifacts themselves were sound. `docs/receipts/artifacts/d1-a2t-calibration-400-16k.json`
(`4894d54d...`) carries all 400 `@16k` ids with per-file size, SHA-256, duration and sample rate;
so do the `@16k+ts2` (`172ea2a9...`) and `@ts2` (`4bfc77f0...`) supplements. What was wrong was
**where the fragments said so**.

Two rails read two different keys:

| rail | reader | key it reads |
| --- | --- | --- |
| payload confinement | `core.base.declared_derived_media_roots` (`DERIVED_MEDIA_SUBDIR_KEYS`) | `a2t_calibration_d1_media_supplement` / `..._sha256` — the CARRIER-PREFIXED pair |
| media identity | `core.config.d1_media_supplement_relpath`, called by `core.flight.FlightRuntime.preflight` (`core/flight/runtime.py` ~1708) | `d1_media_supplement` / `d1_media_supplement_sha256` — the PLAIN pair |

All six Audio2Tool derived-media fragments —
`configs/dataset/audio2tool-calibration-400-{16k,16k-tail2s,tail2s}.json` and their `-smoke4`
twins — declared the supplement **only under the prefixed pair**, written that way by
`scripts/build_a2t_input_rate_16k_fragments.py` and
`scripts/build_cross_carrier_tail2s_fragments.py`. Confinement was therefore satisfied (the derived
root was vouched for) while the identity gate was handed `None` and fell back to the base D1
manifest, which of course carries the *unsuffixed* sealed ids and not the `@16k` ones.

Every other fragment that has ever flown with a supplement — the SLURP `@ts2` runtime views, the
Earnings-22 ESB fragments, the A2T org1 / tier-population / evo fragments — carries the plain pair.
These six were the exception, and they were the first six to reach a real request.

## 2. The three blind spots

1. **Preflight-only.** The media-identity gate runs inside `FlightRuntime.preflight`. Nothing
   before a real flight opened it, so the first evidence of the defect was a flight.
2. **Zero-socket wire check.** Both wire checks ran `preflight` and `wire_check` in a
   subprocess and reported "how far each cell gets". For the four `@16k` / `@16k+ts2` cells the
   documented expected stop was `gate-not-authorized` — the exposure gate refusing an
   unregistered row — which is *upstream* of the media-identity gate. A cell that stops for an
   expected reason hides everything downstream of that reason.
3. **The gate was not in the wire check.** `FlightRuntime.wire_check` runs behind a FAKE gate by
   construction (that is what makes it contactless), so the real
   `contracts.gate_media_identity` was never constructed by either check. The
   `payload_binding_stage` added on 2026-09-07 proved confinement — reading the PREFIXED key —
   and reported BOUND for all six cells, which is exactly why a green wire check was not
   evidence.

**This note closes blind spot 3**, and by construction weakens 1 and 2: the media-identity gate is
now constructed by the wire checks themselves, exactly as preflight constructs it, and a cell that
stops early at the exposure gate still gets its identity rail measured.

## 3. The fix

### 3.1 The fragments (through the builders, not by hand)

`scripts/build_a2t_input_rate_16k_fragments.py::dataset_fragment` and
`scripts/build_cross_carrier_tail2s_fragments.py::a2t_dataset` now emit BOTH spellings from the
same source value. A rebuild adds exactly two keys to each of the six fragments and moves nothing
else:

```
+  "d1_media_supplement": "receipts/artifacts/d1-a2t-calibration-400-16k.json",
+  "d1_media_supplement_sha256": "4894d54d7a47084e049379da1d5d38f2c0bde4c4705eb1f24019175670567ba4",
```

The prefixed pair is kept as it was, so `declared_derived_media_roots` keeps working unchanged.

### 3.2 The rule that makes the defect unrepresentable

`core.config.assert_d1_media_supplement_spellings_agree`, called from
`_d1_media_supplement_pair` (so it runs at every consumption, fail-closed):

* a carrier-prefixed spelling whose own `..._sha256` companion is a real lowercase 64-hex digest is
  a **declaration** — the same discriminator `core.base._assert_d1_media_supplement` already uses;
* a declaration must be accompanied by the plain pair, or the config is refused (this is the exact
  state the six fragments were in);
* when both spellings exist they must be **equal**, value for value, or the config is refused;
* **prose** under a prefixed key stays inert — `audio2tool-calibration-400.json`'s
  `"none, by design. All 400 sample ids are already inside the parent D1 identity closure ..."`
  carries no digest, is not a declaration, and is unaffected.

### 3.3 The gate's cheap half

`contracts.gate_media_identity` gains `media_identity_closure_ids` and
`assert_media_identity_closure` — membership over the base D1 manifest plus this gate's own
supplement, opening no media file, so a whole 400- or 1,000-row roster can be checked ahead of any
contact. The supplement is still verified as strictly as the expensive path verifies it (its own
digest, its parent-D1 binding, its manifest hash, its per-entry shape). The refusal sentence now
has one authority, `_no_d1_media_identity`, shared with `verify_media_identity`, so a pre-flight
check can never report a different sentence than the one a flight would die of.

Proof: `tests/contract/test_a2t_derived_media_d1_declaration.py` — the real gate, built exactly as
preflight builds it over the committed supplement artifacts, admits `tier1_direct:000045@16k`,
`tier1_direct:000045@16k+ts2` and `tier1_direct:000045@ts2`, refuses a forged id, and refuses
`tier1_direct:000045@16k` again the moment the supplement is taken away.

## 4. The missing wire-check stage

`rails.core_client.media_identity_stage`, beside `payload_binding_stage`, constructs the REAL
`contracts.FrozenCoreGate` through the same `for_study_repo` call and the same four config-derived
keyword arguments `FlightRuntime.preflight` uses, off the **composed** config (all four fragments —
`runtime_receipt_relpath` and `model_lock_key` live in the model fragment). It then runs both
halves: `assert_media_identity_closure` over **every** roster id, and the production
`verify_media_identity` over the rows the binding stage loads. Zero sockets, zero servers, zero
model contacts; a refusal is returned, never raised.

Both checks now print the stage per cell and exit non-zero when a cell is not identity-closed.
**A cell is wire-ready only if it BINDS and is IDENTITY-CLOSED.**

## 5. The exposure-ledger supersession — READY TO APPLY, NOT APPLIED HERE

The two rows the flight agent registered on 2026-09-09 bind composed hashes that this repair moves.
**Nothing was spent under the old hashes: zero contacts, zero calls, zero audio seconds, zero GPU
hours** — both rows still read `consumed: no`, and the flight refused at its own first request.

The ledger is NOT edited on this branch, because a flight may be closing rows on `master`. Apply the
paragraph below to `docs/exposure-ledger.md` as a dated supersession note, and correct the two rows'
`composed config hash` / `protocol hash` values in place, before the first contact.

> **2026-09-09 — supersession of the two `SAEA-A2T-OFFICIAL-PROTOCOL-16K*` identity hashes.** The
> six Audio2Tool derived-media dataset fragments declared their hash-pinned D1 media supplement only
> under the carrier-prefixed keys `a2t_calibration_d1_media_supplement` / `..._sha256`, which
> `core.base.declared_derived_media_roots` reads for payload confinement, and NOT under the plain
> `d1_media_supplement` / `d1_media_supplement_sha256` pair that `core.config.
> d1_media_supplement_relpath` — and therefore the media-identity gate
> `core.flight.FlightRuntime.preflight` constructs — is the only reader of. Confinement was
> satisfied while the identity gate saw no supplement at all, and
> `contracts/gate_media_identity.py` refused `tier1_direct:000045@16k` as having "no D1-recorded
> media identity" at the first real request. The repair
> (`docs/readiness/2026-09-09-a2t-derived-media-d1-declaration-fix-v1.md`, commits `ed68ae45` and
> `fc2c18d4`) adds the plain pair to all six fragments through their own builders — exactly two keys
> per fragment, nothing else — and refuses any future fragment whose two spellings disagree or whose
> prefixed declaration has no plain twin. The rosters, the media bytes, the D1 supplements, the
> split identity hashes and every other protocol element are UNCHANGED; only the fragment bytes, and
> therefore the composed config hash and the protocol hash derived from it, move.
> `SAEA-A2T-OFFICIAL-PROTOCOL-16K-V1` cell `R-official-16k` moves from composed config hash
> `257a52cd54c136e496208a0a1b96cda8f7071528fe188d706ba3083f26440d5d` / protocol hash
> `e6158e792c9b477294b8234ab5736d7254cd4984ea4281dcdbeee2396cac2abc` to
> `425b69b3f5a6f1335576630b5b86c98c8a6bad49a755caa43758a51459e0dbb2` /
> `02d56d68fc7eb7835f336ccda6595874f74058866a7b2388d7815da49219fe2f`.
> `SAEA-A2T-OFFICIAL-PROTOCOL-16K-SMOKE-V1` cell `R-official-16k-smoke-4` moves from
> `4fa636b14c326f8df31321940cb05d3ea6af88e0be9598913a206f1648e43895` /
> `1650c041104ee76dce57322b15322cfe1af66b41f402ab83cb802bcbaa6e13ee` to
> `2436b8bdfc361de183390f1e3a6ddda10c680b32199b4c6213be0301816462bf` /
> `c2ea5a8b73e0117cead7456861cfb2c955083c3c88f91dc490c921c0a289293d`. ZERO CONTACTS WERE SPENT
> UNDER THE OLD HASHES: both rows were registered and committed before the first contact, the first
> contact never happened, and both remain `consumed: no` with their full budgets intact. THE FLIGHT
> AGENT RE-REGISTERS AT THE NEW HASHES BEFORE THE FIRST CONTACT — the two rows carry the corrected
> values above, and a run whose composed config hash does not equal the value its own row states is
> not authorized by that row. Neither the split identity hashes
> (`292b7220...` for the 400-row cell, `69e44284...` for the smoke) nor the media exposure row
> `SAEA-SN-MF-A2T-CAL400-16K-MEDIA-V1` nor any budget changes.

## 6. Old and new hashes

Rosters and split identity hashes are **unchanged** — no id set moved, no media byte moved. Only the
six dataset fragments' bytes moved, and with them each cell's composed config hash and the protocol
hash derived from it (`core.config.protocol_hash(config_hash, arm, split_identity_hash)`, arm
`bare-core` throughout).

### 6.1 Cells

| run id | cell | old config hash | new config hash | old protocol hash | new protocol hash | registered? |
| --- | --- | --- | --- | --- | --- | --- |
| `SAEA-A2T-OFFICIAL-PROTOCOL-16K-V1` | `R-official-16k` | `257a52cd54c136e496208a0a1b96cda8f7071528fe188d706ba3083f26440d5d` | `425b69b3f5a6f1335576630b5b86c98c8a6bad49a755caa43758a51459e0dbb2` | `e6158e792c9b477294b8234ab5736d7254cd4984ea4281dcdbeee2396cac2abc` | `02d56d68fc7eb7835f336ccda6595874f74058866a7b2388d7815da49219fe2f` | YES, 2026-09-09, unconsumed |
| `SAEA-A2T-OFFICIAL-PROTOCOL-16K-SMOKE-V1` | `R-official-16k-smoke-4` | `4fa636b14c326f8df31321940cb05d3ea6af88e0be9598913a206f1648e43895` | `2436b8bdfc361de183390f1e3a6ddda10c680b32199b4c6213be0301816462bf` | `1650c041104ee76dce57322b15322cfe1af66b41f402ab83cb802bcbaa6e13ee` | `c2ea5a8b73e0117cead7456861cfb2c955083c3c88f91dc490c921c0a289293d` | YES, 2026-09-09, unconsumed |
| `SAEA-A2T-OFFICIAL-PROTOCOL-16K-TAIL2S-V1` | `R-official-16k-tail2s` | `8c4090f85434775a880c9d2997cab503166c90cb8911baa60111dd51f784e077` | `e377072ddde72060372bd4fd29f9cf279037c8d1e5eb109c3147bf2f805d39e3` | `32b7885bd613d9afe29413d66349e4a21a0bf7881700c50c6a400b11bc9ac9e0` | `01048b34c4f7ad1f7aabf65e46bccc5d34f870668000c40816ad6f14e2ee7e79` | no |
| `SAEA-A2T-OFFICIAL-PROTOCOL-16K-TAIL2S-SMOKE-V1` | `R-official-16k-tail2s-smoke-4` | `f92a58b759e176b3d46627730799e740b825eaf4904d54da5877e2ee28405c48` | `5d7eddcb991197f129de746b918c5cdb9a688a787aa826cfbf79e3edf9504bbd` | `88adf1f3ed0305cb163d6d925453aaf3f9f9425a71ec20e9f54f1117cb53c936` | `e3cb6223c1faf2371abe393b2cca939e48a4925c716938227b77aeac38c89a5f` | no |
| `SAEA-A2T-OFFICIAL-PROTOCOL-TAIL2S-V1` | `R-official-tail2s` | `9b789b3ccf2b181c82e46e967b9f82f3cc9c86a012ab5fe36a3da2713456ffad` | `b9ef1ea43292aaec4ed6cbfd08545cfc4cdafa3a44c25afbad6074f677fde6ca` | `c4c930f2027aec87ac17064cf0029bafffe32fd8cbb0c868867a9d23a30088d2` | `79dc012c35d89fecd469bc00a612d309207cf6296d9735253abb9b3dfb372bb6` | no |
| `SAEA-A2T-OFFICIAL-PROTOCOL-TAIL2S-SMOKE-V1` | `R-official-tail2s-smoke-4` | `7eeeb2ae6571a6e3abceee064ce4ea6daf581e845dc927da04c206233ac368f3` | `b984f2241ee0cffa9bec0843956a2011c71044d3fdeb97c4eeb747a76f4703b5` | `5ea6ab67fd78e2e69b2b41fa1b19543d6101b300674ea64669dfb374e7548cf6` | `58d1fa8a74b7e61ac53209308a70325bae5e102cff4a74070b0265091428eefc` | no |

The four unregistered cells have no ledger row to correct; they inherit the corrected hashes when
their own rows are written. The SLURP `@ts2` cells (`slurp-dev1000-closed-list-tail2s{,-smoke-4}-v1`)
are untouched: their runtime views always carried the plain pair.

### 6.2 Fragments

| dataset fragment | old SHA-256 | new SHA-256 |
| --- | --- | --- |
| `configs/dataset/audio2tool-calibration-400-16k.json` | `8f4595aa5ba4c6f6472f288b1558cea9e1eac39f5e0417213fd38485e1f6177c` | `f86d60fcaf39b4e0df62228f20806b2a81d1aa9f3df065890c1da8bf0a5a5734` |
| `configs/dataset/audio2tool-calibration-400-16k-smoke4.json` | `569c7beae971b9f9ef99697e8b35e309ef5e56ae8fe3b8809d597541578c1ca3` | `0f89d2fd33c560ddc1546b078950e33310a6a120d8628141072b2718ca7f942b` |
| `configs/dataset/audio2tool-calibration-400-16k-tail2s.json` | `1b9902199bfbcc18d5e5868f04a13a40c572ad46ee96c6fbeec934628766264f` | `2a72e182e26469dc780fe6863f44f03984a019ae43d05a12a4f0ea2a394e75b2` |
| `configs/dataset/audio2tool-calibration-400-16k-tail2s-smoke4.json` | `d3c86ee422b8e28d173689f54cc1a5a16ad376046bb53fc96716be1e162355fe` | `d9afa74fff7cb54fe33b93fe6b91bb6d8824877838cf235be3d25c439ee30496` |
| `configs/dataset/audio2tool-calibration-400-tail2s.json` | `c06eaabd4b88c0511adf2b0d5d936fe0be54d1f4b101b2451b06f4a68acac9d9` | `c02aa4c258b0838fa874bb44852b25e881fd9b9275df446c2077b0f1b8ba1632` |
| `configs/dataset/audio2tool-calibration-400-tail2s-smoke4.json` | `6970b65bf38b1bad9ce12eefde963b8edbc2264c6ca907450b68012373ad5d25` | `0066555a22f227b340660ead512fe7151f627a2dde6cd9723fe490a36def37be` |

The two sealed 2026-09-07 wire-check receipts are **not** rewritten to hide the move: each fragment
suite records the pre-fix digests explicitly and asserts the change is bounded to the declaration
fix (`SUPERSEDED_BY_THE_D1_DECLARATION_FIX` in `tests/unit/test_a2t_input_rate_16k_fragments.py`
and `tests/unit/test_cross_carrier_tail2s_fragments.py`).

## 7. Measured wire-check state

`python scripts/a2t_input_rate_16k_wire_check.py` and
`python scripts/cross_carrier_tail2s_wire_check.py`, both **without** `--write`, on a clean
`wt/a2t-d1fix` at `fc2c18d4`. Zero model contacts, zero sockets, zero servers, zero GPU.

| check | cell | payload binding | **media identity** | roster ids checked | closure ids | rows byte-verified | preflight | wire_check |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `a2t_input_rate_16k` | `R-official-16k-smoke-4` | BOUND 4/4 | **IDENTITY-CLOSED** | 4 | 800 | 4 | rc=0 `none` | rc=0 `none` |
| `a2t_input_rate_16k` | `R-official-16k` | BOUND 2/400 | **IDENTITY-CLOSED** | 400 | 800 | 2 | rc=0 `none` | rc=0 `none` |
| `a2t_input_rate_16k` | `R-official-16k-tail2s-smoke-4` | BOUND 4/4 | **IDENTITY-CLOSED** | 4 | 800 | 4 | rc=1 `gate-not-authorized` | rc=0 `none` |
| `a2t_input_rate_16k` | `R-official-16k-tail2s` | BOUND 2/400 | **IDENTITY-CLOSED** | 400 | 800 | 2 | rc=1 `gate-not-authorized` | rc=0 `none` |
| `cross_carrier_tail2s` | `R-official-tail2s-smoke-4` | BOUND 4/4 | **IDENTITY-CLOSED** | 4 | 800 | 4 | rc=1 `gate-not-authorized` | rc=0 `seal-and-score-not-ok` |
| `cross_carrier_tail2s` | `R-official-tail2s` | BOUND 2/400 | **IDENTITY-CLOSED** | 400 | 800 | 2 | rc=1 `gate-not-authorized` | rc=0 `seal-and-score-not-ok` |
| `cross_carrier_tail2s` | `closed-list-tail2s-smoke-4` (SLURP) | BOUND 4/4 | **IDENTITY-CLOSED** | 4 | 9,690 | 4 | rc=1 `gate-not-authorized` | rc=0 `seal-and-score-not-ok` |
| `cross_carrier_tail2s` | `closed-list-tail2s` (SLURP) | BOUND 2/1000 | **IDENTITY-CLOSED** | 1,000 | 9,690 | 2 | rc=1 `gate-not-authorized` | rc=0 `seal-and-score-not-ok` |

Reading the table:

* **Every cell is now BOUND *and* IDENTITY-CLOSED.** A closure of 800 for Audio2Tool is the 400
  sealed base-D1 media entries plus the 400 the variant's own supplement adds; 9,690 is SLURP's.
  The `verified` column is the expensive half — those rows' files were re-measured against D1's
  recorded size and SHA-256 and matched.
* **The two registered `@16k` cells now pass preflight end to end (`rc=0`)** on a clean tree. That
  is the direct proof the defect is gone: the same `FlightRuntime.preflight` that refused
  `tier1_direct:000045@16k` on 2026-09-09 now completes, gate included. The other six cells still
  stop at `gate-not-authorized`, which is correct — they have no exposure row.
* **The ledger does not machine-check the composed hashes.** `contracts.ledger` /
  `gate_exposure` read the run id, split role, split identity hash, budgets and the consumed flag;
  the `composed config hash` / `protocol hash` values live in the row's prose. That is exactly why
  section 5's correction must be applied by hand and cannot be relied on to fail loudly: the two
  `@16k` cells pass preflight today while their rows still state the pre-fix hashes.
* `seal-and-score-not-ok` on the four cross-carrier cells is a **pre-existing** state, not a
  product of this repair — see section 9.

## 8. What this authorizes

**Nothing.** No contact, no server, no scoring, no Stage-3 activity. The six cells still hold their
own preregistration and owner GO; the four unregistered ones still have no exposure row. This note
is a repair record and a ready-to-apply ledger correction, and it grants no contact authority of its
own.

## 9. Known, pre-existing, out of scope

Two assertions in `tests/unit/test_cross_carrier_tail2s_fragments.py` fail at `173425fc` and still
fail here, unrelated to this repair (verified by running them against a clean `git archive HEAD`
extraction):

* `test_emitting_twice_reproduces_every_committed_fragment` — the committed
  `configs/experiment/slurp-dev1000-closed-list-tail2s{,-smoke-4}-v1.json` declare
  `baseline_fragment: "slurp-direct-closed-list-tail2s"` while
  `scripts/build_cross_carrier_tail2s_fragments.py` still emits `"slurp-direct-closed-list"`. The
  builder is stale against a later hand edit. **A rebuild of that script with `--write` therefore
  reverts a live SLURP cell's baseline fragment** — it was reverted by hand during this repair and
  the two experiment fragments are byte-identical to `173425fc`. Whoever owns those SLURP cells
  should re-point the builder; this branch deliberately does not.
* `test_every_wire_check_stop_is_one_of_the_named_preconditions` — the committed 2026-09-07
  cross-carrier receipt records `stop_class: "none"` for both SLURP cells where the test expects
  `slurp-packet-root-missing`.

A third pre-existing state, visible in section 7 but not a test failure: all four
`cross_carrier_tail2s` cells now end at `seal_and_score=SCORING_FAILED`
(`1 of 1 scoring job(s) failed`; the job's own error is `official scorer exited with status 1`)
where the sealed 2026-09-07 receipt recorded `none`. The seal half is downstream of, and reads
nothing from, the media-identity or payload-binding rails — this repair does not touch it, and the
same status reproduces for a single cell driven directly through
`scripts/flights/run_calibration_cell.py --wire-check`. Whoever owns the Audio2Tool official
scorer should read it; this branch deliberately does not.
