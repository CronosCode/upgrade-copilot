from __future__ import annotations

import json
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Callable, Iterable, Optional
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from upgrade_copilot.api import UpgradeCopilot
from upgrade_copilot.ingest.sources import default_sources, resolve_sources


HTML_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Upgrade Copilot</title>
    <style>
      :root {
        --bg: #f7f8fa;
        --ink: #15202b;
        --muted: #607080;
        --panel: #ffffff;
        --accent: #126b67;
        --accent-2: #8a5a12;
        --line: #d7dee6;
        --code: #101820;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: var(--ink);
        background: var(--bg);
      }
      main {
        max-width: 1180px;
        margin: 0 auto;
        padding: 28px 20px 48px;
      }
      header {
        display: grid;
        gap: 12px;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: end;
        margin-bottom: 18px;
      }
      h1 {
        font-size: 1.7rem;
        margin: 0 0 4px;
        letter-spacing: 0;
      }
      p {
        color: var(--muted);
        margin: 0;
      }
      .health {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        justify-content: flex-end;
      }
      .pill {
        border: 1px solid var(--line);
        border-radius: 999px;
        background: var(--panel);
        color: var(--muted);
        font-size: 0.85rem;
        padding: 6px 10px;
      }
      .grid {
        display: grid;
        gap: 14px;
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }
      .panel {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 16px;
      }
      h2 {
        margin: 0 0 12px;
        font-size: 1rem;
      }
      label {
        display: block;
        font-size: 0.83rem;
        color: var(--muted);
        margin: 12px 0 6px;
      }
      input, textarea {
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 6px;
        padding: 10px 12px;
        font: inherit;
        background: white;
        color: var(--ink);
      }
      textarea { min-height: 120px; resize: vertical; }
      button {
        margin-top: 10px;
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 9px 12px;
        font: inherit;
        background: var(--accent);
        color: white;
        cursor: pointer;
      }
      button.secondary { background: var(--accent-2); }
      button:disabled { cursor: wait; opacity: 0.7; }
      pre {
        white-space: pre-wrap;
        word-break: break-word;
        background: var(--code);
        border: 1px solid var(--code);
        border-radius: 6px;
        color: #edf3f7;
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size: 0.82rem;
        padding: 12px;
        min-height: 120px;
        overflow: auto;
      }
      .toolbar {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }
      @media (max-width: 640px) {
        main { padding: 20px 12px 36px; }
        header { grid-template-columns: 1fr; }
        .health { justify-content: flex-start; }
        .grid { grid-template-columns: 1fr; }
      }
      @media (min-width: 641px) and (max-width: 960px) {
        .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      }
    </style>
  </head>
  <body>
    <main>
      <header>
        <div>
          <h1>Upgrade Copilot</h1>
          <p>Grounded migration answers from official documentation.</p>
        </div>
        <div class="health">
          <span class="pill" id="status">Checking index...</span>
          <span class="pill" id="repoMeta">Detecting repository...</span>
        </div>
      </header>
      <div class="grid">
        <section class="panel">
          <h2>Build Index</h2>
          <label for="sourcesPath">Source manifest path (optional)</label>
          <input id="sourcesPath" placeholder="data/official_sources.json">
          <label for="refresh">Refresh cached pages</label>
          <input id="refresh" type="checkbox" style="width:auto">
          <div class="toolbar"><button id="buildButton">Build Local Index</button></div>
          <pre id="buildOutput"></pre>
        </section>
        <section class="panel">
          <h2>Search</h2>
          <label for="libraryFilter">Library filter (comma separated, optional)</label>
          <input id="libraryFilter" placeholder="fastapi,pydantic">
          <label for="searchQuery">Search query</label>
          <textarea id="searchQuery">sqlalchemy safest path 1.4 to 2.0</textarea>
          <div class="toolbar"><button class="secondary" id="searchButton">Run Search</button></div>
          <pre id="searchOutput"></pre>
        </section>
        <section class="panel">
          <h2>Answer</h2>
          <label for="answerLibraryFilter">Library filter (comma separated, optional)</label>
          <input id="answerLibraryFilter" placeholder="pydantic">
          <label for="answerQuestion">Question</label>
          <textarea id="answerQuestion">How do I keep using Pydantic v1 while migrating to v2?</textarea>
          <div class="toolbar"><button id="answerButton">Generate Answer</button></div>
          <pre id="answerOutput"></pre>
        </section>
        <section class="panel">
          <h2>Repo Scan</h2>
          <label for="scanFiles">Dependency files as JSON object</label>
          <textarea id="scanFiles">{"pyproject.toml":"[project]\\ndependencies = [\\"pydantic>=2\\", \\"numpy>=2\\"]"}</textarea>
          <div class="toolbar"><button class="secondary" id="scanButton">Scan Repository</button></div>
          <pre id="scanOutput"></pre>
        </section>
      </div>
    </main>
    <script>
      async function readJson(response) {
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.error || JSON.stringify(payload));
        }
        return payload;
      }

      async function loadHealth() {
        const payload = await readJson(await fetch('/health'));
        document.getElementById('status').textContent =
          (payload.index_loaded ? 'Index ready' : 'Index missing') +
          ' | chunks: ' + payload.chunk_count;
        const dependencies = payload.detected_dependencies.map(function (item) {
          return item.library;
        });
        document.getElementById('repoMeta').textContent =
          'Repo libraries: ' + (dependencies.length ? dependencies.join(', ') : 'none');
      }

      async function postJson(url, body) {
        return readJson(await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }));
      }

      function parseLibraries(value) {
        return value
          .split(',')
          .map(function (item) { return item.trim().toLowerCase(); })
          .filter(Boolean);
      }

      document.getElementById('buildButton').onclick = async function () {
        this.disabled = true;
        try {
          const payload = await postJson('/index/build', {
            sources_path: document.getElementById('sourcesPath').value || null,
            refresh: document.getElementById('refresh').checked,
          });
          document.getElementById('buildOutput').textContent = JSON.stringify(payload, null, 2);
          loadHealth();
        } catch (error) {
          document.getElementById('buildOutput').textContent = error.message;
        } finally {
          this.disabled = false;
        }
      };

      document.getElementById('searchButton').onclick = async function () {
        this.disabled = true;
        try {
          const payload = await postJson('/search', {
            query: document.getElementById('searchQuery').value,
            k: 5,
            libraries: parseLibraries(document.getElementById('libraryFilter').value),
            auto_detect_repo: true,
          });
          document.getElementById('searchOutput').textContent = JSON.stringify(payload, null, 2);
        } catch (error) {
          document.getElementById('searchOutput').textContent = error.message;
        } finally {
          this.disabled = false;
        }
      };

      document.getElementById('answerButton').onclick = async function () {
        this.disabled = true;
        try {
          const payload = await postJson('/answer', {
            question: document.getElementById('answerQuestion').value,
            k: 4,
            libraries: parseLibraries(document.getElementById('answerLibraryFilter').value),
            auto_detect_repo: true,
          });
          document.getElementById('answerOutput').textContent = JSON.stringify(payload, null, 2);
        } catch (error) {
          document.getElementById('answerOutput').textContent = error.message;
        } finally {
          this.disabled = false;
        }
      };

      document.getElementById('scanButton').onclick = async function () {
        this.disabled = true;
        try {
          const payload = await postJson('/repo/scan', {
            files: JSON.parse(document.getElementById('scanFiles').value || '{}'),
            k: 4,
          });
          document.getElementById('scanOutput').textContent = JSON.stringify(payload, null, 2);
        } catch (error) {
          document.getElementById('scanOutput').textContent = error.message;
        } finally {
          this.disabled = false;
        }
      };

      loadHealth().catch(function (error) {
        document.getElementById('status').textContent = error.message;
      });
    </script>
  </body>
