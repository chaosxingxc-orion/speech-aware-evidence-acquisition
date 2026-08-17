"""Concrete ``rails.task_adapter.TaskAdapter`` implementations, one module
per task carrier. Deliberately no re-exports here (module docstring of
``rails.__init__``): each adapter module pulls in its own carrier-specific
loader package, and importing this ``adapters`` package should not force
every carrier's loader to import just to reach one of them.
"""

from __future__ import annotations
