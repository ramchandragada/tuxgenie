#!/usr/bin/env python3
"""Codex App Server backend for a future TuxGenie integration."""

import atexit
import json
import os
import select
import shutil
import subprocess
import threading
import time


MAX_JSON_RPC_MESSAGE_BYTES = 16 * 1024 * 1024

class CodexError(RuntimeError):
    pass


class CodexToolCallCancelled(CodexError):
    """Propagate an explicit user cancellation out of a dynamic tool call."""


class CodexBackend:
    def __init__(self, model=None, cwd=None, timeout=180, memory_enabled=False):
        self.model = model or ""
        self.base_model = self.model
        self.cwd = os.path.abspath(cwd or os.getcwd())
        self.session_default_cwd = self.cwd
        self.timeout = timeout
        self.memory_enabled = bool(memory_enabled)
        # Preferencia de guardado de nuevas conversaciones en esta ejecución.
        # Reanudar una conversación guardada no cambia esta preferencia.
        self.session_save_enabled = bool(memory_enabled)

        # Compatibility with TuxGenie's backend interface.
        self._no_key = False
        self.auto_model = False
        self.expert_mode = False
        self.auto_approve = False

        self._session_input_tokens = 0
        self._session_output_tokens = 0
        self._session_cache_creation_tokens = 0
        self._session_cache_read_tokens = 0

        self._process = None
        self._buffer = bytearray()
        self._request_id = 0
        self._initialized = False
        self._lock = threading.RLock()

        # Un único hilo de Codex por ejecución de TuxGenie.
        self.session_thread_id = None
        self.session_thread_pid = None
        self.session_title = ""
        self.session_title_set = False

        atexit.register(self.close)

    def label(self):
        suffix = f" · {self.model}" if self.model else ""
        return f"OpenAI Codex · App Server{suffix}"

    def session_cost_estimate(self):
        return (
            "Codex usage and limits are managed by your authenticated "
            "Codex account."
        )

    def select_model_for_task(self, task=None, round_num=None):
        return self.model

    def _record_usage(self, usage=None):
        # Codex manages usage through the authenticated account.
        return None

    def _send(self, message):
        if not self._process or self._process.poll() is not None:
            raise CodexError("Codex App Server is not running.")

        payload = json.dumps(message, ensure_ascii=False) + "\n"

        try:
            self._process.stdin.write(payload.encode("utf-8"))
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise CodexError(f"Could not send message to Codex: {exc}") from exc

    def _read_message(self, timeout):
        deadline = time.monotonic() + timeout
        fd = self._process.stdout.fileno()

        while True:
            newline_index = self._buffer.find(b"\n")

            if newline_index >= 0:
                if newline_index > MAX_JSON_RPC_MESSAGE_BYTES:
                    raise CodexError(
                        "Codex App Server sent an oversized JSON-RPC message."
                    )

                line = bytes(self._buffer[:newline_index])
                del self._buffer[:newline_index + 1]

                try:
                    message = json.loads(line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise CodexError(
                        "Codex App Server sent an invalid JSON-RPC message."
                    ) from exc

                if not isinstance(message, dict):
                    raise CodexError(
                        "Codex App Server sent a non-object JSON-RPC message."
                    )

                return message

            if len(self._buffer) > MAX_JSON_RPC_MESSAGE_BYTES:
                raise CodexError(
                    "Codex App Server message exceeded the size limit."
                )

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Timed out waiting for Codex.")

            ready, _, _ = select.select([fd], [], [], remaining)
            if not ready:
                raise TimeoutError("Timed out waiting for Codex.")

            read_size = min(
                4096,
                MAX_JSON_RPC_MESSAGE_BYTES + 1 - len(self._buffer),
            )
            chunk = os.read(fd, read_size)

            if not chunk:
                code = self._process.poll()
                raise CodexError(
                    f"Codex closed its output stream (exit code: {code})."
                )

            self._buffer.extend(chunk)

    def _start(self):
        if self._process and self._process.poll() is None:
            return

        codex = shutil.which("codex")
        if not codex:
            raise CodexError(
                "Codex CLI was not found. Install it and authenticate first."
            )

        command = [
            codex,
            "app-server",
            "--disable", "shell_tool",
            "--disable", "unified_exec",
            "--disable", "unified_exec_tty",
            "--stdio",
        ]

        self._process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            bufsize=0,
        )

        self._buffer.clear()
        self._initialized = False

        try:
            result = self._rpc("initialize", {
                "clientInfo": {
                    "name": "tuxgenie",
                    "title": "TuxGenie",
                    "version": "1.0.0",
                },
                "capabilities": {
                    "experimentalApi": True,
                },
            })

            self._send({
                "method": "initialized",
                "params": {},
            })

            self._initialized = True
            return result

        except Exception:
            self.close()
            raise

    def _respond_to_server_request(self, message, tool_handler):
        method = message.get("method")

        if method == "item/tool/call":
            if not tool_handler:
                response = {
                    "contentItems": [{
                        "type": "inputText",
                        "text": "Tool execution is unavailable in this turn.",
                    }],
                    "success": False,
                }
            else:
                try:
                    result = tool_handler(message.get("params", {}))

                    if isinstance(result, tuple) and len(result) == 2:
                        text, success = result
                    else:
                        text = result
                        failure_prefixes = (
                            "BLOCKED",
                            "ERROR:",
                            "SKIPPED",
                            "Could not read file:",
                            "Unknown tool:",
                        )
                        success = not str(text).lstrip().startswith(
                            failure_prefixes
                        )

                    response = {
                        "contentItems": [{
                            "type": "inputText",
                            "text": str(text),
                        }],
                        "success": bool(success),
                    }

                except CodexToolCallCancelled:
                    raise

                except Exception as exc:
                    response = {
                        "contentItems": [{
                            "type": "inputText",
                            "text": f"Tool execution failed: {exc}",
                        }],
                        "success": False,
                    }

            self._send({
                "id": message["id"],
                "result": response,
            })
            return

        # Never approve unknown server requests automatically.
        self._send({
            "id": message["id"],
            "error": {
                "code": -32601,
                "message": f"Unsupported server request: {method}",
            },
        })

    def _rpc(self, method, params, timeout=60, tool_handler=None):
        self._request_id += 1
        current_id = self._request_id

        self._send({
            "id": current_id,
            "method": method,
            "params": params,
        })

        while True:
            message = self._read_message(timeout)

            if message.get("id") == current_id:
                if "error" in message:
                    raise CodexError(
                        json.dumps(message["error"], ensure_ascii=False)
                    )
                return message.get("result", {})

            if message.get("method") and "id" in message:
                self._respond_to_server_request(message, tool_handler)

    @staticmethod
    def _content_to_text(content):
        if isinstance(content, str):
            return content

        if not isinstance(content, list):
            return str(content or "")

        parts = []

        for block in content:
            if isinstance(block, dict):
                kind = block.get("type")

                if kind == "text":
                    parts.append(block.get("text", ""))

                elif kind == "tool_result":
                    result = block.get("content", "")
                    parts.append(str(result))

                elif kind == "tool_use":
                    parts.append(
                        f"[Requested tool: {block.get('name', 'unknown')}]"
                    )

            else:
                text = getattr(block, "text", None)
                if text:
                    parts.append(text)

        return "\n".join(parts)

    def _build_prompt(self, system, messages):
        if isinstance(system, list):
            system_text = self._content_to_text(system)
        else:
            system_text = str(system or "")

        sections = []


        if system_text.strip():
            sections.append(
                "SYSTEM INSTRUCTIONS:\n" + system_text.strip()
            )

        history = []

        for message in messages or []:
            role = message.get("role", "user").upper()
            content = self._content_to_text(message.get("content", ""))

            if content.strip():
                history.append(f"{role}:\n{content.strip()}")

        if history:
            sections.append("CONVERSATION:\n" + "\n\n".join(history))

        return "\n\n".join(sections)

    def resume_thread(self, thread_id, title="", workspace=None):
        """Reanuda exclusivamente una conversación persistente de TuxGenie."""
        if not self.session_save_enabled:
            raise CodexError("Conversation history is disabled.")
        if not isinstance(thread_id, str) or not thread_id.strip():
            raise CodexError("El identificador de conversación no es válido.")

        with self._lock:
            try:
                self._start()
                registro = None

                # Verificar de nuevo el propietario y que no sea efímera.
                for archivada in (False, True):
                    cursor = None
                    cursores_vistos = set()
                    while True:
                        params = {"limit": 100, "archived": archivada}
                        if cursor:
                            if cursor in cursores_vistos:
                                raise CodexError("Codex devolvió un cursor repetido.")
                            cursores_vistos.add(cursor)
                            params["cursor"] = cursor

                        pagina = self._rpc("thread/list", params)
                        for item in pagina.get("data", []):
                            if item.get("id") == thread_id:
                                registro = dict(item)
                                registro["_archivada"] = archivada
                                break
                        if registro:
                            break
                        cursor = pagina.get("nextCursor")
                        if not cursor:
                            break
                    if registro:
                        break

                if not registro:
                    raise CodexError("La conversación ya no existe o no está disponible.")
                if registro.get("originator") != "tuxgenie":
                    raise CodexError("Por seguridad, solo se pueden continuar conversaciones de TuxGenie.")
                if registro.get("ephemeral", False):
                    raise CodexError("Las conversaciones efímeras no se pueden reanudar.")

                # Un hilo archivado debe restaurarse antes de reanudarlo.
                if registro.get("_archivada"):
                    restaurado = self._rpc(
                        "thread/unarchive", {"threadId": thread_id}, timeout=60
                    )
                    hilo_restaurado = restaurado.get("thread") or {}
                    id_restaurado = hilo_restaurado.get("id")
                    if id_restaurado and id_restaurado != thread_id:
                        raise CodexError("Codex restauró una conversación distinta de la seleccionada.")

                carpeta = registro.get("cwd") or workspace
                if isinstance(carpeta, str) and os.path.isdir(carpeta):
                    self.cwd = os.path.abspath(carpeta)

                params_resume = {
                    "threadId": thread_id,
                    "excludeTurns": True,
                    "cwd": self.cwd,
                    "approvalPolicy": "on-request",
                    "sandbox": "read-only",
                }
                if self.model:
                    params_resume["model"] = self.model

                resultado = self._rpc("thread/resume", params_resume, timeout=60)
                info_hilo = resultado.get("thread") or {}
                id_reanudado = info_hilo.get("id")
                if id_reanudado and id_reanudado != thread_id:
                    raise CodexError("Codex devolvió una conversación distinta de la seleccionada.")

                # Volver a aplicar las restricciones de esta integración.
                self._rpc("thread/settings/update", {
                    "threadId": thread_id,
                    "cwd": self.cwd,
                    "approvalPolicy": "on-request",
                    "sandboxPolicy": {
                        "type": "readOnly",
                        "networkAccess": False,
                    },
                }, timeout=60)

                self.memory_enabled = True
                self.session_thread_id = thread_id
                self.session_thread_pid = self._process.pid
                self.session_title = (title or registro.get("name") or "Conversación de TuxGenie")[:100]
                self.session_title_set = True
                return True

            except Exception:
                self.close()
                raise

    def start_new_conversation(self):
        """Desvincula el hilo actual y prepara uno nuevo con la preferencia S/N."""
        with self._lock:
            self.session_thread_id = None
            self.session_thread_pid = None
            self.session_title = ""
            self.session_title_set = False
            self.cwd = self.session_default_cwd
            self.memory_enabled = bool(self.session_save_enabled)
        return True

    def run_turn(self, prompt, dynamic_tools=None, tool_handler=None):
        """Ejecuta un turno dentro del hilo de esta ejecución de TuxGenie."""
        with self._lock:
            try:
                self._start()
                process_pid = self._process.pid

                # Si el servidor sigue vivo, continuamos el hilo de esta sesión.
                if (
                    self.session_thread_id
                    and self.session_thread_pid == process_pid
                ):
                    thread_id = self.session_thread_id

                else:
                    # Nunca recuperar automáticamente un hilo de una ejecución
                    # anterior. Cada ejecución comienza una conversación nueva.
                    self.session_thread_id = None
                    self.session_thread_pid = None
                    self.session_title_set = False

                    thread_params = {
                        "cwd": self.cwd,
                        "approvalPolicy": "on-request",
                        "sandbox": "read-only",
                        # Sin guardar = hilo efímero, no materializado en disco.
                        "ephemeral": not bool(self.memory_enabled),
                    }

                    if self.model:
                        thread_params["model"] = self.model

                    if dynamic_tools:
                        thread_params["dynamicTools"] = dynamic_tools

                    thread = self._rpc(
                        "thread/start",
                        thread_params,
                        timeout=60,
                        tool_handler=tool_handler,
                    )

                    thread_info = thread.get("thread") or {}
                    thread_id = thread_info.get("id")

                    if not isinstance(thread_id, str) or not thread_id:
                        raise CodexError(
                            "Codex did not return a valid thread ID."
                        )

                    self.session_thread_id = thread_id
                    self.session_thread_pid = process_pid

                turn_params = {
                    "threadId": thread_id,
                    "input": [{
                        "type": "text",
                        "text": str(prompt),
                    }],
                    "approvalPolicy": "on-request",
                    "sandboxPolicy": {
                        "type": "readOnly",
                        "networkAccess": False,
                    },
                }

                self._rpc(
                    "turn/start",
                    turn_params,
                    timeout=60,
                    tool_handler=tool_handler,
                )

                output = []
                completed = False

                while not completed:
                    message = self._read_message(self.timeout)
                    method = message.get("method")
                    params = message.get("params", {})

                    if method and "id" in message:
                        self._respond_to_server_request(
                            message, tool_handler
                        )
                        continue

                    if method == "item/agentMessage/delta":
                        delta = params.get("delta", "")
                        if delta:
                            output.append(delta)
                            print(delta, end="", flush=True)

                    elif method == "turn/completed":
                        completed = True
                        turn = params.get("turn", {})

                        if turn.get("status") != "completed":
                            error = turn.get("error") or {}
                            raise CodexError(
                                error.get(
                                    "message",
                                    "Codex turn did not complete successfully.",
                                )
                            )

                # El nombre se asigna una sola vez, tras el primer turno
                # correcto. Los hilos efímeros no admiten cambios de metadatos.
                if self.memory_enabled and not self.session_title_set:
                    try:
                        if self.session_title:
                            self._rpc(
                                "thread/name/set",
                                {
                                    "threadId": thread_id,
                                    "name": self.session_title,
                                },
                                timeout=15,
                                tool_handler=tool_handler,
                            )
                    except Exception:
                        # Un fallo al nombrar no debe invalidar la respuesta.
                        pass

                    self.session_title_set = True

                return "".join(output)

            except Exception:
                self.close()
                raise

    def ask(self, system, messages, max_tokens=4096, cache_system=False):
        prompt = self._build_prompt(system, messages)
        return self.run_turn(prompt)

    def run_agentic(self, system, task, tools, tool_handler):
        prompt = self._build_prompt(
            system,
            [{"role": "user", "content": task}],
        )

        dynamic_tools = []

        for tool in tools:
            dynamic_tools.append({
                "type": "function",
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool.get(
                    "input_schema",
                    tool.get("inputSchema", {}),
                ),
            })

        # Una ejecución nueva o un servidor reiniciado comienza un hilo nuevo.
        proceso_nuevo = (
            self._process is None
            or self._process.poll() is not None
            or not self.session_thread_id
        )

        if proceso_nuevo:
            if not self.session_title:
                titulo = " ".join(str(task).split())
                self.session_title = (
                    titulo[:72].rstrip()
                    + ("…" if len(titulo) > 72 else "")
                ) or "Sesión de TuxGenie"
            self.session_title_set = False

        return self.run_turn(
            prompt,
            dynamic_tools=dynamic_tools,
            tool_handler=tool_handler,
        )

    def close(self):
        process = self._process
        self._process = None
        self._initialized = False

        if process and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                try:
                    process.kill()
                    process.wait(timeout=2)
                except Exception:
                    pass

        # No reutilizar el hilo al cerrar esta ejecución.
        self.session_thread_id = None
        self.session_thread_pid = None
        self.session_title = ""
        self.session_title_set = False
        self.cwd = self.session_default_cwd
