"""Vendored OpenAI Whisper text normalizer (reproduction/whisper_normalizer/):
byte-identity against the pinned upstream v20240930 copy, import shape, and
normalizer sanity/idempotence.

The exact outputs asserted below (numbers, contractions, currency,
British/American spelling) were verified by actually running the vendored
``EnglishTextNormalizer`` in this study's own WSL venv before being written
here -- never guessed from memory of the upstream README.
"""

import hashlib

import pytest

from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT
from speech_aware_evidence_acquisition.reproduction.whisper_normalizer import (
    BasicTextNormalizer,
    EnglishTextNormalizer,
)

VENDOR_DIR = (
    REPO_ROOT
    / "src"
    / "speech_aware_evidence_acquisition"
    / "reproduction"
    / "whisper_normalizer"
)

# Pinned upstream v20240930 SHA-256, matching this package's own PROVENANCE.md.
EXPECTED_SHA256 = {
    "__init__.py": "f18fcdce4caee7f2e80e4c01ab0457d3a080a872a29489542c6d23c4b0bba572",
    "basic.py": "ad567b3a0e1d03ccc0c35fc746fd6830c35290fe4ed7674eb61ce157ba3d380d",
    "english.py": "2898e4672aeefc9f44cb4de38c115cdf286f5b35ae321433467a7674ce8841d0",
    "english.json": "6607f948be9824d2e1b2fa2223cd94c06c45afa4e05ea0e3d5e1f2bdffde2465",
    "LICENSE": "b5d65a59060e68c4ff940e1eddfa6f94b2d68fdf58ed7f4dd57721c997e35e9d",
}


@pytest.mark.parametrize("filename, expected", sorted(EXPECTED_SHA256.items()))
def test_vendored_file_matches_pinned_upstream_sha256(filename, expected):
    digest = hashlib.sha256((VENDOR_DIR / filename).read_bytes()).hexdigest()
    assert digest == expected, (
        f"{filename} bytes have drifted from the pinned upstream v20240930 copy "
        "-- the vendored normalizer must never be edited in place"
    )


def test_vendored_package_exports_both_normalizers_unmodified():
    # english.py's `from .basic import remove_symbols_and_diacritics` and its
    # `os.path.join(os.path.dirname(__file__), "english.json")` lookup both
    # resolve correctly only because all four files still live together in
    # this same package directory -- this import succeeding at all is part
    # of what this test proves.
    assert BasicTextNormalizer.__name__ == "BasicTextNormalizer"
    assert EnglishTextNormalizer.__name__ == "EnglishTextNormalizer"


def test_english_normalizer_number_expansion():
    normalizer = EnglishTextNormalizer()
    assert normalizer("twenty three") == "23"
    assert normalizer("one oh one") == "101"


def test_english_normalizer_contraction():
    normalizer = EnglishTextNormalizer()
    assert normalizer("won't") == "will not"


def test_english_normalizer_title_and_currency():
    normalizer = EnglishTextNormalizer()
    assert normalizer("Mr. Smith's 2 dollars") == "mister smith is $2"


def test_english_normalizer_spelled_currency_merges_with_number():
    normalizer = EnglishTextNormalizer()
    assert normalizer("$20 million") == "$20000000"


def test_english_normalizer_british_to_american_spelling():
    normalizer = EnglishTextNormalizer()
    assert normalizer("colour centre theatre") == "color center theater"


@pytest.mark.parametrize(
    "text",
    [
        "Mr. Smith's 2 dollars",
        "twenty three",
        "won't",
        "colour centre theatre",
        "$20 million",
        "He's got 100 dollars, right?",
        "one oh one",
        "274th",
    ],
)
def test_english_normalizer_is_idempotent(text):
    normalizer = EnglishTextNormalizer()
    once = normalizer(text)
    twice = normalizer(once)
    assert once == twice
