const vscode = require("vscode");

const DEFAULT_SERVICE_URL = "https://upgrade-copilot.onrender.com";

function activate(context) {
  const client = new UpgradeCopilotClient();
  const provider = new UpgradeCopilotViewProvider(context.extensionUri, client);
  const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 90);

  status.command = "upgradeCopilot.health";
  status.text = "$(sync) Upgrade Copilot";
  status.tooltip = "Check Upgrade Copilot service status";
  status.show();

  context.subscriptions.push(
    status,
    vscode.window.registerWebviewViewProvider("upgradeCopilot.panel", provider),
    vscode.commands.registerCommand("upgradeCopilot.open", async () => {
      await vscode.commands.executeCommand("workbench.view.explorer");
    }),
    vscode.commands.registerCommand("upgradeCopilot.health", async () => {
      await withProgress("Checking Upgrade Copilot", async () => {
        const health = await client.health();
        const state = health.index_loaded ? "ready" : "running without an index";
        vscode.window.showInformationMessage(`Upgrade Copilot is ${state}. Chunks: ${health.chunk_count}.`);
      });
    }),
    vscode.commands.registerCommand("upgradeCopilot.buildIndex", async () => {
      await withProgress("Building Upgrade Copilot index", async () => {
        const result = await client.post("/index/build", { refresh: false });
        vscode.window.showInformationMessage(`Upgrade Copilot indexed ${result.indexed_chunks} chunks.`);
        provider.postState({ type: "result", action: "build", payload: result });
      });
    }),
    vscode.commands.registerCommand("upgradeCopilot.scanWorkspace", async () => {
      await withProgress("Scanning workspace dependencies", async () => {
        const files = await collectDependencyFiles();
        const result = await client.post("/repo/scan", { files, k: 4 });
        const doc = await vscode.workspace.openTextDocument({
          language: "markdown",
          content: formatScan(result),
        });
        await vscode.window.showTextDocument(doc, { preview: true });
        provider.postState({ type: "result", action: "scan", payload: result });
      });
    }),
    vscode.commands.registerCommand("upgradeCopilot.askSelection", async () => {
      const editor = vscode.window.activeTextEditor;
      const selected = editor ? editor.document.getText(editor.selection).trim() : "";
      const fallback = "What should I check before upgrading this dependency?";
      const question = await vscode.window.showInputBox({
        title: "Ask Upgrade Copilot",
        prompt: "Question to answer from official migration docs",
        value: selected ? `How should I migrate this code?\n\n${selected}` : fallback,
      });
      if (!question) {
        return;
      }
      await withProgress("Asking Upgrade Copilot", async () => {
        const answer = await client.post("/answer", { question, k: 5, auto_detect_repo: true });
        const doc = await vscode.workspace.openTextDocument({
          language: "markdown",
          content: formatAnswer(answer),
        });
        await vscode.window.showTextDocument(doc, { preview: true });
      });
    })
  );
}

function deactivate() {}

class UpgradeCopilotClient {
  baseUrl() {
    return vscode.workspace.getConfiguration("upgradeCopilot").get("serviceUrl", DEFAULT_SERVICE_URL).replace(/\/+$/, "");
  }

  async setBaseUrl(value) {
    await vscode.workspace.getConfiguration("upgradeCopilot").update("serviceUrl", value.replace(/\/+$/, ""), vscode.ConfigurationTarget.Global);
  }

  async health() {
    return this.get("/health");
  }

  async get(path) {
    return requestJson(`${this.baseUrl()}${path}`, { method: "GET" });
  }

