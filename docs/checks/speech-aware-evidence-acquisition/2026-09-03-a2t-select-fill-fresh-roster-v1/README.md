# Audio2Tool SELECT/FILL Fresh Roster V1

This directory carries the second 104-row, 13-per-tier Audio2Tool discovery roster for the
prospective SELECT/FILL architecture comparison. The roster is drawn only from the already frozen
400-row evaluation pool behind the unchanged 12,601-row construction partition. It excludes the
completed semantic-flight roster by sample identity, query block, and normalized-token class.

`build_roster.py` is an identity and local carrier-metadata operation. It performs zero model,
network, tokenizer, scorer, and audio-inference contacts. It refuses to overwrite an existing
receipt and verifies the frozen partition and prior-roster identities before materialization.
