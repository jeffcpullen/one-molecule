// User interface only. Every conversion rule lives in project.py.
"use strict";

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
  el("file").textContent = current ? current.text : "";

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
  const result = JSON.parse(convert(el("source").value, schemaText));
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
    el("source").value = presets[select.value];
    run();
  });
}

async function main() {
  el("source").addEventListener("input", schedule);
  el("share").addEventListener("click", async () => {
    const url = new URL(window.location.href);
    url.hash = "src=" + (await encodeShare(el("source").value));
    window.history.replaceState(null, "", url);
    await navigator.clipboard.writeText(url.toString());
    setStatus("Share link copied.");
  });

  version = JSON.parse(await fetchText(BUILD_URL, { cache: "no-store" })).version;
  const starter = JSON.parse(await fetchText(STARTER_URL)).text;
  el("starter").addEventListener("click", () => {
    el("preset").value = "";
    el("source").value = starter;
    run();
  });
  if (window.location.hash.startsWith("#src=")) {
    el("source").value = await decodeShare(window.location.hash.slice(5));
  } else {
    el("source").value = starter;
  }
  await loadPresets();

  const pyodide = await loadPyodide();
  await pyodide.loadPackage("pyyaml");
  for (const name of PY_MODULES) {
    pyodide.FS.writeFile(name, await fetchText(name));
  }
  schemaText = await fetchText(SCHEMA_URL);
  pyodide.runPython("import sys\nsys.path.insert(0, '.')");
  convert = pyodide.pyimport("render").convert_json;
  setStatus(`Ready. Python ${pyodide.runPython("import sys; sys.version.split()[0]")} via Pyodide.`);
  run();
}

main().catch((err) => {
  setStatus("Failed to start: " + err.message);
});