</html>
"""


class UpgradeCopilotWebApp:
    def __init__(
        self,
        copilot: Optional[UpgradeCopilot] = None,
        index_path: Path = Path("data/index.json"),
        cache_dir: Path = Path("data/cache"),
        repo_root: Path = Path.cwd(),
    ) -> None:
        self.copilot = copilot or UpgradeCopilot()
        self.index_path = index_path
        self.cache_dir = cache_dir
        self.repo_root = repo_root.resolve()
        self._try_load_index()

    def __call__(self, environ: dict, start_response: Callable) -> Iterable[bytes]:
        try:
            method = environ["REQUEST_METHOD"].upper()
            path = environ.get("PATH_INFO", "/")

            if method == "OPTIONS":
                return self._respond(start_response, "204 No Content", "", "text/plain; charset=utf-8")
            if method == "GET" and path == "/":
                return self._respond(start_response, "200 OK", HTML_PAGE, "text/html; charset=utf-8")
            if method == "GET" and path == "/health":
                return self._json(start_response, 200, self.health())
            if method == "GET" and path == "/ready":
                ready = self.ready()
                return self._json(start_response, 200 if ready["ready"] else 503, ready)
            if method == "GET" and path == "/repo/dependencies":
                return self._json(start_response, 200, self.repository_dependencies())
            if method == "GET" and path == "/repo/scan":
                return self._json(start_response, 200, self.scan_repository())
            if method == "GET" and path == "/sources":
                payload = {"sources": [spec.__dict__ for spec in default_sources()]}
                return self._json(start_response, 200, payload)
            if method == "POST" and path == "/index/build":
                request = self._read_json(environ)
                payload = self.build_index(
                    sources_path=request.get("sources_path"),
                    refresh=bool(request.get("refresh", False)),
                    timeout=_bounded_int(request.get("timeout", 20), minimum=1, maximum=120, name="timeout"),
                )
                return self._json(start_response, 200, payload)
            if method == "POST" and path == "/search":
                request = self._read_json(environ)
                payload = self.search(
                    query=request["query"],
                    k=_bounded_int(request.get("k", 5), minimum=1, maximum=20, name="k"),
                    libraries=_normalize_libraries(request.get("libraries", [])),
                    auto_detect_repo=bool(request.get("auto_detect_repo", True)),
                )
                return self._json(start_response, 200, payload)
            if method == "POST" and path == "/answer":
                request = self._read_json(environ)
                payload = self.answer(
                    question=request["question"],
                    k=_bounded_int(request.get("k", 4), minimum=1, maximum=20, name="k"),
                    libraries=_normalize_libraries(request.get("libraries", [])),
                    auto_detect_repo=bool(request.get("auto_detect_repo", True)),
                )
                return self._json(start_response, 200, payload)
            if method == "POST" and path == "/repo/scan":
                request = self._read_json(environ)
                payload = self.scan_repository(
                    files=_normalize_file_payload(request.get("files")),
                    k=_bounded_int(request.get("k", 4), minimum=1, maximum=10, name="k"),
                )
                return self._json(start_response, 200, payload)

            return self._json(start_response, 404, {"error": "Route not found"})
        except FileNotFoundError as exc:
            return self._json(start_response, 404, {"error": str(exc)})
        except KeyError as exc:
            return self._json(start_response, 400, {"error": "Missing field: {name}".format(name=exc.args[0])})
        except RuntimeError as exc:
            return self._json(start_response, 409, {"error": str(exc)})
        except ValueError as exc:
            return self._json(start_response, 400, {"error": str(exc)})
        except Exception as exc:
            return self._json(start_response, 500, {"error": "Server error: {msg}".format(msg=str(exc))})

    def health(self) -> dict:
        return {
            "ok": True,
            "index_loaded": bool(self.copilot.store.chunks),
            "chunk_count": len(self.copilot.store.chunks),
            "index_path": str(self.index_path),
            "cache_dir": str(self.cache_dir),
            "repo_root": str(self.repo_root),
            "detected_dependencies": self.repository_dependencies()["dependencies"],
        }

    def ready(self) -> dict:
        if self.copilot.store.chunks:
            return {"ready": True, "reason": "index_loaded", "chunk_count": len(self.copilot.store.chunks)}
        if self.index_path.exists():
            self.copilot.load_index(self.index_path)
            return {"ready": True, "reason": "index_loaded_from_disk", "chunk_count": len(self.copilot.store.chunks)}
        return {"ready": False, "reason": "index_missing", "chunk_count": 0}

    def repository_dependencies(self) -> dict:
        return {
            "repo_root": str(self.repo_root),
            "dependencies": [
                {
                    "library": item.library,
                    "matches": item.matches,
                    "files": item.files,
                }
                for item in self.copilot.detect_repository_dependencies(self.repo_root)
            ],
        }

    def scan_repository(
        self,
        files: Optional[dict[str, str]] = None,
        k: int = 4,
    ) -> dict:
        self._ensure_index()
        return self.copilot.scan_repository(
            repo_root=self.repo_root,
            dependency_files=files,
            k=k,
        )

    def build_index(
        self,
        sources_path: Optional[str] = None,
        refresh: bool = False,
        timeout: int = 20,
    ) -> dict:
        specs = resolve_sources(sources_path)
        chunks = self.copilot.build_index_from_sources(
            specs,
            cache_dir=self.cache_dir,
            refresh=refresh,
            timeout=timeout,
        )
        self.copilot.save_index(self.index_path)
        return {
            "indexed_chunks": len(chunks),
            "source_count": len(specs),
            "index_path": str(self.index_path),
        }

    def _preferred_libraries(
        self,
        libraries: Optional[set[str]] = None,
        auto_detect_repo: bool = True,
    ) -> set[str]:
        preferred = set(libraries or set())
        if auto_detect_repo:
            preferred.update(self.copilot.preferred_libraries(self.repo_root))
        return preferred

    def search(
        self,
        query: str,
        k: int = 5,
        libraries: Optional[set[str]] = None,
        auto_detect_repo: bool = True,
    ) -> dict:
        query = _require_non_empty(query, "query")
        self._ensure_index()
        preferred = self._preferred_libraries(libraries=libraries, auto_detect_repo=auto_detect_repo)
        results = self.copilot.search(
            query,
            k=k,
            preferred_libraries=preferred,
            library_filter=set(libraries or set()) or None,
        )
        return {
            "query": query,
            "preferred_libraries": sorted(preferred),
            "library_filter": sorted(set(libraries or set())),
            "results": [
                {
                    "score": result.score,
                    "semantic_score": result.semantic_score,
                    "lexical_score": result.lexical_score,
                    "chunk_id": result.chunk.chunk_id,
                    "source_id": result.chunk.source_id,
                    "library": result.chunk.library,
                    "title": result.chunk.title,
                    "heading_path": list(result.chunk.heading_path),
                    "text": result.chunk.text,
                    "url": result.chunk.url,
                }
                for result in results
            ],
        }

    def answer(
        self,
        question: str,
        k: int = 4,
        libraries: Optional[set[str]] = None,
        auto_detect_repo: bool = True,
    ) -> dict:
        question = _require_non_empty(question, "question")
        self._ensure_index()
        preferred = self._preferred_libraries(libraries=libraries, auto_detect_repo=auto_detect_repo)
        answer = self.copilot.answer(
            question,
            k=k,
            preferred_libraries=preferred,
            library_filter=set(libraries or set()) or None,
        )
        return {
            "question": question,
            "supported": answer.supported,
            "text": answer.text,
            "preferred_libraries": sorted(preferred),
            "library_filter": sorted(set(libraries or set())),
            "citations": [
                {
                    "label": citation.label,
                    "title": citation.title,
                    "url": citation.url,
                    "chunk_id": citation.chunk_id,
                }
                for citation in answer.citations
            ],
        }

    def _ensure_index(self) -> None:
        if self.copilot.store.chunks:
            return
        if self.index_path.exists():
            self.copilot.load_index(self.index_path)
            return
        raise RuntimeError("No local index is loaded. Build one first with POST /index/build or `upgrade-copilot build-index`.")

    def _try_load_index(self) -> None:
        if self.index_path.exists():
            self.copilot.load_index(self.index_path)

    def _read_json(self, environ: dict) -> dict:
        length = int(environ.get("CONTENT_LENGTH") or 0)
        if length > 1_000_000:
            raise ValueError("Request body is too large")
        raw = environ["wsgi.input"].read(length) if length else b"{}"
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _respond(
        self,
        start_response: Callable,
        status: str,
        body: str,
        content_type: str,
    ) -> Iterable[bytes]:
        encoded = body.encode("utf-8")
        start_response(
            status,
            [
                ("Content-Type", content_type),
                ("Content-Length", str(len(encoded))),
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Allow-Headers", "Content-Type"),
                ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
                ("Cache-Control", "no-store"),
            ],
        )
        return [encoded]

    def _json(self, start_response: Callable, status_code: int, payload: dict) -> Iterable[bytes]:
        status = "{code} {label}".format(code=status_code, label=_status_text(status_code))
        return self._respond(
            start_response,
            status,
            json.dumps(payload, indent=2),
            "application/json; charset=utf-8",
        )


def create_app(
    index_path: Path = Path("data/index.json"),
    cache_dir: Path = Path("data/cache"),
    repo_root: Path = Path.cwd(),
) -> UpgradeCopilotWebApp:
    return UpgradeCopilotWebApp(index_path=index_path, cache_dir=cache_dir, repo_root=repo_root)


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
    index_path: Path = Path("data/index.json"),
    cache_dir: Path = Path("data/cache"),
    repo_root: Path = Path.cwd(),
) -> None:
    app = create_app(index_path=index_path, cache_dir=cache_dir, repo_root=repo_root)
    with make_server(host, port, app, server_class=ThreadingWSGIServer, handler_class=WSGIRequestHandler) as server:
        print("Upgrade Copilot web server listening on http://{host}:{port}".format(host=host, port=port))
        server.serve_forever()


def _status_text(status_code: int) -> str:
    return {
        204: "No Content",
        200: "OK",
        400: "Bad Request",
        404: "Not Found",
        409: "Conflict",
        503: "Service Unavailable",
        500: "Internal Server Error",
    }[status_code]


def _bounded_int(value: object, minimum: int, maximum: int, name: str) -> int:
    parsed = int(value)
    if parsed < minimum or parsed > maximum:
        raise ValueError("{name} must be between {minimum} and {maximum}".format(name=name, minimum=minimum, maximum=maximum))
    return parsed


def _normalize_libraries(value: object) -> set[str]:
    if value in (None, ""):
        return set()
    if not isinstance(value, list):
        raise ValueError("libraries must be a list of strings")
    libraries: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise ValueError("libraries must be a list of strings")
        normalized = item.strip().lower()
        if normalized:
            libraries.add(normalized)
    return libraries


def _normalize_file_payload(value: object) -> Optional[dict[str, str]]:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("files must be an object mapping file paths to text")
    files: dict[str, str] = {}
    for path, content in value.items():
        if not isinstance(path, str) or not isinstance(content, str):
            raise ValueError("files must be an object mapping file paths to text")
        normalized_path = path.strip()
        if normalized_path:
            files[normalized_path] = content
    return files


def _require_non_empty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("{name} must not be empty".format(name=name))
    return value.strip()
