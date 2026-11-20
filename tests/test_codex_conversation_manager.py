import os
import json

import pytest

import codex_conversation_manager as manager


def require_safe_open_support():
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        pytest.skip("La plataforma no admite apertura segura con estos flags.")


def test_opens_regular_file_inside_allowed_root(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    target = root / "thread.jsonl"
    target.write_bytes(b'{"type":"test"}\n')

    with manager._open_codex_jsonl(target, [root]) as stream:
        assert stream.read() == b'{"type":"test"}\n'


def test_rejects_file_outside_allowed_roots(tmp_path):
    require_safe_open_support()
    root = tmp_path / "sessions"
    root.mkdir()
    outside = tmp_path / "private.jsonl"
    outside.write_text("private", encoding="utf-8")

    assert manager._open_codex_jsonl(outside, [root]) is None


def test_rejects_symlink_file(tmp_path):
    require_safe_open_support()
    root = tmp_path / "sessions"
    root.mkdir()
    real_file = root / "real.jsonl"
    real_file.write_text("data", encoding="utf-8")
    link = root / "link.jsonl"
    link.symlink_to(real_file)

    assert manager._open_codex_jsonl(link, [root]) is None


def test_rejects_symlink_directory(tmp_path):
    require_safe_open_support()
    root = tmp_path / "sessions"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    target = outside / "thread.jsonl"
    target.write_text("data", encoding="utf-8")
    link = root / "alias"
    link.symlink_to(outside, target_is_directory=True)

    assert manager._open_codex_jsonl(link / "thread.jsonl", [root]) is None


def test_rejects_oversized_file(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    target = root / "large.jsonl"

    with target.open("wb") as stream:
        stream.truncate(manager.MAX_JSONL_FILE_BYTES + 1)

    assert manager._open_codex_jsonl(target, [root]) is None


class StaticConversationManager(manager.CodexConversationManager):
    def __init__(self, threads):
        super().__init__()
        self.threads = threads

    def obtener_todos(self):
        return self.threads


def make_message(role, text, phase=None):
    payload = {
        "type": "message",
        "role": role,
        "content": [{
            "type": "input_text" if role == "user" else "output_text",
            "text": text,
        }],
    }
    if phase:
        payload["phase"] = phase
    return json.dumps(
        {"type": "response_item", "payload": payload},
        ensure_ascii=False,
    ) + "\n"


def make_thread(thread_id, path):
    return {
        "id": thread_id,
        "originator": "tuxgenie",
        "parentThreadId": None,
        "ephemeral": False,
        "path": str(path),
        "name": "Conversación ficticia",
    }


def test_search_recovers_question_and_answer(tmp_path, monkeypatch):
    codex_home = tmp_path / "codex"
    sessions = codex_home / "sessions"
    sessions.mkdir(parents=True)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    path = sessions / "test.jsonl"
    path.write_text(
        "[]\n"
        + make_message("user", "Consulta sobre marcadorprueba")
        + make_message("assistant", "Respuesta de prueba", phase="final"),
        encoding="utf-8",
    )

    manager_instance = StaticConversationManager({
        "test-thread": make_thread("test-thread", path)
    })

    results = manager_instance._buscar_en_archivos(
        ["marcadorprueba"], set()
    )

    assert len(results) == 1
    fragments = " ".join(results[0]["fragmentos"])
    assert "marcadorprueba" in fragments
    assert "Respuesta de prueba" in fragments


def test_search_skips_oversized_line(tmp_path, monkeypatch):
    codex_home = tmp_path / "codex"
    sessions = codex_home / "sessions"
    sessions.mkdir(parents=True)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setattr(manager, "MAX_JSONL_LINE_BYTES", 128)

    path = sessions / "large-line.jsonl"
    path.write_text(
        make_message("user", "marcadorprueba " + "x" * 300),
        encoding="utf-8",
    )

    manager_instance = StaticConversationManager({
        "large-thread": make_thread("large-thread", path)
    })

    assert manager_instance._buscar_en_archivos(
        ["marcadorprueba"], set()
    ) == []


def test_search_respects_total_read_budget(tmp_path, monkeypatch):
    codex_home = tmp_path / "codex"
    sessions = codex_home / "sessions"
    sessions.mkdir(parents=True)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setattr(manager, "MAX_JSONL_SEARCH_BYTES", 500)
    monkeypatch.setattr(manager, "MAX_JSONL_LINE_BYTES", 1024)
    monkeypatch.setattr(manager, "MAX_JSONL_FILE_BYTES", 4096)

    first_path = sessions / "first.jsonl"
    second_path = sessions / "second.jsonl"

    first_record = make_message("assistant", "z" * 300).encode("utf-8")
    second_record = make_message(
        "user", "marcadorprueba " + "x" * 200
    ).encode("utf-8")

    assert len(first_record) < 500
    assert len(second_record) > 500 - len(first_record)

    first_path.write_bytes(first_record)
    second_path.write_bytes(second_record)

    manager_instance = StaticConversationManager({
        "first-thread": make_thread("first-thread", first_path),
        "second-thread": make_thread("second-thread", second_path),
    })

    assert manager_instance._buscar_en_archivos(
        ["marcadorprueba"], set()
    ) == []


def test_search_removes_codex_environment_context():
    text = (
        "Respuesta visible\n"
        "<environment_context>\n"
        "<cwd>/private/local/path</cwd>\n"
        "<shell>bash</shell>\n"
        "</environment_context>\n"
        "Contenido posterior"
    )
    cleaned = manager.CodexConversationManager._limpiar_contexto_interno(text)

    assert "Respuesta visible" in cleaned
    assert "Contenido posterior" in cleaned
    assert "private/local/path" not in cleaned
    assert "<shell>" not in cleaned


def test_search_removes_unterminated_environment_context():
    text = "Pregunta visible\n<environment_context><cwd>/private/path"
    cleaned = manager.CodexConversationManager._limpiar_contexto_interno(text)

    assert cleaned == "Pregunta visible"
