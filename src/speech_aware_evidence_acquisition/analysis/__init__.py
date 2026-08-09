"""Model-free, post-hoc analysis tools over already-produced run bundles.

Every module here is a READER: it locates COMPLETED attempts under a stable
run_dir, reuses the frozen scoring stack (``speech_aware_evidence_acquisition
.scoring``/``core.scorers``) to score them, and reports statistics. Nothing
here ever opens a model session, writes a run bundle, or mutates attempt
state -- that is ``core.driver``'s job, not this package's.
"""
