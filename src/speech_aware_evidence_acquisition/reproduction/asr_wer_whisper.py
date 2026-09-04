"""Whisper-normalizer WER support (consolidation slice C3b): paper-facing WER
convention for Earnings-21/22.

Most published ASR papers reporting WER on Earnings-21/22 (and on English ASR
benchmarks generally, following OpenAI's own Whisper paper/blog) first pass
BOTH the reference and hypothesis text through Whisper's
``EnglishTextNormalizer`` -- number expansion/contraction ("twenty" <->
"20"), contraction and honorific unification ("won't" -> "will not", "Mr."
-> "mister"), currency/percentage spelling, and British/American spelling
unification -- before computing word error rate. This module exists so this
study can report that SAME field-standard number, for direct comparability
with the literature, SIDE BY SIDE with its own frozen scoring stack.

This is deliberately an ADDITION, never a REPLACEMENT: the frozen
``scoring.normalize.normalize_text_v1``/``saea-scoring-v1`` stack (E0 D3
freeze) is this study's own primary, small, deterministic, stdlib-only
comparison substrate and stays exactly as it is -- ``asr-wer`` keeps
running unchanged. ``asr-wer-whisper`` (registered in ``core/scorers.py``,
see that module's own appended block) is a second, additional scorer that
happens to read the exact same outputs and the exact same gold reference
layer, normalized a different, richer way.

Vendored, read-only normalizer: ``reproduction/whisper_normalizer/`` is a
byte-exact copy of ``whisper/normalizers/`` from
https://github.com/openai/whisper at pinned tag ``v20240930`` (MIT license;
full provenance, per-file SHA-256, and the byte-exactness statement in that
package's own ``PROVENANCE.md``). This module is its only consumer.

Reference-resolution boundary (why the outputs-JSONL-reading, reference-
resolving orchestration is NOT here): ``data.references`` may be imported
ONLY by ``core/scorers.py`` (plus ``data/references.py`` itself) --
``tests/contract/test_reference_import_isolation.py`` AST-enforces that
across the whole ``src/`` tree, and this module is deliberately outside the
allowed set (same reasoning that already keeps ``score_asr_outputs`` and
``score_entity_wer_outputs`` themselves living directly in ``core/scorers.py``
rather than in a ``reproduction/`` module, despite the ``a2t-toolcall``/
``slurp-slu`` scorers living here -- those two never touch
``data.references`` at all, since their gold comes from
``data.audio2tool``/``data.slurp`` instead). ``score_asr_outputs_whisper``
therefore lives in ``core/scorers.py``'s own append-only block (mirroring
``score_asr_outputs``'s I/O shape exactly, per this slice's task brief),
importing ONLY the reference-free pieces from this module: the vendored
normalizer wrapper below.
"""

from __future__ import annotations

from .whisper_normalizer import EnglishTextNormalizer

WHISPER_WER_SCORER_VERSION = "asr-wer-whisper-v20240930"
WHISPER_NORMALIZER_NAME = "whisper-english-v20240930"

# One process-wide instance: EnglishTextNormalizer.__init__ parses
# english.json and compiles its contraction/prefix regex table once;
# constructing it per call would be wasteful and is unnecessary -- the
# vendored class carries no per-call mutable state (__call__ takes the text
# in, returns a new string, mutates nothing on self).
_ENGLISH_NORMALIZER = EnglishTextNormalizer()


def normalize_whisper_english(text: str) -> str:
    """Normalize ``text`` with the vendored, pinned Whisper
    ``EnglishTextNormalizer`` (``WHISPER_NORMALIZER_NAME``). Raises
    ``TypeError`` up front for a non-``str`` input -- the vendored
    normalizer itself would fail deeper and less legibly (e.g. inside a
    regex substitution) on the wrong type, same defensive posture as
    ``scoring.normalize.normalize_text_v1``."""

    if not isinstance(text, str):
        raise TypeError(f"normalize_whisper_english expects str, got {type(text).__name__}")
    return _ENGLISH_NORMALIZER(text)
