# Upgrade Copilot VS Code Extension

This extension is a thin VS Code wrapper around the running Upgrade Copilot HTTP service.

## Development

1. Start the service:

   ```bash
   upgrade-copilot serve --host 127.0.0.1 --port 8000
   ```

2. Open this folder in VS Code.
3. Press `F5` to launch an Extension Development Host.
4. Open the Upgrade Copilot activity bar view.

The extension setting `upgradeCopilot.serviceUrl` controls the service URL.

## Commands

- `Upgrade Copilot: Open`
- `Upgrade Copilot: Check Service`
- `Upgrade Copilot: Build Index`
- `Upgrade Copilot: Ask About Selection`
- `Upgrade Copilot: Scan Workspace`

`Scan Workspace` reads common dependency files from the open VS Code workspace and sends their contents to the configured Upgrade Copilot service via `POST /repo/scan`. This works with a hosted backend because the extension supplies the dependency context instead of requiring the backend to access local files.
