"""Append a NOT-FLOWN pre-flight note to the SAEA-BASE-a2t-a0-400 notes cell.

Same discipline as the P-SLU row's own "Pre-flight registration repair 2026-08-17
(before any core contact, row still unconsumed)" annotation: the row stays
registered and unconsumed, no registered identity or budget changes, and the
reason the flight did not proceed is on the row itself rather than only in a
check directory.
"""

from __future__ import annotations

import io
from pathlib import Path

LEDGER = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/"
    "speech-aware-evidence-acquisition/docs/exposure-ledger.md"
)

ANCHOR = "Audio2Tool license cc-by-nc-4.0 carried on audio-derived results. |"

NOTE = (
    "Audio2Tool license cc-by-nc-4.0 carried on audio-derived results. "
    "**2026-08-18 PRE-FLIGHT CLOSED, NOT FLOWN -- zero core contact; row stays registered "
    "and unconsumed.** Every model-free precondition passed (frozen split resolves 400/400 "
    "with the receipt hash matching the ledger cell verbatim, real audio total measured at "
    "2159.69 s, D1 verify_media_identity('audio2tool') PASS on real frozen-split samples with "
    "the unlisted-id negative control refusing, 0 .pyc under src/, campaign feature cache cold "
    "and isolated, ExecutionPlan valid, payload binding built over all 400 ids, tests/contract "
    "260 passed). The model-free gate dry-run "
    "(contracts.FrozenCoreGate.assert_model_touch_allowed, which opens no socket) REFUSED: "
    "carrier lock key 'audio2tool' profiles ['local-candidates'] do not intersect this study's "
    "speech-only scope. The umbrella lock still files Audio2Tool as LOCAL_CANDIDATE, a profile "
    "whose own catalog description reads 'presence does not authorize an experiment'; "
    "ALLOWED_CARRIER_PROFILES is a literal frozenset with no override, hook or allowlist, and "
    "the gate fails closed on a missing profiles field too, so there is no bypass by "
    "construction. A four-carrier control confirms the refusal is carrier-specific: slurp, "
    "earnings21-original and conec all resolve IN SCOPE through the same call. Repairing this "
    "in flight is forbidden to the flying agent by docs/readiness/HANDOVER.md lines 100-103, "
    "which names audio2tool explicitly and requires the umbrella's formal path plus owner "
    "approval for a lock data-identity change; the decision is already parked as an owner item "
    "at docs/readiness/2026-08-11-validation-plan-wa-wd.md line 141 (lock-profile batch). "
    "Awaiting that decision. Full evidence and the ready-to-fly launcher: "
    "docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-flight/. |"
)


def main() -> int:
    text = LEDGER.read_text(encoding="utf-8")
    if "PRE-FLIGHT CLOSED, NOT FLOWN" in text:
        print("REFUSED: the row is already annotated")
        return 1
    if text.count(ANCHOR) != 1:
        print(f"REFUSED: anchor appears {text.count(ANCHOR)} times, expected exactly 1")
        return 1
    if "|" in NOTE[:-1]:
        print("REFUSED: the note body contains a pipe character")
        return 1
    with io.open(LEDGER, "w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace(ANCHOR, NOTE))
    print("row annotated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
