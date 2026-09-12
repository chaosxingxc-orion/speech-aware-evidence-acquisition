# Mixed speech evidence renderer: root fix and validation

Date: September 12, 2026.

The original Whisper treatment completed 2000 plan/solve contacts, then failed before revise generation. Its typed knowledge and untyped prepared observation were both valid, but the production renderer incorrectly required every evidence item to carry a key/value knowledge role when any typed item existed.

Admit absent roles in a correctly aligned mixed list. Keep typed keys in the stable prefix; retain values and untyped observations, in original order, in the mutable evidence suffix before phase history. Do not relabel observations as knowledge, remove them, or alter historical all-typed/all-untyped requests. The original experiment worktree and artifacts remain unchanged.

Root reproduced two failing mixed-role cases before the fix. The expanded tests call the real request renderer, verify that rendering makes no POST, and compare the rendered body with the actual transport body under both registered v2 orders. After the narrow fix: 122 tests pass, one test skips; targeted Ruff and engineering-base checks pass. Independent source review accepts the change.

The prior fake transport inspected the canonical payload but bypassed production message rendering. That validation established payload composition, not end-to-end rendering. This was the missing coverage boundary.

This is engineering validation only. No recovery generation or downstream task improvement is claimed. Preserve the failed attempt, register any single allowed recovery, and fit every complete actual phase request wave before dispatch.

Receipt: DATA coordination/slurp-speech-observation-pair-v1/mixed-evidence-renderer-validation-v1.json, SHA-256 6d2046d0bea0c792aca2f6bce2405b8625c006c0f947fe59dd284cab3d85c57f.
