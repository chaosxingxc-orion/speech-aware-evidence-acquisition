# Legacy feature-cache audit

The shared build_feature_cache_audit helper builds a model-free artifact from
the existing build_window_feature_inventory and
inspect_legacy_cached_speech_feature_cache APIs. It verifies every unique
inventory audio reference, preserves each request reference, binds the resolved
legacy cache root and encoder identity, and records each validated chunk's
ordinal, relative filename, SHA-256, byte size, token count, and embedding
width. Distinct audio identities sharing one FNV key are refused.

prepare_feature_cache_audit persists the audit through prepare_artifact with
contact class model-free. Its state is
cache-files-verified-runtime-unqualified. The artifact proves file coverage
and byte stability during the audit only. It also recomputes the shared window inventory at the end, re-resolving audio and parent paths to detect source changes or symlink swaps observed across the audit. This is model-free verification of observed reads and does not provide a lock or atomic-read guarantee. It does not prove source encoding
provenance, a live cache hit, or permission to generate; those require later
pinned receipts and runtime qualification.

Validation is synthetic and model-free. The focused test module covers complete
deduplicated coverage, all request references, malformed or missing chunks,
stale prepared artifacts, ambiguous FNV keys, concurrent cache mutation, and delayed audio or parent mutation.
