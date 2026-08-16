const DcpiRouter = (() => {
  const screens = ['search', 'player', 'history', 'favorites'];
  let current = 'search';

  function go(screenName) {
    if (!screens.includes(screenName)) return;
    document.getElementById(`screen-${current}`).classList.remove('active');
    document.getElementById(`screen-${screenName}`).classList.add('active');
    current = screenName;

    document.querySelectorAll('.nav-item').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.screen === screenName);
    });
    document.getElementById('bottom-nav').style.display = screenName === 'player' ? 'none' : 'flex';
    DcpiTelegram.showBackButton(screenName === 'player');

    if (screenName === 'history') loadHistory();
    if (screenName === 'favorites') loadFavorites();
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  async function loadHistory() {
    const list = document.getElementById('history-list');
    list.innerHTML = '<p class="hint">Cargando…</p>';
    try {
      const { history } = await DcpiApi.getHistory();
      if (!history.length) {
        list.innerHTML = '<p class="hint">Aún no has escuchado ninguna canción.</p>';
        return;
      }
      list.innerHTML = history.map((t) => `
        <li class="track-item" data-id="${t.track_id}" data-title="${escapeHtml(t.title)}" data-artist="${escapeHtml(t.artist)}" data-cover="${t.cover_url || ''}">
          <img src="${t.cover_url || ''}" loading="lazy" alt="" onerror="this.style.opacity=0" />
          <div class="meta">
            <div class="t">${escapeHtml(t.title)}</div>
            <div class="a">${escapeHtml(t.artist)}</div>
          </div>
        </li>
      `).join('');
    } catch (e) {
      list.innerHTML = `<p class="hint">${e.message}</p>`;
    }
  }

  async function loadFavorites() {
    const list = document.getElementById('favorites-list');
    list.innerHTML = '<p class="hint">Cargando…</p>';
    try {
      const { favorites } = await DcpiApi.getFavorites();
      if (!favorites.length) {
        list.innerHTML = '<p class="hint">Aún no tienes canciones favoritas.</p>';
        return;
      }
      list.innerHTML = favorites.map((t) => `
        <li class="track-item" data-id="${t.track_id}" data-title="${escapeHtml(t.title)}" data-artist="${escapeHtml(t.artist)}" data-cover="${t.cover_url || ''}" data-duration="${t.duration || 0}">
          <img src="${t.cover_url || ''}" loading="lazy" alt="" onerror="this.style.opacity=0" />
          <div class="meta">
            <div class="t">${escapeHtml(t.title)}</div>
            <div class="a">${escapeHtml(t.artist)}</div>
          </div>
        </li>
      `).join('');
    } catch (e) {
      list.innerHTML = `<p class="hint">${e.message}</p>`;
    }
  }

  function trackFromEl(el) {
    return {
      id: el.dataset.id,
      title: el.dataset.title,
      artist: el.dataset.artist,
      cover: el.dataset.cover,
      duration: Number(el.dataset.duration) || 0,
    };
  }

  document.getElementById('history-list').addEventListener('click', (e) => {
    const item = e.target.closest('.track-item');
    if (item) { DcpiPlayer.playTrack(trackFromEl(item)); go('player'); }
  });
  document.getElementById('favorites-list').addEventListener('click', (e) => {
    const item = e.target.closest('.track-item');
    if (item) { DcpiPlayer.playTrack(trackFromEl(item)); go('player'); }
  });

  document.querySelectorAll('.nav-item').forEach((btn) => {
    btn.addEventListener('click', () => go(btn.dataset.screen));
  });
  document.getElementById('btn-clear-history').addEventListener('click', async () => {
    if (!confirm('¿Borrar todo el historial?')) return;
    await DcpiApi.clearHistory().catch(() => {});
    loadHistory();
  });
  document.getElementById('btn-back').addEventListener('click', () => go('search'));
  DcpiTelegram.onBackButton(() => go('search'));

  return { go };
})();
