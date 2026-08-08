"""Reproduction-probe support (R0.1 plan P0): scorers and sampling helpers.

Deliberately OUTSIDE the E0 D3 frozen scoring package
(:mod:`speech_aware_evidence_acquisition.scoring`) — D3 hashes every source
file under that package, so probe-side additions live here with their own
version constants. Nothing in this package may alter frozen scoring
semantics; it may import them read-only.
"""
