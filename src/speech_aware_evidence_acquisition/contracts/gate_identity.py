"""``FrozenCoreGate`` mixin: D1-anchored media and reference byte-identity verification.

Split out of the former monolithic ``contracts.py`` (R0 repair refactor stage 1).

R0 repair refactor stage 2 (part C, pure move, no behaviour change): further
split into ``gate_d1_lookup.py`` (the shared ``_d1_identity_artifact_path``
helper), ``gate_media_identity.py`` (``verify_media_identity`` + its bitrate-
plausibility check, I-4) and ``gate_reference_identity.py``
(``verify_reference_identity`` + ``_REFERENCE_SCOPED_CARRIER_LOCK_KEYS``,
IMPORTANT 2) -- purely for file size. This module is now a pure composition:
``_MediaReferenceIdentityMixin`` combines the two independent mixins via
multiple inheritance exactly the way ``gate.py``'s own ``FrozenCoreGate``
composes several of these (that module's own docstring: mixins carry only
methods, so this changes nothing about runtime behaviour), and re-exports
every name this module used to define directly so nothing importing from
here needs to change.
"""

from __future__ import annotations

from .gate_media_identity import _MediaIdentityMixin
from .gate_reference_identity import (  # noqa: F401 (re-export, see module docstring)
    _NLP_REFERENCE_D1_LAYER_KEY,
    _REFERENCE_SCOPED_CARRIER_LOCK_KEYS,
    _ReferenceIdentityMixin,
)


class _MediaReferenceIdentityMixin(_MediaIdentityMixin, _ReferenceIdentityMixin):
    """``verify_media_identity`` / ``verify_reference_identity`` and their D1 plumbing."""
