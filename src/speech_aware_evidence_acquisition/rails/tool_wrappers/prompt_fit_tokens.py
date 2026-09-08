"""``saea-tool-prompt-fit-tokens-v1`` -- the Planner's prompt-fit tokenizer.

Wraps ``core.driver.speech_native._LoopbackPromptAuditClient.request_json``
unchanged: the thread-local keep-alive client for the resident llama-server's
NON-GENERATIVE routes, which is how ``scripts/e21_kc_e1_prompt_fit.py``
measures a request on the FLIGHT tokenizer instead of guessing it.

Why this is a tool and not a model contact
------------------------------------------
Nothing here generates a token or reads an answer: the three admitted routes
report the server's properties, render the chat template, and count tokens.
That is a ``service-contact`` -- it happened, so it is ledgered, but the
frozen core stays behind the single door and no ExecutionPlan generation
budget is touched. The route ALLOW-LIST below is what makes that a property
of the code rather than a promise: a caller cannot reach ``/completion``,
``/chat/completions`` or any other generative route through this tool, and
asking for one refuses.

The client is duck-typed on purpose (any object with ``request_json``), so
this module does not import the 7,000-line driver that owns it. The manifest
still pins that method's source by hash, so the wrapped body cannot change
under the tool.
"""

from __future__ import annotations

from typing import Any, Mapping

TOOL_ID = "saea-tool-prompt-fit-tokens-v1"

LEDGER_ROW_TYPE = "service-contact"

#: The only routes this tool may reach. Every one is non-generative; adding a
#: generative route here would turn a service contact into a model contact and
#: is exactly what this list exists to prevent.
ALLOWED_ROUTES = ("/props", "/apply-template", "/tokenize")


def prompt_fit_request_tool(
    client: Any, method: str, path: str, payload: Mapping[str, object] | None = None
):
    """``client.request_json(method, path, payload)`` verbatim, on an admitted
    non-generative route.

    ``ToolResult.result`` is the client's own decoded JSON mapping. The client
    itself does the HTTP, the status check and the JSON decode; this wrapper
    adds the route guard and nothing else.
    """

    from ..tools import ToolCatalogError, ToolResult

    if path not in ALLOWED_ROUTES:
        raise ToolCatalogError(
            f"route {path!r} is not one of this tool's non-generative routes "
            f"{ALLOWED_ROUTES}; the frozen core is reached through the single door, "
            "never through a catalog tool"
        )
    if not hasattr(client, "request_json"):
        raise ToolCatalogError(
            "prompt-fit tokenizer needs a client exposing request_json(method, path, payload)"
        )
    return ToolResult(tool_id=TOOL_ID, result=client.request_json(method, path, payload))
