"""Tests for the HTTP/SSE server client."""

import sys
from pathlib import Path
from unittest.mock import Mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from agent.client import ServerClient


def stream_response(lines):
    response = Mock()
    response.raise_for_status.return_value = None
    response.iter_lines.return_value = iter(lines)
    return response


def test_stream_accepts_sse_data_without_space():
    client = ServerClient()
    client.session.post = Mock(return_value=stream_response([
        'data:{"content":"A","finish_reason":null}',
        'data:{"content":"B","finish_reason":"stop"}',
    ]))
    assert list(client.chat([], stream=True)) == [
        {"content": "A", "finish_reason": None},
        {"content": "B", "finish_reason": "stop"},
    ]


def test_stream_decodes_bytes_when_response_has_no_charset():
    client = ServerClient()
    client.session.post = Mock(return_value=stream_response([
        b'data:{"content":"A"}',
    ]))
    assert list(client.chat([], stream=True)) == [{"content": "A"}]


def test_stream_accepts_sse_data_with_space_and_done():
    client = ServerClient()
    client.session.post = Mock(return_value=stream_response([
        'data: {"content":"A"}',
        "data: [DONE]",
        'data: {"content":"ignored"}',
    ]))
    assert list(client.chat([], stream=True)) == [{"content": "A"}]
