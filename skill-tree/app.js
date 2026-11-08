const state = {
  data: null,
  category: null,
  query: "",
  selected: null,
};

const $ = (id) => document.getElementById(id);

async function load() {
  const res = await fetch("./data/tree-compact.json", { cache: "no-store" });
  if (!res.ok) throw new Error("tree-compact.json missing — run ste-build");
  state.data = await res.json();
  renderAll();
}

function renderStats() {
  const s = state.data.stats || {};
  $("stats").innerHTML = [
    ["Nodes", s.nodes ?? "—"],
    ["Skills", s.skills ?? "—"],
    ["Docs", s.docs ?? "—"],
    ["Edges", s.edges ?? "—"],
  ]
    .map(([k, v]) => `<div class="stat"><b>${v}</b><span>${k}</span></div>`)
    .join("");
  $("productTag").textContent = state.data.product?.tagline || state.data.product?.name || "Skill tree";
  $("statusPills").innerHTML = `
    <span class="pill ok">engine online</span>
    <span class="pill">${Object.keys(state.data.categories || {}).length} categories</span>
    <span class="pill">${(state.data.generated_at || "").slice(0, 19)}Z</span>
  `;
}

function renderCats() {
  const cats = state.data.categories || {};
  const entries = Object.entries(cats).sort((a, b) => b[1].length - a[1].length);
  $("cats").innerHTML =
    `<button class="cat ${!state.category ? "active" : ""}" data-cat="">All categories <em>${state.data.stats?.skills ?? ""}</em></button>` +
    entries
      .map(
        ([c, ids]) =>
          `<button class="cat ${state.category === c ? "active" : ""}" data-cat="${c}">${c.replaceAll("_", " ")} <em>${ids.length}</em></button>`
      )
      .join("");
  $("cats").onclick = (e) => {
    const btn = e.target.closest("[data-cat]");
    if (!btn) return;
    state.category = btn.dataset.cat || null;
    state.query = "";
    $("q").value = "";
    renderAll();
  };
}

function nodeMap() {
  const m = new Map();
  for (const n of state.data.nodes || []) m.set(n.id, n);
  return m;
}

function renderTree() {
  const nodes = nodeMap();
  const cats = Object.entries(state.data.categories || {}).sort((a, b) => b[1].length - a[1].length);
  const filtered = state.category ? cats.filter(([c]) => c === state.category) : cats;
  $("viewTitle").textContent = state.category ? state.category.replaceAll("_", " ") : "Full tree";
  $("viewSub").textContent = `${state.data.product?.name || "Skill Tree"} · click cards to inspect`;
  $("tree").classList.remove("hidden");
  $("results").classList.add("hidden");
  $("tree").innerHTML = filtered
    .map(([cat, ids]) => {
      const cards = ids
        .map((id) => nodes.get(id))
        .filter(Boolean)
        .sort((a, b) => b.score - a.score)
        .map(
          (n) => `
        <article class="card" data-id="${n.id}">
          <h4>${escapeHtml(n.name)}</h4>
          <p>${escapeHtml(n.description || "No description")}</p>
          <div class="meta">
            <span class="tag">${escapeHtml(n.kind)}</span>
            <span class="tag">score ${n.score}</span>
            ${(n.tags || []).slice(0, 2).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}
          </div>
        </article>`
        )
        .join("");
      return `
      <div class="branch open" data-branch="${cat}">
        <div class="branch-h">
          <strong>${cat.replaceAll("_", " ")}</strong>
          <span>${ids.length} nodes</span>
        </div>
        <div class="branch-b">${cards}</div>
      </div>`;
    })
    .join("");

  $("tree").onclick = (e) => {
    const h = e.target.closest(".branch-h");
    if (h) {
      h.parentElement.classList.toggle("open");
      return;
    }
    const card = e.target.closest(".card");
    if (card) selectNode(card.dataset.id);
  };
}

function renderSearch() {
  const q = state.query.toLowerCase();
  const hits = (state.data.nodes || []).filter((n) => {
    if (n.kind === "root" || n.kind === "category") return false;
    const blob = `${n.name} ${n.description} ${(n.tags || []).join(" ")} ${n.category}`.toLowerCase();
    return blob.includes(q);
  });
  $("viewTitle").textContent = `Search: ${state.query}`;
  $("viewSub").textContent = `${hits.length} hits`;
  $("tree").classList.add("hidden");
  $("results").classList.remove("hidden");
  $("results").innerHTML = hits
    .slice(0, 60)
    .map(
      (n) => `
    <article class="card" data-id="${n.id}">
      <h4>${escapeHtml(n.name)}</h4>
      <p>${escapeHtml(n.description || "")}</p>
      <div class="meta"><span class="tag">${escapeHtml(n.category)}</span><span class="tag">${escapeHtml(n.kind)}</span></div>
    </article>`
    )
    .join("");
  $("results").onclick = (e) => {
    const card = e.target.closest(".card");
    if (card) selectNode(card.dataset.id);
  };
}

function selectNode(id) {
  const n = (state.data.nodes || []).find((x) => x.id === id);
  if (!n) return;
  state.selected = n;
  $("detail").innerHTML = `
    <h3>${escapeHtml(n.name)}</h3>
    <p class="muted">${escapeHtml(n.description || "")}</p>
    <div class="kv">
      <b>id</b><span><code>${escapeHtml(n.id)}</code></span>
      <b>kind</b><span>${escapeHtml(n.kind)}</span>
      <b>category</b><span>${escapeHtml(n.category)}</span>
      <b>score</b><span>${n.score}</span>
      <b>depth</b><span>${n.depth}</span>
      <b>parent</b><span>${escapeHtml(n.parent || "—")}</span>
      <b>prereqs</b><span>${(n.prerequisites || []).map(escapeHtml).join(", ") || "—"}</span>
      <b>unlocks</b><span>${(n.unlocks || []).map(escapeHtml).join(", ") || "—"}</span>
      <b>tags</b><span>${(n.tags || []).map(escapeHtml).join(", ") || "—"}</span>
    </div>
    <pre>${escapeHtml(JSON.stringify(n, null, 2))}</pre>
  `;
}

function renderAll() {
  renderStats();
  renderCats();
  if (state.query.trim()) renderSearch();
  else renderTree();
}

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&")
    .replaceAll("<", "<")
    .replaceAll(">", ">")
    .replaceAll('"', """);
}

$("q").addEventListener("input", (e) => {
  state.query = e.target.value.trim();
  renderAll();
});

$("btnVerify").onclick = () => {
  const s = state.data.stats || {};
  alert(`Tree verify (client)\n nodes=${s.nodes}\n skills=${s.skills}\n edges=${s.edges}\n categories=${Object.keys(state.data.categories || {}).length}`);
};

$("btnExpand").onclick = () => {
  document.querySelectorAll(".branch").forEach((b) => b.classList.add("open"));
};

load().catch((err) => {
  document.body.innerHTML = `<pre style="color:#f88;padding:24px">Failed to load skill tree: ${err}</pre>`;
});
