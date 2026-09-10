# Shared window feature encoding

`core.preparation_encoding.encode_window_feature_cache` receives a verified
window-feature inventory, an already attached standard client, and a custody
guard. It never starts, attaches, stops, or releases a service lease.

Each distinct source-audio SHA-256 is encoded at most once. Before any fresh
contact, an existing legacy cache key must have a supplied, matching final
provenance record. Cache files alone are refused. Fresh contacts register the
existing `SliceRecord`, use the fixed English preprocessing instruction with
one completion token, inspect cache chunks after the response, and preserve
only the client's ordinary traces.

The encoder artifact has schema `saea-window-feature-encoding-record-v1`.
It records current and inherited contact identities separately. Its caller is
responsible for validating the session receipt, final normal-stop receipt,
cache coverage, and final provenance assembly.
