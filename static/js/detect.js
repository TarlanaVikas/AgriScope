// AgriScope detection workbench. Vanilla ES module, no build step.
// All server-provided text is inserted with textContent (never innerHTML).

const root = document.querySelector("[data-detect]");
const cfg = {
  api: root.dataset.api,
  maxMb: Number(root.dataset.maxMb) || 10,
  ready: root.dataset.ready === "true",
};
const $ = (sel) => root.querySelector(sel);
const $$ = (sel) => [...root.querySelectorAll(sel)];

const ALLOWED = ["image/jpeg", "image/png", "image/webp"];
const TIMEOUT_MS = 180_000;
const COLORS = ["#b83a26", "#a6620a", "#b0456a", "#5c6b1e", "#7a5aa6", "#8a4b2a"];
const HEALTHY = "#2f7a2b";

const el = {
  dzWrap: $("[data-dz-wrap]"), dz: $("[data-dz]"), input: $("#file"), dzError: $("[data-dz-error]"),
  preview: $("[data-preview]"), previewImg: $("[data-preview-img]"), previewMeta: $("[data-preview-meta]"), remove: $("[data-remove]"),
  slider: $("#threshold"), sliderOut: $("#threshold-out"), analyze: $("[data-analyze]"),
  panel: $("[data-results]"), live: $("[data-live]"),
  elapsed: $("[data-elapsed]"), slow: $("[data-slow]"), cancel: $("[data-cancel]"),
  errTitle: $("[data-error-title]"), errMsg: $("[data-error-message]"), retry: $("[data-retry]"),
  kicker: $("[data-kicker]"), title: $("[data-title]"), summary: $("[data-summary]"), caution: $("[data-caution]"),
  stage: $("[data-stage]"), stageInner: $("[data-stage-inner]"), stageImg: $("[data-stage-img]"),
  legendNote: $("[data-legend-note]"), findings: $("[data-findings]"), runMeta: $("[data-run-meta]"),
  another: $("[data-another]"), download: $("[data-download]"),
};

let file = null;
let objectUrl = null;
let controller = null;
let timer = null;
let lastResult = null;

const pct = (v) => `${Math.round(v * 100)}%`;
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

function h(tag, attrs = {}, ...kids) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v == null) continue;
    if (k === "class") node.className = v;
    else if (k === "style") node.setAttribute("style", v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) node.append(kid instanceof Node ? kid : document.createTextNode(kid));
  return node;
}

/* ---------- view + step state ---------- */
function showView(name) {
  for (const v of $$("[data-view]")) v.hidden = v.dataset.view !== name;
  el.panel.setAttribute("aria-busy", name === "loading" ? "true" : "false");
}
function setStep(current) {
  for (const li of $$("[data-step]")) {
    const n = Number(li.dataset.step);
    li.classList.toggle("done", n < current);
    if (n === current) li.setAttribute("aria-current", "step"); else li.removeAttribute("aria-current");
    const dot = li.querySelector(".dot");
    dot.textContent = n < current ? "✓" : String(n);
  }
}
function announce(text) { el.live.textContent = ""; requestAnimationFrame(() => { el.live.textContent = text; }); }

/* ---------- file handling ---------- */
function fileError(msg) { el.dzError.textContent = msg; el.dzError.hidden = !msg; }

function validate(f) {
  if (!f) return "No file selected.";
  const okType = ALLOWED.includes(f.type) || /\.(jpe?g|png|webp)$/i.test(f.name);
  if (!okType) return "That file type isn't supported. Choose a JPG, PNG or WebP photo.";
  if (f.size === 0) return "That file is empty.";
  if (f.size > cfg.maxMb * 1024 * 1024) return `That photo is ${(f.size / 1048576).toFixed(1)} MB. The limit is ${cfg.maxMb} MB.`;
  return "";
}

