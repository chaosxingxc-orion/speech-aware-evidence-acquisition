"""``BaseAudioModel.parse_tool_call`` from the pinned Audio2Tool release,
vendored as a module-level function.

Upstream: https://github.com/audio2tool/Audio2Tool, MIT License,
Copyright (c) 2026 Audio2Tool Authors. Pinned commit
``b9d5383ca30945fbafb965a04bea40117e1e8a82``; the source method lives in
``audio_benchmark/models/base.py``, git blob SHA-1
``977ce0cdde41b44b35ee2e6f43808d4eb16fec96``.

The function below is the upstream method's own text, dedented by one level
and with the bound ``self`` parameter removed -- nothing else. That exact
derivation is re-applied against the local clone by
``tests/unit/test_audio2tool_official_scorer.py``, which fails if this file
and the clone ever disagree.

Why a module-level copy rather than an import: this repository never
installs the upstream package (its ``models/base.py`` imports torch at
module scope and its registry pulls in every model adapter), and the parse
rule is protocol, not machinery -- the replication's predicted tool name and
parameters must come from the published regexes, first-match semantics and
fallback included, not from a re-derivation of them.
"""

from typing import Any, Dict, Tuple

def parse_tool_call(raw_output: str) -> Tuple[str, str, Dict[str, Any]]:
    """
    Parse raw model output into structured tool call.

    Args:
        raw_output: Raw string output from the model

    Returns:
        Tuple of (tool_name, tool_call_string, parameters_dict)
    """
    import re

    # Default parsing logic - can be overridden by subclasses
    # Try to extract function call pattern: tool_name(param1=val1, param2=val2)
    pattern = r'(\w+)\s*\((.*?)\)'
    match = re.search(pattern, raw_output)

    if match:
        tool_name = match.group(1)
        params_str = match.group(2)
        tool_call = f"{tool_name}({params_str})"

        # Parse parameters
        params = {}
        if params_str.strip():
            # Handle both key=value and key='value' formats
            param_pattern = r"(\w+)\s*=\s*['\"]?([^,'\"]+)['\"]?"
            for param_match in re.finditer(param_pattern, params_str):
                key = param_match.group(1)
                value = param_match.group(2).strip()
                params[key] = value

        return tool_name, tool_call, params

    # Fallback: try to extract just tool name
    words = raw_output.split()
    for word in words:
        if word.endswith('()'):
            tool_name = word[:-2]
            return tool_name, word, {}

    return "", raw_output, {}
