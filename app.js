function formatBytes(n) {
  if (n == null) return '—';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}
function statusClass(status, security) {
  const s = (status || 'queued').toLowerCase();
  if (s === 'blocked' || security === 'quarantined' || security === 'binary-quarantine') return 'bad';
  if (s === 'extracted' || s === 'distilled' || s === 'indexed') return 'ok';
  if (s === 'scanned' || s === 'retrieved') return 'warn';
  return '';
}
function esc(s) {
  const map = { '&': '&' + 'amp;', '<': '&' + 'lt;', '>': '&' + 'gt;', '"': '&' + 'quot;', "'": '&#39;' };
  return String(s ?? '').replace(/[&<>"']/g, (c) => map[c]);
}

const state = { tab: 'skills', q: '', mime: 'all', status: 'all', selected: null, inventory: null, knowledge: null };

async function load() {
  const [inv, kb] = await Promise.all([
    fetch('./data/inventory.json').then((r) => { if (!r.ok) throw new Error('inventory '+r.status); return r.json(); }),
    fetch('./data/knowledge.json').then((r) => { if (!r.ok) throw new Error('knowledge '+r.status); return r.json(); }),
  ]);
  state.inventory = inv;
  state.knowledge = kb;
  render();
}

function render() {
  const root = document.getElementById('app');
  const inv = state.inventory;
  const kb = state.knowledge;
  if (!inv || !kb) { root.innerHTML = `<p class="empty">Loading inventory and knowledge base…</p>`; return; }
  const items = inv.items || [];
  const skills = kb.skills || [];
  const docs = kb.docs || [];
  const coverage = kb.coverage || {};
  const mimes = ['all', ...Array.from(new Set(items.map(i => i.mime_type).filter(Boolean))).sort()];
  const statuses = ['all', ...Array.from(new Set(items.map(i => i.status).filter(Boolean))).sort()];
  const needle = state.q.trim().toLowerCase();

  const filteredItems = items.filter(i => {
    if (state.mime !== 'all' && i.mime_type !== state.mime) return false;
    if (state.status !== 'all' && i.status !== state.status) return false;
    if (!needle) return true;
    return (i.name||'').toLowerCase().includes(needle) || (i.id||'').toLowerCase().includes(needle) || (i.security_status||'').toLowerCase().includes(needle);
  });
  const pool = state.tab === 'docs' ? docs : skills;
  const filteredSkills = !needle ? pool : pool.filter(s => (s.name||'').toLowerCase().includes(needle) || (s.description||'').toLowerCase().includes(needle) || (s.preview||'').toLowerCase().includes(needle));
  const blocked = items.filter(i => i.status === 'blocked' || (i.security_status && i.security_status !== 'cleared' && i.security_status !== 'pending'))
    .filter(i => !needle || (i.name||'').toLowerCase().includes(needle));

  let body = '';
  if (state.tab === 'skills' || state.tab === 'docs') {
    body = `<div class="grid">${filteredSkills.map(s => `
      <article class="card">
        <div class="chips"><span class="chip ok">${esc(s.kind)}</span><span class="chip mono">${esc(s.chars)} chars</span></div>
        <h3>${esc(s.name)}</h3>
        <p>${esc(s.description)}</p>
        <button data-open="${esc(s.id)}">Open preview</button>
      </article>`).join('') || '<p class="empty">No matches.</p>'}</div>`;
    if (state.selected) {
      body += `<div class="detail" role="region"><strong>${esc(state.selected.name)}</strong>\npath: ${esc(state.selected.path)}\n\n${esc(state.selected.preview)}\n<div style="margin-top:12px"><button data-close>Close</button></div></div>`;
    }
  } else if (state.tab === 'inventory') {
    body = `<div class="table-wrap"><table><thead><tr><th>Name</th><th>Status</th><th>MIME</th><th>Size</th><th>Link</th></tr></thead><tbody>
      ${filteredItems.map(i => `<tr>
        <td><div>${esc(i.name)}</div><div class="mono" style="color:var(--muted)">${esc(i.id)}</div></td>
        <td><span class="chip ${statusClass(i.status,i.security_status)}">${esc(i.status)}${i.security_status?` · ${esc(i.security_status)}`:''}</span></td>
        <td class="mono">${esc(i.mime_type)}</td>
        <td class="mono">${formatBytes(i.size_bytes)}</td>
        <td>${i.web_view_link?`<a href="${esc(i.web_view_link)}" target="_blank" rel="noreferrer">Drive</a>`:'—'}</td>
      </tr>`).join('')}</tbody></table>${filteredItems.length?'' :'<p class="empty">No files match.</p>'}</div>`;
  } else if (state.tab === 'security') {
    body = `<div class="table-wrap"><table><thead><tr><th>Name</th><th>Reason</th><th>Action taken</th></tr></thead><tbody>
      ${blocked.map(i => `<tr><td>${esc(i.name)}</td><td class="mono">${esc(i.security_status||'blocked')}</td><td>${esc(i.note||'Not downloaded into knowledge base. Not executed.')}</td></tr>`).join('')}
    </tbody></table></div>`;
  } else {
    body = `<div class="grid">
      <article class="card"><h3>Requirements</h3>${(kb.requirements||[]).map(r=>`<p><span class="chip ${r.status==='done'?'ok':r.status==='blocked'?'bad':'warn'}">${esc(r.status)}</span> ${esc(r.id)}: ${esc(r.text)}</p>`).join('')}</article>
      <article class="card"><h3>Assumptions</h3>${(kb.product?.assumptions||[]).map(a=>`<p>• ${esc(a)}</p>`).join('')}</article>
      <article class="card"><h3>Coverage by status</h3>${Object.entries(coverage.by_status||{}).map(([k,v])=>`<p><span class="chip mono">${esc(k)}</span> ${esc(v)}</p>`).join('')}</article>
    </div>`;
  }

  root.innerHTML = `
    <header class="hero">
      <div class="chips">
        <span class="chip ok">Drive folder reconciled</span>
        <span class="chip">EXTRACT · ${esc(inv.reconciled_count)} items</span>
        <span class="chip warn">Vercel token not in session</span>
      </div>
      <h1>EXTRACT Skill Distillery</h1>
      <p>${esc(kb.product?.tagline)}. ${esc(kb.product?.decision)}</p>
    </header>
    <section class="stats">
      <div class="stat"><b>${esc(inv.reconciled_count)}</b><span>files reconciled</span></div>
      <div class="stat"><b>${esc(coverage.distilled_entries||0)}</b><span>distilled entries</span></div>
      <div class="stat"><b>${esc(skills.length)}</b><span>skills extracted</span></div>
      <div class="stat"><b>${esc((coverage.blocked_security||[]).length)}</b><span>security blocked</span></div>
    </section>
    <div class="toolbar">
      <div class="tabs">
        ${['skills','docs','inventory','security','product'].map(t=>`<button data-tab="${t}" class="${state.tab===t?'active':''}">${t[0].toUpperCase()+t.slice(1)}</button>`).join('')}
      </div>
      <input id="q" value="${esc(state.q)}" placeholder="${state.tab==='inventory'||state.tab==='security'?'Search files…':'Search skills and docs…'}" aria-label="Search" />
      ${(state.tab==='inventory'||state.tab==='security')?`
        <select id="mime" aria-label="MIME filter">${mimes.map(m=>`<option value="${esc(m)}" ${state.mime===m?'selected':''}>${esc(m)}</option>`).join('')}</select>
        <select id="status" aria-label="Status filter">${statuses.map(s=>`<option value="${esc(s)}" ${state.status===s?'selected':''}>${esc(s)}</option>`).join('')}</select>
      `:''}
    </div>
    ${body}
    <footer class="footer">Source: Google Drive folder EXTRACT (${esc(inv.folder_id)}). Drive originals unchanged. Secrets and binaries quarantined. Generated ${esc(kb.generated_at)}.</footer>
  `;

  root.querySelectorAll('[data-tab]').forEach(btn => btn.addEventListener('click', () => { state.tab = btn.dataset.tab; state.selected=null; render(); }));
  const q = root.querySelector('#q');
  if (q) q.addEventListener('input', (e) => { state.q = e.target.value; render(); /* keep focus */ document.getElementById('q')?.focus(); const el=document.getElementById('q'); if(el){ el.value=state.q; el.selectionStart=el.selectionEnd=el.value.length; } });
  const mime = root.querySelector('#mime');
  if (mime) mime.addEventListener('change', (e) => { state.mime = e.target.value; render(); });
  const status = root.querySelector('#status');
  if (status) status.addEventListener('change', (e) => { state.status = e.target.value; render(); });
  root.querySelectorAll('[data-open]').forEach(btn => btn.addEventListener('click', () => {
    const id = btn.dataset.open;
    state.selected = [...skills, ...docs].find(s => s.id === id) || null;
    render();
  }));
  root.querySelector('[data-close]')?.addEventListener('click', () => { state.selected=null; render(); });
}

load().catch((e) => {
  document.getElementById('app').innerHTML = `<h1>EXTRACT Skill Distillery</h1><p class="empty">Failed to load data: ${esc(e.message||e)}</p>`;
});
