# KC-S1b prospective replica registration

The owner continuation authorizes this bounded same-profile replica. Keep generation held
until the separate tokenizer fit and final generation registration are complete.

The model, dataset and baseline fragment bytes match historical study d737e354 exactly;
see fragment-parity.json. Complete-roster payload parity is recorded under
docs/checks/speech-aware-evidence-acquisition/2026-09-09-kc-s1b-replica-parity.
The historical transport diff was reviewed: the extracted render_request body preserves
the speech-query-prefix-v2 branch; the added construction-only handling does not apply to
any of these 1,000 requests. Targeted configuration/campaign/transport tests passed:
122 passed and one skipped. This is engineering evidence, not a new scientific outcome.

fit-plan.json carries the computed protocol, split, attempt and complete required service
identity. The runtime root is /home/chao because receipt binary paths already begin with
llama.cpp-featcache/. Do not append that directory twice. The receipt-pinned decoder and
build remain unchanged; no executable, weight or environment was replaced.

Use one root-owned decoder service at c65536/np4, with max64 output reserve. The fitter's
3,001 tokenizer contacts are separately metered and must cover all 1,000 actual requests.
Service lifecycle and read-only health/props/slots monitoring are recorded in service receipts.
They generate no task response. Record 10-second utilization, power, memory and slot samples;
retain load/idle/preparation/fit/generation/scoring time categories separately.

Do not infer generation authorization from a technical check. After fit, bind its exact
artifact, register the resulting generation protocol and freeze the execution checkout.
The exposure row for generation is intentionally registered after fit binding to avoid
claiming that a pre-pin protocol hash describes the final run.

The experiment configuration prospectively fixes both strict per-sample entity F1 and
per-sample SLU-F1, their historical controls and paired estimators. Keep corpus micro SLU-F1
separate. NEW500 is historically exposed. A same-profile repeat does not close the historical
different-geometry rung-2 requirement.

Use scripts/flights/run_campaign.py coordinate-fit with the registered fit cell, explicit
repository/data/runtime/lock paths, owner Codex, expected session ID
slurp-g1-np4-c65536-20260909-codex and contact cap3001. This root entry builds the full roster
before starting the existing serving wrapper. It publishes the immutable fit artifact
receipt and releases the fit lease while its wrapper remains foreground for later workers.
Use the existing serving_session.sh stop command at a root-selected service boundary.
Do not terminate the foreground coordinator merely because the fit receipt was published.
