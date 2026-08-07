"""``python -m speech_aware_evidence_acquisition.core.driver`` entry point.

R0 operator-path repair (independent rereview
``2026-08-07-saea-r0-script-engineering-review-assessment.md`` finding B1):
``python -m <package>`` only ever executes ``<package>/__main__.py`` -- never
a package's own ``__init__.py`` (that module-execution special case is
reserved for ``__main__.py`` alone; see ``__init__.py``'s own module comment
for why its previous ``if __name__ == "__main__":`` guard there was dead code
for exactly this invocation form). This file exists solely to bridge that
gap: the real argument parsing and dispatch is, and remains, ``core.driver.main``
(``cli.py``). The ``saea-driver`` console script (``pyproject.toml``'s
``[project.scripts]``) calls the same ``main`` directly.
"""

from __future__ import annotations

import sys

from . import main

if __name__ == "__main__":
    sys.exit(main())
