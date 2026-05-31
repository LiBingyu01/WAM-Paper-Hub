const DATA_URL = "data/papers.json";
const META_URL = "data/meta.json";
const FAVORITE_KEY = "uav-vln-awesome-hub-favorites";
const TOPIC_ORDER = [
  "Foundations",
  "Traditional UAV VLN",
  "UAV VLA",
  "UAV WAM",
  "Datasets & Simulators",
  "Evaluation",
];

let papers = [];
let meta = {};
let favorites = new Set(JSON.parse(localStorage.getItem(FAVORITE_KEY) || "[]"));

const els = {
  totalPapers: document.getElementById("totalPapers"),
  totalTopics: document.getElementById("totalTopics"),
  lastUpdated: document.getElementById("lastUpdated"),
  visibleCount: document.getElementById("visibleCount"),
  topicButtons: document.getElementById("topicButtons"),
  topicFilter: document.getElementById("topicFilter"),
  relevanceFilter: document.getElementById("relevanceFilter"),
  monthFilter: document.getElementById("monthFilter"),
  clearMonthBtn: document.getElementById("clearMonthBtn"),
  searchInput: document.getElementById("searchInput"),
  sortSelect: document.getElementById("sortSelect"),
  sectionContainer: document.getElementById("topicSections"),
  template: document.getElementById("paperTemplate"),
  exportCsvBtn: document.getElementById("exportCsvBtn"),
  exportBibBtn: document.getElementById("exportBibBtn"),
  themeToggle: document.getElementById("themeToggle"),
};

function saveFavorites() {
  localStorage.setItem(FAVORITE_KEY, JSON.stringify([...favorites]));
}

function dateOnly(date) {
  if (!date) return "Unknown date";
  return String(date).slice(0, 10);
}

function paperMonth(paper) {
  const d = dateOnly(paper.date || paper.published);
  return /^\d{4}-\d{2}-\d{2}/.test(d) ? d.slice(0, 7) : "Unknown";
}

function paperDay(paper) {
  const d = dateOnly(paper.date || paper.published);
  return /^\d{4}-\d{2}-\d{2}/.test(d) ? d.slice(8, 10) : "--";
}

function formatMonth(yyyyMm) {
  if (!/^\d{4}-\d{2}$/.test(yyyyMm)) return yyyyMm;
  const [year, month] = yyyyMm.split("-");
  return `${year}.${month}`;
}

function truncate(text, len = 420) {
  if (!text) return "";
  return text.length > len ? text.slice(0, len).trim() + "…" : text;
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
      if (f === "topics") return esc((p.topics || []).join("; "));
      return esc(p[f]);
    }).join(","));
  });
  return lines.join("\n");
}

