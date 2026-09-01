"""
HTTP client for communicating with the mini-agent Rust server.

Supports both regular JSON requests and SSE streaming.
"""

import json
import requests
from typing import Generator


class ServerClient:
    """Client for the mini-agent-runtime server API."""

    def __init__(self, base_url: str = "http://127.0.0.1:3000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def health(self) -> dict:
        """Check server health."""
        resp = self.session.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    def list_tools(self) -> list[dict]:
        """List available tools from the server."""
        resp = self.session.get(f"{self.base_url}/tools")
        resp.raise_for_status()
        return resp.json()

    def chat(self, messages: list[dict], stream: bool = False) -> dict | Generator:
        """
        Send a chat request to the server.

        Args:
            messages: List of chat messages in OpenAI format.
            stream: If True, returns a generator of SSE chunks.

        Returns:
            Either a dict response or a generator of stream chunks.
        """
        payload = {
            "messages": messages,
            "stream": stream,
        }

        if stream:
            return self._chat_stream(payload)
        else:
            resp = self.session.post(
                f"{self.base_url}/chat",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    def _chat_stream(self, payload: dict) -> Generator[dict, None, None]:
        """Handle SSE streaming response."""
        resp = self.session.post(
            f"{self.base_url}/chat",
            json=payload,
            stream=True,
            headers={"Accept": "text/event-stream"},
        )
        resp.raise_for_status()
        # `requests` otherwise leaves text/event-stream without a charset as
        # bytes; force incremental UTF-8 decoding so multibyte characters are
        # not split into malformed SSE/JSON lines.
        resp.encoding = "utf-8"

        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8")
            if line.startswith("data:"):
                # SSE permits an optional single space after the field colon.
                data_str = line[5:].lstrip(" ")
                if data_str.strip() == "[DONE]":
                    break
                try:
                    yield json.loads(data_str)
                except json.JSONDecodeError:
                    continue

    def is_server_running(self) -> bool:
        """Check if the server is reachable."""
        try:
            self.health()
            return True
        except requests.ConnectionError:
            return False
