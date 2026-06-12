from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Optional

from upgrade_copilot.api import UpgradeCopilot
from upgrade_copilot.config import Settings
from upgrade_copilot.index.models import SourceDocument
from upgrade_copilot.ingest.sources import resolve_sources
from upgrade_copilot.web import serve


def _read_documents(path: Path) -> list[SourceDocument]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [SourceDocument(**item) for item in payload]


def build_parser() -> argparse.ArgumentParser:
    settings = Settings()
    parser = argparse.ArgumentParser(prog="upgrade-copilot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest")
    ingest.add_argument("manifest", type=Path, help="JSON file containing source documents")

    build_index = subparsers.add_parser("build-index")
    build_index.add_argument(
        "--sources",
        type=Path,
        default=None,
        help="JSON source manifest. Defaults to built-in official migration sources.",
    )
    build_index.add_argument(
        "--index-path",
        type=Path,
        default=settings.index_path,
        help="Destination path for the persisted index.",
    )
    build_index.add_argument(
        "--cache-dir",
        type=Path,
        default=settings.cache_dir,
        help="Directory for cached raw HTML.",
    )
    build_index.add_argument(
        "--refresh",
        action="store_true",
        help="Re-fetch sources even if cached HTML exists.",
    )
    build_index.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Per-source fetch timeout in seconds.",
    )

    search = subparsers.add_parser("search")
    search.add_argument("manifest", type=Path, help="JSON file containing source documents")
    search.add_argument("query", help="Search query")
    search.add_argument("-k", type=int, default=5)

    search_index = subparsers.add_parser("search-index")
    search_index.add_argument("query", help="Search query")
    search_index.add_argument("--index-path", type=Path, default=settings.index_path)
    search_index.add_argument("-k", type=int, default=5)

    answer = subparsers.add_parser("answer")
    answer.add_argument("manifest", type=Path, help="JSON file containing source documents")
    answer.add_argument("question", help="Question to answer")
    answer.add_argument("-k", type=int, default=4)

    answer_index = subparsers.add_parser("answer-index")
    answer_index.add_argument("question", help="Question to answer")
    answer_index.add_argument("--index-path", type=Path, default=settings.index_path)
    answer_index.add_argument("-k", type=int, default=4)

    scan_repo = subparsers.add_parser("scan-repo")
    scan_repo.add_argument("--repo-root", type=Path, default=settings.repo_root)
    scan_repo.add_argument("--index-path", type=Path, default=settings.index_path)
    scan_repo.add_argument("-k", type=int, default=4)

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--host", default=os.environ.get("UPGRADE_COPILOT_HOST", "127.0.0.1"))
    serve_parser.add_argument("--port", type=int, default=int(os.environ.get("UPGRADE_COPILOT_PORT", "8000")))
    serve_parser.add_argument("--index-path", type=Path, default=settings.index_path)
    serve_parser.add_argument("--cache-dir", type=Path, default=settings.cache_dir)
    serve_parser.add_argument("--repo-root", type=Path, default=settings.repo_root)

    return parser


def _print_search_results(copilot: UpgradeCopilot, query: str, k: int) -> None:
    for result in copilot.search(query, k=k):
        heading = " > ".join(result.chunk.heading_path)
        prefix = f"{result.chunk.title} / {heading}" if heading else result.chunk.title
        print(f"{result.score:.3f}  {prefix}")
        print(result.chunk.text)


def _print_answer(copilot: UpgradeCopilot, question: str, k: int) -> None:
    answer = copilot.answer(question, k=k)
    print(answer.text)
    for citation in answer.citations:
        print(f"- {citation.label} -> {citation.url}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    copilot = UpgradeCopilot()

    if args.command == "ingest":
        documents = _read_documents(args.manifest)
        chunks = copilot.ingest_documents(documents)
        print(f"Indexed {len(chunks)} chunks")
        return 0

    if args.command == "build-index":
        specs = resolve_sources(args.sources)
        chunks = copilot.build_index_from_sources(
            specs,
            cache_dir=args.cache_dir,
            refresh=args.refresh,
            timeout=args.timeout,
        )
        copilot.save_index(args.index_path)
        print(f"Indexed {len(chunks)} chunks from {len(specs)} sources into {args.index_path}")
        return 0

    if args.command == "search-index":
        copilot.load_index(args.index_path)
        _print_search_results(copilot, args.query, args.k)
        return 0

    if args.command == "answer-index":
        copilot.load_index(args.index_path)
        _print_answer(copilot, args.question, args.k)
        return 0

    if args.command == "scan-repo":
        copilot.load_index(args.index_path)
        print(json.dumps(copilot.scan_repository(repo_root=args.repo_root, k=args.k), indent=2))
        return 0

    if args.command == "serve":
        serve(
            host=args.host,
            port=args.port,
            index_path=args.index_path,
            cache_dir=args.cache_dir,
            repo_root=args.repo_root,
        )
        return 0

    documents = _read_documents(args.manifest)
    copilot.ingest_documents(documents)

    if args.command == "search":
        _print_search_results(copilot, args.query, args.k)
        return 0

    if args.command == "answer":
        _print_answer(copilot, args.question, args.k)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
