(function () {
  const form = document.getElementById('task-form');
  const msg = document.getElementById('msg');
  const body = document.getElementById('body');
  const preview = document.getElementById('preview');
  const tabEdit = document.getElementById('tab-edit');
  const tabPrev = document.getElementById('tab-preview');
  let taskId = form.dataset.id || '';

  if (!form.elements.date.value) {
    form.elements.date.valueAsDate = new Date();
  }

  function show(editing) {
    body.hidden = !editing;
    preview.hidden = editing;
    tabEdit.classList.toggle('active', editing);
    tabPrev.classList.toggle('active', !editing);
  }
  tabEdit.addEventListener('click', () => show(true));
  tabPrev.addEventListener('click', async () => {
    const r = await fetch('/api/preview', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: body.value}),
    });
    preview.innerHTML = (await r.json()).html;
    show(false);
  });

  function payload() {
    const f = form.elements;
    return {
      title: f.title.value, date: f.date.value, source: f.source.value,
      category: f.category.value, protocol: f.protocol.value, difficulty: f.difficulty.value,
      time_minutes: f.time_minutes.value, tools: f.tools.value, tags: f.tags.value,
      status: f.status.value, hints_used: f.hints_used.value,
      resolved_later: f.resolved_later.checked, body: body.value,
    };
  }

  form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    msg.className = ''; msg.textContent = 'Lagrer…';
    try {
      const r = await fetch(taskId ? '/api/tasks/' + taskId : '/api/tasks', {
        method: taskId ? 'PUT' : 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload()),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'Ukjent feil');
      taskId = data.task.id;
      history.replaceState(null, '', data.url);
      form.dataset.id = taskId;
      const g = data.git || {};
      const gitText = {committed: 'committet', unchanged: 'ingen endring', 'no-repo': 'ikke git-repo ennå',
                       error: 'FEIL: ' + (g.message || '')}[g.status] || '';
      msg.className = g.status === 'error' ? 'err' : 'ok';
      msg.textContent = 'Lagret ' + new Date().toLocaleTimeString('nb-NO') + (gitText ? ' · git: ' + gitText : '');
    } catch (e) {
      msg.className = 'err';
      msg.textContent = 'IKKE lagret: ' + e.message;
    }
  });
})();