function setFile(f) {
  const problem = validate(f);
  if (problem) { fileError(problem); return false; }
  fileError("");
  cancel(true);
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  file = f;
  objectUrl = URL.createObjectURL(f);
  el.previewImg.src = objectUrl;
  el.previewImg.onload = () => {
    el.previewMeta.textContent = `${f.name} · ${(f.size / 1024).toFixed(0)} KB · ${el.previewImg.naturalWidth}×${el.previewImg.naturalHeight} px`;
  };
  el.previewMeta.textContent = `${f.name} · ${(f.size / 1024).toFixed(0)} KB`;
  el.dzWrap.hidden = true;
  el.preview.hidden = false;
  el.analyze.disabled = false;
  lastResult = null;
  showView("empty");
  setStep(2);
  return true;
}

function clearFile() {
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  file = objectUrl = lastResult = null;
  el.input.value = "";
  el.previewImg.removeAttribute("src");
  el.preview.hidden = true;
  el.dzWrap.hidden = false;
  el.analyze.disabled = true;
  fileError("");
  showView("empty");
  setStep(1);
}

el.input.addEventListener("change", () => { if (el.input.files[0]) setFile(el.input.files[0]); el.input.value = ""; });
el.remove.addEventListener("click", () => { clearFile(); el.input.focus(); });

for (const ev of ["dragenter", "dragover"]) el.dz.addEventListener(ev, (e) => { e.preventDefault(); el.dz.classList.add("is-drag"); });
for (const ev of ["dragleave", "dragend"]) el.dz.addEventListener(ev, () => el.dz.classList.remove("is-drag"));
el.dz.addEventListener("drop", (e) => {
  e.preventDefault(); el.dz.classList.remove("is-drag");
  const files = [...(e.dataTransfer?.files || [])];
  if (files.length > 1) fileError("Please drop one photo at a time. Using the first one.");
  if (files[0]) { const ok = setFile(files[0]); if (ok && files.length > 1) fileError("Please drop one photo at a time. Using the first one."); }
});
// Dropping outside the zone must not navigate the browser away from the page.
for (const ev of ["dragover", "drop"]) window.addEventListener(ev, (e) => { if (!el.dz.contains(e.target)) e.preventDefault(); });
window.addEventListener("paste", (e) => {
  const item = [...(e.clipboardData?.files || [])].find((f) => f.type.startsWith("image/"));
  if (item) setFile(item);
});

for (const btn of $$("[data-sample]")) {
  btn.addEventListener("click", async () => {
    try {
      const res = await fetch(btn.dataset.sample);
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const name = btn.dataset.sample.split("/").pop();
      setFile(new File([blob], name, { type: blob.type || "image/jpeg" }));
    } catch { fileError("Couldn't load that sample photo."); }
  });
}

function paintSlider() {
  const v = Number(el.slider.value);
  el.sliderOut.textContent = `${v}%`;
  el.slider.style.setProperty("--fill", `${((v - 5) / 90) * 100}%`);
}
el.slider.addEventListener("input", paintSlider);
paintSlider();

/* ---------- analysis ---------- */
function startTimer() {
  const t0 = Date.now();
  el.elapsed.textContent = "0 s"; el.slow.hidden = true;
  timer = setInterval(() => {
    const s = Math.round((Date.now() - t0) / 1000);
    el.elapsed.textContent = `${s} s`;
    el.slow.hidden = s < 12;
  }, 1000);
}
function stopTimer() { clearInterval(timer); timer = null; }

function cancel(silent = false) {
  if (!controller) return;
  controller.abort("user");
  controller = null; stopTimer();
  if (!silent) { showView("empty"); setStep(2); el.analyze.disabled = !file; announce("Analysis cancelled."); }
}

function showError(title, message) {
  stopTimer(); controller = null;
  el.errTitle.textContent = title; el.errMsg.textContent = message;
  showView("error"); setStep(2);
  el.analyze.disabled = !file;
  announce(`${title}. ${message}`);
  el.errTitle.focus({ preventScroll: false });
}

