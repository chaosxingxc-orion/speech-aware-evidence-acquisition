# Sole native-graph capacity recovery

The first native-graph capacity attempt stopped after141 nongenerative contacts.
The initial tokenization succeeded, the four-row graph completed offline, and the
first subsequent apply-template contact failed with Broken pipe. The serving
session remained healthy, all four slots idle, Windows free memory21.32GiB.
A persistent audit connection was held unused across the roughly50-second graph
walk; stale keep-alive reuse is the identified client-lifecycle defect consistent
with this failure. No capacity or quality conclusion follows from that request.

The correction creates one shared audit-client connection per endpoint and closes
it afterward. It never retries a failed endpoint. The schema, templates, token
ranking, four graph paths, output budgets, roster, speech bound and geometry are
unchanged. Unit verification covers fresh connections and exception propagation.
The previously completed model-free full integration covers both44-request paths.

This is recovery index1 of the native-graph capacity flight; a second failure stops
it. Preserve the predecessor worker ca0341fa4, contact journal, scratch traces and
failure logs. Root may archive only the exact quiescent old lease after verifying
process and service state. Keep every other historical failure, frozen worker and
queue unchanged. No initial seed generation is admitted by this recovery.
