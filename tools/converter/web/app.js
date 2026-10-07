// User interface only. Every conversion rule lives in project.py.

const PY_MODULES = ["project.py", "render.py"];
const SCHEMA_URL = "molecule-config.schema.json";
const PRESETS_URL = "presets.json";
const STARTER_URL = "starter.json";
const BUILD_URL = "build.json";

const el = (id) => document.getElementById(id);
let convert = null;
let schemaText = null;
let selected = null;
let timer = null;
let version = "";
let sourceView = null;
let fileView = null;

function getSource() {
  return sourceView.state.doc.toString();
}

function setDoc(view, text) {
  view.dispatch({
    changes: { from: 0, to: view.state.doc.length, insert: text },
    selection: { anchor: 0 },
    scrollIntoView: true,
  });
}

async function makeEditors() {
  const { basicSetup, minimalSetup, EditorView } = await import("codemirror");
  const { EditorState } = await import("@codemirror/state");
  const { keymap, lineNumbers } = await import("@codemirror/view");
  const { indentWithTab } = await import("@codemirror/commands");
  const { yaml } = await import("@codemirror/lang-yaml");
  sourceView = new EditorView({
    parent: el("source"),
    extensions: [
      basicSetup,
      keymap.of([indentWithTab]),
      yaml(),
      EditorView.contentAttributes.of({ "aria-label": "Single-config molecule.yml" }),
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          schedule();
        }
      }),
    ],
  });
  fileView = new EditorView({
    parent: el("file"),
    extensions: [
      minimalSetup,
      lineNumbers(),
      yaml(),
      EditorState.readOnly.of(true),
      EditorView.editable.of(false),
      EditorView.contentAttributes.of({ "aria-label": "Projected file" }),
    ],
  });
  window.converter = {
    source: getSource,
    file: () => fileView.state.doc.toString(),
  };
}

async function fetchText(url, options) {
  const res = await fetch(version ? `${url}?v=${version}` : url, options);
  if (!res.ok) {
    throw new Error(`could not load ${url} (HTTP ${res.status}). Reload the page to retry.`);
  }
  return res.text();
}

function setStatus(text) {
  el("status").textContent = text;
}

async function encodeShare(text) {
  const stream = new Blob([text]).stream().pipeThrough(new CompressionStream("deflate-raw"));
  const bytes = new Uint8Array(await new Response(stream).arrayBuffer());
  let bin = "";
  bytes.forEach((b) => { bin += String.fromCharCode(b); });
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function decodeShare(code) {
  const b64 = code.replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64 + "===".slice((b64.length + 3) % 4));
  const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
  return new Response(stream).text();
}

function renderResult(result) {
  const tree = el("tree");
  tree.replaceChildren();
  const paths = result.files.map((f) => f.path);
  if (!paths.includes(selected)) {
    selected = paths[0] || null;
  }
  for (const file of result.files) {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = file.path;
    button.className = file.path === selected ? "file selected" : "file";
    button.addEventListener("click", () => {
      selected = file.path;
      renderResult(result);
    });
    li.appendChild(button);
    tree.appendChild(li);
  }
  const current = result.files.find((f) => f.path === selected);
  const text = current ? current.text : "";
  if (fileView.state.doc.toString() !== text) {
    setDoc(fileView, text);
  }

  const notices = el("notices");
  notices.replaceChildren();
  for (const n of result.notices) {
    const li = document.createElement("li");
    li.className = "notice " + n.kind;
    const where = [n.node, n.key].filter((x) => x).join(" / ");
    li.textContent = `${n.kind}${where ? " (" + where + ")" : ""}: ${n.message}`;
    notices.appendChild(li);
  }
  if (!result.notices.length) {
    const li = document.createElement("li");
    li.textContent = "None.";
    notices.appendChild(li);
  }
}

function run() {
  if (!convert) {
    return;
  }
  const result = JSON.parse(convert(getSource(), schemaText));
  renderResult(result);
}

function schedule() {
  clearTimeout(timer);
  timer = setTimeout(run, 250);
}

async function loadPresets() {
  const presets = JSON.parse(await fetchText(PRESETS_URL));
  const select = el("preset");
  for (const name of Object.keys(presets)) {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    select.appendChild(option);
  }
  select.addEventListener("change", async () => {
    if (!select.value) {
      return;
    }
    setDoc(sourceView, presets[select.value]);
    run();
  });
}

async function main() {
  await makeEditors();
  el("share").addEventListener("click", async () => {
    const url = new URL(window.location.href);
    url.hash = "src=" + (await encodeShare(getSource()));
    window.history.replaceState(null, "", url);
    await navigator.clipboard.writeText(url.toString());
    setStatus("Share link copied.");
  });

  version = JSON.parse(await fetchText(BUILD_URL, { cache: "no-store" })).version;
  schemaText = await fetchText(SCHEMA_URL);
  el("spec-version").textContent = JSON.parse(schemaText)["x-spec"].version;
  const starter = JSON.parse(await fetchText(STARTER_URL)).text;
  el("starter").addEventListener("click", () => {
    el("preset").value = "";
    setDoc(sourceView, starter);
    run();
  });
  if (window.location.hash.startsWith("#src=")) {
    setDoc(sourceView, await decodeShare(window.location.hash.slice(5)));
  } else {
    setDoc(sourceView, starter);
  }
  await loadPresets();

  const pyodide = await loadPyodide();
  await pyodide.loadPackage("pyyaml");
  for (const name of PY_MODULES) {
    pyodide.FS.writeFile(name, await fetchText(name));
  }
  pyodide.runPython("import sys\nsys.path.insert(0, '.')");
  convert = pyodide.pyimport("render").convert_json;
  setStatus(`Ready. Python ${pyodide.runPython("import sys; sys.version.split()[0]")} via Pyodide.`);
  run();
}

main().catch((err) => {
  setStatus("Failed to start: " + err.message);
});
