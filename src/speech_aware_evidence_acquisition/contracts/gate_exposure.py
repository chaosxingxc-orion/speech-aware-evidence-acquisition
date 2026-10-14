"""``FrozenCoreGate`` mixin: umbrella-lock carrier scope + exposure-ledger
pre-registration cross-check.

Split out of the former monolithic ``contracts.py`` (R0 repair refactor stage 1,
pure move, no behaviour change).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Mapping

from .errors import GateClosed
from .identifiers import CONSTRUCTION_VISIBLE_ARMS
from .ledger import _CARRIER_CELL_TOKEN_SPLIT, _EXPOSURE_CARRIER_COLUMN, _EXPOSURE_RUN_COLUMN, _parse_ledger_tables
from .plan import (
    FINAL_REPORT_SPLIT_ROLE,
    ExecutionPlan,
    require_owner_split_allowance,
)
from .receipts import general_audio_deny_lock_keys

# The umbrella lock's speech-aware-* profiles (docs/datasets.lock.json `profiles`,
# 2026-08-04 semantic migration) that may legitimately back a plan carrier: core
# evaluation carriers, secondary public carriers, entity/rare-word diagnostics and
# small optional public assets. `speech-aware-annotations` is deliberately excluded:
# it holds annotation-only entries with no speech audio of their own, so it can
# never back a model touch. `frozen-baseline`, `local-candidates`,
# `retained-cross-domain` and `deferred` are non-speech-aware profiles and are
# never allowed here.
ALLOWED_CARRIER_PROFILES = frozenset(
    {
        "speech-aware-core",
        "speech-aware-secondary",
        "speech-aware-diagnostics",
        "speech-aware-small-public",
    }
)

#: Where committed roster receipts live, relative to ``source_root``. The
#: ``contracts`` package must not import ``core`` (module docstring of
#: ``gate.py``: the circular-import note), so the construction-role check
#: below parses these receipts dependency-free and recomputes their identity
#: hash with the SAME four-line convention every other identity check in this
#: package uses: sha256 over the LF-joined, sorted, carrier-prefixed
#: ``f"{lock_key}/{sample_id}"`` ids, no trailing newline.
ROSTER_RECEIPTS_RELDIR = "docs/receipts/rosters"
ROSTER_RECEIPT_SCHEMA = "saea-roster-receipt-v1"
CONSTRUCTION_ROSTER_ROLE = "construction"

#: Non-roster companion files that live beside the roster receipts because a
#: roster receipt pins them by path and sha256 (so they cannot move). Only these
#: exact schemas are skipped by the construction-role scan; any other
#: non-roster schema still fails closed.
ROSTER_COMPANION_SCHEMAS = frozenset({"saea-a2t-paired-roster-comparator-rows-v1"})

#: The ``derived_from`` keys under which a partitioned ``final-report`` roster
#: receipt declares its parent and its sibling(s) (owner decision 147;
#: ``scripts/build_slurp_test_sample_roster.py`` writes both). The gate reads
#: them only to decide WHICH committed receipts it must re-prove a partition
#: against from their item lists; a declaration is never trusted on its own.
PARTITION_PARENT_KEY = "source_roster"
PARTITION_SIBLING_KEY = "sibling_roster"
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


class _ExposureAndCarrierMixin:
    """Carrier-scope resolution and exposure-ledger pre-registration cross-check."""

    def _lock_dataset_entries(
        self, lock: Mapping[str, object] | None = None
    ) -> dict[str, Mapping[str, object]]:
        """Every ``kind: dataset`` entry in the umbrella lock, keyed by name.

        Real speech-aware carriers live in ``asset_catalog`` alongside the
        frozen-baseline ``datasets`` list, local-candidate assets and the
        general-audio assets explicitly excluded from this study. Model entries
        live in a disjoint ``models`` list and never appear here — a plan cannot
        claim a model lock key as its speech carrier."""

        if lock is None:
            lock, _ = self._load_lock_with_hash()
        entries: dict[str, Mapping[str, object]] = {}
        for list_key in ("datasets", "asset_catalog"):
            value = lock.get(list_key)
            if not isinstance(value, list):
                continue
            for item in value:
                if (
                    isinstance(item, Mapping)
                    and item.get("kind") == "dataset"
                    and isinstance(item.get("name"), str)
                ):
                    entries[item["name"]] = item
        if not entries:
            raise GateClosed("datasets lock yields no named dataset entries")
        return entries

    def _resolve_carrier_dataset_entry(
        self, carrier_lock_key: str, lock: Mapping[str, object] | None = None
    ) -> Mapping[str, object]:
        """Resolve and scope-check a plan's carrier against the umbrella lock (I2).

        A carrier must: (a) exist as a ``kind: dataset`` entry in the umbrella lock
        — model entries and unknown keys are refused; (b) not be one of the
        general-audio assets this study explicitly excludes; and (c) carry a
        non-empty ``profiles`` list intersecting this study's speech-aware scope.
        A dataset entry with no ``profiles`` field fails closed rather than being
        assumed in scope: naming a key in the lock never by itself proves it is a
        speech-domain carrier of this study."""

        entry = self._lock_dataset_entries(lock).get(carrier_lock_key)
        if entry is None:
            raise GateClosed(
                f"carrier lock key {carrier_lock_key!r} is not a dataset entry in "
                "the umbrella datasets lock (model entries and unknown keys are "
                "never a valid speech carrier); model touch refused"
            )
        if carrier_lock_key in general_audio_deny_lock_keys(self.source_root):
            raise GateClosed(
                f"carrier lock key {carrier_lock_key!r} is a general-audio asset "
                "explicitly excluded from the speech-aware-evidence-acquisition "
                "study, whose scope is human speech and its linguistic content "
                "only (ASR, entities, contextual biasing, spoken QA, meeting "
                "speech); model touch refused"
            )
        profiles = entry.get("profiles")
        if not isinstance(profiles, list) or not profiles:
            raise GateClosed(
                f"carrier lock key {carrier_lock_key!r} has no profiles field in "
                "the umbrella datasets lock; scope cannot be proven so the touch "
                "is refused (fail-closed)"
            )
        if not (set(profiles) & ALLOWED_CARRIER_PROFILES):
            raise GateClosed(
                f"carrier lock key {carrier_lock_key!r} profiles {profiles!r} do "
                "not intersect this study's speech-only scope "
                f"{sorted(ALLOWED_CARRIER_PROFILES)}; model touch refused"
            )
        return entry

    def _construction_roster_identity_hashes(
        self, carrier_lock_key: str
    ) -> dict[str, str]:
        """Every committed construction-role roster of one carrier, as
        ``{split_identity_hash: relpath}``, recomputed from the receipt's own
        items rather than trusted from its recorded hash."""

        directory = Path(self.source_root) / ROSTER_RECEIPTS_RELDIR
        hashes: dict[str, str] = {}
        if not directory.is_dir():
            return hashes
        for path in sorted(directory.glob("*.json")):
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                raise GateClosed(f"roster receipt unreadable ({path}): {error}") from error
            if not isinstance(document, Mapping):
                raise GateClosed(f"roster receipt {path} must be a JSON object")
            schema = document.get("schema")
            if not isinstance(schema, str) or not schema:
                raise GateClosed(f"roster receipt {path} declares no schema; fail-closed")
            if schema != ROSTER_RECEIPT_SCHEMA:
                # The rosters directory also holds declared non-roster receipts (comparator-row
                # companions, runtime-subset receipts, ...). A file that DECLARES another schema is
                # not a construction roster and is skipped; only a schema-less or unreadable file
                # refuses the touch (2026-10-11: the first typed-loop flip was blocked by two such
                # companions although every real roster was intact).
                continue
            if document.get("carrier_lock_key") != carrier_lock_key:
                continue
            if document.get("roster_role") != CONSTRUCTION_ROSTER_ROLE:
                continue
            items = document.get("items")
            if not isinstance(items, list) or not items:
                raise GateClosed(f"roster receipt {path} has no items")
            ids: list[str] = []
            for item in items:
                if not isinstance(item, Mapping):
                    raise GateClosed(f"roster receipt {path} has a malformed item")
                sample_id = item.get("sample_id")
                if not isinstance(sample_id, str) or not sample_id:
                    raise GateClosed(
                        f"roster receipt {path} has an item with no sample_id"
                    )
                ids.append(f"{carrier_lock_key}/{sample_id}")
            if len(set(ids)) != len(ids):
                raise GateClosed(f"roster receipt {path} repeats a sample_id")
            measured = hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()
            if measured != document.get("split_identity_hash"):
                raise GateClosed(
                    f"roster receipt {path} split_identity_hash does not match the hash "
                    "recomputed from its own items; refusing a tampered receipt"
                )
            hashes[measured] = str(path)
        return hashes

    def _require_construction_role_for_visible_targets(
        self, plan: "ExecutionPlan", arm: str | None
    ) -> None:
        """Gold may cross to the frozen core ONLY on a construction roster.

        ``contracts.CONSTRUCTION_VISIBLE_ARMS`` names the arms whose D2-frozen
        field set carries construction gold (owner decision 2026-09-05: the
        core may act as a proposer over construction rows with their labels,
        producing artifacts, never answers). For such an arm this gate refuses
        the touch unless the plan's OWN ``split_identity_hash`` is that of a
        committed ``roster_role == "construction"`` roster of the plan's own
        carrier, and the plan's split role is ``"discovery"`` (the role a
        construction roster keeps, the TRAIN90 precedent).

        Every other arm is completely unaffected: the method returns
        immediately, so a caller that does not pass an arm at all -- every
        pre-existing caller -- behaves exactly as before. That is also why the
        check fails closed on a missing arm name for a construction-visible
        request: it can only ever be reached by naming the arm.
        """

        if arm is None or arm not in CONSTRUCTION_VISIBLE_ARMS:
            return
        if plan.split_role != "discovery":
            raise GateClosed(
                f"arm {arm!r} may see construction gold only on a discovery split; the "
                f"plan declares split role {plan.split_role!r}; model touch refused"
            )
        hashes = self._construction_roster_identity_hashes(plan.carrier_lock_key)
        if plan.split_identity_hash not in hashes:
            raise GateClosed(
                f"arm {arm!r} makes construction gold visible to the frozen core, so its "
                f"split identity must be a committed roster_role='construction' roster "
                f"of carrier {plan.carrier_lock_key!r}; "
                f"{plan.split_identity_hash!r} is not one of "
                f"{sorted(hashes.values()) or 'any (none committed)'}; model touch refused"
            )

    # ------------------------------------------------------------------ #
    # The final-reporting read (owner decisions 99 and 107; decision 108)
    # ------------------------------------------------------------------ #

    def _carrier_roster_receipts(
        self, carrier_lock_key: str
    ) -> list[tuple[str, Mapping[str, object], frozenset[str], str]]:
        """``(relpath, document, sample ids, recomputed identity hash)`` for every
        committed roster receipt of one carrier.

        The identity hash is recomputed from the receipt's OWN items with the
        same four-line convention every identity check in this package uses --
        sha256 over the LF-joined, sorted, carrier-prefixed
        ``f"{lock_key}/{sample_id}"`` ids -- and a receipt whose recorded hash
        disagrees is refused as tampered. Deliberately separate from
        :meth:`_construction_roster_identity_hashes`, which is on the hot path
        of every construction-visible touch and must keep looking at
        construction receipts only.
        """

        directory = Path(self.source_root) / ROSTER_RECEIPTS_RELDIR
        rows: list[tuple[str, Mapping[str, object], frozenset[str], str]] = []
        if not directory.is_dir():
            return rows
        for path in sorted(directory.glob("*.json")):
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                raise GateClosed(f"roster receipt unreadable ({path}): {error}") from error
            if not isinstance(document, Mapping):
                raise GateClosed(f"roster receipt {path} must be a JSON object")
            if document.get("carrier_lock_key") != carrier_lock_key:
                continue
            if document.get("schema") != ROSTER_RECEIPT_SCHEMA:
                raise GateClosed(
                    f"roster receipt {path} schema {document.get('schema')!r} is not "
                    f"{ROSTER_RECEIPT_SCHEMA!r}"
                )
            items = document.get("items")
            if not isinstance(items, list) or not items:
                raise GateClosed(f"roster receipt {path} has no items")
            ids: list[str] = []
            for item in items:
                if not isinstance(item, Mapping):
                    raise GateClosed(f"roster receipt {path} has a malformed item")
                sample_id = item.get("sample_id")
                if not isinstance(sample_id, str) or not sample_id:
                    raise GateClosed(f"roster receipt {path} has an item with no sample_id")
                ids.append(sample_id)
            if len(set(ids)) != len(ids):
                raise GateClosed(f"roster receipt {path} repeats a sample_id")
            measured = hashlib.sha256(
                "\n".join(sorted(f"{carrier_lock_key}/{value}" for value in ids)).encode(
                    "utf-8"
                )
            ).hexdigest()
            if measured != document.get("split_identity_hash"):
                raise GateClosed(
                    f"roster receipt {path} split_identity_hash does not match the hash "
                    "recomputed from its own items; refusing a tampered receipt"
                )
            rows.append(
                (
                    str(Path(path).relative_to(Path(self.source_root)).as_posix()),
                    document,
                    frozenset(ids),
                    measured,
                )
            )
        return rows

    def _final_report_roster(
        self,
        plan: "ExecutionPlan",
        receipts: list[tuple[str, Mapping[str, object], frozenset[str], str]] | None = None,
    ) -> tuple[str, Mapping[str, object], frozenset[str]]:
        """The ONE committed ``split_role: final-report`` roster of the plan's
        carrier whose recomputed identity is the plan's own, as
        ``(relpath, receipt document, sample ids)``.

        ``receipts`` lets a caller that has already parsed the carrier's
        receipts (:meth:`_require_final_report_isolation`) pass them in instead
        of paying for the parse twice; ``None`` parses them here."""

        if receipts is None:
            receipts = self._carrier_roster_receipts(plan.carrier_lock_key)
        matches = [
            (relpath, document, ids)
            for relpath, document, ids, measured in receipts
            if document.get("split_role") == FINAL_REPORT_SPLIT_ROLE
            and measured == plan.split_identity_hash
        ]
        if len(matches) != 1:
            raise GateClosed(
                f"a {FINAL_REPORT_SPLIT_ROLE!r} plan's split identity must be that of "
                f"exactly ONE committed roster receipt of carrier "
                f"{plan.carrier_lock_key!r} whose own split_role is "
                f"{FINAL_REPORT_SPLIT_ROLE!r}; {plan.split_identity_hash!r} matches "
                f"{len(matches)}; model touch refused"
            )
        return matches[0]

    # ------------------------------------------------------------------ #
    # Declared partitions of a final-report roster (owner decision 147)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _declared_partition(
        document: Mapping[str, object], relpath: str
    ) -> tuple[Mapping[str, object] | None, tuple[Mapping[str, object], ...]]:
        """``(parent declaration, sibling declarations)`` read off a roster
        receipt's ``derived_from`` block, or ``(None, ())`` when the receipt
        declares no partition at all.

        A partitioned roster (``scripts/build_slurp_test_sample_roster.py``)
        writes ``derived_from.source_roster`` (the parent) and
        ``derived_from.sibling_roster`` (one mapping, or a list of mappings for
        a partition into more than two parts), each naming a
        ``split_identity_hash``. Half a declaration -- a parent without a
        sibling or a sibling without a parent -- is refused rather than read as
        "no partition": it can only come from a hand-edited receipt.
        """

        derived = document.get("derived_from")
        if not isinstance(derived, Mapping):
            return None, ()
        parent = derived.get(PARTITION_PARENT_KEY)
        siblings_raw = derived.get(PARTITION_SIBLING_KEY)
        if parent is None and siblings_raw is None:
            return None, ()
        if not isinstance(parent, Mapping) or siblings_raw is None:
            raise GateClosed(
                f"roster receipt {relpath} declares half a partition: derived_from must "
                f"carry BOTH a {PARTITION_PARENT_KEY!r} mapping and a "
                f"{PARTITION_SIBLING_KEY!r} mapping (or list of mappings); model touch "
                "refused"
            )
        siblings = (
            tuple(siblings_raw) if isinstance(siblings_raw, list) else (siblings_raw,)
        )
        if not siblings or any(not isinstance(value, Mapping) for value in siblings):
            raise GateClosed(
                f"roster receipt {relpath} derived_from.{PARTITION_SIBLING_KEY} must be a "
                "mapping or a non-empty list of mappings; model touch refused"
            )
        return parent, siblings

    @staticmethod
    def _declared_identity(
        declaration: Mapping[str, object], what: str, relpath: str
    ) -> str:
        value = declaration.get("split_identity_hash")
        if not isinstance(value, str) or _SHA256_HEX.fullmatch(value) is None:
            raise GateClosed(
                f"roster receipt {relpath} declares a {what} without a 64-hex "
                "split_identity_hash; model touch refused"
            )
        return value

    @staticmethod
    def _label(document: Mapping[str, object], measured: str) -> str:
        roster_id = document.get("roster_id")
        return (
            f"{roster_id} ({measured[:12]}...)"
            if isinstance(roster_id, str) and roster_id
            else f"({measured[:12]}...)"
        )

    def _require_items_partition(
        self,
        relpath: str,
        whole_label: str,
        whole_ids: frozenset[str],
        parts: list[tuple[str, frozenset[str]]],
    ) -> None:
        """Prove from item lists that ``parts`` partition ``whole_ids``:
        pairwise disjoint, and their union is exactly the whole (no id short,
        no id surplus). Set equality of the carrier-prefixed ids implies
        equality of the identity hashes by construction, and is the stronger
        statement, so the ids are compared and no hash is trusted."""

        for index, (left_label, left_ids) in enumerate(parts):
            for right_label, right_ids in parts[index + 1 :]:
                shared = left_ids & right_ids
                if shared:
                    raise GateClosed(
                        f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} roster "
                        f"{relpath}: partition members {left_label} and {right_label} share "
                        f"{len(shared)} sample id(s) (first: {sorted(shared)[:3]}); model "
                        "touch refused"
                    )
        union: set[str] = set()
        for _label, ids in parts:
            union |= ids
        missing = whole_ids - union
        if missing:
            raise GateClosed(
                f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} roster "
                f"{relpath}: the union of {[label for label, _ids in parts]} is short of "
                f"the declared parent {whole_label} by {len(missing)} sample id(s) (first: "
                f"{sorted(missing)[:3]}); model touch refused"
            )
        surplus = union - whole_ids
        if surplus:
            raise GateClosed(
                f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} roster "
                f"{relpath}: {len(surplus)} sample id(s) of "
                f"{[label for label, _ids in parts]} are not in the declared parent "
                f"{whole_label} (first: {sorted(surplus)[:3]}); model touch refused"
            )

    def _final_report_partition_exemptions(
        self,
        plan: "ExecutionPlan",
        relpath: str,
        document: Mapping[str, object],
        roster_ids: frozenset[str],
        receipts: list[tuple[str, Mapping[str, object], frozenset[str], str]],
    ) -> dict[str, str]:
        """``{identity hash: relpath}`` of the committed receipts the roster
        intersection of :meth:`_require_final_report_disjointness` may skip,
        each one EARNED from committed item lists, never from a recorded hash.

        Owner decision 147 (2026-09-27; design record
        ``docs/readiness/2026-09-27-slurp-test-sample-design-v1.md`` section
        7.3): a test SAMPLE and its CLOSURE complement partition the frozen
        FULL test roster, so each shares every one of its ids with the parent by
        construction. The exemption is narrow and symmetric:

        * **the roster is a declared partition member** -- its receipt names a
          parent (``derived_from.source_roster``) and sibling(s)
          (``derived_from.sibling_roster``). The parent and every sibling must
          be committed ``final-report`` receipts of the same carrier found by
          their RECOMPUTED identity; every sibling must itself declare the same
          parent and declare this roster (and the other siblings) as ITS
          siblings; a declared ``roster_id``/``repo_relpath``/file ``sha256``
          of the parent must match the committed file; and the item lists must
          prove that the roster and every sibling are pairwise disjoint and
          that their union is exactly the parent (no id short, no id surplus).
          Then the parent and the siblings are skipped;
        * **the roster is a declared parent** -- other committed receipts of
          the carrier declare it as their ``source_roster``. All of them must be
          ``final-report``, each must declare exactly the others as its
          siblings, and their item lists must prove they partition this roster.
          Then those children are skipped.

        Anything else -- a roster that declares nothing and is declared by
        nothing -- gets an empty mapping and the intersection runs exactly as
        before. Any declared partition that does not prove is a REFUSAL naming
        the identity that failed, never a fall-through: a roster that asks for
        the exemption and cannot earn it does not fly.
        """

        by_hash = {
            measured: (other_relpath, other_document, other_ids)
            for other_relpath, other_document, other_ids, measured in receipts
        }
        exempt: dict[str, str] = {}

        def committed_final_report(
            declared_hash: str, what: str
        ) -> tuple[str, Mapping[str, object], frozenset[str]]:
            found = by_hash.get(declared_hash)
            if found is None:
                raise GateClosed(
                    f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} roster "
                    f"{relpath}: declared {what} ({declared_hash[:12]}...) is not a "
                    f"committed roster receipt of carrier {plan.carrier_lock_key!r} (by "
                    "recomputed identity); model touch refused"
                )
            found_relpath, found_document, _found_ids = found
            if found_document.get("split_role") != FINAL_REPORT_SPLIT_ROLE:
                raise GateClosed(
                    f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} roster "
                    f"{relpath}: declared {what} "
                    f"{self._label(found_document, declared_hash)} at {found_relpath} "
                    f"has split_role {found_document.get('split_role')!r}, not "
                    f"{FINAL_REPORT_SPLIT_ROLE!r}; a partition of a final-reporting "
                    "roster is final-reporting in every part; model touch refused"
                )
            return found

        def require_declared_fields(
            declaration: Mapping[str, object],
            what: str,
            found_relpath: str,
            found_document: Mapping[str, object],
        ) -> None:
            declared_id = declaration.get("roster_id")
            if declared_id is not None and declared_id != found_document.get("roster_id"):
                raise GateClosed(
                    f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} roster "
                    f"{relpath}: declared {what} roster_id {declared_id!r} is not the "
                    f"committed receipt's {found_document.get('roster_id')!r} at "
                    f"{found_relpath}; model touch refused"
                )
            declared_relpath = declaration.get("repo_relpath")
            if declared_relpath is not None and declared_relpath != found_relpath:
                raise GateClosed(
                    f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} roster "
                    f"{relpath}: declared {what} repo_relpath {declared_relpath!r} is not "
                    f"where the committed receipt of that identity lives ({found_relpath}); "
                    "model touch refused"
                )
            declared_sha = declaration.get("sha256")
            if declared_sha is not None:
                actual = hashlib.sha256(
                    (Path(self.source_root) / found_relpath).read_bytes()
                ).hexdigest()
                if actual != declared_sha:
                    raise GateClosed(
                        f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} "
                        f"roster {relpath}: declared {what} file sha256 {declared_sha!r} "
                        f"is not the committed bytes of {found_relpath} ({actual}); model "
                        "touch refused"
                    )

        def sibling_hashes_of(
            other_relpath: str, other_document: Mapping[str, object]
        ) -> tuple[str, frozenset[str]]:
            """``(declared parent hash, declared sibling hashes)`` of another
            receipt, both required to be present."""

            parent_declaration, sibling_declarations = self._declared_partition(
                other_document, other_relpath
            )
            if parent_declaration is None:
                raise GateClosed(
                    f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} roster "
                    f"{relpath}: committed receipt {other_relpath} declares no partition "
                    "of its own, so it cannot be this roster's sibling; model touch refused"
                )
            return (
                self._declared_identity(parent_declaration, "parent", other_relpath),
                frozenset(
                    self._declared_identity(value, "sibling", other_relpath)
                    for value in sibling_declarations
                ),
            )

        own_label = self._label(document, plan.split_identity_hash)

        # (a) this roster declares a parent and sibling(s).
        parent_declaration, sibling_declarations = self._declared_partition(document, relpath)
        if parent_declaration is not None:
            parent_hash = self._declared_identity(parent_declaration, "parent", relpath)
            if parent_hash == plan.split_identity_hash:
                raise GateClosed(
                    f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} roster "
                    f"{relpath}: it declares ITSELF as its parent; model touch refused"
                )
            parent_relpath, parent_document, parent_ids = committed_final_report(
                parent_hash, "parent"
            )
            require_declared_fields(parent_declaration, "parent", parent_relpath, parent_document)
            parent_label = self._label(parent_document, parent_hash)
            declared_sibling_hashes = tuple(
                self._declared_identity(value, "sibling", relpath) for value in sibling_declarations
            )
            if len(set(declared_sibling_hashes)) != len(declared_sibling_hashes):
                raise GateClosed(
                    f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} roster "
                    f"{relpath}: a sibling is declared twice; model touch refused"
                )
            parts: list[tuple[str, frozenset[str]]] = [(own_label, roster_ids)]
            members: dict[str, str] = {}
            for declaration, sibling_hash in zip(sibling_declarations, declared_sibling_hashes):
                if sibling_hash in (plan.split_identity_hash, parent_hash):
                    raise GateClosed(
                        f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} roster "
                        f"{relpath}: declared sibling ({sibling_hash[:12]}...) is the roster "
                        "itself or its parent; model touch refused"
                    )
                sibling_relpath, sibling_document, sibling_ids = committed_final_report(
                    sibling_hash, "sibling"
                )
                require_declared_fields(declaration, "sibling", sibling_relpath, sibling_document)
                sibling_label = self._label(sibling_document, sibling_hash)
                # Mutual declaration: the sibling names the same parent and
                # names this roster (and every other sibling) as its siblings.
                their_parent, their_siblings = sibling_hashes_of(sibling_relpath, sibling_document)
                if their_parent != parent_hash:
                    raise GateClosed(
                        f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} roster "
                        f"{relpath}: declared sibling {sibling_label} at {sibling_relpath} "
                        f"declares parent ({their_parent[:12]}...), not this roster's parent "
                        f"{parent_label}; model touch refused"
                    )
                expected = (set(declared_sibling_hashes) - {sibling_hash}) | {
                    plan.split_identity_hash
                }
                if set(their_siblings) != expected:
                    raise GateClosed(
                        f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} roster "
                        f"{relpath}: declared sibling {sibling_label} at {sibling_relpath} "
                        f"does not declare this roster {own_label} (and the other declared "
                        "siblings) as its own siblings; the declaration is not mutual; model "
                        "touch refused"
                    )
                parts.append((sibling_label, sibling_ids))
                members[sibling_hash] = sibling_relpath
            self._require_items_partition(relpath, parent_label, parent_ids, parts)
            exempt[parent_hash] = parent_relpath
            exempt.update(members)

        # (b) other committed receipts declare THIS roster as their parent.
        children: list[tuple[str, Mapping[str, object], frozenset[str], str]] = []
        for other_relpath, other_document, other_ids, measured in receipts:
            if measured == plan.split_identity_hash:
                continue
            derived = other_document.get("derived_from")
            if not isinstance(derived, Mapping):
                continue
            declared_parent = derived.get(PARTITION_PARENT_KEY)
            if (
                isinstance(declared_parent, Mapping)
                and declared_parent.get("split_identity_hash") == plan.split_identity_hash
            ):
                children.append((other_relpath, other_document, other_ids, measured))
        if children:
            child_hashes = {measured for _r, _d, _i, measured in children}
            parts = []
            for child_relpath, child_document, child_ids, child_hash in children:
                child_label = self._label(child_document, child_hash)
                if child_document.get("split_role") != FINAL_REPORT_SPLIT_ROLE:
                    raise GateClosed(
                        f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} roster "
                        f"{relpath}: committed receipt {child_label} at {child_relpath} "
                        f"declares this roster as its parent but has split_role "
                        f"{child_document.get('split_role')!r}, not "
                        f"{FINAL_REPORT_SPLIT_ROLE!r}; model touch refused"
                    )
                parent_declaration_of_child, _sibling_declarations = self._declared_partition(
                    child_document, child_relpath
                )
                assert parent_declaration_of_child is not None  # selected on it above
                require_declared_fields(
                    parent_declaration_of_child, "parent", relpath, document
                )
                _their_parent, their_siblings = sibling_hashes_of(child_relpath, child_document)
                if set(their_siblings) != child_hashes - {child_hash}:
                    raise GateClosed(
                        f"partition proof failed for the {FINAL_REPORT_SPLIT_ROLE!r} roster "
                        f"{relpath}: child {child_label} at {child_relpath} declares "
                        f"siblings {sorted(value[:12] for value in their_siblings)}, not "
                        "exactly the other committed receipts that declare this roster as "
                        f"their parent {sorted(value[:12] for value in child_hashes - {child_hash})}; "
                        "model touch refused"
                    )
                parts.append((child_label, child_ids))
            self._require_items_partition(relpath, own_label, roster_ids, parts)
            for child_relpath, _d, _i, child_hash in children:
                exempt[child_hash] = child_relpath
        return exempt

    @staticmethod
    def _bytes_contain_any(path: Path, needles: tuple[bytes, ...]) -> bool:
        """Stream ``path`` and report whether any needle occurs in its bytes.

        A superset test that costs one sequential read and no JSON parse: if a
        knowledge snapshot's bytes do not contain the roster's carrier/split id
        prefix, no roster id can be inside it and the exact intersection can be
        skipped. Chunks overlap by ``max(len(needle)) - 1`` so a needle
        straddling a chunk boundary is still found.
        """

        if not needles:
            return False
        overlap = max(len(needle) for needle in needles) - 1
        tail = b""
        with Path(path).open("rb") as handle:
            while True:
                chunk = handle.read(1 << 20)
                if not chunk:
                    return False
                window = tail + chunk
                if any(needle in window for needle in needles):
                    return True
                tail = window[-overlap:] if overlap else b""

    def _require_final_report_disjointness(
        self,
        plan: "ExecutionPlan",
        relpath: str,
        roster_ids: frozenset[str],
        document: Mapping[str, object] | None = None,
        receipts: list[tuple[str, Mapping[str, object], frozenset[str], str]] | None = None,
    ) -> None:
        """Re-prove, at gate time, that nothing the control plane was built from
        intersects the final-reporting roster.

        A committed disjointness receipt is a record, not a proof: it could have
        been minted before a store was rebuilt. So the ids are intersected here,
        against every other committed roster receipt of the carrier (construction
        rosters, exemplar-pool rosters and every other roster alike) and against
        every knowledge store / exemplar pool snapshot under the controlled data
        root. Only ``source_sample_ids`` is taken from a snapshot; its ``values``
        and ``facets`` blocks -- which carry the construction gold -- are never
        inspected.

        The ONE exception (owner decision 147, 2026-09-27) is a receipt that this
        roster is proven -- from committed item lists, by
        :meth:`_final_report_partition_exemptions` -- to partition or be
        partitioned by: its declared parent and sibling(s), or its declared
        children. Those receipts overlap this roster by construction and only
        they are skipped; every other receipt, and every snapshot, is
        intersected exactly as before. ``document`` and ``receipts`` are the
        roster's own receipt and the carrier's parsed receipts when the caller
        already holds them; either may be ``None`` and is then looked up here.
        """

        if receipts is None:
            receipts = self._carrier_roster_receipts(plan.carrier_lock_key)
        if document is None:
            document = next(
                other_document
                for _other_relpath, other_document, _other_ids, measured in receipts
                if measured == plan.split_identity_hash
            )
        exempt = self._final_report_partition_exemptions(
            plan, relpath, document, roster_ids, receipts
        )
        for other_relpath, _document, other_ids, measured in receipts:
            if measured == plan.split_identity_hash:
                continue
            if measured in exempt:
                # Proven partition member (parent, sibling or child): the
                # overlap is the roster itself by construction. Nothing else
                # is ever skipped.
                continue
            shared = roster_ids & other_ids
            if shared:
                raise GateClosed(
                    f"the {FINAL_REPORT_SPLIT_ROLE!r} roster {relpath} shares "
                    f"{len(shared)} sample id(s) with the committed roster "
                    f"{other_relpath} (first: {sorted(shared)[:3]}); a final-reporting "
                    "read may never overlap a roster the control plane was built or "
                    "optimized on; model touch refused"
                )

        prefixes = tuple(
            sorted(
                {
                    ":".join(value.split(":")[:2]).encode("utf-8") + b":"
                    for value in roster_ids
                    if value.count(":") >= 2
                }
            )
        )
        base = Path(self.data_root) / "knowledge" / plan.carrier_lock_key
        if not base.is_dir():
            return
        for path in sorted(base.rglob("snapshot.json")):
            if not self._bytes_contain_any(path, prefixes):
                continue
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                raise GateClosed(
                    f"knowledge snapshot unreadable ({path}): {error}"
                ) from error
            source_ids = (
                document.get("source_sample_ids") if isinstance(document, Mapping) else None
            )
            if not isinstance(source_ids, list):
                continue
            shared = roster_ids & {str(value) for value in source_ids}
            if shared:
                raise GateClosed(
                    f"the {FINAL_REPORT_SPLIT_ROLE!r} roster {relpath} shares "
                    f"{len(shared)} sample id(s) with the knowledge store / exemplar pool "
                    f"{path} (first: {sorted(shared)[:3]}); model touch refused"
                )

    def _declared_resume_predecessors(
        self, plan: "ExecutionPlan", states: Mapping[str, str]
    ) -> frozenset:
        """The interrupted attempts of ``plan.run_id`` that ``plan.attempt_id``
        resumes, read from ``runs/<run>/<attempt>/resume-declaration.json``
        (written by ``core.flight.runtime`` before its first gate touch).

        Refuses, by name, a declaration that names this attempt itself, an
        attempt that has no record, or one that is FINALIZED. Empty (the
        non-resume case) when the file is absent.
        """

        path = (
            Path(self.data_root) / "runs" / plan.run_id / str(plan.attempt_id)
            / "resume-declaration.json"
        )
        if not path.is_file():
            return frozenset()
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise GateClosed(f"resume declaration unreadable ({path}): {error}") from error
        entries = document.get("predecessors") if isinstance(document, Mapping) else None
        if (
            not isinstance(document, Mapping)
            or document.get("schema") != "saea-resume-declaration-v1"
            or document.get("run_id") != plan.run_id
            or document.get("attempt_id") != plan.attempt_id
            or not isinstance(entries, list)
            or not entries
        ):
            raise GateClosed(f"resume declaration {path} is malformed or names another attempt")
        names = []
        for entry in entries:
            name = entry.get("attempt_id") if isinstance(entry, Mapping) else None
            if not isinstance(name, str) or not name or name == plan.attempt_id:
                raise GateClosed(f"resume declaration {path} names an invalid predecessor")
            if name not in states:
                raise GateClosed(
                    f"resume declaration {path} names attempt {name!r}, which has no attempt record"
                )
            if states[name] == "FINALIZED":
                raise GateClosed(
                    f"attempt {plan.run_id!r}/{name!r} is FINALIZED; a settled attempt is "
                    "consumed and cannot be resumed; model touch refused"
                )
            names.append(name)
        return frozenset(names)

    def _require_final_report_attempt_budget(
        self, plan: "ExecutionPlan", allowance: Mapping[str, object]
    ) -> None:
        """ONE sealed attempt per permitted READ run id; one recovery for a
        preparation run id.

        Protocol section 4.4: "No repeat, no second configuration, no best-of."
        A second attempt of the one read is refused even as a recovery -- the
        resume clause of section 7 is a decision the owner takes by registering
        a fresh run id, never something this gate lets through. The preparation
        passes are label-free encoder work and keep the ordinary one-recovery
        budget the rest of this repository uses.

        One narrow exception (owner decision 309, 2026-10-14): an attempt that
        RESUMES an interrupted, never-FINALIZED attempt of the same run --
        declared in its own ``resume-declaration.json``, keeping that attempt's
        complete rows and flying only the rows it never completed -- takes the
        interrupted attempt's slot (:meth:`_declared_resume_predecessors`). It is
        still one attempt, flies no row twice and selects nothing; a fresh
        attempt that declares no predecessor is counted exactly as before.
        """

        read_ids = {
            str(value) for value in (allowance.get("read_run_ids") or ()) if value
        }
        is_read = plan.run_id in read_ids
        limit = 1 if is_read else 2
        kind = "read" if is_read else "preparation"
        directory = Path(self.data_root) / "attempts" / plan.run_id
        states: dict[str, str] = {}
        if directory.is_dir():
            for path in sorted(directory.glob("*.json")):
                try:
                    document = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError) as error:
                    raise GateClosed(
                        f"attempt record unreadable ({path}): {error}"
                    ) from error
                states[path.stem] = str(
                    document.get("state") if isinstance(document, Mapping) else "UNKNOWN"
                )
        own = plan.attempt_id
        # Owner decision 309 (2026-10-14): a RESUME of an interrupted attempt
        # (a crash -- power loss, host restart -- leaves the attempt OPENED with
        # no manifest) takes over that attempt's slot instead of being counted
        # as a second attempt. The exemption is deliberately narrow: it applies
        # only to attempts the plan's own attempt directory declares in
        # ``resume-declaration.json``, never to a FINALIZED one (a settled read
        # is consumed), and the resume still counts as ONE attempt. A fresh
        # attempt that declares nothing is counted exactly as before.
        superseded = self._declared_resume_predecessors(plan, states)
        counted = {name: state for name, state in states.items() if name not in superseded}
        distinct = len(counted) + (1 if own is not None and own not in counted else 0)
        if distinct > limit:
            raise GateClosed(
                f"{FINAL_REPORT_SPLIT_ROLE!r} {kind} run {plan.run_id!r} allows at most "
                f"{limit} attempt(s); attempts {sorted(states)} already exist and this "
                f"plan declares {own!r}; model touch refused (protocol section 4.4: no "
                "repeat, no second configuration, no best-of)"
            )
        if own is not None and states.get(own) in {"FINALIZED", "ABORTED"}:
            raise GateClosed(
                f"attempt {plan.run_id!r}/{own!r} is already {states[own]}; a "
                f"{FINAL_REPORT_SPLIT_ROLE!r} {kind} attempt is never re-flown; model "
                "touch refused"
            )

    def _require_final_report_isolation(
        self, plan: "ExecutionPlan", arm: str | None
    ) -> None:
        """Everything a ``final-report`` touch must satisfy beyond its plan.

        Returns immediately for every other split role, so no pre-existing
        caller's behaviour changes. Owner decisions 99 and 107; one-shot read
        protocol ``docs/readiness/2026-09-19-slurp-test-split-one-read-protocol
        -v1-draft.md`` sections 2.3, 4.4 and 6.3.
        """

        if plan.split_role != FINAL_REPORT_SPLIT_ROLE:
            return
        allowance = require_owner_split_allowance(
            run_id=plan.run_id,
            execution_profile=plan.execution_profile,
            carrier_lock_key=plan.carrier_lock_key,
            split_identity_hash=plan.split_identity_hash,
            owner_allowance=plan.owner_allowance,
            source_root=self.source_root,
        )
        if arm is not None and arm in CONSTRUCTION_VISIBLE_ARMS:
            raise GateClosed(
                f"arm {arm!r} makes construction gold visible to the frozen core and may "
                f"only fly on a construction roster of a discovery split; a "
                f"{FINAL_REPORT_SPLIT_ROLE!r} plan can never carry it; model touch refused"
            )
        receipts = self._carrier_roster_receipts(plan.carrier_lock_key)
        relpath, document, roster_ids = self._final_report_roster(plan, receipts)
        self._require_final_report_disjointness(
            plan, relpath, roster_ids, document=document, receipts=receipts
        )
        self._require_final_report_attempt_budget(plan, allowance)

    def _require_exposure_preregistration(
        self, plan: "ExecutionPlan", lock: Mapping[str, object] | None = None
    ) -> None:
        """The pre-registered row is cross-checked field by field against the plan.

        A run id string alone proves nothing: the row must have been written with
        the same profile, split role, split identity hash and budgets the plan now
        claims, and must still read ``consumed = no``. EVERY markdown table in the
        ledger whose header carries the contract's run-id column contributes rows
        (I2) -- a second table, or a stray prose line between two data rows of one
        table, can never make a registered row invisible to the duplicate/consumed/
        budget checks below."""

        try:
            text = Path(self.exposure_ledger).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise GateClosed(
                f"exposure ledger missing or unreadable ({self.exposure_ledger}): {error}"
            ) from error
        rows = _parse_ledger_tables(text)

        def cell(row: Mapping[str, str], column_name: str) -> str:
            if column_name not in row:
                raise GateClosed(
                    f"exposure row lacks column {column_name!r} (its governing table "
                    "header does not declare it)"
                )
            return row[column_name]

        matched = [row for row in rows if cell(row, _EXPOSURE_RUN_COLUMN) == plan.run_id]
        if not matched:
            raise GateClosed(
                f"model touch refused: run {plan.run_id!r} has no pre-registered exposure "
                f"row in {self.exposure_ledger} (rows are written before results are read)"
            )
        if len(matched) > 1:
            raise GateClosed(f"run {plan.run_id!r} is pre-registered more than once")
        row = matched[0]
        for column_name, expected in (
            ("execution profile", plan.execution_profile),
            ("split role", plan.split_role),
            ("split identity hash", plan.split_identity_hash),
        ):
            actual = cell(row, column_name)
            if actual != expected:
                raise GateClosed(
                    f"exposure row disagrees with the execution plan on {column_name!r}: "
                    f"row {actual!r} vs plan {expected!r}; model touch refused"
                )
        carrier_cell = cell(row, _EXPOSURE_CARRIER_COLUMN)
        known_carrier_keys = set(self._lock_dataset_entries(lock))
        carrier_tokens = [
            token for token in _CARRIER_CELL_TOKEN_SPLIT.split(carrier_cell) if token
        ]
        named_carriers = [token for token in carrier_tokens if token in known_carrier_keys]
        if len(named_carriers) != 1:
            raise GateClosed(
                f"exposure row column {_EXPOSURE_CARRIER_COLUMN!r} ({carrier_cell!r}) must "
                "name exactly one known carrier lock key unambiguously; found "
                f"{named_carriers or 'none'}; model touch refused (I2: ambiguous carrier "
                "metadata fails closed)"
            )
        if named_carriers[0] != plan.carrier_lock_key:
            raise GateClosed(
                f"exposure row column {_EXPOSURE_CARRIER_COLUMN!r} names carrier "
                f"{named_carriers[0]!r}, not the execution plan's carrier "
                f"{plan.carrier_lock_key!r}; model touch refused (I2: carrier scope and "
                "exposure carrier must bind)"
            )
        if cell(row, "consumed").lower() != "no":
            raise GateClosed(
                f"exposure row for {plan.run_id!r} is already consumed; a consumed run "
                "cannot be re-executed"
            )
        for column_name, planned, parse in (
            ("calls", plan.planned_model_calls, int),
            ("speech audio seconds", plan.planned_speech_audio_seconds, int),
            ("gpu hours", plan.planned_gpu_hours, float),
        ):
            raw = cell(row, column_name)
            try:
                registered = parse(raw)
            except ValueError as error:
                raise GateClosed(
                    f"exposure row column {column_name!r} must be a number, got {raw!r}"
                ) from error
            if not math.isfinite(registered) or registered < 0:
                raise GateClosed(
                    f"exposure row column {column_name!r} must be a finite non-negative "
                    f"number, got {raw!r}; NaN or negative cells would disable the "
                    "budget arithmetic"
                )
            if registered < planned:
                raise GateClosed(
                    f"execution plan claims {planned} {column_name} but only {registered} "
                    "were pre-registered; model touch refused"
                )
        # Owner amendment 2026-08-06 (SAEA-OWNER-AMENDMENT-2026-08-06-BUDGET-CAPS):
        # the slice-wide summation that used to run here -- summing every
        # registered row plus AttemptStore.all_actual_usage()'s durable actuals and
        # refusing a campaign total over the frozen first-slice caps -- is retired.
        # What remains, checked above, is per-row: the matched row's registered
        # calls/speech-audio-seconds/gpu-hours must each be >= this plan's own
        # declared values, and the row itself must be unconsumed. See
        # docs/engineering.md and the amendment record for the full rationale.
