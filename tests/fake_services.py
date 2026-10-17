"""One fake HTTP server standing in for the LLM, Telegram and the leads sink.

It listens on all interfaces so the n8n container reaches it through host.docker.internal.
Every request is recorded; tests script the LLM behavior and sink failures.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TELEGRAM_TOKEN = "123456:test-token"
LEADS_SECRET = "leads-test-secret"
TELEGRAM_CHAT_ID = "-100200300"


class FakeServices:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._release = threading.Event()
        self.reset()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # keep test output quiet
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                try:
                    body = json.loads(raw) if raw else None
                except ValueError:
                    body = None
                owner._handle(self, self.path, body)

        self._server = ThreadingHTTPServer(("0.0.0.0", 0), Handler)
        self._server.daemon_threads = True
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    # --- lifecycle -----------------------------------------------------------

    def start(self) -> "FakeServices":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._release.set()
        self._server.shutdown()
        self._server.server_close()

    def reset(self) -> None:
        """Forget recorded calls and restore the default behavior."""
        self._release.set()  # free any handler still hanging from a previous test
        with self._lock:
            self.llm_calls: list[dict] = []
            self.telegram_calls: list[dict] = []
            self.leads_calls: list[dict] = []
            self.llm_mode = "json"  # json | raw | 500 | hang
            self.llm_content: object = {"reply": "Hola", "intent": "other"}
            self.leads_status = 200
            self.telegram_status = 200
        self._release.clear()

    # --- scripting -----------------------------------------------------------

    def llm_returns_json(self, reply: str, intent: str) -> None:
        self.llm_mode, self.llm_content = "json", {"reply": reply, "intent": intent}

    def llm_returns_raw(self, text: str) -> None:
        self.llm_mode, self.llm_content = "raw", text

    def llm_fails_with_500(self) -> None:
        self.llm_mode = "500"

    def llm_hangs(self) -> None:
        self.llm_mode = "hang"

    # --- request handling ----------------------------------------------------

    @staticmethod
    def _respond(handler, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)

    def _handle(self, handler, path: str, body) -> None:
        record = {"path": path, "body": body, "headers": dict(handler.headers)}
        if path == "/openai/v1/chat/completions":
            with self._lock:
                self.llm_calls.append(record)
                mode, content = self.llm_mode, self.llm_content
            if mode == "hang":
                self._release.wait(timeout=30)
                return
            if mode == "500":
                return self._respond(handler, 500, {"error": "llm exploded"})
            text = content if mode == "raw" else json.dumps(content, ensure_ascii=False)
            return self._respond(
                handler, 200, {"choices": [{"message": {"role": "assistant", "content": text}}]}
            )
        if path == f"/bot{TELEGRAM_TOKEN}/sendMessage":
            with self._lock:
                self.telegram_calls.append(record)
                status = self.telegram_status
            return self._respond(handler, status, {"ok": status == 200})
        if path == "/leads":
            with self._lock:
                self.leads_calls.append(record)
                status = self.leads_status
            return self._respond(handler, status, {"ok": status == 200})
        self._respond(handler, 404, {"error": "unknown path"})
