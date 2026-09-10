# Prepared raw-audio feature-cache guard

This change adds PreparedFeatureCacheGuard in
core/model/prepared_feature_cache.py. Construct it with
PreparedFeatureCacheGuard.from_artifact, passing the hash-pinned audit path and
SHA-256, an explicit WindowFeatureEncoderIdentity, expected cache directory,
expected embedding width, and data_root.

The guard loads the existing model-free audit artifact and requires state
cache-files-verified-runtime-unqualified. On every actual render it matches
payload sample, media path, duration, and sample rate to the registered
inventory request; resolves and hashes the source audio; extracts exactly one
input_audio part from the rendered body; compares the decoded base64 bytes;
and reuses the public legacy cache inspection helper to verify the complete
registered chunk set, including hashes, sizes, ordinals, token counts, and
embedding width. Missing, changed, additional, or unregistered content raises
PreparedFeatureCacheError before transport POST.

LlamaServerTransport accepts the optional typed feature_cache_guard argument
and invokes it at the end of render_request. Therefore request fitting and
actual sends share the same check. Feature-packet and text-only requests are
refused by the opt-in guard rather than silently treated as raw audio.
Existing transports without the guard retain their prior rendering behavior.

This client rail validates request/cache identity only. It does not establish
encoder provenance, server-side cache-hit behavior, or runtime qualification.
No configuration factory or runtime receipt binding is included.
