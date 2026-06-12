import json
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

from upgrade_copilot.web import UpgradeCopilotWebApp


def _call_app(
    app: UpgradeCopilotWebApp,
    method: str,
    path: str,
    payload: Optional[dict] = None,
) -> Tuple[str, bytes]:
    raw = json.dumps(payload or {}).encode("utf-8")
    captured: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = headers

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": BytesIO(raw),
    }
    body = b"".join(app(environ, start_response))
    return captured["status"], body


def _call_app_with_headers(
    app: UpgradeCopilotWebApp,
    method: str,
    path: str,
    payload: Optional[dict] = None,
) -> Tuple[str, dict[str, str], bytes]:
    raw = json.dumps(payload or {}).encode("utf-8")
    captured: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = dict(headers)

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": BytesIO(raw),
    }
    body = b"".join(app(environ, start_response))
    return captured["status"], captured["headers"], body


def test_health_endpoint_reports_empty_index(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
        [project]
        dependencies = ["fastapi>=0.110", "pydantic>=2"]
        """,
        encoding="utf-8",
    )
    app = UpgradeCopilotWebApp(
        index_path=tmp_path / "index.json",
        cache_dir=tmp_path / "cache",
        repo_root=tmp_path,
    )

    status, body = _call_app(app, "GET", "/health")
    payload = json.loads(body.decode("utf-8"))

    assert status.startswith("200")
    assert payload["index_loaded"] is False
    assert [item["library"] for item in payload["detected_dependencies"]] == ["fastapi", "pydantic"]


def test_ready_endpoint_and_cors_headers(tmp_path: Path) -> None:
    app = UpgradeCopilotWebApp(
        index_path=tmp_path / "index.json",
        cache_dir=tmp_path / "cache",
        repo_root=tmp_path,
    )

    status, headers, body = _call_app_with_headers(app, "GET", "/ready")
    payload = json.loads(body.decode("utf-8"))

    assert status.startswith("503")
    assert payload["ready"] is False
    assert headers["Access-Control-Allow-Origin"] == "*"

    status, _, body = _call_app_with_headers(app, "OPTIONS", "/answer")
    assert status.startswith("204")
    assert body == b""


def test_search_rejects_empty_query(tmp_path: Path) -> None:
    app = UpgradeCopilotWebApp(
        index_path=tmp_path / "index.json",
        cache_dir=tmp_path / "cache",
        repo_root=tmp_path,
    )

    status, body = _call_app(app, "POST", "/search", {"query": "", "k": 5})
    payload = json.loads(body.decode("utf-8"))

    assert status.startswith("400")
    assert payload["error"] == "query must not be empty"


def test_build_search_and_answer_endpoints(tmp_path: Path) -> None:
    pydantic_html = tmp_path / "pydantic.html"
    pydantic_html.write_text(
        "<html><body><h1>Continue using v1</h1><p>Import from pydantic.v1 during migration.</p></body></html>",
        encoding="utf-8",
    )
    manifest = tmp_path / "sources.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "source_id": "pydantic-v2-migration",
                    "library": "pydantic",
                    "title": "Pydantic V2 Migration Guide",
                    "url": pydantic_html.as_uri(),
                    "tags": ["migration", "official"],
                }
            ]
        ),
        encoding="utf-8",
    )

    (tmp_path / "pyproject.toml").write_text(
        """
        [project]
        dependencies = ["pydantic>=2"]
        """,
        encoding="utf-8",
    )

    app = UpgradeCopilotWebApp(
        index_path=tmp_path / "index.json",
        cache_dir=tmp_path / "cache",
        repo_root=tmp_path,
    )

    status, build_body = _call_app(
        app,
        "POST",
        "/index/build",
        {"sources_path": str(manifest), "refresh": False},
    )
    build_payload = json.loads(build_body.decode("utf-8"))

    assert status.startswith("200")
    assert build_payload["indexed_chunks"] >= 1

    status, search_body = _call_app(
        app,
        "POST",
        "/search",
        {"query": "keep using pydantic v1", "k": 3, "auto_detect_repo": True},
    )
    search_payload = json.loads(search_body.decode("utf-8"))
    assert status.startswith("200")
    assert search_payload["results"][0]["source_id"] == "pydantic-v2-migration"
    assert "pydantic" in search_payload["preferred_libraries"]

    status, answer_body = _call_app(
        app,
        "POST",
        "/answer",
        {"question": "How do I keep using Pydantic v1 while migrating to v2?", "k": 3},
    )
    answer_payload = json.loads(answer_body.decode("utf-8"))
    assert status.startswith("200")
    assert answer_payload["supported"] is True
    assert answer_payload["citations"]

    status, scan_body = _call_app(
        app,
        "POST",
        "/repo/scan",
        {
            "files": {
                "pyproject.toml": '[project]\ndependencies = ["pydantic>=2"]',
            },
            "k": 3,
        },
    )
    scan_payload = json.loads(scan_body.decode("utf-8"))
    assert status.startswith("200")
    assert scan_payload["dependency_count"] == 1
    assert scan_payload["dependencies"][0]["library"] == "pydantic"
    assert scan_payload["guidance"][0]["citations"]
