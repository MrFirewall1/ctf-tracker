(function () {
  const PALETTE = ['#ff3b3b', '#d4d4da', '#9a9aa3', '#b02a2a', '#ff8a8a', '#6b6b74'];
  const STATUS_COLORS = {solved_alone: '#d4d4da', solved_hint: '#9a9aa3', solved_solution: '#6b6b74', unsolved: '#ff3b3b'};
  const style = getComputedStyle(document.documentElement);
  Chart.defaults.color = style.getPropertyValue('--muted').trim() || '#6b7385';
  Chart.defaults.borderColor = style.getPropertyValue('--line').trim() || '#dfe3ea';
  Chart.defaults.maintainAspectRatio = false;

  const pct = v => v === null ? null : Math.round(v * 100);
  const el = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

  function tile(value, label) {
    return `<div class="tile"><div class="v">${esc(value)}</div><div class="l">${esc(label)}</div></div>`;
  }

  function mk(id, cfg) {
    const old = Chart.getChart(el(id));
    if (old) old.destroy();
    return new Chart(el(id), cfg);
  }
  function clearCharts() {
    document.querySelectorAll('canvas:not(#c-skills)').forEach(c => { const x = Chart.getChart(c); if (x) x.destroy(); });
  }

  function rateChart(id, rows) {
    mk(id, {
      type: 'bar',
      data: {
        labels: rows.map(r => `${r.label} (${r.solved}/${r.total})`),
        datasets: [{label: 'Løsningsrate %', data: rows.map(r => pct(r.rate)), backgroundColor: PALETTE[0]}],
      },
      options: {indexAxis: 'y', scales: {x: {min: 0, max: 100}}, plugins: {legend: {display: false}}},
    });
  }

  const INTROS = JSON.parse(el('intros-data').textContent);
  const CAT = id => (INTROS[id] || {}).title || id;

  function renderIntro(cat) {
    const box = el('intro');
    if (!cat || !INTROS[cat]) { box.hidden = true; box.innerHTML = ''; return; }
    const i = INTROS[cat];
    box.hidden = false;
    box.innerHTML = `<h2>${esc(i.title)}</h2><p>${esc(i.summary)}</p>` +
      '<h3>Nøkkelbegreper</h3><dl>' + i.terms.map(t => `<dt>${esc(t[0])}</dt><dd>${esc(t[1])}</dd>`).join('') + '</dl>' +
      '<h3>Slik kommer du i gang</h3><ol>' + i.start.map(x => `<li>${esc(x)}</li>`).join('') + '</ol>' +
      `<p class="muted">Verktøy: ${esc(i.tools)}</p>`;
  }

  function currentFilter() {
    const q = new URLSearchParams();
    ['category', 'difficulty', 'protocol'].forEach(k => { const v = el('f-' + k).value; if (v) q.set(k, v); });
    return q;
  }

  const DIFF = {easy: 'Lett', medium: 'Middels', hard: 'Vanskelig'};
  async function renderCatalog(q) {
    const box = el('catalog-body');
    try {
      const r = await fetch('/api/catalog' + (q.toString() ? '?' + q : ''));
      const c = await r.json();
      if (!r.ok) { box.innerHTML = '<p class="muted">Kunne ikke hente katalogen.</p>'; return; }
      const rows = Object.keys(DIFF).filter(k => c.by_difficulty[k]).map(k => {
        const x = c.by_difficulty[k];
        return `<tr><td>${DIFF[k]}</td><td>${x.total}</td><td>${x.ready}</td><td>${x.partial}</td><td>${x.missing}</td><td>${x.logged}</td></tr>`;
      }).join('');
      const t = c.total;
      box.innerHTML = t.total
        ? `<p><strong>${t.ready}</strong> av ${t.total} oppgaver er klare til å løse, og du har logget <strong>${t.logged}</strong>. ` +
          `<a href="/practice">Åpne Oppvarming →</a></p>` +
          '<table><thead><tr><th>Nivå</th><th>Totalt</th><th>Klare</th><th>Delvis</th><th>Mangler filer</th><th>Logget</th></tr></thead><tbody>' +
          rows + `<tr><td><strong>Sum</strong></td><td>${t.total}</td><td>${t.ready}</td><td>${t.partial}</td><td>${t.missing}</td><td>${t.logged}</td></tr></tbody></table>` +
          (c.downloads_dir_set ? '' : '<p class="muted">Start appen med CTF_DOWNLOADS_DIR for å se hvilke filer som er lastet ned.</p>')
        : '<p class="muted">Ingen oppgaver i katalogen med dette filteret.</p>';
    } catch (e) { box.innerHTML = '<p class="muted">Kunne ikke hente katalogen.</p>'; }
  }

  async function renderXp() {
    try {
      const x = await (await fetch('/api/xp')).json();
      const L = x.level;
      el('xp-level').textContent = 'Nivå ' + L.number + ' · ' + L.name;
      el('xp-total').textContent = x.xp;
      el('xp-next').textContent = L.next_at ? ' · ' + L.to_next + ' XP til ' + L.next_name : ' · høyeste nivå nådd';
      el('xp-bar').style.width = Math.round(L.progress * 100) + '%';
      el('xp-streak').textContent = x.streak.current;
      el('xp-week').textContent = x.week_xp;
      el('xp-days').textContent = x.active_days;
      const hm = el('heatmap');
      hm.innerHTML = x.heatmap.map(d => `<i class="${d.n ? 'l' + Math.min(d.n, 4) : ''}" title="${d.date}: ${d.n}"></i>`).join('');
      hm.scrollLeft = hm.scrollWidth;
      mk('c-skills', {
        type: 'radar',
        data: {labels: x.skills.map(k => k.label), datasets: [{label: 'XP', data: x.skills.map(k => k.xp),
               borderColor: '#ff3b3b', backgroundColor: 'rgba(255,59,59,.2)', pointBackgroundColor: '#ff3b3b'}]},
        options: {scales: {r: {beginAtZero: true, ticks: {display: false}, grid: {color: '#2f2f36'}, angleLines: {color: '#2f2f36'}}}, plugins: {legend: {display: false}}},
      });
    } catch (e) { /* XP er valgfritt: resten av dashbordet virker uten */ }
  }

  async function main() {
    renderXp();
    const q = currentFilter();
    renderIntro(q.get('category'));
    history.replaceState(null, '', q.toString() ? '?' + q : location.pathname);
    el('weakest').innerHTML = ''; el('revisit').innerHTML = '';
    renderCatalog(q);
    const r = await fetch('/api/stats' + (q.toString() ? '?' + q : ''));
    const data = await r.json();
    if (!r.ok) {
      const box = el('load-error');
      box.hidden = false; box.textContent = data.error || 'Kunne ikke hente data.';
      return;
    }
    if (data.errors.length) {
      const box = el('parse-errors');
      box.hidden = false;
      box.innerHTML = '<strong>Filer som ikke kunne leses:</strong> ' + data.errors.map(e => esc(e.file + ': ' + e.error)).join('; ');
    }
    const s = data.stats, t = s.totals;
    el('tiles').innerHTML =
      tile(t.tasks, 'Oppgaver logget') +
      tile(t.solved, 'Løst (alene/hint)') +
      tile(t.rate === null ? '–' : pct(t.rate) + ' %', 'Løsningsrate') +
      tile(s.streak.current + ' d', `Streak (lengste ${s.streak.longest} d)`) +
      tile(t.avg_hints === null ? '–' : t.avg_hints, 'Hint per oppgave (snitt)') +
      tile(t.resolved_later, 'Løst på nytt uten hjelp') +
      tile(t.explained + ' / ' + t.tasks, 'Med «Hva jeg lærte» utfylt');

    if (!t.tasks) {
      clearCharts();
      el('weakest').innerHTML = q.toString()
        ? '<p class="muted">Ingen loggede oppgaver med dette filteret ennå.</p>'
        : '<p class="muted">Logg noen oppgaver for å se statistikk.</p>';
      el('revisit').innerHTML = '';
      return;
    }

    mk('c-solved', {
      data: {
        labels: s.solved_over_time.labels,
        datasets: [
          {type: 'bar', label: 'Løst per uke', data: s.solved_over_time.solved, backgroundColor: PALETTE[0], yAxisID: 'y'},
          {type: 'line', label: 'Totalt løst', data: s.solved_over_time.cumulative, borderColor: PALETTE[1], backgroundColor: PALETTE[1], yAxisID: 'y2', tension: 0.2},
        ],
      },
      options: {scales: {y: {beginAtZero: true, ticks: {precision: 0}}, y2: {position: 'right', beginAtZero: true, ticks: {precision: 0}, grid: {drawOnChartArea: false}}}},
    });

    rateChart('c-cat', s.by_category);
    rateChart('c-proto', s.by_protocol);

    mk('c-hints', {
      type: 'line',
      data: {
        labels: s.hints_over_time.labels,
        datasets: [{label: 'Hint per oppgave', data: s.hints_over_time.avg_hints, borderColor: PALETTE[2],
                    backgroundColor: PALETTE[2], spanGaps: true, tension: 0.2}],
      },
      options: {scales: {y: {beginAtZero: true}}, plugins: {legend: {display: false}}},
    });

    el('revisit').innerHTML = s.to_revisit.length
      ? '<ul>' + s.to_revisit.map(x =>
          `<li><a href="/tasks/${encodeURIComponent(x.id)}">${esc(x.title)}</a> <span class="muted">${esc(x.date)} · ${esc(x.label)}</span></li>`
        ).join('') + '</ul>'
      : '<p class="muted">Ingenting å gjenta akkurat nå.</p>';

    mk('c-status', {
      type: 'doughnut',
      data: {
        labels: s.status_share.map(x => x.label),
        datasets: [{data: s.status_share.map(x => x.count), backgroundColor: s.status_share.map(x => STATUS_COLORS[x.key])}],
      },
      options: {plugins: {legend: {position: 'right'}}},
    });

    mk('c-sessions', {
      type: 'bar',
      data: {
        labels: s.sessions_per_week.labels,
        datasets: [{label: 'Treningsdager', data: s.sessions_per_week.days, backgroundColor: PALETTE[4]}],
      },
      options: {scales: {y: {beginAtZero: true, max: 7, ticks: {precision: 0}}}, plugins: {legend: {display: false}}},
    });

    el('weakest').innerHTML = s.weakest.length
      ? '<table><thead><tr><th>Område</th><th>Type</th><th>Løst / totalt</th><th>Rate</th></tr></thead><tbody>' +
        s.weakest.map(w => `<tr><td>${esc(w.label)}</td><td>${esc(w.kind)}</td><td>${w.solved} / ${w.total}</td>` +
          `<td><span class="bar" style="width:${pct(w.rate)}px"></span> ${pct(w.rate)} %</td></tr>`).join('') +
        '</tbody></table>'
      : '<p class="muted">Ingen områder med lav rate ennå (trenger minst 2 oppgaver i en gruppe).</p>';
  }
  const qs = new URLSearchParams(location.search);
  ['category', 'difficulty', 'protocol'].forEach(k => { if (qs.get(k)) el('f-' + k).value = qs.get(k); });
  ['category', 'difficulty', 'protocol'].forEach(k => el('f-' + k).addEventListener('change', () => {
    el('load-error').hidden = true; main().catch(e => { const b = el('load-error'); b.hidden = false; b.textContent = 'Feil: ' + e.message; });
  }));
  main().catch(e => { const b = el('load-error'); b.hidden = false; b.textContent = 'Feil: ' + e.message; });
})();