async function analyze() {
  if (!file || controller) return;
  controller = new AbortController();
  const timeout = setTimeout(() => controller?.abort("timeout"), TIMEOUT_MS);
  const body = new FormData();
  body.append("file", file);
  body.append("confidence", String(Number(el.slider.value) / 100));
  el.analyze.disabled = true;
  showView("loading"); setStep(2); startTimer(); announce("Analyzing your photo.");
  const myController = controller;
  try {
    const res = await fetch(cfg.api, { method: "POST", body, signal: myController.signal });
    let data = null;
    try { data = await res.json(); } catch { /* non-JSON error page from a proxy */ }
    if (!res.ok || !data?.ok) {
      const message = data?.error?.message || `The server returned an unexpected response (HTTP ${res.status}).`;
      return showError(titleFor(res.status, data?.error?.code), message);
    }
    renderResults(data);
  } catch (err) {
    if (myController.signal.aborted && myController.signal.reason === "user") return;
    if (myController.signal.aborted) return showError("Analysis timed out", "That took too long and was stopped. Try a smaller photo.");
    showError("Can't reach AgriScope", "The request didn't reach the server. Check your connection and try again.");
  } finally {
    clearTimeout(timeout);
  }
}

function titleFor(status, code) {
  if (code === "model_unavailable") return "Detection is unavailable";
  if (status === 413 || code === "file_too_large") return "That photo is too large";
  if (status === 415 || code === "unsupported_type") return "Unsupported file";
  if (status === 422) return "That image couldn't be read";
  if (status >= 500) return "The analysis failed";
  return "Couldn't analyze that photo";
}

/* ---------- results ---------- */
function verdictFor(data) {
  const diseases = data.findings.filter((f) => !f.healthy);
  const healthy = data.findings.find((f) => f.healthy);
  if (!data.detections.length) {
    return { kicker: "No detections", title: `Nothing recognized at ${pct(data.threshold)}`,
      summary: "None of the classes this model knows were found in this photo at the current threshold.",
      caution: "That does not mean the plant is healthy. Try a closer, sharper, well-lit photo of the affected area, or lower the threshold." };
  }
  if (!diseases.length) {
    return { kicker: "Result", title: "Looks like a healthy leaf",
      summary: `${plural(healthy.count, "region", "regions")} matched the healthy-leaf class, with a top confidence of ${pct(healthy.top_confidence)}.`,
      caution: "A healthy reading isn't a guarantee: early or hidden problems may not show in one photo." };
  }
  const top = diseases[0];
  let summary = `${pct(top.top_confidence)} top confidence across ${plural(top.count, "region", "regions")}.`;
  if (diseases.length > 1) summary += ` ${plural(diseases.length - 1, "other class", "other classes")} also detected.`;
  if (healthy) summary += " Some regions also matched healthy leaf.";
  return { kicker: "Most likely finding", title: top.label, summary,
    caution: top.top_confidence < 0.5 ? "Confidence is below 50%, so treat this as a hint and check the plant in person." : "" };
}

