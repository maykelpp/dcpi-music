const DcpiSearch = (() => {
  const input = document.getElementById('search-input');
  const status = document.getElementById('search-status');
  const list = document.getElementById('search-results');

  let debounceTimer = null;
  let lastQuery = '';
  let lastResults = [];

  function skeletonRow() {
    return `<li class="track-item">
      <div class="skeleton" style="width:52px;height:52px;"></div>
      <div class="meta" style="flex:1">
        <div class="skeleton" style="height:12px;width:70%;margin-bottom:6px;"></div>
        <div class="skeleton" style="height:10px;width:45%;"></div>
      </div>
    </li>`;
  }

  function renderSkeletons() {
    list.innerHTML = Array(6).fill(0).map(skeletonRow).join('');
  }

  function fmtDuration(sec) {
    const m = Math.floor(sec / 60);
    const s = String(sec % 60).padStart(2, '0');
    return `${m}:${s}`;
  }

  function renderResults(results) {
    lastResults = results;
    if (!results.length) {
      list.innerHTML = '';
      status.textContent = 'Sin resultados.';
      return;
    }
    status.textContent = '';
    list.innerHTML = results.map((t, i) => `
      <li class="track-item" data-index="${i}">
        <img src="${t.cover || ''}" loading="lazy" alt="" onerror="this.style.opacity=0" />
        <div class="meta">
          <div class="t">${escapeHtml(t.title)}</div>
          <div class="a">${escapeHtml(t.artist)}</div>
        </div>
        <span class="dur mono">${fmtDuration(t.duration)}</span>
      </li>
    `).join('');
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  list.addEventListener('click', (e) => {
    const item = e.target.closest('.track-item');
    if (!item) return;
    const track = lastResults[Number(item.dataset.index)];
    if (track) {
      DcpiPlayer.playTrack(track, lastResults);
      DcpiRouter.go('player');
    }
  });

  input.addEventListener('input', () => {
    const q = input.value.trim();
    clearTimeout(debounceTimer);

    if (q.length < 2) {
      list.innerHTML = '';
      status.textContent = '';
      return;
    }

    debounceTimer = setTimeout(async () => {
      if (q === lastQuery) return;
      lastQuery = q;
      renderSkeletons();
      status.textContent = '';
      try {
        const { results } = await DcpiApi.search(q);
        if (input.value.trim() === q) renderResults(results);
      } catch (err) {
        status.textContent = err.message || 'Error al buscar.';
        list.innerHTML = '';
      }
    }, 350); // debounce
  });

  return {};
})();
