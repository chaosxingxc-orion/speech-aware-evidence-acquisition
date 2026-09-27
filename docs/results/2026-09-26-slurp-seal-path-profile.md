# Profile of the seal path: what the drvfs mount owns, measured over ROLL-2's sealed bundle

During the ROLL-2 flight the run directory grew at about 1.5 MB/s into two large files while `/mnt/e` (drvfs over 9p) writes sequentially at about 164 MB/s and ext4 at about 1,590 MB/s, so the coordinator asked whether the seal is mount-bound before moving the run root to ext4. This note profiles one complete offline replay of the seal writer's stages over the sealed bytes of `SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1` (919 MiB in the attempt directory; trace 719 MiB, 50,380 records; 1,080 rows x 5 samples), to a scratch directory on the mount and to one on ext4, with `cProfile`. Measurement only: nothing about the flight machinery is changed.

**Method.** `scripts/analysis/slurp_seal_path_profile.py` (recipe `slurp-seal-path-profile-v1`). `FlightRuntime.seal()` needs a live composed flight, so it is not invoked; every stage it performs on the run directory is re-run with the repository's own functions where they take a path (`write_json_artifact`, `sha256_file`, `verify_bundle`, `seal_scoring_inputs`, `read_attempt_trace_facts`, `write_flight_receipts`) and with the exact writer expressions of `seal()` for `outputs.jsonl` and `phases.json`. The in-flight trace growth (`TraceSink.emit`: open-append-close per record) is replayed separately, once per record and once per file. Every reproduced file is hashed against the sealed artifact's sha256. Official scoring is a scorer contact and is not part of the profile (the deferred-scoring seal ends at `seal_scoring_inputs`; the scorer runs later in the score worker). Zero model, server, encoder, tokenizer, scorer, GPU or network contacts; single-threaded; each target profiled on its own, wall pass then `cProfile` pass, one process at a time, beside the live flight on port 8080 (which was neither started, stopped nor probed). Timings vary between runs; hashes, sizes, counts and byte-identity flags are deterministic.

## 0. The sealed bytes were untouched

| target | pass | invocation | files | bytes | listing sha256 before | after | identical | scratch deleted |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| mount | wall | -- | 18 | 963,583,441 | `e1d5bbedeefaf8c3...` | `e1d5bbedeefaf8c3...` | yes | yes |
| ext4 | wall | -- | 18 | 963,583,441 | `e1d5bbedeefaf8c3...` | `e1d5bbedeefaf8c3...` | yes | yes |
| mount | cprofile | inflight | 18 | 963,583,441 | `e1d5bbedeefaf8c3...` | `e1d5bbedeefaf8c3...` | yes | yes |
| mount | cprofile | seal | 18 | 963,583,441 | `e1d5bbedeefaf8c3...` | `e1d5bbedeefaf8c3...` | yes | yes |
| ext4 | cprofile | -- | 18 | 963,583,441 | `e1d5bbedeefaf8c3...` | `e1d5bbedeefaf8c3...` | yes | yes |
| mount | wall | repeat | 18 | 963,583,441 | `e1d5bbedeefaf8c3...` | `e1d5bbedeefaf8c3...` | yes | yes |
| ext4 | wall | repeat | 18 | 963,583,441 | `e1d5bbedeefaf8c3...` | `e1d5bbedeefaf8c3...` | yes | yes |

