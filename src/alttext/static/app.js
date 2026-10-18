const fileInput = document.getElementById("files");
const drop = document.getElementById("drop");
const fileList = document.getElementById("file-list");
const contextInput = document.getElementById("context");
const go = document.getElementById("go");
const statusLine = document.getElementById("status");
const result = document.getElementById("result");
const resultTitle = document.getElementById("result-title");
const summary = document.getElementById("summary");
const cards = document.getElementById("cards");
const jsonButton = document.getElementById("json");
const csvButton = document.getElementById("csv");

const MAX_BYTES = 12 * 1024 * 1024;
const MAX_FILES = 20;
const state = { files: [], model: "", items: [] };

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

function setStatus(message, isError = false) {
  statusLine.textContent = message;
  statusLine.classList.toggle("is-error", isError);
}

function addFiles(files) {
  for (const file of files) {
    if (!file.type.startsWith("image/")) continue;
    if (file.size > MAX_BYTES) {
      setStatus(`${file.name} is larger than 12 MB and was skipped.`, true);
      continue;
    }
    if (state.files.length >= MAX_FILES) {
      setStatus(`Only ${MAX_FILES} images fit in one batch.`, true);
      break;
    }
    if (!state.files.some((item) => item.name === file.name && item.size === file.size)) {
      state.files.push(file);
    }
  }
  renderFileList();
}

function renderFileList() {
  fileList.innerHTML = state.files.map((file, index) => `<li class="file-item">
    <span class="file-name">${escapeHtml(file.name)}</span>
    <button class="remove" type="button" data-index="${index}">Remove</button>
  </li>`).join("");
  if (state.files.length) setStatus(`${state.files.length} image${state.files.length === 1 ? "" : "s"} ready.`);
}

fileInput.addEventListener("change", () => { addFiles(fileInput.files); fileInput.value = ""; });
fileList.addEventListener("click", (event) => {
  const button = event.target.closest(".remove");
  if (!button) return;
  state.files.splice(Number(button.dataset.index), 1);
  renderFileList();
});

["dragenter", "dragover"].forEach((name) => drop.addEventListener(name, (event) => {
  event.preventDefault(); drop.classList.add("is-over");
}));
["dragleave", "drop"].forEach((name) => drop.addEventListener(name, (event) => {
  event.preventDefault(); drop.classList.remove("is-over");
}));
drop.addEventListener("drop", (event) => addFiles(event.dataTransfer.files));

document.addEventListener("paste", (event) => {
  const files = [];
  for (const item of event.clipboardData ? event.clipboardData.items : []) {
    if (item.type.startsWith("image/")) {
      const file = item.getAsFile();
      if (file) files.push(file);
    }
  }
  if (files.length) { addFiles(files); setStatus("Pasted image added."); }
});

function card(item, index) {
  const suggestion = item.suggestion;
  const decorative = Boolean(suggestion.decorative);
  return `<article class="card" data-index="${index}">
    <img class="thumb" src="${item.preview}" alt="">
    <div>
      <h3>${escapeHtml(item.name)}</h3>
      <p class="conf">${Math.round((Number(suggestion.confidence) || 0) * 100)}% confidence</p>
      <div class="field">
        <label for="alt-${index}">Alt text</label>
        <textarea id="alt-${index}" data-field="alt" ${decorative ? "disabled" : ""}>${escapeHtml(suggestion.alt)}</textarea>
      </div>
      <label class="check"><input type="checkbox" data-field="decorative" ${decorative ? "checked" : ""}> Decorative image</label>
      ${suggestion.text_in_image ? `<p class="text-note"><strong>Text in image:</strong> ${escapeHtml(suggestion.text_in_image)}</p>` : ""}
      <div class="card-actions">
        <button class="copy" type="button" data-index="${index}">Copy alt text</button>
      </div>
    </div>
  </article>`;
}

function render(data) {
  state.model = data.model;
  state.items = data.items.map((item, index) => ({
    ...item,
    preview: URL.createObjectURL(state.files[index]),
  }));
  result.hidden = false;
  summary.textContent = `${data.items.length} suggestion${data.items.length === 1 ? "" : "s"} · ${data.model}`;
  cards.innerHTML = state.items.map(card).join("");
  resultTitle.focus();
}

cards.addEventListener("change", (event) => {
  if (event.target.dataset.field !== "decorative") return;
  const card = event.target.closest(".card");
  const textarea = card.querySelector("textarea");
  textarea.disabled = event.target.checked;
  if (event.target.checked) textarea.value = "";
});

cards.addEventListener("click", async (event) => {
  const button = event.target.closest(".copy");
  if (!button) return;
  const card = button.closest(".card");
  const textarea = card.querySelector("textarea");
  const text = textarea.value.trim();
  try {
    await navigator.clipboard.writeText(text);
    button.textContent = "Copied";
    setTimeout(() => { button.textContent = "Copy alt text"; }, 1500);
  } catch {
    textarea.select();
  }
});

function rows() {
  return state.items.map((item, index) => {
    const card = cards.querySelector(`[data-index="${index}"]`);
    const textarea = card.querySelector("textarea");
    const decorative = card.querySelector('[data-field="decorative"]').checked;
    return {
      name: item.name,
      alt: decorative ? "" : textarea.value.trim(),
      decorative,
      text_in_image: item.suggestion.text_in_image || "",
      confidence: item.suggestion.confidence || 0,
      notes: item.suggestion.notes || "",
    };
  });
}

function download(blob, name) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = name;
  link.click();
  URL.revokeObjectURL(link.href);
}

jsonButton.addEventListener("click", () => {
  download(new Blob([JSON.stringify({ model: state.model, items: rows() }, null, 2)], { type: "application/json" }), "alttext.json");
});

csvButton.addEventListener("click", () => {
  const columns = ["name", "alt", "decorative", "text_in_image", "confidence", "notes"];
  const q = (value) => `"${String(value == null ? "" : value).replaceAll('"', '""')}"`;
  const lines = [columns.join(",")].concat(rows().map((row) => columns.map((column) => q(row[column])).join(",")));
  download(new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" }), "alttext.csv");
});

async function suggest() {
  if (!state.files.length) {
    setStatus("Add at least one image first.", true);
    return;
  }
  go.disabled = true;
  go.textContent = "Writing...";
  setStatus("Reading the images locally. The first run loads the model.");
  result.hidden = true;
  document.querySelector("main").setAttribute("aria-busy", "true");

  const body = new FormData();
  for (const file of state.files) body.append("files", file);
  body.append("context", contextInput.value.trim());

  try {
    const response = await fetch("/api/suggest", { method: "POST", body });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Server returned ${response.status}`);
    }
    render(await response.json());
    setStatus("Done. Review every suggestion before publishing.");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    go.disabled = false;
    go.textContent = "Write alt text";
    document.querySelector("main").setAttribute("aria-busy", "false");
  }
}

go.addEventListener("click", suggest);
document.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    event.preventDefault();
    suggest();
  }
});