  async post(path, payload) {
    return requestJson(`${this.baseUrl()}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }
}

class UpgradeCopilotViewProvider {
  constructor(extensionUri, client) {
    this.extensionUri = extensionUri;
    this.client = client;
    this.view = undefined;
  }

  resolveWebviewView(webviewView) {
    this.view = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = this.html(webviewView.webview);
    webviewView.webview.onDidReceiveMessage(async (message) => {
      try {
        if (message.type === "setUrl") {
          await this.client.setBaseUrl(message.url || DEFAULT_SERVICE_URL);
          this.postState({ type: "result", action: "config", payload: { serviceUrl: this.client.baseUrl() } });
          return;
        }
        if (message.type === "health") {
          this.postState({ type: "result", action: "health", payload: await this.client.health() });
          return;
        }
        if (message.type === "build") {
          this.postState({ type: "result", action: "build", payload: await this.client.post("/index/build", { refresh: Boolean(message.refresh) }) });
          return;
        }
        if (message.type === "scan") {
          const files = await collectDependencyFiles();
          this.postState({ type: "result", action: "scan", payload: await this.client.post("/repo/scan", { files, k: 4 }) });
          return;
        }
        if (message.type === "search") {
          this.postState({
            type: "result",
            action: "search",
            payload: await this.client.post("/search", {
              query: message.query,
              k: 5,
              libraries: parseLibraries(message.libraries),
              auto_detect_repo: true,
            }),
          });
          return;
        }
        if (message.type === "answer") {
          this.postState({
            type: "result",
            action: "answer",
            payload: await this.client.post("/answer", {
              question: message.question,
              k: 5,
              libraries: parseLibraries(message.libraries),
              auto_detect_repo: true,
            }),
          });
        }
      } catch (error) {
        this.postState({ type: "error", message: error.message });
      }
    });
  }

  postState(payload) {
    if (this.view) {
      this.view.webview.postMessage(payload);
    }
  }

  html(webview) {
    const nonce = getNonce();
    const serviceUrl = escapeHtml(this.client.baseUrl());
    return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
  <style>
    body { color: var(--vscode-foreground); font-family: var(--vscode-font-family); padding: 12px; }
    label { display: block; margin: 12px 0 4px; color: var(--vscode-descriptionForeground); }
    input, textarea { width: 100%; box-sizing: border-box; color: var(--vscode-input-foreground); background: var(--vscode-input-background); border: 1px solid var(--vscode-input-border); padding: 7px; }
    textarea { min-height: 92px; resize: vertical; }
    button { margin-top: 8px; margin-right: 6px; color: var(--vscode-button-foreground); background: var(--vscode-button-background); border: 0; padding: 7px 10px; cursor: pointer; }
    button.secondary { color: var(--vscode-button-secondaryForeground); background: var(--vscode-button-secondaryBackground); }
    pre { white-space: pre-wrap; word-break: break-word; background: var(--vscode-textCodeBlock-background); padding: 10px; min-height: 120px; }
    .row { display: flex; gap: 6px; align-items: center; }
    .row input { flex: 1; }
  </style>
</head>
<body>
  <label for="serviceUrl">Service URL</label>
  <div class="row">
    <input id="serviceUrl" value="${serviceUrl}">
    <button id="saveUrl">Save</button>
  </div>
  <button id="health">Check</button>
  <button id="build" class="secondary">Build Index</button>
  <button id="scan" class="secondary">Scan Workspace</button>

  <label for="libraries">Library filter</label>
  <input id="libraries" placeholder="fastapi,pydantic">

  <label for="query">Search</label>
  <textarea id="query">sqlalchemy safest path 1.4 to 2.0</textarea>
  <button id="search">Search</button>

  <label for="question">Answer</label>
  <textarea id="question">How do I keep using Pydantic v1 while migrating to v2?</textarea>
  <button id="answer">Answer</button>

  <pre id="output">Ready.</pre>

  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    const output = document.getElementById('output');
    const post = (type, body = {}) => vscode.postMessage({ type, ...body });
    document.getElementById('saveUrl').addEventListener('click', () => post('setUrl', { url: document.getElementById('serviceUrl').value }));
    document.getElementById('health').addEventListener('click', () => post('health'));
    document.getElementById('build').addEventListener('click', () => post('build', { refresh: false }));
    document.getElementById('scan').addEventListener('click', () => post('scan'));
    document.getElementById('search').addEventListener('click', () => post('search', { query: document.getElementById('query').value, libraries: document.getElementById('libraries').value }));
    document.getElementById('answer').addEventListener('click', () => post('answer', { question: document.getElementById('question').value, libraries: document.getElementById('libraries').value }));
    window.addEventListener('message', event => {
      const message = event.data;
      output.textContent = message.type === 'error' ? message.message : JSON.stringify(message.payload, null, 2);
    });
  </script>
</body>
</html>`;
  }
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const text = await response.text();
  let payload;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch (error) {
    throw new Error(`Invalid JSON from ${url}: ${text.slice(0, 200)}`);
  }
  if (!response.ok) {
    throw new Error(payload.error || `${response.status} ${response.statusText}`);
  }
  return payload;
}

function parseLibraries(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
}

async function collectDependencyFiles() {
  const names = [
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements.in",
    "setup.cfg",
    "setup.py",
    "Pipfile",
    "poetry.lock",
    "uv.lock",
  ];
  const files = {};
  for (const name of names) {
    const uris = await vscode.workspace.findFiles(`**/${name}`, "**/{.git,node_modules,.venv,dist,build}/**", 20);
    for (const uri of uris) {
      const bytes = await vscode.workspace.fs.readFile(uri);
      const relative = vscode.workspace.asRelativePath(uri, false);
      files[relative] = Buffer.from(bytes).toString("utf8").slice(0, 250000);
    }
  }
  return files;
}

async function withProgress(title, task) {
  return vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title, cancellable: false }, task);
}

function formatAnswer(answer) {
  const citations = (answer.citations || [])
    .map((citation) => `- [${citation.label}](${citation.url})`)
    .join("\n");
  return `# Upgrade Copilot Answer\n\n${answer.text}\n\n## Citations\n\n${citations || "No citations returned."}\n`;
}

function formatScan(scan) {
  const dependencies = (scan.dependencies || [])
    .map((dependency) => `- ${dependency.library}: ${dependency.matches.join(", ")} in ${dependency.files.join(", ")}`)
    .join("\n");
  const guidance = (scan.guidance || [])
    .map((item) => {
      const citations = (item.citations || []).map((citation) => `  - [${citation.label}](${citation.url})`).join("\n");
      return `## ${item.library}\n\n${item.summary}\n\n${citations || "No citations returned."}`;
    })
    .join("\n\n");
  return `# Upgrade Copilot Workspace Scan\n\n## Detected Dependencies\n\n${dependencies || "No supported dependencies detected."}\n\n${guidance}\n`;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function getNonce() {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let text = "";
  for (let index = 0; index < 32; index += 1) {
    text += alphabet.charAt(Math.floor(Math.random() * alphabet.length));
  }
  return text;
}

module.exports = { activate, deactivate };