function renderResults(data) {
  stopTimer(); controller = null; lastResult = data;
  el.analyze.disabled = !file;
  const v = verdictFor(data);
  el.kicker.textContent = v.kicker; el.title.textContent = v.title; el.summary.textContent = v.summary;
  el.caution.textContent = v.caution; el.caution.hidden = !v.caution;

  // colours per finding
  let ci = 0;
  const colorOf = new Map();
  for (const f of data.findings) colorOf.set(f.class_id, f.healthy ? HEALTHY : COLORS[ci++ % COLORS.length]);

  // image + boxes
  el.stageImg.src = objectUrl;
  const { width: W, height: H } = data.image;
  el.stageInner.style.setProperty("--ar", String(W / H));
  for (const old of el.stageInner.querySelectorAll(".box")) old.remove();
  el.stage.classList.remove("has-focus");
  const boxes = new Map();
  data.detections.forEach((d, i) => {
    const b = d.box;
    const box = h("div", {
      class: `box${b.y1 / H < 0.07 ? " tag-in" : ""}${b.x1 / W > 0.6 ? " tag-right" : ""}`, "aria-hidden": "true",
      style: `--c:${colorOf.get(d.class_id)};left:${(b.x1 / W) * 100}%;top:${(b.y1 / H) * 100}%;width:${((b.x2 - b.x1) / W) * 100}%;height:${((b.y2 - b.y1) / H) * 100}%`,
    }, h("span", { class: "tag" }, String(i + 1), h("span", { class: "lbl" }, ` ${d.label} ${pct(d.confidence)}`)));
    boxes.set(d.id, box);
    el.stageInner.append(box);
  });
  el.legendNote.hidden = !data.detections.length;

  function highlight(ids) {
    const on = new Set(ids || []);
    el.stage.classList.toggle("has-focus", on.size > 0);
    for (const [id, box] of boxes) box.classList.toggle("is-active", on.has(id));
  }

  // findings
  let armed = false; // ignore the toggle event fired by the initially-open item, so boxes start as plain numbers
  el.findings.replaceChildren();
  data.findings.forEach((f, idx) => {
    const c = colorOf.get(f.class_id);
    const g = f.guidance;
    const chips = h("div", { class: "regions", role: "group", "aria-label": `Regions for ${f.label}` });
    for (const id of f.detection_ids) {
      const d = data.detections[id];
      const chip = h("button", { type: "button", class: "chip", "aria-pressed": "false" }, `Box ${id + 1} · ${pct(d.confidence)}`);
      chip.addEventListener("click", () => {
        const on = chip.getAttribute("aria-pressed") !== "true";
        for (const other of el.findings.querySelectorAll(".chip")) { other.setAttribute("aria-pressed", "false"); other.classList.remove("is-on"); }
        chip.setAttribute("aria-pressed", String(on)); chip.classList.toggle("is-on", on);
        highlight(on ? [id] : []);
      });
      chips.append(chip);
    }
    const body = h("div", { class: "body" },
      g ? [h("p", { style: "margin-top:1rem" }, g.summary),
           h("h4", {}, "Signs to look for"), h("ul", {}, g.signs.map((s) => h("li", {}, s))),
           h("h4", {}, "General next steps"), h("ul", {}, g.actions.map((s) => h("li", {}, s))),
           h("p", { class: "src" }, "General reference notes, not produced by the model and not a diagnosis. Local conditions and regulations matter; ask a local agricultural adviser.")]
        : h("p", { style: "margin-top:1rem" }, "The model reported this class, but AgriScope has no reference notes for it."),
      h("h4", {}, "Regions on your photo"), chips);

    const det = h("details", { class: "finding", style: `--c:${c}`, ...(idx === 0 ? { open: true } : {}) },
      h("summary", {},
        h("span", { class: "swatch", "aria-hidden": "true" }),
        h("span", { class: "name" }, f.label),
        h("span", { class: "sub" }, `${f.group} · ${plural(f.count, "region", "regions")}`),
        h("span", { class: "conf" },
          h("span", { class: "track", "aria-hidden": "true" }, h("span", { class: "fill", style: `--w:${f.top_confidence * 100}%` })),
          h("b", {}, `${pct(f.top_confidence)} top`))),
      body);
    const sum = det.querySelector("summary");
    const on = () => highlight(f.detection_ids), off = () => { if (!el.findings.querySelector(".chip.is-on")) highlight([]); };
    sum.addEventListener("mouseenter", on); sum.addEventListener("mouseleave", off);
    sum.addEventListener("focus", on); sum.addEventListener("blur", off);
    det.addEventListener("toggle", () => { if (!armed) return; if (det.open) on(); else off(); });
    el.findings.append(det);
  });

  setTimeout(() => { armed = true; }, 50);
  const tookS = (data.inference_ms / 1000).toFixed(1);
  el.runMeta.textContent = `Analyzed in ${tookS} s · threshold ${pct(data.threshold)} · ${W}×${H} px · ${plural(data.detections.length, "detection", "detections")}`;
  showView("results"); setStep(3);
  announce(`Analysis complete. ${v.title}. ${v.summary}`);
  el.title.focus({ preventScroll: false });
  el.title.scrollIntoView({ block: "start", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
}

el.analyze.addEventListener("click", analyze);
el.retry.addEventListener("click", () => { showView("empty"); analyze(); });
el.cancel.addEventListener("click", () => cancel(false));
el.another.addEventListener("click", () => { clearFile(); document.getElementById("capture-h").scrollIntoView({ block: "start" }); el.input.focus(); });
el.download.addEventListener("click", () => {
  if (!lastResult) return;
  const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: "application/json" });
  const a = h("a", { href: URL.createObjectURL(blob), download: "agriscope-result.json" });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
});

showView("empty");
setStep(1);
