"""Invoke source-bound live speech span observation after native selection."""


TOOL_ID = "saea-tool-live-speech-span-v1"


def observe_live_speech_span(provider, context, arguments, source_response_sha256):
    """Return one validated span observation selected by the frozen core."""
    from ..tools import ToolResult

    selection = provider.observe_span(
        context=context,
        arguments=arguments,
        source_response_sha256=source_response_sha256,
    )
    provider.validate_span_selection(
        context=context,
        arguments=arguments,
        source_response_sha256=source_response_sha256,
        selection=selection,
    )
    return ToolResult(tool_id=TOOL_ID, result=selection)