Scratch targets: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-SEAL-PATH-PROFILE-V1/scratch-mount` (v9fs); `/home/chao/saea-worktrees/.decomp-scratch/seal-profile-ext4` (ext2/ext3); `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-SEAL-PATH-PROFILE-V1/scratch-mount-rep` (v9fs); `/home/chao/saea-worktrees/.decomp-scratch/seal-profile-ext4-rep` (ext2/ext3). Sealed directory filesystem: v9fs.

## 1. Every reproduced artifact is byte-identical to the sealed one

| stage | target | bytes written | sha256 equals sealed | sha256 |
| --- | --- | ---: | ---: | ---: |
| trace_append_per_record | mount | 753,967,799 | yes | `bcece87d800e48d2` |
| trace_append_per_record | ext4 | 753,967,799 | yes | `bcece87d800e48d2` |
| trace_append_batched | mount | 753,967,799 | yes | `bcece87d800e48d2` |
| trace_append_batched | ext4 | 753,967,799 | yes | `bcece87d800e48d2` |
| outputs_write | mount | 15,215,195 | yes | `d8c51e137aea8e9f` |
| outputs_write | ext4 | 15,215,195 | yes | `d8c51e137aea8e9f` |
| phases_write | mount | 159,728,458 | yes | `fe82722fdaa10b44` |
| phases_write | ext4 | 159,728,458 | yes | `fe82722fdaa10b44` |
| trace_manifest_write | mount | 5,409,338 | yes | `25f22d4dab595296` |
| trace_manifest_write | ext4 | 5,409,338 | yes | `25f22d4dab595296` |
| flight_receipts_write | mount | 27,417,107 | yes | `9bff6e94e451adb7` |
| flight_receipts_write | ext4 | 27,417,107 | yes | `9bff6e94e451adb7` |
| manifest_hashing | mount | 774,593,901 | yes | -- |
| manifest_hashing | ext4 | 774,593,901 | yes | -- |

`verify_bundle` on the path-rewritten generation manifest: mount: verified, 1080 rows, attempt state FINALIZED; ext4: verified, 1080 rows, attempt state FINALIZED.

## 2. Wall time per stage, mount against ext4

| stage | kind | MiB | mount s | ext4 s | mount - ext4 s | mount share of stage % | MiB/s mount | MiB/s ext4 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sealed_trace_read | input | 719.0 | 2.725 | 2.796 | -0.071 | -2.6 | 263.8 | 257.2 |
| trace_append_per_record | in-flight | 719.0 | 355.647 | 0.729 | 354.918 | 99.8 | 2.0 | 986.3 |
| trace_append_batched | in-flight | 719.0 | 8.820 | 0.452 | 8.368 | 94.9 | 81.5 | 1591.9 |
| outputs_write | seal | 14.5 | 0.323 | 0.134 | 0.189 | 58.4 | 45.0 | 108.2 |
| phases_write | seal | 152.3 | 3.011 | 2.229 | 0.782 | 26.0 | 50.6 | 68.3 |
| trace_manifest_write | seal | 5.2 | 0.122 | 0.059 | 0.063 | 51.5 | 42.3 | 87.3 |
| manifest_hashing | seal | 738.7 | 3.501 | 0.421 | 3.080 | 88.0 | 211.0 | 1755.1 |
| run_manifest_write | seal | 0.1 | 0.012 | 0.001 | 0.011 | 94.1 | 4.5 | 77.3 |
| verify_bundle | seal | 738.7 | 13.960 | 11.768 | 2.192 | 15.7 | 52.9 | 62.8 |
| seal_scoring_inputs | seal | 0.1 | 0.047 | 0.006 | 0.042 | 87.7 | 1.2 | 9.5 |
| trace_facts_scan | seal | 719.0 | 15.848 | 1.296 | 14.552 | 91.8 | 45.4 | 554.6 |
| flight_receipts_write | seal | 26.1 | 1.125 | 0.768 | 0.357 | 31.7 | 23.2 | 34.0 |
| **seal total** (the nine seal stages) | seal | -- | **37.949** | **16.683** | 21.266 | 56.0 | -- | -- |

`phases_write` splits into serialise + write: mount 1.99 s + 1.02 s, ext4 2.04 s + 0.19 s; the serialisation is `json.dumps(indent=2)`, which is the pure-Python encoder because `indent` disables the C encoder.

Variability: a second wall pass per target (a live flight shares the host and the mount, so single passes carry its noise):

| stage | mount pass 1 s | mount repeat s | ext4 pass 1 s | ext4 repeat s |
| --- | ---: | ---: | ---: | ---: |
| sealed_trace_read | 2.725 | 4.109 | 2.796 | 2.570 |
| trace_append_per_record | 355.647 | -- | 0.729 | 0.535 |
| trace_append_batched | 8.820 | 5.695 | 0.452 | 0.313 |
| outputs_write | 0.323 | 0.236 | 0.134 | 0.088 |
| phases_write | 3.011 | 2.570 | 2.229 | 1.867 |
| trace_manifest_write | 0.122 | 0.144 | 0.059 | 0.054 |
| manifest_hashing | 3.501 | 2.963 | 0.421 | 0.280 |
| run_manifest_write | 0.012 | 0.016 | 0.001 | 0.001 |
| verify_bundle | 13.960 | 14.649 | 11.768 | 11.426 |
| seal_scoring_inputs | 0.047 | 0.043 | 0.006 | 0.007 |
| trace_facts_scan | 15.848 | 13.059 | 1.296 | 1.988 |
| flight_receipts_write | 1.125 | 0.920 | 0.768 | 1.161 |

## 3. The in-flight trace append: per-record open/close against one open

| pattern | target | records | wall s | ms per record | MiB/s | bytes identical |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| trace_append_per_record | mount | 50,380 | 355.65 | 7.059 | 2.0 | yes |
| trace_append_per_record | ext4 | 50,380 | 0.73 | 0.015 | 986.3 | yes |
| trace_append_batched | mount | 50,380 | 8.82 | 0.175 | 81.5 | yes |
| trace_append_batched | ext4 | 50,380 | 0.45 | 0.009 | 1591.7 | yes |

`TraceSink.emit` has no `fsync`; its per-record cost is the open/append/close round trip. On the mount the per-record pattern costs 7.06 ms per record against 0.175 ms batched (346.8 s of open/close overhead over the whole trace); on ext4 0.015 ms against 0.009 ms. Both patterns write the identical bytes. This is in-flight cost spread over the hours of the flight, not seal cost: at the flight's contact rate it is a fixed few milliseconds per record on the mount.

## 4. Where the time goes inside each stage (`cProfile`, tottime by category)

Categories: `io.read` / `io.write` are the C-level read and write calls; `io.open/close/stat` the open, close, stat, replace and lock calls (the 9p round trips); `fsync` is `os.fsync`; `json.encode` / `json.decode` are the `json` package's encoder and decoder frames (the pure-Python indent encoder lands here too); `hash` is `hashlib`; `boundary/validate` is `contracts.boundary` (`TraceRecord.validate` and the information-boundary walk); `bundle.python` is the repository's own bundle / flight / driver frames; `other` is interpreter overhead, `str.split`, decoding and the like. `for line in file` iteration is not a recorded call, so in `trace_facts_scan` the raw read hides in `other`. Shares are of the profiled pass's own tottime; the profiled pass is slower than the wall pass wherever Python frames dominate.

**mount** (profiled pass; wall of the profiled pass in the first column):

| stage | wall s | tottime s | io.read | io.write | io.open/close/stat | fsync | json.encode | json.decode | hash | boundary/validate | bundle.python | other |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sealed_trace_read | 3.05 | 3.05 | 100.0 | 0.0 | 0.1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| trace_append_per_record | 386.62 | 386.62 | 0.0 | 2.0 | 97.8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.2 |
| trace_append_batched | 4.94 | 4.94 | 0.0 | 94.8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 5.2 |
| outputs_write | 0.29 | 0.29 | 0.0 | 59.7 | 0.9 | 0.0 | 37.7 | 0.0 | 0.0 | 0.0 | 0.0 | 1.7 |
| phases_write | 10.67 | 10.67 | 0.0 | 9.1 | 0.0 | 0.0 | 82.7 | 0.0 | 0.0 | 0.0 | 0.0 | 8.1 |
| trace_manifest_write | 0.21 | 0.21 | 17.6 | 11.2 | 6.7 | 0.0 | 57.8 | 0.0 | 0.7 | 0.0 | 0.3 | 5.7 |
| manifest_hashing | 3.49 | 3.49 | 94.0 | 0.0 | 0.1 | 0.0 | 0.0 | 0.0 | 5.7 | 0.0 | 0.1 | 0.0 |
| run_manifest_write | 0.01 | 0.01 | 3.5 | 1.8 | 85.4 | 0.0 | 7.0 | 0.0 | 0.2 | 0.0 | 0.4 | 1.8 |
| verify_bundle | 27.64 | 27.41 | 14.6 | 0.0 | 0.1 | 0.0 | 15.1 | 8.7 | 1.8 | 17.5 | 1.6 | 40.6 |
| seal_scoring_inputs | 0.04 | 0.04 | 9.3 | 2.6 | 69.5 | 16.0 | 0.2 | 0.0 | 0.4 | 0.0 | 0.7 | 1.4 |
| trace_facts_scan | 20.41 | 20.41 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 8.7 | 0.0 | 0.0 | 88.4 | 2.9 |
| flight_receipts_write | 2.70 | 2.70 | 5.2 | 3.8 | 0.6 | 1.0 | 81.3 | 2.1 | 0.9 | 0.0 | 0.1 | 5.1 |

**ext4** (profiled pass; wall of the profiled pass in the first column):

| stage | wall s | tottime s | io.read | io.write | io.open/close/stat | fsync | json.encode | json.decode | hash | boundary/validate | bundle.python | other |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sealed_trace_read | 4.70 | 4.70 | 99.9 | 0.0 | 0.1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| trace_append_per_record | 0.74 | 0.74 | 0.0 | 39.9 | 40.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 19.9 |
| trace_append_batched | 0.33 | 0.33 | 0.0 | 82.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 17.5 |
| outputs_write | 0.10 | 0.10 | 0.0 | 8.3 | 0.1 | 0.0 | 89.7 | 0.0 | 0.0 | 0.0 | 0.0 | 1.9 |
| phases_write | 9.74 | 9.74 | 0.0 | 2.0 | 0.0 | 0.0 | 90.4 | 0.0 | 0.0 | 0.0 | 0.0 | 7.6 |
| trace_manifest_write | 0.15 | 0.15 | 0.5 | 1.6 | 0.1 | 0.0 | 88.1 | 0.0 | 1.0 | 0.0 | 0.5 | 8.2 |
| manifest_hashing | 0.35 | 0.35 | 31.5 | 0.0 | 0.4 | 0.0 | 0.0 | 0.0 | 67.5 | 0.0 | 0.5 | 0.1 |
| run_manifest_write | 0.00 | 0.00 | 0.8 | 2.5 | 5.8 | 0.0 | 72.4 | 0.0 | 1.5 | 0.0 | 1.7 | 15.4 |
| verify_bundle | 26.68 | 26.41 | 1.5 | 0.0 | 0.0 | 0.0 | 17.2 | 10.0 | 2.0 | 20.1 | 1.7 | 47.3 |
| seal_scoring_inputs | 0.01 | 0.01 | 0.5 | 0.8 | 3.7 | 88.6 | 0.6 | 0.0 | 1.0 | 0.0 | 1.1 | 3.7 |
| trace_facts_scan | 2.10 | 2.10 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 62.7 | 0.0 | 0.0 | 24.2 | 13.0 |
| flight_receipts_write | 2.40 | 2.40 | 0.1 | 0.5 | 0.0 | 0.7 | 89.7 | 2.4 | 1.1 | 0.0 | 0.1 | 5.5 |

Top functions of `verify_bundle` by tottime on mount:

| function | category | tottime s | cumtime s | calls |
| --- | --- | ---: | ---: | ---: |
| `boundary.py:85 assert_information_boundary` | boundary/validate | 4.177 | 12.274 | 5,414,520 |
| `<method 'read' of '_io.BufferedReader' objects>` | io.read | 4.001 | 4.001 | 11 |
| `encoder.py:205 iterencode` | json.encode | 3.955 | 3.955 | 52,541 |
| `<built-in method builtins.isinstance>` | other | 2.768 | 8.052 | 30,499,018 |
| `decoder.py:343 raw_decode` | json.decode | 2.244 | 2.244 | 51,463 |
| `typing.py:1465 __subclasscheck__` | other | 1.680 | 4.847 | 5,629,739 |
| `typing.py:1194 __instancecheck__` | other | 1.120 | 5.967 | 5,629,739 |
| `<built-in method builtins.issubclass>` | other | 1.037 | 2.445 | 5,629,739 |
| `<method 'decode' of 'bytes' objects>` | other | 0.875 | 0.875 | 4 |
| `<frozen abc>:121 __subclasscheck__` | other | 0.775 | 1.408 | 5,629,761 |
| `<built-in method _abc._abc_subclasscheck>` | other | 0.633 | 0.633 | 5,629,761 |
| `<built-in method _hashlib.openssl_sha256>` | hash | 0.455 | 0.455 | 56,866 |

Top functions of `verify_bundle` by tottime on ext4:

| function | category | tottime s | cumtime s | calls |
| --- | --- | ---: | ---: | ---: |
| `boundary.py:85 assert_information_boundary` | boundary/validate | 4.608 | 13.570 | 5,414,520 |
| `encoder.py:205 iterencode` | json.encode | 4.356 | 4.356 | 52,541 |
| `<built-in method builtins.isinstance>` | other | 3.070 | 8.921 | 30,499,006 |
| `decoder.py:343 raw_decode` | json.decode | 2.511 | 2.511 | 51,463 |
| `typing.py:1465 __subclasscheck__` | other | 1.840 | 5.366 | 5,629,739 |
| `typing.py:1194 __instancecheck__` | other | 1.242 | 6.609 | 5,629,739 |
| `<built-in method builtins.issubclass>` | other | 1.148 | 2.724 | 5,629,739 |
| `<method 'decode' of 'bytes' objects>` | other | 1.027 | 1.027 | 4 |
| `<frozen abc>:121 __subclasscheck__` | other | 0.856 | 1.576 | 5,629,761 |
| `<built-in method _abc._abc_subclasscheck>` | other | 0.720 | 0.720 | 5,629,761 |
| `<method 'split' of 'str' objects>` | other | 0.543 | 0.543 | 10,601 |
| `<built-in method _hashlib.openssl_sha256>` | hash | 0.504 | 0.504 | 56,866 |

## 5. The fsync finding

There is no per-record `fsync` anywhere on the seal path or on the in-flight trace path. `os.fsync` is called exactly 3 time(s) in `seal_scoring_inputs`, 1 time(s) in `flight_receipts_write` -- four whole-file syncs per seal, each on a small file (the three scoring-input files) or one atomic 27 MB replace (the flight receipts). Their combined wall on the mount is 1.17 s against 0.77 s on ext4. Batching them is therefore moot: there is nothing per-record to batch, and the per-record cost that does exist (the trace append's open/close) is bytes-neutral to batch, as section 3 shows, but lives in the flight, not in the seal.

## 6. What share of the seal the mount owns

Over the nine seal stages the replay takes **37.9 s on the mount and 16.7 s on ext4**, so the mount owns **21.3 s = 56 % of the seal wall** and the remaining 44 % is CPU that moves with the run root nowhere (the repeat passes read 34.6 s and 16.9 s). The three stages where the mount costs most are `trace_facts_scan` (+14.6 s), `manifest_hashing` (+3.1 s), `verify_bundle` (+2.2 s); the largest stage on ext4 -- pure CPU -- is `verify_bundle` at 11.8 s. But the mount's share is not bandwidth: `trace_facts_scan` alone is +14.6 s of the 21.3 s, and its profile puts 88 % of that time inside `read_attempt_trace_facts`'s own frame -- the `for line in handle` iteration, which pulls the 719 MiB trace through `TextIOWrapper`'s 8 KiB buffer, about 92,000 small reads over 9p. `verify_bundle` reads the same file with `read_bytes` (a few large reads) and pays about 4 s for it. Everything else the mount owns is 6.7 s: whole-file hashing and the large writes at 40-200 MiB/s, i.e. the ~164 MB/s the mount is rated at. The seal writes about 198 MiB (outputs, phases, trace manifest, manifest, receipts) and reads the 719 MiB trace three times (hash, verify, trace facts). The 1.5 MB/s growth seen during the flight is consistent with the trace's per-record open/append/close pattern, which replays at 2.0 MiB/s on the mount while the same bytes stream at 82 MiB/s in one open; it is a round-trip cost, not a bandwidth ceiling. Decision numbers: moving the run root to ext4 saves about 21 s per seal of this size (of which 15 s is one function's small-read pattern that a `read_bytes`-then-split in `read_attempt_trace_facts` would recover without moving anything) and about 5.9 minutes of trace append spread over the flight; it leaves the 17 s of CPU untouched -- `verify_bundle`'s parse, boundary walk and canonical re-serialisation of every trace record, and the pure-Python indent encoder on the 160 MB `phases.json` and 27 MB receipts. Neither code change is made here.

## 7. Artefacts

Under `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SEAL-PATH-PROFILE-V1/`:

| file | sha256 |
| --- | --- |
| `profile-ext4-cprofile.json` | `d1b8c8e72b76f3666394621a9cc7f88867b9897cde4041bea53c2b92b34b3390` |
| `profile-ext4-wall-repeat.json` | `b32d3c72b2a40ae82ded0cc80f498780ebc0eb3a3d0f1293643423c007b73aca` |
| `profile-ext4-wall.json` | `d25d436805922a295e58b3085a918512ba88a1bef4ec04ccc6c97aac9dd8ec7e` |
| `profile-mount-cprofile-inflight.json` | `cab1d8b754299043cf0b9f1a58d4910748405b25a168934a975707f44166f35c` |
| `profile-mount-cprofile-seal.json` | `483a0ce9bc0ab3d0bc4d9524f2b6d5866ce190b93a37c8fecbcbaa35ea01b392` |
| `profile-mount-wall-repeat.json` | `464221232bf2a270ce266171e7989c9245db6a230b2282858bbcff644cc776f3` |
| `profile-mount-wall.json` | `0041e8b3a57c2a34f702f4b234e754c6d2682682a0b395e1678b6a39e1030274` |

Rendered 2026-09-27T05:07:59+00:00 by `slurp-seal-path-profile-v1`; timings are measurements of their pass, everything else is deterministic.
