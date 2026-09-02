# G6 fixed16 seal recovery

This write-once receipt records the second G6 recovery attempt for flight
`flight-20260902T221239Z`. The first attempt used 8 contacts; the second used
456, for a cumulative 464. Metadata confirms 456 complete request-response-cost
triples. The attempt failed after model completion during phase trace emission:
unprefixed OBS payload keys violated `TraceContract`.

This audit inspected only external attempt and trace metadata. It did not inspect
response meaning, gold labels, or scorer results. The source paths and hashes are
frozen in `recovery-plan.json`.

No further model contact or recontact is authorized. Only model-free reconstruction
of the 16 final outputs from both traces, source-bound external sealing, and the
unchanged one-process whole-manifest scorer may proceed. This receipt does not
qualify a paper candidate or make a performance claim.
