#!/usr/bin/env python3
"""Capture a client's actual request at a LOCAL SYNTHETIC endpoint, never a model.

Run on the host with its installed Codex executable. Use an empty, disposable
profile and a synthetic packet. No account tokens are read/copied and no remote
provider is contacted by this fixture. This diagnostic does not admit a real
transport. Save its raw request/events outside Git, beside the compact report.
"""
import argparse
import hashlib
import http.server
import json
import os
from pathlib import Path
import queue
import subprocess
import threading

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def audit(binary, output, request_contract):
    binary, output = Path(binary).resolve(strict=True), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "profile").mkdir()
    (output / "work").mkdir()
    requests, events = [], []
    expected = json.loads(Path(request_contract).read_text(encoding="utf-8"))
    synthetic_input = "Synthetic isolation fixture. No dataset, feedback, owner decision or research proposal."
    if expected["input"] != [{"role": "user", "content": synthetic_input}]:
        raise ValueError("The client audit accepts only the fixed synthetic input.")
    broker_tool = expected["tools"][0]

    class Fixture(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"data":[]}')

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            # Never retain headers or credentials, even if a future client errs.
            requests.append({"path": self.path, "authorization_present": bool(self.headers.get("Authorization")),
                             "payload": json.loads(raw)})
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.end_headers()
            item = {"id": "msg_fixture", "type": "message", "role": "assistant", "status": "completed",
                    "content": [{"type": "output_text", "text": "Synthetic fixture only.", "annotations": []}]}
            records = [
                {"type": "response.created", "response": {"id": "resp_fixture", "status": "in_progress", "output": []}},
                {"type": "response.output_item.added", "output_index": 0,
                 "item": dict(item, status="in_progress", content=[])},
                {"type": "response.output_text.delta", "item_id": "msg_fixture", "output_index": 0,
                 "content_index": 0, "delta": "Synthetic fixture only."},
                {"type": "response.output_item.done", "output_index": 0, "item": item},
                {"type": "response.completed", "response": {"id": "resp_fixture", "status": "completed",
                 "output": [item], "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}}},
            ]
            for record in records:
                self.wfile.write(("data: " + json.dumps(record) + "\n\n").encode())
                self.wfile.flush()

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    disabled = ("apps plugins hooks memories shell_tool unified_exec code_mode_host browser_use browser_use_external "
        "browser_use_full_cdp_access computer_use view_image image_generation multi_agent multi_agent_v2 goals "
        "sleep_tool skill_search workspace_dependencies shell_snapshot unbounded_connection_retries enable_request_compression")
    config = {"model_provider": "fixture", "model_providers.fixture.name": "Synthetic local fixture",
        "model_providers.fixture.base_url": f"http://127.0.0.1:{server.server_port}/v1",
        "model_providers.fixture.wire_api": "responses", "model_providers.fixture.requires_openai_auth": False,
        "model_providers.fixture.request_max_retries": 0, "model_providers.fixture.stream_max_retries": 0,
        "project_doc_max_bytes": 0, "web_search": "disabled", "features.skip_host_skill_discovery": True,
        "features.code_mode": False, "skills.config": [], "mcp_servers": {}, "model_reasoning_effort": "low"}
    config.update({"features." + key: False for key in disabled.split()})
    args = [str(binary), "app-server", "--listen", "stdio://"]
    for key, value in config.items():
        args.extend(["-c", key + "=" + json.dumps(value)])
    # Do not inherit this chat's pipe, thread, originator, or workspace variables.
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "PROGRAMDATA", "COMSPEC", "PATHEXT"}}
    env["CODEX_HOME"] = str(output / "profile")
    incoming = queue.Queue()
    error = None
    with (output / "stderr.txt").open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(args, cwd=output / "work", env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=stderr, text=True, encoding="utf-8")

        def consume():
            for line in process.stdout:
                incoming.put(json.loads(line))

        threading.Thread(target=consume, daemon=True).start()

        def send(value):
            process.stdin.write(json.dumps(value) + "\n")
            process.stdin.flush()

        def rpc(identity, method, params):
            send({"id": identity, "method": method, "params": params})
            while True:
                item = incoming.get(timeout=25)
                events.append(item)
                if item.get("id") == identity:
                    if "error" in item:
                        raise RuntimeError("Synthetic client protocol failed.")
                    return item["result"]

        try:
            rpc(1, "initialize", {"clientInfo": {"name": "saea_synthetic_proof", "version": "1"},
                                  "capabilities": {"experimentalApi": True}})
            send({"method": "initialized", "params": {}})
            thread = rpc(2, "thread/start", {"model": "gpt-6-sol", "modelProvider": "fixture",
                "allowProviderModelFallback": False, "cwd": str(output / "work"), "environments": [],
                "ephemeral": True, "approvalPolicy": "never", "sandbox": "read-only",
                "baseInstructions": expected["instructions"], "developerInstructions": "Use only the registered packet and tool.",
                "dynamicTools": [{"type": "function", "name": broker_tool["name"],
                    "description": broker_tool["description"], "inputSchema": broker_tool["parameters"]}]})
            rpc(3, "turn/start", {"threadId": thread["thread"]["id"],
                                  "input": [{"type": "text", "text": synthetic_input, "text_elements": []}]})
            while True:
                item = incoming.get(timeout=25)
                events.append(item)
                if item.get("method") == "turn/completed":
                    break
        except Exception as failure:
            error = type(failure).__name__
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            server.shutdown()
            server.server_close()
    for name, value in (("requests.json", requests), ("events.json", events), ("expected.json", expected)):
        (output / name).write_text(canonical(value) + "\n", encoding="utf-8")
    matches = [canonical(request["payload"]) == canonical(expected) for request in requests]
    report = {"schema": "saea-proposer-client-synthetic-audit-v1", "fixture_only": True,
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(), "requests": len(requests),
        "request_file_sha256": hashlib.sha256((output / "requests.json").read_bytes()).hexdigest(),
        "actual_outbound_matches_registered_request": bool(matches) and all(matches),
        "authorization_header_present": any(r["authorization_present"] for r in requests),
        "error_type": error, "external_model_contacts": 0, "research_proposals": 0,
        "transport_admission": "withheld-pending-compatible-enforced-adapter",
        "raw_evidence_directory": str(output)}
    (output / "report.json").write_text(canonical(report) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--request-contract", required=True, type=Path,
                        help="Synthetic contract exported by the shared proposer module in the WSL environment")
    args = parser.parse_args()
    print(json.dumps(audit(args.binary, args.output, args.request_contract)))
