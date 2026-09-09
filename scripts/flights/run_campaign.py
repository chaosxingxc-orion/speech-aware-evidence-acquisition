#!/usr/bin/env python3
"""Thin compatibility entry point for the shared config-driven campaign CLI."""
from speech_aware_evidence_acquisition.core.flight.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
