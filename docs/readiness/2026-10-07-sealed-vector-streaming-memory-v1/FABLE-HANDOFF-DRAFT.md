# Fable handoff draft: sealed-vector memory correction

The prepared four-input envelope is only 10.8 KB of selected IDs. The active facet
source is 504 MiB on disk and the original loader temporarily holds its bytes and
all decoded lines beside the complete parsed table. Root's exact frozen-source
profile peaked at 1,960.84 MiB and completed under the 4/4 GiB guard; it did not
reproduce the reported approximately 20 GiB Windows drop.

A prospective shared-loader correction replaces transient full-file buffers with
two bounded hash/UTF-8 and record-decoding passes while retaining every source row
and all original validation. Synthetic full-table float.hex parity passes in all
eight old/new cases. At 1,024 rows, traced peaks fall from 144.52 to 64.49 MiB for
vectors and 145.15 to 64.73 MiB for segments; retained table sizes stay the same.
Seventy-two focused tests and lint pass. No inference, scoring or runtime controls
are used by this engineering change.

Root owns integration and fresh source-bound preparation before another natural
attempt. Existing frozen and prepared bytes stay immutable. The source fingerprint
change makes old envelopes stale; the fix is not evidence that the natural proof
qualified or that the approximately 20 GiB failure cause is resolved.
