// User interface only. Every conversion rule lives in project.py.

const PY_MODULES = ["project.py", "render.py"];
const SCHEMA_URL = "molecule-config.schema.json";
const PRESETS_URL = "presets.json";
const STARTER_URL = "starter.json";
const BUILD_URL = "build.json";
const DEFAULT_SCENARIOS_DIR = "extensions/molecule";
const SOURCE_NAME = "molecule.yml";
const SVG_NS = "http://www.w3.org/2000/svg";

const el = (id) => document.getElementById(id);
let convert = null;
let schemaText = null;
let selected = null;
let sourceSelected = SOURCE_NAME;
let available = new Map();
let workersAuto = true;
let workers = 1;
let readyStatus = "";
let lastResult = null;
let timer = null;
let version = "";
let sourceView = null;
let sourceFileView = null;
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
  const readOnlyView = (parent, label) => new EditorView({
    parent,
    extensions: [
      minimalSetup,
      lineNumbers(),
      yaml(),
      EditorState.readOnly.of(true),
      EditorView.editable.of(false),
      EditorView.contentAttributes.of({ "aria-label": label }),
    ],
  });
  sourceView = new EditorView({
    parent: el("source"),
    extensions: [
      basicSetup,
      keymap.of([indentWithTab]),
      yaml(),
      EditorView.contentAttributes.of({ "aria-label": SOURCE_NAME }),
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          schedule();
        }
      }),
    ],
  });
  sourceFileView = readOnlyView(el("source-file"), "Referenced playbook");
  fileView = readOnlyView(el("file"), "Projected file");
  window.converter = {
    source: getSource,
    sourceFile: () => sourceFileView.state.doc.toString(),
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

function commonDir(paths) {
  if (!paths.length) {
    return "";
  }
  const parts = paths.map((p) => p.split("/"));
  const limit = Math.min(...parts.map((p) => p.length)) - 2;
  let count = 0;
  while (count < limit && parts.every((p) => p[count] === parts[0][count])) {
    count += 1;
  }
  return count ? parts[0].slice(0, count).join("/") + "/" : "";
}

function playbookGroups(paths) {
  const groups = [];
  for (const path of paths) {
    const cut = path.lastIndexOf("/");
    const heading = cut < 0 ? "" : path.slice(0, cut + 1);
    let group = groups.find((g) => g.heading === heading);
    if (!group) {
      group = { heading, entries: [] };
      groups.push(group);
    }
    group.entries.push({ path, label: path.slice(heading.length), kind: "playbook", available: available.has(path) });
  }
  return groups;
}

function renderFiles(list, groups, current, onSelect) {
  list.replaceChildren();
  for (const group of groups) {
    if (group.heading) {
      const li = document.createElement("li");
      li.className = "dir";
      li.textContent = group.heading;
      list.appendChild(li);
    }
    for (const entry of group.entries) {
      const li = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      const label = document.createElement("span");
      label.className = "label";
      entry.label.split("/").forEach((part, index, parts) => {
        label.append(index < parts.length - 1 ? part + "/" : part);
        if (index < parts.length - 1) {
          label.appendChild(document.createElement("wbr"));
        }
      });
      button.appendChild(label);
      button.dataset.path = entry.path;
      button.dataset.kind = entry.kind;
      const classes = ["file"];
      if (!group.heading) {
        classes.push("top");
      }
      if (!entry.available) {
        classes.push("missing");
        button.dataset.available = "false";
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = "not available";
        button.appendChild(tag);
        button.title = entry.path + " is not part of this input";
      } else {
        button.title = "View " + entry.path;
      }
      if (entry.path === current) {
        classes.push("selected");
      }
      button.className = classes.join(" ");
      button.setAttribute("aria-pressed", entry.path === current ? "true" : "false");
      button.addEventListener("click", () => onSelect(entry.path));
      li.appendChild(button);
      list.appendChild(li);
    }
  }
}

function showMissing(note, path) {
  note.textContent = `${path} is not part of this input.`;
  note.hidden = false;
}

function renderSource(result) {
  const paths = result.playbooks;
  if (sourceSelected !== SOURCE_NAME && !paths.includes(sourceSelected)) {
    sourceSelected = SOURCE_NAME;
  }
  const groups = [{ heading: "", entries: [{ path: SOURCE_NAME, label: SOURCE_NAME, kind: "source", available: true }] }];
  renderFiles(el("source-files"), groups.concat(playbookGroups(paths)), sourceSelected, (path) => {
    sourceSelected = path;
    renderSource(lastResult);
  });
  el("source-path").textContent = sourceSelected;
  const editing = sourceSelected === SOURCE_NAME;
  const present = !editing && available.has(sourceSelected);
  el("source").hidden = !editing;
  el("source-file").hidden = !present;
  el("source-missing").hidden = true;
  if (present) {
    if (sourceFileView.state.doc.toString() !== available.get(sourceSelected)) {
      setDoc(sourceFileView, available.get(sourceSelected));
    }
    sourceFileView.requestMeasure();
  } else if (!editing) {
    showMissing(el("source-missing"), sourceSelected);
  } else {
    sourceView.requestMeasure();
  }
}

function renderTree(result) {
  const projected = result.files.map((f) => f.path);
  const extra = result.playbooks.filter((p) => !projected.includes(p));
  const all = projected.concat(extra);
  if (!all.includes(selected)) {
    selected = all[0] || null;
  }
  const root = commonDir(projected);
  const groups = [{
    heading: root,
    entries: result.files.map((f) => ({ path: f.path, label: f.path.slice(root.length), kind: "projected", available: true })),
  }].concat(playbookGroups(extra));
  renderFiles(el("tree"), groups, selected, (path) => {
    selected = path;
    renderTree(lastResult);
  });
  el("file-path").textContent = selected || "";
  const current = result.files.find((f) => f.path === selected);
  let text = "";
  let missing = false;
  if (current) {
    text = current.text;
  } else if (selected && available.has(selected)) {
    text = available.get(selected);
  } else if (selected) {
    missing = true;
  }
  el("file").hidden = missing;
  el("file-missing").hidden = true;
  if (missing) {
    showMissing(el("file-missing"), selected);
  } else if (fileView.state.doc.toString() !== text) {
    setDoc(fileView, text);
  }
}

function svg(tag, attrs, text) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) {
    node.setAttribute(key, String(value));
  }
  if (text !== undefined) {
    node.textContent = text;
  }
  return node;
}

