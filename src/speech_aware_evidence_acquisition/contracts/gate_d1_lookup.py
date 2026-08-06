"""``FrozenCoreGate`` mixin: resolve D1's own identity artifact path.

Split out of ``gate_identity.py`` (R0 repair refactor stage 2, part C, pure
move, no behaviour change) purely for file size -- shared by both
``gate_media_identity.py`` and ``gate_reference_identity.py``, which each
independently mix it in via multiple inheritance (``gate.py``'s own module
docstring: mixins carry only methods, so combining several changes nothing
about ``FrozenCoreGate``'s runtime behaviour).
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .errors import GateClosed
from .receipts import _resolve_under, _safe_relative_path


class _D1IdentityLookupMixin:
    """``_d1_identity_artifact_path``: D1's own artifact path, resolved
    THROUGH the E0 closure receipt."""

    def _d1_identity_artifact_path(self):
        """Resolve D1's own artifact path THROUGH the E0 closure receipt (never a
        hardcoded filename) -- the same discipline :meth:`_validate_e0` already
        uses for every deliverable, applied here for exactly one of them so
        :meth:`verify_media_identity` can independently load D1's per-sample
        media facts without depending on ``_validate_e0`` having run first in
        the same call (it always will in the real ``FrozenCoreGate.
        for_study_repo`` production path via ``assert_model_touch_allowed``,
        but this method is a second, independently callable rail — see its own
        docstring)."""

        e0 = self._load(self.e0_receipt, "E0 closure receipt")
        deliverables = e0.get("deliverables")
        if not isinstance(deliverables, Mapping) or "d1_identity" not in deliverables:
            raise GateClosed("E0 closure receipt lacks a d1_identity deliverable")
        entry = deliverables["d1_identity"]
        if not isinstance(entry, Mapping) or "artifact" not in entry:
            raise GateClosed("E0 closure receipt d1_identity deliverable is malformed")
        relative = _safe_relative_path(entry["artifact"], "E0 deliverable d1_identity artifact")
        return _resolve_under(
            Path(self.e0_receipt).parent, relative, "E0 deliverable d1_identity artifact"
        )
