const DATA_URL = "data/papers.json";
const META_URL = "data/meta.json";
const FAVORITE_KEY = "uav-vln-wam-hub-favorites";
const TOPIC_ORDER = [
  "UAV VLN",
  "Navigation Foundation",
  "Traditional Navigation",
  "Instruction Following",
  "Vision-Language-Action",
  "World Action Model",
  "Embodied AI",
  "Multimodal Perception",
  "Dataset / Simulator",
  "Evaluation",
  "Survey",
  "Other",
];

let papers = [];
let meta = {};
let favorites = new Set(JSON.parse(localStorage.getItem(FAVORITE_KEY) || "[]"));

const els = {
  totalPapers: document.getElementById("totalPapers"),
  totalTopics: document.getElementById("totalTopics"),
  lastUpdated: document.getElementById("lastUpdated"),
  visibleCount: document.getElementById("visibleCount"),
  topicChips: document.getElementById("topicChips"),
  topicFilter: document.getElementById("topicFilter"),
  relevanceFilter: document.getElementById("relevanceFilter"),
  searchInput: document.getElementById("searchInput"),
  sortSelect: document.getElementById("sortSelect"),
  paperList: document.getElementById("paperList"),
  template: document.getElementById("paperTemplate"),
  exportCsvBtn: document.getElementById("exportCsvBtn"),
  exportBibBtn: document.getElementById("exportBibBtn"),
  themeToggle: document.getElementById("themeToggle"),
};

function saveFavorites() {
  localStorage.setItem(FAVORITE_KEY, JSON.stringify([...favorites]));
}

function allTopics() {
  const set = new Set();
  papers.forEach(p => (p.topics || p.tags || []).forEach(t => set.add(t)));
  return [...set].sort((a, b) => {
    const ia = TOPIC_ORDER.indexOf(a);
    const ib = TOPIC_ORDER.indexOf(b);
    if (ia !== -1 || ib !== -1) return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
    return a.localeCompare(b);
  });
}

function truncate(text, len = 520) {
  if (!text) return "";
  return text.length > len ? text.slice(0, len).trim() + "…" : text;
}

function dateOnly(date) {
  if (!date) return "Unknown date";
  return String(date).slice(0, 10);
}

function download(filename, content, type = "text/plain") {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function toCSV(rows) {
  const fields = ["title", "authors", "date", "venue", "topics", "uav_relevance", "abs_url", "pdf_url", "code_url"];
  const esc = v => `"${String(v ?? "").replaceAll('"', '""')}"`;
  const lines = [fields.join(",")];
  rows.forEach(p => {
    lines.push(fields.map(f => {
      if (f === "authors") return esc((p.authors || []).join("; "));
      if (f === "topics") return esc((p.topics || p.tags || []).join("; "));
      return esc(p[f]);
    }).join(","));
  });
  return lines.join("\n");
}

function renderStats() {
  const topics = allTopics();
  els.totalPapers.textContent = papers.length;
  els.totalTopics.textContent = topics.length;
  els.lastUpdated.textContent = meta.updated_at ? dateOnly(meta.updated_at) : "local";
  els.topicChips.innerHTML = "";
  topics.forEach(topic => {
    const count = papers.filter(p => (p.topics || p.tags || []).includes(topic)).length;
    const chip = document.createElement("button");
    chip.className = "chip";
    chip.type = "button";
    chip.textContent = `${topic} ${count}`;
    chip.addEventListener("click", () => {
      els.topicFilter.value = topic;
      renderPapers();
      document.getElementById("papers").scrollIntoView({ behavior: "smooth" });
    });
    els.topicChips.appendChild(chip);
  });

  els.topicFilter.innerHTML = `<option value="All">All Topics</option>`;
  topics.forEach(topic => {
    const option = document.createElement("option");
    option.value = topic;
    option.textContent = topic;
    els.topicFilter.appendChild(option);
  });
}

function getFilteredPapers() {
  const q = els.searchInput.value.trim().toLowerCase();
  const topic = els.topicFilter.value;
  const relevance = els.relevanceFilter.value;
  const sort = els.sortSelect.value;

  let rows = papers.filter(p => {
    const topics = p.topics || p.tags || [];
    const text = [
      p.title,
      (p.authors || []).join(" "),
      p.abstract,
      topics.join(" "),
      p.venue,
      p.uav_relevance,
    ].join(" ").toLowerCase();
    const matchQ = !q || text.includes(q);
    const matchTopic = topic === "All" || topics.includes(topic);
    const matchRel = relevance === "All" || p.uav_relevance === relevance;
    return matchQ && matchTopic && matchRel;
  });

  rows.sort((a, b) => {
    if (sort === "date-asc") return String(a.date || "").localeCompare(String(b.date || ""));
    if (sort === "title-asc") return String(a.title || "").localeCompare(String(b.title || ""));
    if (sort === "favorite") return Number(favorites.has(b.id)) - Number(favorites.has(a.id));
    return String(b.date || "").localeCompare(String(a.date || ""));
  });

  return rows;
}

function link(label, href) {
  if (!href) return null;
  const a = document.createElement("a");
  a.textContent = label;
  a.href = href;
  a.target = "_blank";
  a.rel = "noreferrer";
  return a;
}

function bibButton(paper) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = "BibTeX";
  btn.addEventListener("click", () => {
    navigator.clipboard.writeText(paper.bibtex || "");
    btn.textContent = "Copied";
    setTimeout(() => (btn.textContent = "BibTeX"), 1200);
  });
  return btn;
}

