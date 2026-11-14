import json
import os
from types import SimpleNamespace

import pytest

import codex_backend as codex


@pytest.fixture
def backend_with_pipe():
    read_fd, write_fd = os.pipe()
    instance = codex.CodexBackend(timeout=1)
    stdout = os.fdopen(read_fd, "rb", buffering=0)

    instance._process = SimpleNamespace(
        stdout=stdout,
        poll=lambda: None,
    )

    yield instance, write_fd

    stdout.close()
    os.close(write_fd)
    instance._process = None


def test_read_message_accepts_valid_json(backend_with_pipe):
    instance, write_fd = backend_with_pipe
    expected = {"id": 1, "result": {"status": "ok"}}

    os.write(write_fd, json.dumps(expected).encode() + b"\n")

    assert instance._read_message(1) == expected


def test_read_message_preserves_next_buffered_message(backend_with_pipe):
    instance, write_fd = backend_with_pipe

    os.write(write_fd, b'{"id":1}\n{"id":2}\n')

    assert instance._read_message(1) == {"id": 1}
    assert instance._read_message(1) == {"id": 2}


def test_read_message_rejects_invalid_json(backend_with_pipe):
    instance, write_fd = backend_with_pipe
    os.write(write_fd, b"not-json\n")

    with pytest.raises(codex.CodexError, match="invalid JSON-RPC"):
        instance._read_message(1)


def test_read_message_rejects_non_object_json(backend_with_pipe):
    instance, write_fd = backend_with_pipe
    os.write(write_fd, b"[]\n")

    with pytest.raises(codex.CodexError, match="non-object"):
        instance._read_message(1)


def test_read_message_rejects_oversized_message(backend_with_pipe, monkeypatch):
    instance, write_fd = backend_with_pipe
    monkeypatch.setattr(codex, "MAX_JSON_RPC_MESSAGE_BYTES", 8)

    os.write(write_fd, b"123456789")

    with pytest.raises(codex.CodexError, match="size limit"):
        instance._read_message(1)


def test_failed_initialization_closes_process(monkeypatch):
    class FakeProcess:
        def __init__(self):
            self.alive = True
            self.terminated = False

        def poll(self):
            return None if self.alive else -15

        def terminate(self):
            self.terminated = True
            self.alive = False

        def wait(self, timeout=None):
            return -15

        def kill(self):
            self.alive = False

    process = FakeProcess()
    instance = codex.CodexBackend()

    monkeypatch.setattr(codex.shutil, "which", lambda _: "/usr/bin/codex")
    monkeypatch.setattr(
        codex.subprocess,
        "Popen",
        lambda *args, **kwargs: process,
    )

    def fail_initialize(*args, **kwargs):
        raise codex.CodexError("Initialization failed")

    monkeypatch.setattr(instance, "_rpc", fail_initialize)

    with pytest.raises(codex.CodexError, match="Initialization failed"):
        instance._start()

    assert process.terminated
    assert instance._process is None
    assert instance._initialized is False


def test_build_prompt_preserves_configured_language():
    backend = codex.CodexBackend()
    prompt = backend._build_prompt(
        "Respond only in English.",
        [{"role": "user", "content": "Explain this error."}],
    )

    assert "Respond only in English." in prompt
    assert "Explain this error." in prompt
    assert "IDIOMA OBLIGATORIO" not in prompt
    assert "Spanish edition" not in prompt


def test_build_prompt_does_not_force_a_default_language():
    backend = codex.CodexBackend()
    prompt = backend._build_prompt(
        "",
        [{"role": "user", "content": "Hello"}],
    )

    assert "Hello" in prompt
    assert "Responde siempre en español" not in prompt


def test_tool_call_cancellation_propagates_without_success_response(monkeypatch):
    backend = codex.CodexBackend()
    sent_messages = []

    monkeypatch.setattr(backend, "_send", sent_messages.append)

    def cancel_tool(_params):
        raise codex.CodexToolCallCancelled("User cancelled.")

    request = {
        "id": 7,
        "method": "item/tool/call",
        "params": {
            "callId": "call-1",
            "threadId": "thread-1",
            "turnId": "turn-1",
            "tool": "run_command",
            "arguments": {"command": "example"},
        },
    }

    with pytest.raises(codex.CodexToolCallCancelled):
        backend._respond_to_server_request(request, cancel_tool)

    assert sent_messages == []


@pytest.mark.parametrize(
    ("tool_result", "expected_success"),
    [
        ("BLOCKED: private file", False),
        ("BLOCKED by TuxGenie safety filter", False),
        ("ERROR: missing command", False),
        ("SKIPPED by the user", False),
        ("Could not read file: permission denied", False),
        ("Unknown tool: something", False),
        ("Command completed successfully", True),
        (("Command failed", False), False),
        (("Command completed", True), True),
    ],
)
def test_tool_result_success_status(tool_result, expected_success, monkeypatch):
    backend = codex.CodexBackend()
    sent = []
    monkeypatch.setattr(backend, "_send", sent.append)

    request = {
        "id": 12,
        "method": "item/tool/call",
        "params": {
            "callId": "call-test",
            "threadId": "thread-test",
            "turnId": "turn-test",
            "tool": "run_command",
            "arguments": {"command": "test"},
        },
    }

    backend._respond_to_server_request(
        request,
        lambda _params: tool_result,
    )

    assert len(sent) == 1
    assert sent[0]["result"]["success"] is expected_success
