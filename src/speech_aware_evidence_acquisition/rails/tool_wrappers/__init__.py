"""Thin wrapper bodies for the tool catalog (WAVE W3, 2026-09-08).

One module per tool. Each module holds exactly one body function that calls
an EXISTING repository function unchanged and returns its result inside a
``rails.tools.ToolResult``, plus a ``rails.tools.DerivationRecord`` when the
tool changes the bytes that go on the wire. Nothing here reimplements,
re-parameterizes, re-orders or "improves" the function it wraps: the whole
point of the catalog is that the wrapped path and the direct path are the
same path, which every wrapper's byte-equivalence test pins.

The manifests live beside the registration block in ``rails/tools.py``, not
here, and each body imports ``ToolResult``/``DerivationRecord`` INSIDE the
function rather than at module level. That is not style: ``rails.tools``
imports these modules at the bottom of its own body to register them, so a
module-level ``from ..tools import ...`` here would be a genuine import
cycle the moment a caller (a test, say) imported a wrapper first. A
function-level import of an already-loaded module is a dict lookup, and it
keeps every wrapper module importable on its own.

Deliberately no re-exports in this ``__init__``: importing one wrapper must
not drag in the loader modules of all the others (same reason
``rails.adapters`` re-exports nothing).
"""

from __future__ import annotations
