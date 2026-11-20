#!/usr/bin/env python3
# Administrador de conversaciones de Codex para TuxGenie.
# Interfaz en español. Eliminación exclusivamente manual.

import os
import re
import stat
import json
import unicodedata
from pathlib import Path
from datetime import datetime

from codex_backend import CodexBackend


MAX_JSONL_FILE_BYTES = 16 * 1024 * 1024
MAX_JSONL_LINE_BYTES = 1024 * 1024
MAX_JSONL_SEARCH_BYTES = 64 * 1024 * 1024


def _open_codex_jsonl(path, allowed_roots):
    """Open a regular JSONL file without following symlinks."""
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory is None:
        return None

    path = Path(path)
    flags = os.O_RDONLY | nofollow | getattr(os, "O_CLOEXEC", 0)
    dir_flags = flags | directory

    for root in allowed_roots:
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue

        parts = relative.parts
        if not parts or any(part in ("", ".", "..") for part in parts):
            continue

        root_fd = None
        current_fd = None
        file_fd = None

        try:
            root_fd = os.open(os.fspath(root), dir_flags)
            current_fd = root_fd

            for part in parts[:-1]:
                next_fd = os.open(part, dir_flags, dir_fd=current_fd)
                if current_fd != root_fd:
                    os.close(current_fd)
                current_fd = next_fd

            file_fd = os.open(parts[-1], flags, dir_fd=current_fd)
            info = os.fstat(file_fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_size > MAX_JSONL_FILE_BYTES
            ):
                continue

            stream = os.fdopen(file_fd, "rb")
            file_fd = None
            return stream

        except (OSError, ValueError):
            continue

        finally:
            if file_fd is not None:
                os.close(file_fd)
            if current_fd is not None and current_fd != root_fd:
                os.close(current_fd)
            if root_fd is not None:
                os.close(root_fd)

    return None


