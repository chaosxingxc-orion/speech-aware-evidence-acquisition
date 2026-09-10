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

## Remaining bounded closure

The saved-inventory full cache audit and zero-contact warm validation are
running on CPU. Final source-bound provenance, root lease release and the
isolated strict-cache service qualification remain pending. Next, bind the
current OpenJiuwen bridge and both real DR request fits to the prepared
CPU-projector inference configuration. Keep max_tokens=1024 and both declared
draft sources and delivery rules. This report does not yet authorize either
DR generation group.