function renderPapers() {
  const rows = getFilteredPapers();
  els.visibleCount.textContent = rows.length;
  els.paperList.innerHTML = "";

  if (!rows.length) {
    els.paperList.innerHTML = `<p class="muted">No papers found. Try another keyword or filter.</p>`;
    return;
  }

  rows.forEach(p => {
    const node = els.template.content.cloneNode(true);
    node.querySelector(".paper-title").textContent = p.title || "Untitled";
    node.querySelector(".paper-meta").textContent = `${(p.authors || []).slice(0, 6).join(", ")}${(p.authors || []).length > 6 ? ", et al." : ""} · ${dateOnly(p.date || p.published)} · ${p.venue || "arXiv"} · UAV relevance: ${p.uav_relevance || "-"}`;
    node.querySelector(".paper-abstract").textContent = truncate(p.abstract || "No abstract available.");

    const fav = node.querySelector(".favorite-btn");
    fav.textContent = favorites.has(p.id) ? "★" : "☆";
    fav.classList.toggle("active", favorites.has(p.id));
    fav.addEventListener("click", () => {
      if (favorites.has(p.id)) favorites.delete(p.id); else favorites.add(p.id);
      saveFavorites();
      renderPapers();
    });

    const tagRow = node.querySelector(".tag-row");
    (p.topics || p.tags || []).forEach(t => {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = t;
      tagRow.appendChild(tag);
    });

    const links = node.querySelector(".paper-links");
    [
      link("arXiv", p.abs_url),
      link("PDF", p.pdf_url),
      link("Code", p.code_url),
      link("Project", p.project_url),
    ].filter(Boolean).forEach(x => links.appendChild(x));
    links.appendChild(bibButton(p));

    els.paperList.appendChild(node);
  });
}

async function loadData() {
  const [paperRes, metaRes] = await Promise.all([
    fetch(DATA_URL, { cache: "no-store" }),
    fetch(META_URL, { cache: "no-store" }).catch(() => null),
  ]);
  papers = await paperRes.json();
  meta = metaRes && metaRes.ok ? await metaRes.json() : {};
  renderStats();
  renderPapers();
}

function initTheme() {
  const current = localStorage.getItem("uav-vln-wam-theme") || "light";
  document.documentElement.dataset.theme = current;
  els.themeToggle.textContent = current === "dark" ? "Light" : "Dark";
  els.themeToggle.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("uav-vln-wam-theme", next);
    els.themeToggle.textContent = next === "dark" ? "Light" : "Dark";
  });
}

els.searchInput.addEventListener("input", renderPapers);
els.topicFilter.addEventListener("change", renderPapers);
els.relevanceFilter.addEventListener("change", renderPapers);
els.sortSelect.addEventListener("change", renderPapers);
els.exportCsvBtn.addEventListener("click", () => download("uav-vln-wam-papers.csv", toCSV(getFilteredPapers()), "text/csv"));
els.exportBibBtn.addEventListener("click", () => download("uav-vln-wam-papers.bib", getFilteredPapers().map(p => p.bibtex || "").join("\n\n"), "text/plain"));

initTheme();
loadData().catch(err => {
  console.error(err);
  els.paperList.innerHTML = `<p class="muted">Failed to load data/papers.json. Run with a local server, e.g. python -m http.server 8000.</p>`;
});
