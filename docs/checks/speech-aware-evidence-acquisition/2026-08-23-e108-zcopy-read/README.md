# E108 zero-copy one-shot read — landed artifacts

Date: 2026-08-23 (read attempt `attempt-20260824T012500Z-e108rd`, UTC-stamped id). One-shot
semantics: the registered read under row `SAEA-SN-MF-EVIDENCE-E108-ZCOPY-READ` executed exactly
once; no rerun, no threshold change, no partial re-read. The reading agent stalled at the
harness level AFTER the read completed; the coordinator verified execution from the durable
attempt (zero service contacts proven by the unchanged server log: 1,117,739 bytes, mtime
2026-08-23 14:19:16) and performed this landing without re-running anything.

- `read-verdict.json` — sha256 `e0154a4e26a839abb7a44584714442415724dd93f95996e1111b15c84a82504c`
  (schema `saea-speech-native-read-v1`); source flight receipt `14be9f41…a503a`, decisions
  `4e9ebefc…6d99`, binding `a2ccd4b0…03dfe`.
- `read-stdout.txt`, `read-stderr.txt` (stderr empty).

Headline (reader outputs verbatim; interpretation lives in
`docs/readiness/2026-08-23-e108-verdict.md`):

- `support_gate_passed: false` — 6 of 8 conjuncts fail: top-k-reachable 96 (<100),
  action-variable 14 (<24), adaptive boundary acquisitions 7 (<18), boundary-stable
  non-primary actions 0 (<12), incremental boundary repairs 0 (<3), oracle gain 2 (<6);
  passing: query count 108 (≥100), mechanism failures 0.
- Training-free controller: `deferred-support-gate-failed` (per contract; never evaluated).
- Primary (embedded speech-only K1-M11) **92/108 = 0.8519**; retrieval-top1 88; candidate-
  action-state 90; boundary-stable 92; final-minus-primary 0 (primary-control aggregator);
  oracle 94; parse failures 0; calls 3×101 + 5×7 = 338; 454.03 tokens/s aggregate.
- Information flow (`m11-information-flow-v1`): boundary supply — 7 acquisitions, 4 changed
  predictions, **4 helpful / 0 harmful** (net +4, 3 unresolved); factor supply — 108 eligible,
  5 changed, **2 helpful / 0 harmful** (106 neutral); generated-state-as-external-supply 0.
