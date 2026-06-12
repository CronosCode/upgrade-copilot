# Upgrade Copilot

Upgrade Copilot is a retrieval-first backend for dependency migration help. The current implementation is intentionally local and lightweight:

- ingest official upgrade docs
- clean and chunk them by heading-aware sections
- embed them with a deterministic local embedder by default
- search them with a simple vector store
- answer only from retrieved evidence with citations
- evaluate retrieval and abstention behavior

## Quick Start

Install the package in editable mode and run the tests:

```bash
python -m pip install -e ".[dev]"
pytest
```

Build a persistent local index from the built-in official source manifest:

```bash
upgrade-copilot build-index
upgrade-copilot search-index "sqlalchemy session changes"
upgrade-copilot answer-index "How do I keep using Pydantic v1 while migrating to v2?"
```

Run the local HTTP + HTML interface:

```bash
upgrade-copilot serve
```

Then open `http://127.0.0.1:8000`.

For container or Kubernetes usage, bind the service to all interfaces:

```bash
UPGRADE_COPILOT_HOST=0.0.0.0 upgrade-copilot serve
```

If you have not installed the package globally, use the repo-local runner instead:

```bash
./bin/serve
```

Or create a local virtual environment and use the Makefile:

```bash
make venv
make serve
```

## Current Architecture

- `upgrade_copilot.ingest.sources`: official source manifest
- `upgrade_copilot.ingest.fetch`: local/file/HTTP document fetcher
- `upgrade_copilot.ingest.clean`: HTML cleaning into text blocks
- `upgrade_copilot.ingest.chunk`: heading-aware chunking
- `upgrade_copilot.index.embeddings`: hashing embedder with optional SentenceTransformers backend
- `upgrade_copilot.index.faiss_store`: simple vector store interface with persistence
- `upgrade_copilot.retrieval.search`: retrieval and lexical reranking
- `upgrade_copilot.rag.answer`: grounded answers with citations
- `upgrade_copilot.eval.*`: retrieval and answer quality checks

## CLI

The CLI currently expects a JSON manifest of `SourceDocument` objects.

```bash
upgrade-copilot search docs.json "sqlalchemy session changes"
upgrade-copilot answer docs.json "How do I keep using Pydantic v1 while migrating to v2?"
```

To index the built-in official migration sources or a custom source manifest:

```bash
upgrade-copilot build-index --sources data/official_sources.json --index-path data/index.json
upgrade-copilot search-index --index-path data/index.json "numpy NPY201"
upgrade-copilot answer-index --index-path data/index.json "What does FastAPI recommend before moving to Pydantic v2?"
```

## HTTP And HTML

The built-in server uses only the Python standard library and exposes both JSON endpoints and an HTML page.

- `GET /`: browser UI for building the index, searching, and answering
- `GET /health`: server and index status
- `GET /ready`: readiness status; returns `503` until an index is loaded or readable
- `GET /repo/dependencies`: detected repository libraries used to bias retrieval
- `GET /repo/scan`: scan the server-mounted repository and return upgrade guidance
- `GET /sources`: built-in official source manifest
- `POST /index/build`: fetch official docs, build the local index, and persist it
- `POST /search`: search the loaded index
- `POST /answer`: answer a question from the loaded index
- `POST /repo/scan`: scan posted dependency file contents and return upgrade guidance

Search and answer requests can include `libraries` to hard-filter results and `auto_detect_repo` to bias retrieval toward libraries detected from files like `pyproject.toml` and `requirements.txt`.

Example:

```bash
curl -X POST http://127.0.0.1:8000/index/build \
  -H "Content-Type: application/json" \
  -d '{"sources_path":"data/official_sources.json","refresh":false}'

curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"numpy NPY201","k":5}'

curl -X POST http://127.0.0.1:8000/repo/scan \
  -H "Content-Type: application/json" \
  -d '{"files":{"pyproject.toml":"[project]\ndependencies = [\"pydantic>=2\", \"numpy>=2\"]"},"k":4}'
```

## Repository Scanner

The repo scanner detects supported dependency families from dependency files, then asks Upgrade Copilot for official-doc-backed migration guidance for each detected library. The response includes matched files, matched package names, summaries, citations, and top retrieved official sources.

This supports two modes:

- Server-side: `GET /repo/scan` scans the repository mounted at `UPGRADE_COPILOT_REPO_ROOT`.
- Hosted/extension: `POST /repo/scan` accepts dependency file contents from a client, so a hosted backend does not need direct filesystem access to a developer workstation.

CLI usage:

```bash
upgrade-copilot scan-repo --repo-root . --index-path data/index.json
```

## Docker

Build and run the image locally:

```bash
docker build -t upgrade-copilot:local .
docker run --rm -p 8000:8000 upgrade-copilot:local
```

The image runs as a non-root user, includes the checked-in official source manifest, cached docs, and `data/index.json`, and exposes the service on port `8000`. On Render, the service also honors Render's `PORT` environment variable.

Runtime configuration is available through environment variables:

- `UPGRADE_COPILOT_HOST`
- `UPGRADE_COPILOT_PORT`
- `UPGRADE_COPILOT_INDEX_PATH`
- `UPGRADE_COPILOT_CACHE_DIR`
- `UPGRADE_COPILOT_REPO_ROOT`

## Kubernetes

Demo manifests live in `deploy/kubernetes`.

```bash
kubectl apply -k deploy/kubernetes
kubectl -n upgrade-copilot port-forward svc/upgrade-copilot 8000:8000
```

Before publishing, set `spec.template.spec.containers[0].image` in `deploy/kubernetes/deployment.yaml` to your registry image, for example `ghcr.io/<owner>/upgrade-copilot:<tag>`.

## VS Code Extension

The VS Code wrapper lives in `extension/vscode`. It contributes an Upgrade Copilot activity bar view and commands for checking the service, building the index, searching, and answering from selected code.

Development flow:

```bash
code extension/vscode
```

Press `F5` from that VS Code window to launch an Extension Development Host. The extension setting `upgradeCopilot.serviceUrl` defaults to `https://upgrade-copilot.onrender.com`.

For hosted usage, deploy the Docker image somewhere reachable over HTTPS, then set `upgradeCopilot.serviceUrl` to that base URL. This repo's extension is currently configured for `https://upgrade-copilot.onrender.com`. The extension can scan workspace dependency files locally and POST only those file contents to `/repo/scan`; the hosted service returns migration guidance without needing access to the full repository.

Typical hosting path:

1. Build and push the image to a registry such as GitHub Container Registry.
2. Deploy it to Kubernetes, Fly.io, Render, Railway, Azure Container Apps, or another HTTPS-capable container host.
3. Put TLS and auth in front of it if it will be reachable outside your private network.
4. Set the VS Code extension setting `upgradeCopilot.serviceUrl` to the hosted URL.
5. Package/publish the VS Code extension after setting its `publisher` metadata.