class CodexConversationManager:

    PAGE_SIZE = 12

    def __init__(self, backend=None, on_continue=None, on_new=None, on_delete=None):
        # backend es la sesión activa de TuxGenie; si falta, se usa uno temporal.
        self.backend = backend
        self.on_continue = on_continue
        self.on_new = on_new
        self.on_delete = on_delete
        self._ultimo_metodo_busqueda = "sin ejecutar"

    @staticmethod
    def pintar(texto, tono="blanco", negrita=False):
        """Aplicar colores de terminal sin ensuciar salidas redirigidas."""
        if not os.isatty(1):
            return str(texto)

        paleta = {
            "rojo": "31",
            "verde": "32",
            "amarillo": "33",
            "azul": "34",
            "magenta": "35",
            "cyan": "36",
            "gris": "90",
            "blanco": "97",
        }

        codigo = paleta.get(tono, "97")
        prefijo = "1;" if negrita else ""
        return chr(27) + f"[{prefijo}{codigo}m{texto}" + chr(27) + "[0m"

    def _api(self, method, params):
        backend = self.backend or CodexBackend(memory_enabled=False)
        propio = self.backend is None
        try:
            with backend._lock:
                backend._start()
                return backend._rpc(method, params)
        finally:
            if propio:
                backend.close()

    @staticmethod
    def fecha_es(timestamp):
        if not timestamp:
            return "Fecha desconocida"

        fecha = datetime.fromtimestamp(timestamp)
        dias = [
            "lunes", "martes", "miércoles", "jueves",
            "viernes", "sábado", "domingo"
        ]
        meses = [
            "enero", "febrero", "marzo", "abril",
            "mayo", "junio", "julio", "agosto",
            "septiembre", "octubre", "noviembre", "diciembre"
        ]
        return (
            f"{dias[fecha.weekday()]} {fecha.day} "
            f"de {meses[fecha.month - 1]} de {fecha.year} "
            f"{fecha:%H:%M}"
        )

    @staticmethod
    def titulo_preview(preview):
        if not isinstance(preview, str):
            return "Conversación sin título"

        if "CONVERSATION:" not in preview:
            return "Conversación sin título"

        contenido = preview.split("CONVERSATION:", 1)[1]

        match = re.search(
            r"(?ms)^USER:\s*\n(.*?)(?=^(?:ASSISTANT|TOOL|USER):\s*$|\Z)",
            contenido
        )

        if not match:
            return "Conversación sin título"

        texto = " ".join(match.group(1).split())
        texto = re.sub(r"[\x00-\x1f\x7f]", " ", texto)
        texto = texto.strip()

        if not texto:
            return "Conversación sin título"

        return texto[:75].rstrip() + ("…" if len(texto) > 75 else "")

    @staticmethod
    def tamano_archivo(path):
        if not path:
            return 0

        try:
            info = os.stat(path, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode):
                return 0

            return getattr(info, "st_blocks", 0) * 512 or info.st_size
        except OSError:
            return 0

    def obtener_todos(self):
        backend = self.backend or CodexBackend(memory_enabled=False)
        propio = self.backend is None
        elementos = {}

        try:
            with backend._lock:
                backend._start()
                for archivada in (False, True):
                    cursor = None
                    cursores_vistos = set()

                    while True:
                        params = {"limit": 100, "archived": archivada}
                        if cursor:
                            if cursor in cursores_vistos:
                                raise RuntimeError("Codex devolvió un cursor repetido.")
                            cursores_vistos.add(cursor)
                            params["cursor"] = cursor

                        resultado = backend._rpc("thread/list", params)
                        for item in resultado.get("data", []):
                            thread_id = item.get("id")
                            if thread_id:
                                copia = dict(item)
                                copia["_archivada"] = archivada
                                elementos[thread_id] = copia

                        cursor = resultado.get("nextCursor")
                        if not cursor:
                            break
        finally:
            if propio:
                backend.close()

        return elementos

    def listar(self):
        elementos = self.obtener_todos()

        hijos = {}
        for item in elementos.values():
            padre = item.get("parentThreadId")
            if padre:
                hijos.setdefault(padre, []).append(item)

        raices = [
            item for item in elementos.values()
            if item.get("originator") == "tuxgenie"
            and not item.get("parentThreadId")
            and not item.get("ephemeral", False)
        ]

        conversaciones = []

        for raiz in raices:
            relacionados = []
            pendientes = [raiz.get("id")]
            visitados = set(pendientes)

            while pendientes:
                padre = pendientes.pop()

                for hijo in hijos.get(padre, []):
                    hijo_id = hijo.get("id")
                    if not hijo_id or hijo_id in visitados:
                        continue

                    visitados.add(hijo_id)
                    relacionados.append(hijo)
                    pendientes.append(hijo_id)

            rutas = set()
            tamano = 0

            for item in [raiz] + relacionados:
                ruta = item.get("path")
                if ruta and ruta not in rutas:
                    rutas.add(ruta)
                    tamano += self.tamano_archivo(ruta)

            nombre = raiz.get("name") or self.titulo_preview(
                raiz.get("preview", "")
            )

            conversaciones.append({
                "id": raiz["id"],
                "titulo": nombre,
                "creada": raiz.get("createdAt"),
                "actualizada": raiz.get("updatedAt"),
                "workspace": raiz.get("cwd") or "Desconocido",
                "tamano": tamano,
                "archivada": raiz.get("_archivada", False),
                "hijos": relacionados,
            })

        conversaciones.sort(
            key=lambda x: x.get("actualizada") or 0,
            reverse=True
        )

        return conversaciones

    @staticmethod
    def _normalizar(texto):
        texto = unicodedata.normalize("NFKD", str(texto or "").lower())
        return "".join(ch for ch in texto if not unicodedata.combining(ch))

    @classmethod
    def _terminos(cls, consulta):
        ignorar = {
            "que", "cual", "como", "cuando", "donde", "para", "por", "con",
            "una", "uno", "unos", "unas", "los", "las", "del", "de", "el",
            "la", "y", "o", "en", "sobre", "entre", "desde", "hasta", "me",
            "mi", "mis", "tu", "tus", "su", "sus", "hablamos", "dijimos",
            "conversacion", "anterior", "pasado", "recuerdo", "recuerdas",
            "tema", "algo", "esto", "esta", "ese", "esa", "aquel", "aquella",
            "the", "and", "for", "with", "from", "about", "what", "when",
            "where", "how", "did", "you", "our", "your", "this", "that",
        }
        tokens = re.findall(r"[a-z0-9]{2,}", cls._normalizar(consulta))
        salida = []
        for token in tokens:
            if token not in ignorar and token not in salida:
                salida.append(token)
        return salida[:6]

    @staticmethod
    def _limpiar_contexto_interno(texto):
        if not isinstance(texto, str):
            return ""
        return re.sub(
            r"<environment_context\b[^>]*>.*?(?:</environment_context\s*>|\Z)",
            "",
            texto,
            flags=re.IGNORECASE | re.DOTALL,
        ).strip()

    @staticmethod
    def _extraer_mensaje_usuario(texto):
        """Quitar instrucciones internas y conservar solo el diálogo real."""
        texto = CodexConversationManager._limpiar_contexto_interno(texto)
        if not texto:
            return ""

        # TuxGenie empaqueta instrucciones internas y el encargo del usuario
        # dentro de un único mensaje user. Solo la sección CONVERSATION es
        # diálogo; nunca debemos mostrar ni recuperar el bloque de sistema.
        if "CONVERSATION:" in texto:
            dialogo = texto.split("CONVERSATION:", 1)[1]
            patron = re.compile(
                r"(?ms)^(USER|ASSISTANT):[ \t]*\n(.*?)(?=^(?:USER|ASSISTANT|TOOL):[ \t]*\n|\Z)"
            )
            usuarios = [
                bloque.strip()
                for rol, bloque in patron.findall(dialogo)
                if rol == "USER" and bloque.strip()
            ]
            return "\n".join(usuarios).strip()

        # Algunos mensajes de inicialización pueden contener instrucciones
        # del sistema sin sección de conversación. No son mensajes del usuario.
        if re.search(
            r"(?im)^(?:SYSTEM INSTRUCTIONS:|IDIOMA OBLIGATORIO:|"
            r"You are TuxGenie,)",
            texto,
        ):
            return ""

        return texto.strip()

    @staticmethod
    def _texto_payload(payload):
        contenido = payload.get("content", [])
        if isinstance(contenido, str):
            return contenido
        if not isinstance(contenido, list):
            return ""
        partes = []
        for bloque in contenido:
            if not isinstance(bloque, dict):
                continue
            if bloque.get("type") in ("input_text", "output_text", "text"):
                texto = bloque.get("text")
                if isinstance(texto, str) and texto.strip():
                    partes.append(
                        CodexConversationManager._limpiar_contexto_interno(texto)
                    )
        return "\n".join(partes)

    @staticmethod
    def _fragmento(texto, terminos, limite=1000):
        limpio = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", texto or "")
        limpio = re.sub(r"\s+", " ", limpio).strip()
        if len(limpio) <= limite:
            return limpio
        plegado = CodexConversationManager._normalizar(limpio)
        posiciones = [plegado.find(t) for t in terminos if t and plegado.find(t) >= 0]
        if not posiciones:
            return limpio[:limite].rstrip() + "…"
        inicio = max(0, min(posiciones) - limite // 3)
        fin = min(len(limpio), inicio + limite)
        if inicio:
            fragmento = "…" + limpio[inicio:fin]
        else:
            fragmento = limpio[inicio:fin]
        if fin < len(limpio):
            fragmento += "…"
        return fragmento

    @classmethod
    def _terminos_api(cls, consulta, terminos_normalizados):
        originales = re.findall(r"[^\W_]{2,}", str(consulta or "").lower(), flags=re.UNICODE)
        salida = []
        vistos = set()
        for original in originales:
            normal = cls._normalizar(original)
            if normal in terminos_normalizados and normal not in vistos:
                vistos.add(normal)
                salida.append(original)
        return salida[:6]

    def _buscar_por_api(self, terminos, excluir_ids):
        """Usa thread/search si la versión local del App Server lo admite."""
        backend = self.backend or CodexBackend(memory_enabled=False)
        propio = self.backend is None
        encontrados = {}
        usado = False
        try:
            with backend._lock:
                backend._start()
                # La validación de propiedad se hace con thread/list, cuyo
                # resultado incluye originator en las versiones locales.
                catalogo = (
                    self.obtener_todos()
                    if self.backend is backend
                    else CodexConversationManager(backend=backend).obtener_todos()
                )
                for termino in terminos:
                    for archivada in (False, True):
                        cursor = None
                        cursores = set()
                        while True:
                            params = {
                                "searchTerm": termino,
                                "limit": 50,
                                "archived": archivada,
                                "sortKey": "updated_at",
                                "sortDirection": "desc",
                            }
                            if cursor:
                                if cursor in cursores:
                                    raise RuntimeError("Cursor repetido en búsqueda histórica.")
                                cursores.add(cursor)
                                params["cursor"] = cursor
                            resultado = backend._rpc("thread/search", params)
                            usado = True
                            for hallazgo in resultado.get("data", []):
                                hilo = hallazgo.get("thread") or {}
                                thread_id = hilo.get("id")
                                metadata = catalogo.get(thread_id)
                                if (
                                    not thread_id
                                    or thread_id in excluir_ids
                                    or not metadata
                                    or metadata.get("originator") != "tuxgenie"
                                    or metadata.get("parentThreadId")
                                    or metadata.get("ephemeral", False)
                                ):
                                    continue
                                item = encontrados.setdefault(thread_id, {
                                    "id": thread_id,
                                    "titulo": metadata.get("name") or hilo.get("name") or self.titulo_preview(metadata.get("preview", "")),
                                    "creada": metadata.get("createdAt") or hilo.get("createdAt"),
                                    "actualizada": metadata.get("updatedAt") or hilo.get("updatedAt"),
                                    "score": 0,
                                    "fragmentos": [],
                                })
                                snippet = hallazgo.get("snippet")
                                if isinstance(snippet, str) and snippet.strip():
                                    snippet_limpio = self._extraer_mensaje_usuario(snippet)
                                    if snippet_limpio:
                                        if snippet_limpio not in item["fragmentos"] and len(item["fragmentos"]) < 3:
                                            item["fragmentos"].append(snippet_limpio[:1200])
                                item["score"] += 2
                            cursor = resultado.get("nextCursor")
                            if not cursor:
                                break
            return sorted(encontrados.values(), key=lambda x: (x["score"], x.get("actualizada") or 0), reverse=True), usado
        finally:
            if propio:
                backend.close()

    def _buscar_en_archivos(self, terminos, excluir_ids, limite=3, solo_ids=None):
        """Busca en JSONL y devuelve el mensaje relevante junto a su respuesta."""
        elementos = self.obtener_todos()
        hijos = {}
        for item in elementos.values():
            padre = item.get("parentThreadId")
            if padre:
                hijos.setdefault(padre, []).append(item)

        raices = [
            item for item in elementos.values()
            if item.get("originator") == "tuxgenie"
            and not item.get("parentThreadId")
            and not item.get("ephemeral", False)
            and item.get("id") not in excluir_ids
            and (solo_ids is None or item.get("id") in solo_ids)
        ]

        codex_home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).expanduser().resolve()
        # No resolver estos directorios: una carpeta sessions que sea
        # un enlace simbólico debe rechazarse, no convertirse en raíz válida.
        raices_permitidas = [
            codex_home / "sessions",
            codex_home / "archived_sessions",
        ]
        resultados = []
        bytes_leidos = 0

        for raiz in raices:
            relacionados = []
            pendientes = [raiz.get("id")]
            vistos = set(pendientes)
            while pendientes:
                padre = pendientes.pop()
                for hijo in hijos.get(padre, []):
                    hijo_id = hijo.get("id")
                    if hijo_id and hijo_id not in vistos:
                        vistos.add(hijo_id)
                        relacionados.append(hijo)
                        pendientes.append(hijo_id)

            titulo = raiz.get("name") or self.titulo_preview(raiz.get("preview", ""))
            titulo_tokens = set(self._terminos(titulo))
            score = sum(4 for termino in terminos if termino in titulo_tokens)
            mensajes = []
            rutas = set()

            # Leer únicamente archivos regulares ubicados dentro de CODEX_HOME.
            for hilo in [raiz] + relacionados:
                ruta_original = hilo.get("path")
                if (
                    not isinstance(ruta_original, str)
                    or not ruta_original
                    or len(ruta_original) > 4096
                    or ruta_original in rutas
                ):
                    continue
                rutas.add(ruta_original)
                try:
                    ruta = Path(os.path.abspath(os.path.expanduser(ruta_original)))
                    archivo = _open_codex_jsonl(ruta, raices_permitidas)
                    if archivo is None:
                        continue

                    with archivo:
                        numero = 0
                        while bytes_leidos < MAX_JSONL_SEARCH_BYTES:
                            restante = MAX_JSONL_SEARCH_BYTES - bytes_leidos
                            linea_bytes = archivo.readline(
                                min(MAX_JSONL_LINE_BYTES + 1, restante)
                            )
                            if not linea_bytes:
                                break

                            bytes_leidos += len(linea_bytes)
                            if len(linea_bytes) > MAX_JSONL_LINE_BYTES:
                                # No procesar ni intentar completar líneas enormes.
                                break

                            if (
                                len(linea_bytes) == restante
                                and restante < MAX_JSONL_LINE_BYTES + 1
                                and not linea_bytes.endswith(b"\n")
                            ):
                                # El presupuesto terminó en medio de una línea.
                                break

                            numero += 1
                            try:
                                linea = linea_bytes.decode("utf-8")
                                registro = json.loads(linea)
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                continue
                            if not isinstance(registro, dict):
                                continue
                            if registro.get("type") != "response_item":
                                continue
                            payload = registro.get("payload")
                            if not isinstance(payload, dict):
                                continue
                            if payload.get("type") != "message":
                                continue
                            rol = payload.get("role")
                            if rol not in ("user", "assistant"):
                                continue
                            if rol == "assistant" and payload.get("phase") == "analysis":
                                continue
                            texto = self._texto_payload(payload)
                            if rol == "user":
                                texto = self._extraer_mensaje_usuario(texto)
                            if not texto.strip():
                                continue
                            tokens = set(self._terminos(texto))
                            coincidencias = [t for t in terminos if t in tokens]
                            peso = 4 if rol == "user" else 2
                            puntos = peso * len(coincidencias)
                            mensajes.append({
                                "numero": numero,
                                "rol": rol,
                                "texto": texto,
                                "phase": payload.get("phase"),
                                "score": puntos,
                                "coincidencias": bool(coincidencias),
                            })
                except (OSError, ValueError):
                    continue

            # Recuperar parejas pregunta/respuesta: la respuesta puede no repetir
            # literalmente las palabras usadas en la pregunta.
            seleccionados = []
            claves = set()

            def agregar(indice, extra=0):
                if indice < 0 or indice >= len(mensajes):
                    return
                mensaje = mensajes[indice]
                clave = (mensaje["numero"], mensaje["rol"])
                if clave in claves:
                    return
                claves.add(clave)
                seleccionados.append((mensaje, mensaje["score"] + extra))

            indices_usuario = [
                i for i, mensaje in enumerate(mensajes)
                if mensaje["rol"] == "user" and mensaje["coincidencias"]
            ]
            indices_usuario.sort(
                key=lambda i: mensajes[i]["score"], reverse=True
            )

            for indice in indices_usuario[:2]:
                agregar(indice)
                # Buscar la respuesta del asistente antes del siguiente
                # mensaje del usuario. Preferir phase=final y, si no existe,
                # tomar el último mensaje del asistente en ese turno.
                candidatos = []
                for j in range(indice + 1, min(len(mensajes), indice + 12)):
                    if mensajes[j]["rol"] == "user":
                        break
                    if mensajes[j]["rol"] == "assistant":
                        candidatos.append(j)
                if candidatos:
                    finales = [j for j in candidatos if mensajes[j].get("phase") == "final"]
                    agregar((finales or candidatos)[-1], extra=3)

            # Consultas que coincidan directamente con una respuesta del IA.
            indices_asistente = [
                i for i, mensaje in enumerate(mensajes)
                if mensaje["rol"] == "assistant"
                and mensaje["coincidencias"]
                and mensaje.get("phase") != "commentary"
            ]
            indices_asistente.sort(
                key=lambda i: mensajes[i]["score"], reverse=True
            )
            for indice in indices_asistente[:2]:
                agregar(indice)
                for j in range(indice - 1, max(-1, indice - 7), -1):
                    if mensajes[j]["rol"] == "user":
                        agregar(j, extra=1)
                        break

            if not seleccionados and score <= 0:
                continue

            # La puntuación combina título, pregunta y respuesta.
            score += sum(puntos for _, puntos in seleccionados)
            fragmentos = []
            for mensaje, _ in sorted(
                seleccionados,
                key=lambda par: (par[0]["numero"], par[0]["rol"] == "assistant")
            )[:4]:
                etiqueta = "Tú" if mensaje["rol"] == "user" else "Codex"
                fragmentos.append(
                    f"{etiqueta}: {self._fragmento(mensaje['texto'], terminos)}"
                )

            if score <= 0:
                continue

            resultados.append({
                "id": raiz["id"],
                "titulo": titulo,
                "creada": raiz.get("createdAt"),
                "actualizada": raiz.get("updatedAt"),
                "score": score,
                "fragmentos": fragmentos or [f"Título relacionado: {titulo}"],
            })

        return sorted(
            resultados,
            key=lambda x: (x["score"], x.get("actualizada") or 0),
            reverse=True,
        )[:limite]

    def buscar(self, consulta, max_resultados=3, excluir_ids=None):
        """Busca contexto histórico y combina snippets API con pares JSONL."""
        terminos = self._terminos(consulta)
        if not terminos:
            self._ultimo_metodo_busqueda = "consulta sin términos"
            return []
        excluir_ids = set(excluir_ids or ())

        api_resultados = []
        api_disponible = False
        try:
            terminos_api = self._terminos_api(consulta, set(terminos))
            api_resultados, api_disponible = self._buscar_por_api(
                terminos_api or terminos, excluir_ids
            )
        except Exception:
            # La búsqueda nativa no existe o no está disponible en esta versión.
            api_resultados = []
            api_disponible = False

        # En historiales pequeños, el JSONL complementa la búsqueda nativa:
        # thread/search puede encontrar la pregunta, pero no devolver la respuesta.
        try:
            total = sum(item["tamano"] for item in self.listar())
        except Exception:
            total = None

        locales = []
        # Si la API encontró hilos, leer solo esos JSONL para recuperar también
        # la respuesta del asistente. Esto escala aunque la biblioteca completa
        # sea grande, porque no se recorren todas las conversaciones.
        ids_api = {
            item.get("id") for item in api_resultados if item.get("id")
        }
        try:
            if ids_api:
                locales = self._buscar_en_archivos(
                    terminos, excluir_ids, max_resultados,
                    solo_ids=set(list(ids_api)[:max_resultados]),
                )
            elif total is not None and total <= 256 * 1024 * 1024:
                # Si la API no encontró nada, hacer una comprobación local
                # completa solo cuando el historial total sea pequeño.
                locales = self._buscar_en_archivos(
                    terminos, excluir_ids, max_resultados
                )
        except Exception:
            locales = []

        combinados = {}
        for resultado in locales:
            combinados[resultado["id"]] = dict(resultado)

        for resultado in api_resultados:
            actual = combinados.get(resultado["id"])
            if actual is None:
                combinados[resultado["id"]] = dict(resultado)
                continue

            # Conservar primero fragmentos locales etiquetados como Tú/Codex.
            fragmentos = list(actual.get("fragmentos", []))
            for fragmento in resultado.get("fragmentos", []):
                if fragmento not in fragmentos and len(fragmentos) < 4:
                    fragmentos.append(fragmento)
            actual["fragmentos"] = fragmentos
            actual["score"] = max(
                int(actual.get("score") or 0),
                int(resultado.get("score") or 0),
            )

        resultados = sorted(
            combinados.values(),
            key=lambda x: (x.get("score", 0), x.get("actualizada") or 0),
            reverse=True,
        )[:max_resultados]

        if locales and api_disponible:
            self._ultimo_metodo_busqueda = "App Server + JSONL local (pregunta y respuesta)"
        elif locales:
            self._ultimo_metodo_busqueda = "JSONL local (pregunta y respuesta)"
        elif api_resultados:
            self._ultimo_metodo_busqueda = "App Server thread/search (solo snippets disponibles)"
        elif total is not None and total > 256 * 1024 * 1024 and not api_disponible:
            self._ultimo_metodo_busqueda = "búsqueda omitida: API no disponible e historial grande"
        else:
            self._ultimo_metodo_busqueda = "sin coincidencias históricas"

        return resultados

    @staticmethod
    def formato_tamano(valor):
        if valor >= 1024 ** 3:
            return f"{valor / (1024 ** 3):.2f} GB"
        if valor >= 1024 ** 2:
            return f"{valor / (1024 ** 2):.2f} MB"
        if valor >= 1024:
            return f"{valor / 1024:.2f} KB"
        return f"{valor} bytes"

    def renombrar(self, conversacion, nuevo_nombre):
        nombre = nuevo_nombre.strip()

        if not nombre:
            print("El título no puede estar vacío.")
            return False

        if len(nombre) > 100:
            print("El título no puede superar los 100 caracteres.")
            return False

        actual = self.obtener_todos().get(conversacion["id"])

        if (
            not actual
            or actual.get("originator") != "tuxgenie"
            or actual.get("parentThreadId")
            or actual.get("ephemeral", False)
        ):
            print("No se pudo verificar que la conversación sea de TuxGenie.")
            return False

        self._api("thread/name/set", {
            "threadId": conversacion["id"],
            "name": nombre,
        })

        print("Título actualizado correctamente.")
        return True

    def eliminar(self, conversacion):
        # Volver a verificar el registro justo antes de eliminar.
        elementos = self.obtener_todos()
        actual = elementos.get(conversacion["id"])

        if (
            not actual
            or actual.get("originator") != "tuxgenie"
            or actual.get("parentThreadId")
            or actual.get("ephemeral", False)
        ):
            print("No se pudo verificar la conversación. No se eliminó.")
            return False

        # Reconstruir los hilos descendientes.
        hijos = {}
        for item in elementos.values():
            padre = item.get("parentThreadId")
            if padre:
                hijos.setdefault(padre, []).append(item)

        pendientes = [conversacion["id"]]
        visitados = set(pendientes)
        dependientes = []

        while pendientes:
            padre = pendientes.pop()

            for item in hijos.get(padre, []):
                item_id = item.get("id")
                if not item_id or item_id in visitados:
                    continue

                visitados.add(item_id)
                dependientes.append(item)
                pendientes.append(item_id)

        print("\nADVERTENCIA DE ELIMINACIÓN")
        print("Conversación:", conversacion["titulo"])
        print("Hilos dependientes:", len(dependientes))
        print("Espacio estimado recuperable:",
              self.formato_tamano(conversacion["tamano"]))

        if dependientes:
            print(
                "Codex puede eliminar también los hilos dependientes "
                "de esta conversación."
            )

        print("\nEsta acción no se puede deshacer.")
        confirmacion = input(
            "Escribe ELIMINAR para confirmar: "
        ).strip()

        if confirmacion != "ELIMINAR":
            print("Operación cancelada. No se eliminó nada.")
            return False

        self._api("thread/delete", {
            "threadId": conversacion["id"],
        })

        if self.on_delete:
            self.on_delete(conversacion)

        print("Conversación eliminada correctamente.")
        return True

    def ejecutar(self):
        pagina = 0
        c = self.pintar

        while True:
            conversaciones = self.listar()
            total = len(conversaciones)
            espacio = sum(x["tamano"] for x in conversaciones)
            paginas = max(1, (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
            pagina = min(pagina, paginas - 1)
            inicio = pagina * self.PAGE_SIZE
            fin = min(inicio + self.PAGE_SIZE, total)

            print("\n" + c("━" * 68, "cyan"))
            print(c("  🧠 ADMINISTRADOR DE CONVERSACIONES CODEX", "magenta", True))
            print(c("  Historial, continuidad y memoria de TuxGenie", "gris"))
            print(c("━" * 68, "cyan"))
            print(
                c("  Conversaciones:", "cyan", True), c(total, "verde", True),
                c("  |  Almacenamiento:", "cyan", True),
                c(self.formato_tamano(espacio), "amarillo", True),
            )
            print(c(f"  Página {pagina + 1} de {paginas}", "magenta", True))
            print(c("─" * 68, "gris"))

            if not conversaciones:
                print(c("\n  Todavía no hay conversaciones guardadas.", "gris"))
                print(c("  Puedes crear una nueva conversación desde aquí.", "gris"))

            for indice in range(inicio, fin):
                item = conversaciones[indice]
                estado = "Archivada" if item["archivada"] else "Activa"
                color_estado = "amarillo" if item["archivada"] else "verde"
                print("\n  " + c(f"[{indice + 1}] ", "amarillo", True) + c(item["titulo"], "blanco", True))
                print(
                    "      " + c("Fecha:", "cyan") + " " + self.fecha_es(item["creada"])
                    + "  " + c("Tamaño:", "cyan") + " " + self.formato_tamano(item["tamano"])
                )
                print("      " + c("Estado:", "cyan") + " " + c(estado, color_estado, True))

            print("\n" + c("─" * 68, "gris"))
            opciones = c("[s]", "verde", True) + " Siguiente página    "
            opciones += c("[a]", "amarillo", True) + " Página anterior    "
            if self.on_new:
                opciones += c("[n]", "cyan", True) + " Nueva conversación    "
            opciones += c("[v]", "magenta", True) + " Volver"
            print(opciones)

            try:
                opcion = input("\nSelecciona una conversación o una opción: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\n" + c("Regresando al menú principal.", "amarillo"))
                return

            if opcion == "v":
                print(c("\nRegresando al menú principal...", "cyan", True))
                return

            if opcion == "s":
                if pagina + 1 < paginas:
                    pagina += 1
                continue

            if opcion == "a":
                pagina = max(0, pagina - 1)
                continue

            if opcion == "n":
                if not self.on_new:
                    print(c("Nueva conversación solo está disponible dentro de TuxGenie.", "amarillo"))
                    continue
                try:
                    self.on_new()
                    print(c("\nNueva conversación preparada. Escribe tu siguiente mensaje en TuxGenie.", "verde", True))
                    return "new"
                except Exception as exc:
                    print(c("No se pudo iniciar una conversación nueva:", "rojo"), exc)
                    continue

            if not opcion.isdigit():
                print(c("Opción no válida.", "rojo", True))
                continue

            indice = int(opcion) - 1
            if indice < inicio or indice >= fin:
                print(c("Selecciona un número de la página actual.", "rojo"))
                continue

            item = conversaciones[indice]
            print("\n" + c("CONVERSACIÓN SELECCIONADA", "magenta", True))
            print(c("Título:", "cyan"), item["titulo"])
            print(c("Fecha:", "cyan"), self.fecha_es(item["creada"]))
            print(c("Tamaño:", "cyan"), self.formato_tamano(item["tamano"]))
            print(c("Espacio de trabajo:", "cyan"), item["workspace"])
            print(c("Hilos dependientes:", "cyan"), len(item["hijos"]))

            try:
                accion = input("\n[c] Continuar  [r] Cambiar título  [e] Eliminar  [v] Volver: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                continue

            if accion == "c":
                if not self.on_continue:
                    print(c("Para continuarla, abre el administrador desde TuxGenie.", "amarillo"))
                else:
                    try:
                        self.on_continue(item)
                        print(c("\nConversación reanudada. Tu siguiente mensaje continuará este hilo.", "verde", True))
                        return "continued"
                    except Exception as exc:
                        print(c("No se pudo reanudar la conversación:", "rojo"), exc)

            elif accion == "r":
                try:
                    nuevo = input("Escribe el nuevo título: ")
                    self.renombrar(item, nuevo)
                except (KeyboardInterrupt, EOFError):
                    print(c("\nCambio de título cancelado.", "amarillo"))
                except Exception as exc:
                    print(c("No se pudo cambiar el título:", "rojo"), exc)

            elif accion == "e":
                try:
                    self.eliminar(item)
                except (KeyboardInterrupt, EOFError):
                    print(c("\nEliminación cancelada.", "amarillo"))
                except Exception as exc:
                    print(c("No se pudo eliminar la conversación:", "rojo"), exc)

            elif accion != "v":
                print(c("Opción no válida.", "rojo"))

            try:
                input("\nPulsa Enter para actualizar la lista...")
            except (KeyboardInterrupt, EOFError):
                continue



def main():
    try:
        CodexConversationManager().ejecutar()
    except (KeyboardInterrupt, EOFError):
        print("\nAdministrador cerrado.")
    except Exception as exc:
        print("\nError del administrador:", type(exc).__name__, str(exc))


if __name__ == "__main__":
    main()
