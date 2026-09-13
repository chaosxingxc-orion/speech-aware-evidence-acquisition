"""Invoke the on-demand speech observation provider after native selection."""


TOOL_ID = "saea-tool-live-speech-observation-v1"


def observe_live_speech(provider, context, arguments, source_response_sha256):
    """Return one source-bound live observation selected by the frozen core."""
    from ..tools import ToolResult

    return ToolResult(
        tool_id=TOOL_ID,
        result=provider.observe(
            context=context,
            arguments=arguments,
            source_response_sha256=source_response_sha256,
        ),
    )
