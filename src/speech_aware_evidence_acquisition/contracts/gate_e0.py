"""``FrozenCoreGate`` mixin: E0 closure receipt + D3 scoring-freeze validation.

Split out of the former monolithic ``contracts.py`` (R0 repair refactor stage 1).
Behaviour-preserving move with ONE deliberate exception: every ``_measure_file``
call below goes through a live reference to the ``contracts`` package object
(``_contracts_pkg``) rather than the bare/imported name, so that
``monkeypatch.setattr(contracts, "_measure_file", spy)``
(``tests/contract/test_runtime_identity_fastpath.py``) is observed here exactly
as it was when this method lived directly in ``contracts.py``. A plain
``from .receipts import _measure_file`` would bind a SEPARATE reference in this
module's own namespace, invisible to a patch applied to the top-level package
object -- see ``receipts.py``'s module docstring for the full reasoning.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Mapping

import speech_aware_evidence_acquisition.contracts as _contracts_pkg

from .errors import GateClosed
from .identifiers import E0_RECEIPT_SCHEMA, SCORING_PACKAGE_RELPATH, _SHA256
from .receipts import _resolve_under, _safe_relative_path

# IMPORTANT B follow-up (round-2 external-threat-model review): the module
# prefix every real scoring submodule imports under, e.g.
# ``speech_aware_evidence_acquisition.scoring.wer`` -- used to scan
# ``sys.modules`` for scoring code THIS process has already loaded (see
# ``FrozenCoreGate._assert_no_relocated_bytecode_cache``).
_SCORING_MODULE_PREFIX = "speech_aware_evidence_acquisition.scoring"


class _E0AndScoringFreezeMixin:
    """``_validate_e0``, its scoring-freeze enforcement and the bytecode-cache guard."""

    def _validate_e0(self) -> None:
        e0 = self._load(self.e0_receipt, "E0 closure receipt")
        self._require_schema(e0, E0_RECEIPT_SCHEMA, "E0 closure receipt")
        if set(e0) != {"schema", "study", "deliverables"}:
            raise GateClosed("E0 closure receipt must have exact schema/study/deliverables keys")
        deliverables = e0["deliverables"]
        if not isinstance(deliverables, Mapping) or set(deliverables) != set(self.E0_DELIVERABLES):
            raise GateClosed(
                f"E0 receipt deliverables must be exactly {self.E0_DELIVERABLES}"
            )
        artifacts_root = Path(self.e0_receipt).parent
        artifact_paths: dict[str, Path] = {}
        for name in self.E0_DELIVERABLES:
            entry = deliverables[name]
            if not isinstance(entry, Mapping) or set(entry) != {"status", "artifact", "sha256"}:
                raise GateClosed(f"E0 deliverable {name} must have exact status/artifact/sha256")
            if entry["status"] != "CLOSED":
                raise GateClosed(
                    f"E0 deliverable {name} is not CLOSED (found {entry['status']!r}); "
                    "model touch refused"
                )
            recorded = entry["sha256"]
            if not isinstance(recorded, str) or _SHA256.fullmatch(recorded) is None:
                raise GateClosed(f"E0 deliverable {name} lacks a valid artifact sha256")
            relative = _safe_relative_path(entry["artifact"], f"E0 deliverable {name} artifact")
            artifact = _resolve_under(artifacts_root, relative, f"E0 deliverable {name} artifact")
            _, actual = _contracts_pkg._measure_file(artifact, f"E0 deliverable {name} artifact")
            if actual != recorded:
                raise GateClosed(
                    f"E0 deliverable {name} artifact hash drift: receipt {recorded[:12]}..., "
                    f"actual {actual[:12]}...; model touch refused"
                )
            artifact_paths[name] = artifact
        self._validate_scoring_freeze(artifact_paths["d3_scoring"])

    def _validate_scoring_freeze(self, d3_artifact: Path) -> None:
        """The D3 freeze is enforced, not asserted: re-hash every frozen scoring
        source against the live tree and refuse any unlisted scoring module.

        Without this, editing ``scoring/*.py`` after closure would leave every
        receipt hash intact — the artifact records hashes of code that would no
        longer be the code doing the scoring."""

        document = self._load(d3_artifact, "D3 scoring artifact")
        frozen = document.get("frozen_sources_sha256")
        if not isinstance(frozen, Mapping) or not frozen:
            raise GateClosed(
                "D3 scoring artifact lacks a non-empty frozen_sources_sha256 mapping; "
                "an unfrozen scoring stack cannot open the model gate"
            )
        for relpath, recorded in frozen.items():
            if not isinstance(recorded, str) or _SHA256.fullmatch(recorded) is None:
                raise GateClosed(f"frozen scoring source {relpath!r} lacks a valid sha256")
            relative = _safe_relative_path(relpath, f"frozen scoring source {relpath!r}")
            source = _resolve_under(self.source_root, relative, f"frozen scoring source {relpath!r}")
            _, actual = _contracts_pkg._measure_file(source, f"frozen scoring source {relpath!r}")
            if actual != recorded:
                raise GateClosed(
                    f"scoring freeze drift: {relpath} is {actual[:12]}... on disk but the "
                    f"D3 receipt froze {recorded[:12]}...; model touch refused"
                )
        scoring_dir = Path(self.source_root) / SCORING_PACKAGE_RELPATH
        if not scoring_dir.is_dir():
            raise GateClosed(f"scoring package directory missing: {scoring_dir}")
        self._assert_no_relocated_bytecode_cache(scoring_dir)
        actual_sources: set[str] = set()
        for entry in sorted(scoring_dir.rglob("*")):
            rel_parts = entry.relative_to(scoring_dir).parts
            # Symlink refusal must precede the __pycache__ skip: a symlinked
            # directory NAMED __pycache__ would otherwise slip through by name.
            if entry.is_dir() and entry.is_symlink():
                raise GateClosed(
                    "scoring package contains a symlinked directory "
                    f"{'/'.join(rel_parts)!r}; rglob does not descend through it, "
                    "so its contents would be importable yet invisible to the "
                    "freeze — refused"
                )
            # M-1 (external-threat-model review): a __pycache__ entry is no longer
            # silently invisible to the freeze. Demonstrated defect: a hand-planted
            # .pyc whose SOURCE hash still matched the D3 receipt (Python's import
            # machinery can be made to trust a hash-based .pyc without ever
            # re-checking it against the .py bytes) made scoring run different code
            # than the receipt described, with every hash the gate checks staying
            # green. The freeze covers Python SOURCE only (module docstring above) --
            # so any bytecode cache under the frozen scoring package, planted or
            # merely stale, is refused outright rather than skipped.
            if "__pycache__" in rel_parts:
                raise GateClosed(
                    "scoring package contains a __pycache__ entry "
                    f"{'/'.join(rel_parts)!r}; the D3 freeze binds source bytes only, "
                    "so cached/forged bytecode next to frozen sources is refused rather "
                    "than silently ignored -- purge it (PYTHONDONTWRITEBYTECODE=1 keeps "
                    "it from reappearing) before opening the gate"
                )
            if entry.is_dir():
                continue
            if entry.is_file() and entry.name.endswith(".py"):
                actual_sources.add(f"{SCORING_PACKAGE_RELPATH}/{'/'.join(rel_parts)}")
                continue
            raise GateClosed(
                "scoring package contains a non-source entry "
                f"{'/'.join(rel_parts)!r} (data file or dangling symlink); the freeze "
                "covers Python sources only, so nothing else may live there"
            )
        declared = set(frozen)
        unlisted = sorted(actual_sources - declared)
        if unlisted:
            raise GateClosed(
                f"scoring package contains source files the D3 freeze does not name: "
                f"{unlisted}; model touch refused"
            )

    def _assert_no_relocated_bytecode_cache(self, scoring_dir: Path) -> None:
        """IMPORTANT B follow-up (round-2 external-threat-model review).

        The on-disk ``__pycache__`` walk in :meth:`_validate_scoring_freeze`
        only ever sees a bytecode cache co-located with the frozen scoring
        sources. ``sys.pycache_prefix`` -- settable via the
        ``PYTHONPYCACHEPREFIX`` environment variable -- relocates EVERY
        ``.pyc`` Python would read or write (forged or merely stale) into a
        mirrored tree elsewhere on disk that walk never visits, so on its own
        the ``__pycache__`` refusal is not a guarantee against bytecode the
        interpreter would still execute. Demonstrated: a forged
        ``UNCHECKED_HASH`` ``.pyc`` placed in the relocated prefix tree
        executed while ``wer.py``'s source hash still matched the D3 freeze
        and ``_validate_scoring_freeze`` PASSED. Separately,
        ``PYTHONDONTWRITEBYTECODE=1`` (the previously prescribed mitigation)
        stops Python from WRITING a new ``.pyc`` -- it does nothing to stop an
        ALREADY-planted one from being READ and executed; writing is not
        reading, and the old runbook wording conflated the two.

        Two checks, stated exactly for what each closes:

        1. Refuse outright if EITHER ``sys.pycache_prefix`` or the
           ``PYTHONPYCACHEPREFIX`` environment variable is set for this
           process. Whatever the on-disk walk found, an active relocated-
           cache configuration means that walk did not see everywhere this
           interpreter would actually look for (or write) a ``.pyc`` -- so
           the freeze cannot vouch for what would run. This is the primary,
           load-bearing check: with no relocation configured, Python only
           ever reads/writes a ``.pyc`` directly beside its ``.py`` source,
           exactly the location the walk above already refuses any entry
           under.
        2. For every ``speech_aware_evidence_acquisition.scoring[.*]``
           submodule THIS process has already imported FROM this exact
           ``scoring_dir`` (``sys.modules``, filtered by ``__file__``
           resolving inside ``scoring_dir`` -- a module imported from a
           DIFFERENT ``scoring_dir``, e.g. a synthetic test fixture's own
           tree, is simply not this gate's concern and is skipped): refuse
           if its ``__file__`` does not end in ``.py`` (a sourceless/
           bytecode-only import -- the exact shape a hash-based-forged
           ``.pyc`` with no matching ``.py`` on disk would take), or if its
           ``__cached__`` resolves OUTSIDE ``scoring_dir`` (a relocated
           cache still recorded on the module even if the prefix that
           produced it has since been unset in THIS process).

        STATED GUARANTEE -- precise, not overstated: with this check
        passing, (a) THIS process has no active relocated-cache
        configuration that could make Python read or write a ``.pyc``
        anywhere other than directly beside its ``.py`` source (where the
        walk above already refuses any entry), and (b) every scoring
        submodule THIS process has already imported from ``scoring_dir`` was
        loaded from a ``.py`` file inside it, with no bytecode cache
        recorded outside it. It does NOT -- and cannot -- prove that no
        OTHER process (its own ``PYTHONPYCACHEPREFIX``, running concurrently
        or having run earlier or later) holds or will hold a forged cache it
        can execute independently of this gate check, nor does it retroactively
        validate an import that happens in THIS process AFTER this check
        runs. The freeze covers Python source bytes read by a clean import
        of this checked tree; it was never, and is still not, a guarantee
        about interpreter-wide bytecode-loading configuration beyond that.
        """

        prefix = sys.pycache_prefix
        env_prefix = os.environ.get("PYTHONPYCACHEPREFIX")
        if prefix or env_prefix:
            raise GateClosed(
                "a relocated bytecode cache is configured for this process "
                f"(sys.pycache_prefix={prefix!r}, PYTHONPYCACHEPREFIX={env_prefix!r}); "
                "this moves every .pyc -- forged or stale -- outside the tree the "
                "scoring __pycache__ refusal can see, so the freeze cannot vouch for "
                "what bytecode this process would execute; unset it and retry"
            )
        scoring_dir_resolved = Path(scoring_dir).resolve()
        for name, module in list(sys.modules.items()):
            if module is None or not (
                name == _SCORING_MODULE_PREFIX or name.startswith(_SCORING_MODULE_PREFIX + ".")
            ):
                continue
            module_file = getattr(module, "__file__", None)
            if module_file is None:
                continue  # a namespace/frozen/builtin entry -- nothing on disk to check
            try:
                module_file_resolved = Path(module_file).resolve()
            except OSError:
                continue
            if not module_file_resolved.is_relative_to(scoring_dir_resolved):
                # Loaded from a DIFFERENT scoring_dir entirely (e.g. a
                # synthetic test fixture's own tmp tree) -- not this gate's
                # concern; only modules genuinely loaded from THIS checked
                # directory are in scope.
                continue
            if module_file_resolved.suffix != ".py":
                raise GateClosed(
                    f"scoring module {name!r} was loaded from a non-source file "
                    f"({module_file!r}); this process's import machinery did not use "
                    "the frozen .py source, so the D3 freeze cannot vouch for what "
                    "runs -- refused"
                )
            cached = getattr(module, "__cached__", None)
            if cached is not None:
                try:
                    cached_resolved = Path(cached).resolve()
                except OSError:
                    cached_resolved = Path(cached)
                if not cached_resolved.is_relative_to(scoring_dir_resolved):
                    raise GateClosed(
                        f"scoring module {name!r} has a bytecode cache recorded outside "
                        f"the checked scoring package ({cached!r}); a relocated cache "
                        "cannot be vouched for by this freeze -- refused"
                    )
