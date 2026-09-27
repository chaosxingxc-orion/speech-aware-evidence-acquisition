# Two trace-path throughput fixes, priced by measurement and accepted by byte identity

Owner decision 140 made sampling throughput a first-class engineering objective; this note lands its cheapest concrete item, the two findings of `docs/results/2026-09-26-slurp-seal-path-profile.md`: in flight, `core.tracing.TraceSink.emit` opened, appended and closed the trace file per record (7.06 ms per record on the drvfs/9p run root, 355.6 s over ROLL-2's 50,380 records against 8.8 s in one open); at seal, `core.driver.speech_native.read_attempt_trace_facts` pulled the 719 MiB trace through `TextIOWrapper`'s 8 KiB chunks (about 92,000 reads over 9p, 14.6 s of a 37.9 s seal). Both are fixed at commit `90ba94b0` (branch `fable/tracefix`) without moving the run root, and both are accepted the way the profile proved its replay: every reproduced file byte-identical to the sealed one, `verify_bundle` passing, the sealed directory's listing hash identical before and after. Model-free; zero model, server, encoder, scorer or network contacts; one I/O pass at a time beside the live DET flight on port 8080, which was neither started, stopped nor probed.

## 1. What changed, and the flush policy

**`TraceSink.emit`** opens one append handle lazily on the first record (the trace file still does not exist before the first record, so "no file" still means "no records" for every reader and a second sink on the same directory is still refused) and, under a lock, writes the same serialised line plus `"\n"` and calls `flush()`; `close()` closes the handle and writes the trace manifest as before. There is no `fsync` in either form (the profile found none on the trace path; the seal's four whole-file fsyncs are untouched).

The flush policy is **per record**, chosen from what the recovery readers rely on. `core.flight.resume._scan_trace` (E10 resume-recovery, bundle invariant I7r) reads the aborted attempt's trace line by line and refuses the WHOLE predecessor attempt on a single malformed line; `core.driver.speech_native.build_flight_receipt_from_disk` counts an interrupted attempt's contacts from the same file through `read_attempt_trace_facts`. The property both need is therefore: *when `emit` returns, that record is a whole newline-terminated line handed to the kernel, whatever the process does afterwards.* The old per-record `close()` gave exactly that (kernel page cache, no fsync); `flush()` after every write gives the same at the same granularity, and removes only the open/close round trip. A process killed at any instant leaves a trace complete up to the last `emit` that returned, with no torn tail from a Python buffer. `FlightRuntime.abort` does not close the client's sink, so an aborted attempt's trace is, as before, complete to its last returned `emit`.

**`read_attempt_trace_facts`** iterates the file through `io.BufferedReader` with a 64 MiB buffer (C-level `readline`, 13 raw reads for the 719 MiB trace, one line resident at a time) and the per-record accounting moved unchanged into `_trace_facts_from_lines`. Two alternatives were measured on an ext4 copy of the trace and rejected: text mode with a 64 MiB buffer still issued 92,039 raw reads (`TextIOWrapper` reads 8 KiB chunks regardless of the buffer), and a Python-level block splitter was slower than the old reader on ext4 (2.0 s against 1.45 s). The chosen form is a streaming reader: its own allocation peak is the buffer (64.7 MiB traced, against 0.6 MiB for the old reader), never the whole trace, so the host reserve (owner decision 119) is untouched.

## 2. The sealed bytes were untouched

`scripts/analysis/trace_path_throughput_acceptance.py` (recipe `trace-path-throughput-acceptance-v1`), over the sealed bundle `runs/SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1/attempt-slurp-native-stage3-roll-2-fold-a-v1-generation/` (18 files, 963,583,441 bytes, v9fs), read-only; scratch targets created and deleted by each pass; the OLD code imported from a `git archive` of `bc507604` (this fix's parent) extracted to an ext4 directory that is also deleted.

| pass | groups | sealed listing sha256 before | after | identical | scratch deleted |
| --- | --- | --- | --- | ---: | ---: |
| mount (v9fs) | patterns | `f8bf9323f5cde37f...` | `f8bf9323f5cde37f...` | yes | yes |
| mount (v9fs) | classes | `f8bf9323f5cde37f...` | `f8bf9323f5cde37f...` | yes | yes |
| mount (v9fs) | readers + seal | `f8bf9323f5cde37f...` | `f8bf9323f5cde37f...` | yes | yes |
| ext4 | all | `f8bf9323f5cde37f...` | `f8bf9323f5cde37f...` | yes | yes |

(The profile's listing hash was `e1d5bbedeefaf8c3...`; the directory has since gained its score files, which is why the listing hash differs from the profile's while the artifact hashes below are the profile's exactly.)

## 3. Byte identity, old against new

| what | old | new | sealed | identical on mount | identical on ext4 |
| --- | --- | --- | --- | ---: | ---: |
| trace, real `TraceSink` replay of the 50,380 sealed records (emit in order, then `close()`) | `bcece87d800e48d2...` | `bcece87d800e48d2...` | `bcece87d800e48d2...` | yes | yes |
| trace manifest written by that `close()` | `25f22d4dab595296...` | `25f22d4dab595296...` | `25f22d4dab595296...` | yes | yes |
| trace, pure write pattern (per-record open/close against one open + flush per record) | `bcece87d800e48d2...` | `bcece87d800e48d2...` | `bcece87d800e48d2...` | yes | yes |
| facts object of `read_attempt_trace_facts` (canonical JSON sha256) | `1166aea39e22fadf...` | `1166aea39e22fadf...` | -- | equal | equal |
| `outputs.jsonl` (seal writer expression) | -- | `d8c51e137aea8e9f...` | `d8c51e137aea8e9f...` | yes | yes |
| `phases.json` (seal writer expression) | -- | `fe82722fdaa10b44...` | `fe82722fdaa10b44...` | yes | yes |
| `flight-receipts.json` (`write_flight_receipts`) | -- | `9bff6e94e451adb7...` | `9bff6e94e451adb7...` | yes | yes |
| `verify_bundle` on the path-rewritten generation manifest | -- | verified, 1080 rows, FINALIZED | -- | pass | pass |

The facts object is label-free and is recorded in the artefacts: 8,996 requests / 8,996 responses / 8,996 cost records, 1,080 distinct sample ids and packet ids, 0 speech-query failures, max prompt tokens 13,851, max completion tokens 512.

## 4. Old against new, in the profile's units

In flight (the trace append; 50,380 records, 719 MiB):

| form | target | wall s | ms per record | MiB/s |
| --- | --- | ---: | ---: | ---: |
| old pattern: open/append/close per record | mount | 414.30 | 8.224 | 1.7 |
| new pattern: one open, write + flush per record | mount | 11.20 | 0.222 | 64.2 |
| old pattern | ext4 | 1.33 | 0.026 | 542.3 |
| new pattern | ext4 | 0.52 | 0.010 | 1372.2 |
| old `TraceSink` (validation + serialisation + write) | mount | 420.49 | 8.346 | -- |
| new `TraceSink` | mount | 49.26 | 0.978 | -- |
| old `TraceSink` | ext4 | 25.17 | 0.500 | -- |
| new `TraceSink` | ext4 | 25.06 | 0.498 | -- |

The mount figures were taken beside the live flight, which is why the old pattern reads 414 s here against the profile's 356 s; the gain is 37x on the pure pattern and 8.5x through the real class, whose remaining 49 s is about 25 s of record validation and canonical serialisation common to both forms (the ext4 rows, where I/O is nearly free, show the two classes equal). Spread over a flight this recovers about 6 to 7 minutes of the trace's growth time on the mount.

At seal (the trace-facts pass; the nine seal stages replayed with the new code):

| stage | mount old s | mount new s | ext4 old s | ext4 new s |
| --- | ---: | ---: | ---: | ---: |
| `read_attempt_trace_facts` (subprocess, own tree) | 19.64 | 7.95 | 1.59 | 1.65 |
| `trace_facts_scan` (in-process, new) | -- | 7.32 | -- | 1.60 |
| seal total, nine stages, new code | -- | 39.61 | -- | 18.82 |

The profile's `trace_facts_scan` was 15.8 s on the mount against 1.3 s on ext4; here the old reader took 19.6 s under the flight's contention and the new one 7.95 s, in line with the ~4 s `read_bytes` pays for the same file plus the JSON parse. On ext4 the two readers are equal within noise (1.59 s against 1.65 s; 1.40 s against 1.40 s in an earlier readers-only pass). The remaining seal cost is the CPU the profile already named (`verify_bundle` 20.4 s on the mount, 13.5 s on ext4; the pure-Python indent encoder on `phases.json`) and the bandwidth-shaped hashing and writes.

Reader memory: traced allocation peak of the read call 64.7 MiB (new) against 0.6 MiB (old); both worker processes report the same 0.816 GiB peak RSS, which is the `speech_native` import baseline, not the read.

## 5. Tests and gates

`tests/unit/test_trace_sink.py`: byte identity of the new sink against the per-record pattern on a fixture with non-ASCII, escaped-newline and 100 KB payloads; lazy file creation and visibility before `close()`; four concurrent emitters with no torn line; a SIGKILLed child process leaving exactly the records whose `emit` returned (40 records, seven of them 70,000 characters, every line whole, no manifest), with a control showing that a buffered handle without a per-record flush loses records under the same kill. `tests/unit/test_speech_native_finalize_from_disk.py`: identical lines from the two line sources at buffer sizes 1, 3, 7, 64, 4096 and 64 MiB (multi-byte characters straddling every boundary), identical facts, a final unterminated line, an empty file, and identical refusals (blank line, non-UTF-8 bytes, missing file). Suites run in the worktree with `PYTHONPATH` pinned to it and the imported package asserted: 619 passed, 1 skipped over the flight, runtime, bundle, trace, receipt, resume and contract suites. `bash scripts/flights/batch/main_gates_generic.sh` (all seven) exit 0 verbatim on the main checkout and the same seven checks exit 0 against the worktree.

## 6. Artefacts

Under `SPEECHRL_DATA_DIR/analysis/SAEA-TRACE-PATH-FIX-V1/`:

| file | sha256 |
| --- | --- |
| `acceptance-mount-patterns.json` | `04cacb0d5da6a78d539280eb4155bba8a4d82f59e350111e1ced79832dd51d18` |
| `acceptance-mount-classes.json` | `611e39b1b3771bcc8d90343c807922ff5cfce1ad2c1b8533c2ad06f7a73ad64b` |
| `acceptance-mount-readers.json` | `c1e9975e8860327aeab67232073c692bdb68e62da426047238ed6c00b0c8fe5f` |
| `acceptance-ext4.json` | `f370c39821b36b56962612a401479a03284c89e26db9775b2bb0beee815ab1fb` |

Passes generated 2026-09-27T05:49:36Z to 06:09:10Z at tree `90ba94b0`; timings are measurements of their pass, everything else is deterministic.
