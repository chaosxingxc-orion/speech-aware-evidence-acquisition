"""Cross-cutting identity/schema constants shared by every contracts submodule.

Split out of the former monolithic ``contracts.py`` (R0 repair refactor stage 1,
pure move, no behaviour change). These are the constants multiple submodules
within (and outside) the ``contracts`` package import -- kept in one dependency-
free module so no two submodules need to import each other just to share a
regex or a schema string.
"""

from __future__ import annotations

import re

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
# IMPORTANT 3 (external-threat-model review round 3): the ONE canonical
# identifier pattern for every run_id/attempt_id/session_id this study ever
# embeds verbatim into a filesystem path -- core.attempts (an attempt's
# directory name + file stem), core.tracing (a trace file's stem),
# core.session (a session receipt's file stem), and now ExecutionPlan.validate
# itself. Previously each of those three core modules independently defined
# its OWN compiled copy of this exact same regex text; none of them was ever
# consulted by ExecutionPlan.validate, which accepted "any non-empty string"
# for run_id -- so a run_id containing `/`, `\`, or a `..` traversal segment
# (rejected by every one of those three copies) sailed straight through plan
# construction/validation. Defined HERE, at the bottom of the module's
# dependency graph (contracts.py imports nothing from core/), and imported by
# every consumer instead of re-copied, so there is exactly one definition of
# "a safe identifier" a fourth divergent regex could never quietly drift from.
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

STUDY_SLUG = "speech-aware-evidence-acquisition"
MODEL_LOCK_KEY = "qwen3-omni-30b-a3b-instruct-gguf"
E0_RECEIPT_SCHEMA = "saea-e0-closure-receipt-v1"
RUNTIME_RECEIPT_SCHEMA = "saea-runtime-receipt-v2"
SCORING_PACKAGE_RELPATH = "src/speech_aware_evidence_acquisition/scoring"