function renderOrder(order) {
  const box = el("order");
  box.replaceChildren();
  const input = el("workers");
  input.max = String(Math.max(1, order.scenarios.length));
  if (Number(input.value) !== order.workers) {
    input.value = order.workers;
  }
  input.setCustomValidity("");
  const items = order.scenarios.filter((s) => s.step);
  if (!items.length) {
    return;
  }
  const steps = Math.max(...items.map((s) => s.step));
  const longest = Math.max(...items.map((s) => s.name.length));
  const blockW = Math.max(88, Math.ceil(longest * 7.4) + 20);
  const blockH = 26;
  const gapX = 34;
  const gapY = 8;
  const top = 22;
  const pad = 4;
  const rows = new Array(steps + 1).fill(0);
  const place = {};
  for (const item of items) {
    const row = rows[item.step];
    rows[item.step] += 1;
    place[item.name] = {
      x: pad + (item.step - 1) * (blockW + gapX),
      y: top + row * (blockH + gapY),
    };
  }
  const height = top + Math.max(...rows) * (blockH + gapY) - gapY + pad;
  const width = pad * 2 + steps * blockW + (steps - 1) * gapX;
  const root = svg("svg", { width, height, viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": "Scenario start order" });
  for (let step = 1; step <= steps; step += 1) {
    root.appendChild(svg("text", { class: "step", x: pad + (step - 1) * (blockW + gapX) + blockW / 2, y: 14 }, `step ${step}`));
  }
  for (const item of items) {
    const from = item.parent && place[item.parent];
    if (!from) {
      continue;
    }
    const to = place[item.name];
    const x1 = from.x + blockW;
    const y1 = from.y + blockH / 2;
    const x2 = to.x;
    const y2 = to.y + blockH / 2;
    const bend = Math.max(12, (x2 - x1) / 2);
    root.appendChild(svg("path", {
      class: "edge",
      "data-from": item.parent,
      "data-to": item.name,
      d: `M${x1},${y1} C${x1 + bend},${y1} ${x2 - bend},${y2} ${x2},${y2}`,
    }));
  }
  for (const item of items) {
    const at = place[item.name];
    const group = svg("g", { class: "block", "data-name": item.name, "data-step": item.step, transform: `translate(${at.x},${at.y})` });
    group.appendChild(svg("rect", { width: blockW, height: blockH, rx: 5 }));
    group.appendChild(svg("text", { x: blockW / 2, y: blockH / 2 }, item.name));
    root.appendChild(group);
  }
  box.appendChild(root);
}

function workersValue() {
  if (workersAuto) {
    return undefined;
  }
  return workers;
}

function run() {
  if (!convert) {
    return;
  }
  let result;
  try {
    result = JSON.parse(convert(getSource(), schemaText, el("scenarios-dir").value, workersValue()));
  } catch (err) {
    setStatus("Conversion failed: " + err.message);
    return;
  }
  if (readyStatus && el("status").textContent.startsWith("Conversion failed")) {
    setStatus(readyStatus);
  }
  lastResult = result;
  renderSource(result);
  renderTree(result);
  renderOrder(result.order);

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

function schedule() {
  clearTimeout(timer);
  timer = setTimeout(run, 250);
}

function loadInput(text, scenariosDir, files) {
  el("scenarios-dir").value = scenariosDir;
  available = new Map(Object.entries(files));
  sourceSelected = SOURCE_NAME;
  workersAuto = true;
  setDoc(sourceView, text);
  run();
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
    const preset = presets[select.value];
    loadInput(preset.text, preset.scenarios_dir, preset.playbooks || {});
  });
}

async function main() {
  await makeEditors();
  el("share").addEventListener("click", async () => {
    const url = new URL(window.location.href);
    url.hash = "src=" + (await encodeShare(getSource()));
    if (el("scenarios-dir").value !== DEFAULT_SCENARIOS_DIR) {
      url.hash += "&dir=" + encodeURIComponent(el("scenarios-dir").value);
    }
    window.history.replaceState(null, "", url);
    await navigator.clipboard.writeText(url.toString());
    setStatus("Share link copied.");
  });
  el("workers").addEventListener("input", () => {
    const input = el("workers");
    const text = input.value.trim();
    const value = Number(text);
    if (!/^[0-9]+$/.test(text) || !Number.isSafeInteger(value) || value < 1) {
      input.setCustomValidity("Enter a whole number of at least 1.");
      return;
    }
    input.setCustomValidity("");
    workers = value;
    workersAuto = false;
    run();
  });

  version = JSON.parse(await fetchText(BUILD_URL, { cache: "no-store" })).version;
  schemaText = await fetchText(SCHEMA_URL);
  el("spec-version").textContent = JSON.parse(schemaText)["x-spec"].version;
  const starter = JSON.parse(await fetchText(STARTER_URL)).text;
  el("starter").addEventListener("click", () => {
    el("preset").value = "";
    loadInput(starter, DEFAULT_SCENARIOS_DIR, {});
  });
  el("scenarios-dir").addEventListener("change", run);
  if (window.location.hash.startsWith("#src=")) {
    const params = new URLSearchParams(window.location.hash.slice(1));
    const dirs = [...el("scenarios-dir").options].map((o) => o.value);
    if (dirs.includes(params.get("dir"))) {
      el("scenarios-dir").value = params.get("dir");
    }
    setDoc(sourceView, await decodeShare(params.get("src")));
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
  readyStatus = `Ready. Python ${pyodide.runPython("import sys; sys.version.split()[0]")} via Pyodide.`;
  setStatus(readyStatus);
  run();
}

main().catch((err) => {
  setStatus("Failed to start: " + err.message);
});
