const DcpiRouter = (() => {
  const screens = ['search', 'player', 'library', 'history', 'favorites'];
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
    document.getElementById('mini-player').style.display = screenName === 'player' ? 'none' : '';
    DcpiTelegram.showBackButton(screenName === 'player');

    if (screenName === 'library') loadLibrary();
    if (screenName === 'history') loadHistory();
    if (screenName === 'favorites') loadFavorites();
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  async function loadLibrary() {
    const list = document.getElementById('library-list');
    const status = document.getElementById('library-status');
    list.innerHTML = '<p class="hint">Leyendo descargas guardadas…</p>';
    try {
      const items = await DcpiLibrary.all();
      if (!items.length) {
        list.innerHTML = '<p class="hint">Todavía no hay canciones descargadas. Abre una canción compatible y pulsa Guardar en Biblioteca.</p>';
        status.textContent = 'Biblioteca local vacía.';
        return;
      }
      status.textContent = items.length + ' canción(es) guardadas en este dispositivo.';
      list.innerHTML = items.map((t, i) =>
        '<li class="track-item" data-library-index="' + i + '">' +
        '<img src="' + escapeHtml(t.cover || '') + '" loading="lazy" alt="" onerror="this.style.opacity=0">' +
        '<div class="meta"><div class="t">' + escapeHtml(t.title) + '</div>' +
        '<div class="a">' + escapeHtml(t.artist) + ' · DESCARGADA</div></div>' +
        '<button class="text-btn" data-remove-library="' + i + '">Quitar</button></li>'
      ).join('');
      list.querySelectorAll('[data-library-index]').forEach(el => el.addEventListener('click', e => {
        if (e.target.closest('[data-remove-library]')) return;
        const item = items[Number(el.dataset.libraryIndex)];
        const track = DcpiLibrary.playable(item);
        DcpiPlayer.playTrack(track, [track]);
        go('player');
      }));
      list.querySelectorAll('[data-remove-library]').forEach(btn => btn.addEventListener('click', async e => {
        e.stopPropagation();
        await DcpiLibrary.remove(items[Number(btn.dataset.removeLibrary)].id);
        loadLibrary();
      }));
    } catch (e) {
      list.innerHTML = '<p class="hint">No se pudo abrir la biblioteca: ' + escapeHtml(e.message || 'error') + '</p>';
    }
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
      source: (el.dataset.id || '').split(':')[0], // el ID siempre viene como "fuente:id"
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
  document.getElementById('btn-refresh-library').addEventListener('click', loadLibrary);
  document.getElementById('btn-clear-history').addEventListener('click', async () => {
    if (!confirm('¿Borrar todo el historial?')) return;
    await DcpiApi.clearHistory().catch(() => {});
    loadHistory();
  });
  document.getElementById('btn-back').addEventListener('click', () => go('search'));
  DcpiTelegram.onBackButton(() => go('search'));

  return { go };
})();