function topicSlug(topic) {
  return topic.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function allTopics() {
  return TOPIC_ORDER.filter(topic => papers.some(p => (p.topics || []).includes(topic)));
}

function availableMonths(rows = papers) {
  const months = new Set();
  rows.forEach(p => {
    const m = paperMonth(p);
    if (m !== "Unknown") months.add(m);
  });
  return [...months].sort((a, b) => b.localeCompare(a));
}

function matchesFilters(paper) {
  const q = els.searchInput.value.trim().toLowerCase();
  const topic = els.topicFilter.value;
  const relevance = els.relevanceFilter.value;
  const month = els.monthFilter.value;
  const topics = paper.topics || [];
  const text = [
    paper.title,
    (paper.authors || []).join(" "),
    paper.abstract,
    topics.join(" "),
    paper.venue,
    paper.uav_relevance,
  ].join(" ").toLowerCase();

  const matchQ = !q || text.includes(q);
  const matchTopic = topic === "All" || topics.includes(topic);
  const matchRel = relevance === "All" || paper.uav_relevance === relevance;
  const matchMonth = !month || paperMonth(paper) === month;
  return matchQ && matchTopic && matchRel && matchMonth;
}

function sortByDay(rows, direction = "desc") {
  return rows.sort((a, b) => {
    const da = String(a.date || a.published || "").slice(0, 10);
    const db = String(b.date || b.published || "").slice(0, 10);
    return direction === "asc" ? da.localeCompare(db) : db.localeCompare(da);
  });
}

function sortRows(rows) {
  const sort = els.sortSelect.value;
  rows.sort((a, b) => {
    if (sort === "date-asc") return String(a.date || "").localeCompare(String(b.date || ""));
    if (sort === "title-asc") return String(a.title || "").localeCompare(String(b.title || ""));
    if (sort === "favorite") return Number(favorites.has(b.id)) - Number(favorites.has(a.id)) || String(b.date || "").localeCompare(String(a.date || ""));
    return String(b.date || "").localeCompare(String(a.date || ""));
  });
  return rows;
}

function getFilteredPapers() {
  return sortRows(papers.filter(matchesFilters));
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

function createPaperCard(p) {
  const node = els.template.content.cloneNode(true);
  node.querySelector(".paper-title").textContent = p.title || "Untitled";
  node.querySelector(".paper-meta").textContent = `${(p.authors || []).slice(0, 6).join(", ")}${(p.authors || []).length > 6 ? ", et al." : ""} · ${dateOnly(p.date || p.published)} · ${p.venue || "arXiv"} · UAV relevance: ${p.uav_relevance || "-"}`;
  node.querySelector(".paper-abstract").textContent = truncate(p.abstract || "No abstract available.");

  const dayBadge = node.querySelector(".paper-day");
  if (dayBadge) dayBadge.textContent = paperDay(p);

  const fav = node.querySelector(".favorite-btn");
  fav.textContent = favorites.has(p.id) ? "★" : "☆";
  fav.classList.toggle("active", favorites.has(p.id));
  fav.addEventListener("click", () => {
    if (favorites.has(p.id)) favorites.delete(p.id); else favorites.add(p.id);
    saveFavorites();
    renderSections();
  });

  const tagRow = node.querySelector(".tag-row");
  (p.topics || []).forEach(t => {
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

  return node;
}

function renderMonthPicker() {
  const months = availableMonths();
  if (!months.length) return;
  els.monthFilter.min = months[months.length - 1];
  els.monthFilter.max = months[0];
}

function createMonthIndex(topic, topicRows) {
  const monthCounts = new Map();
  topicRows.forEach(p => {
    const m = paperMonth(p);
    if (m !== "Unknown") monthCounts.set(m, (monthCounts.get(m) || 0) + 1);
  });

  const months = [...monthCounts.keys()].sort((a, b) => b.localeCompare(a));
  if (!months.length) return null;

  const wrap = document.createElement("div");
  wrap.className = "month-index";

  const label = document.createElement("div");
  label.className = "month-index-label";
  label.textContent = "Year · Month";
  wrap.appendChild(label);

  months.forEach(m => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "month-chip";
    if (els.monthFilter.value === m) btn.classList.add("active");
    btn.innerHTML = `<span>${formatMonth(m)}</span><small>${monthCounts.get(m)}</small>`;
    btn.addEventListener("click", () => {
      els.topicFilter.value = topic;
      els.monthFilter.value = m;
      renderSections();
      const target = document.getElementById(topicSlug(topic));
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    wrap.appendChild(btn);
  });

  return wrap;
}

function groupByMonth(rows) {
  const groups = new Map();
  rows.forEach(p => {
    const m = paperMonth(p);
    if (!groups.has(m)) groups.set(m, []);
    groups.get(m).push(p);
  });
  const direction = els.sortSelect.value === "date-asc" ? "asc" : "desc";
  const months = [...groups.keys()].sort((a, b) => direction === "asc" ? a.localeCompare(b) : b.localeCompare(a));
  return months.map(m => [m, sortByDay(groups.get(m), direction)]);
}

function renderStats() {
  els.totalPapers.textContent = papers.length;
  els.totalTopics.textContent = TOPIC_ORDER.length;
  els.lastUpdated.textContent = meta.updated_at ? dateOnly(meta.updated_at) : "local";

  renderMonthPicker();
  els.topicButtons.innerHTML = "";
  TOPIC_ORDER.forEach(topic => {
    const count = papers.filter(p => (p.topics || []).includes(topic)).length;
    const months = availableMonths(papers.filter(p => (p.topics || []).includes(topic))).length;
    const btn = document.createElement("button");
    btn.className = "survey-jump-btn";
    btn.type = "button";
    btn.innerHTML = `<strong>${topic}</strong><span>${count} papers · ${months} months</span>`;
    btn.addEventListener("click", () => {
      els.topicFilter.value = topic;
      renderSections();
      const target = document.getElementById(topicSlug(topic));
      if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    els.topicButtons.appendChild(btn);
  });

  els.topicFilter.innerHTML = `<option value="All">All Topics</option>`;
  TOPIC_ORDER.forEach(topic => {
    const option = document.createElement("option");
    option.value = topic;
    option.textContent = topic;
    els.topicFilter.appendChild(option);
  });
}

function renderSections() {
  const rows = getFilteredPapers();
  els.visibleCount.textContent = rows.length;
  els.sectionContainer.innerHTML = "";

  const selectedTopic = els.topicFilter.value;
  const renderTopics = selectedTopic === "All" ? TOPIC_ORDER : [selectedTopic];

  renderTopics.forEach(topic => {
    const topicRows = rows.filter(p => (p.topics || []).includes(topic));
    if (!topicRows.length) return;

    const section = document.createElement("section");
    section.className = "topic-section";
    section.id = topicSlug(topic);

    const head = document.createElement("div");
    head.className = "topic-section-head";
    head.innerHTML = `<div><h3>${topic}</h3><p class="topic-time-hint">Indexed by year-month; papers inside each month are ordered by day.</p></div><span class="count-badge">${topicRows.length} papers</span>`;
    section.appendChild(head);

    const allTopicRowsBeforeMonth = papers.filter(p => {
      const topics = p.topics || [];
      const relevance = els.relevanceFilter.value;
      const q = els.searchInput.value.trim().toLowerCase();
      const text = [p.title, (p.authors || []).join(" "), p.abstract, topics.join(" "), p.venue, p.uav_relevance].join(" ").toLowerCase();
      return topics.includes(topic) && (relevance === "All" || p.uav_relevance === relevance) && (!q || text.includes(q));
    });
    const monthIndex = createMonthIndex(topic, allTopicRowsBeforeMonth);
    if (monthIndex) section.appendChild(monthIndex);

    const grouped = groupByMonth(topicRows);
    grouped.forEach(([month, monthRows]) => {
      const monthBlock = document.createElement("div");
      monthBlock.className = "month-block";
      monthBlock.id = `${topicSlug(topic)}-${month}`;

      const monthHead = document.createElement("div");
      monthHead.className = "month-head";
      monthHead.innerHTML = `<div class="calendar-badge"><span>${month === "Unknown" ? "--" : month.slice(5, 7)}</span><small>${month === "Unknown" ? "Unknown" : month.slice(0, 4)}</small></div><div><h4>${formatMonth(month)}</h4><p>${monthRows.length} papers, sorted by day</p></div>`;
      monthBlock.appendChild(monthHead);

      const list = document.createElement("div");
      list.className = "paper-list";
      monthRows.forEach(p => list.appendChild(createPaperCard(p)));
      monthBlock.appendChild(list);
      section.appendChild(monthBlock);
    });

    els.sectionContainer.appendChild(section);
  });

  if (!els.sectionContainer.children.length) {
    els.sectionContainer.innerHTML = `<p class="muted">No papers found. Try another keyword, topic, relevance, or month filter.</p>`;
  }
}

async function loadData() {
  const [paperRes, metaRes] = await Promise.all([
    fetch(DATA_URL, { cache: "no-store" }),
    fetch(META_URL, { cache: "no-store" }).catch(() => null),
  ]);
  papers = await paperRes.json();
  meta = metaRes && metaRes.ok ? await metaRes.json() : {};
  renderStats();
  renderSections();
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

els.searchInput.addEventListener("input", renderSections);
els.topicFilter.addEventListener("change", renderSections);
els.relevanceFilter.addEventListener("change", renderSections);
els.monthFilter.addEventListener("change", renderSections);
els.clearMonthBtn.addEventListener("click", () => {
  els.monthFilter.value = "";
  renderSections();
});
els.sortSelect.addEventListener("change", renderSections);
els.exportCsvBtn.addEventListener("click", () => download("uav-vln-awesome-papers.csv", toCSV(getFilteredPapers()), "text/csv"));
els.exportBibBtn.addEventListener("click", () => download("uav-vln-awesome-papers.bib", getFilteredPapers().map(p => p.bibtex || "").join("\n\n"), "text/plain"));

initTheme();
loadData().catch(err => {
  console.error(err);
  els.sectionContainer.innerHTML = `<p class="muted">Failed to load data/papers.json. Run with a local server, e.g. python -m http.server 8000.</p>`;
});
