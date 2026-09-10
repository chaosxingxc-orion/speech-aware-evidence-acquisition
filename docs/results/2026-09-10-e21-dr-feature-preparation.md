# E21 DR full-window feature preparation

The registered offline GPU encoding completed all 1,593 unique windows from
44 discovery calls. Both planned DR draft-source groups will share these
features. This is feature preparation only; no DR task-quality result or
official score was produced.

## Completed contact

- Run: SAEA-E21-DR-FULL-WINDOW-GPU-ENCODING-V1.
- Attempt: attempt-20260910-dr-full-window-gpu-encoding-v1.
- Frozen encoding implementation: 942ff9ae.
- Session: serving-e21-dr-full-window-gpu-encoding-v1.
- Actual build: cddb000cb45ab44d33c84483cf5e5962cbbaa5bf.
- Encoding artifact: analysis/SAEA-E21-DR-FULL-WINDOW-GPU-ENCODING-V1/window-encoding.json.
- Artifact SHA256: 821a591aa5d176a13dc12954e5cad01596dcd4915a0a0b7a5fe1f57ba5a85936.
- Successful contacts and feature-output entries: 1,593 each.
- Speech presented: 141,345.8526875 seconds, with duplicate preparation avoided.
- One-token responses: 1,593 completion tokens; no task answer is inferred from them.
- Sum of client request latency: 2,353.8263 seconds.
- No automatic retry, extra performance probe or encoding replay occurred.

The immutable full input inventory remains bound by file SHA256
7b12a5c32654855701c48b57152ab1643e0c776b9a7a3853fda009a6ac78face.
The two source-draft bindings passed the shared predecessor loader: each covers
44 calls and 1,593 windows, with identical window identities and time spans.
The content-free readiness receipt is coordination/e21-dr-predecessor-readiness.json,
SHA256 8cdac78ae181796a1f81accab4090b5ffa0f7bcb87a830e59f8f58bc177cea46.

## Resource observations

The ten-second monitor covers 3,560.71 seconds. Its mean GPU utilization is
26.67%, with 1,358.89 sampled active seconds and 2,201.82 sampled parked
seconds. Sampling short requests undercounts completed requests; the 1,593
metered contacts above are authoritative. These monitor aggregates do not
separate model load, CPU verification, transfer and GPU execution accurately
enough to assign all parked time to one cause.

Host free memory fell to 7.25 GiB. The root reclaimed clean WSL file cache
twice, without restarting the service or changing source/model bytes. The
external resource-event journal preserves the observations. GPU utilization
was not maximized in this sequential preparation window; no extra neural
probe was added to improve the reported throughput.

## Operator-stop reconciliation

The shared operator stop returned an unforced SIGTERM receipt at
2026-09-10T11:27:16.549869+00:00 with exit code zero. The foreground watch
subsequently observed the same disappearance, mislabeled it as unrequested,
and overwrote session-stop.json at 11:27:16.739675+00:00. Its own exit code
was one. This is a competing-writer defect in the external stop/watch paths,
not evidence of a failed encoding or an unrequested model restart.

The exact first stdout bytes were extracted from the original recorded tool
result, without reconstructing receipt fields. Both stop records remain
unchanged and addressable under the serving directory:

- session-stop.operator-requested.json, SHA256 ca92115b3be5365f2cb262b8abecdddab6ae2fd3b579835be6664660b15918a6.
- session-stop.operator-tool-event.jsonl preserves the source tool record.
- session-stop.wrapper-final.json preserves the later wrapper output.
- session-stop.reconciliation.json, SHA256 18ce9fd5fad3d8d54c465aaf74d01fe0724cb5686c1eaecc7a338cb9822e7d69.

PID 604 was independently observed gone. The final provenance must bind the
preserved operator-returned normal stop and retain this reconciliation beside
it; the contradictory final wrapper record must never be silently rewritten
or discarded.

## Completed feature closure and serving hold

The complete cache audit and final preparation provenance are published:

- window-feature-cache-audit.json: cc59a1dee59908c7fae25500b9ab40383b4aa9f9ef00a2946ba7c544b60180a8.
- window-feature-preparation-provenance.json: 72d097e3b153baccb75b4e6e221bc83a1ac60d36dd194c39822993db684ed757.

Both cover exactly 1,593 unique inputs and the provenance binds all 1,593
successful encoding contacts and feature outputs. Full warm verification
completed with zero new neural contact and the same encoding artifact hash.
The encoder lease and monitor are closed. Preparation is complete.

The isolated strict-cache service qualification is STOPPED after its only
recovery. The first attempt refused locally with zero requests because this
test passed a JSON list where SliceRecord requires a tuple. Reusing the
existing core.preparation_encoding._slice converter passed registration of
all four actual sources with sockets forbidden.

The recovery matched all four actual request body hashes to the measured fit,
then made three metered requests totaling 31.1288125 speech seconds:

| Case | Observed result |
|---|---|
| Valid cache | Successful one-token decode; both cache-hit markers observed. |
| Missing cache | Expected server HTTP refusal; no encoding fallback. |
| Malformed cache | Request metered; connection reset, without a completed case receipt. |
| Injected cached-decode error | Not contacted; trigger remains absent. |

The kernel records SIGSEGV in libllama-server-impl.so for the isolated server.
The exact source-level crash cause is not established. The injected fault was
never activated. Original and private feature files remain unchanged, and the
server log contains zero encoder/fallback markers. This is not a complete
strict-cache qualification. No third retry or automatic restart was performed.

The content-free stopped receipt is
analysis/SAEA-E21-STRICT-CACHE-QUALIFICATION-RECOVERY-V1/qualification-stopped.json,
SHA256 85d37f416ccd8dc95877de4f549e3285ea4eacc974cbf2d4ccfb287890511be7.
Its attempt is ABORTED; the service, coordinator, monitor and lease are closed.

The four-request fit itself remains valid as a narrow capacity observation:
five metadata/tokenizer contacts, minimum 5,792-token margin under the 2x rule,
SHA256 58f581e0d7487dc2ee8098cb3b88ee8c56b081070f039ec7a15b8b30859b353c.
It does not qualify task delivery or full DR request capacity.

Assess the already admitted formal-window-packets decoder-only fallback using
the complete features. Do not re-encode the 1,593 windows or widen the stopped
test under a new name. Both DR generation groups remain held until their
selected serving path, current OpenJiuwen bridge and actual full request
capacity are qualified.
