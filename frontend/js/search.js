const DcpiSearch = (() => {
  const input = document.getElementById('search-input');
  const status = document.getElementById('search-status');
  const list = document.getElementById('search-results');
  const screen = document.getElementById('screen-search');

  let debounceTimer = null;
  let lastQuery = '';
  let allItems = [];        // acumulado (feed) o resultados actuales (búsqueda)
  let mode = 'feed';        // 'feed' | 'search'
  let feedOffset = 0;
  let feedSeed = null;      // ID de la última canción reproducida
  let loadingMore = false;
  let feedExhausted = false;
  let requestSeq = 0;
  const searchCache = new Map();
  let warmedPreview = null;

  function skeletonRow() {
    return `<li class="track-item">
      <div class="skeleton" style="width:52px;height:52px;"></div>
      <div class="meta" style="flex:1">
        <div class="skeleton" style="height:12px;width:70%;margin-bottom:6px;"></div>
        <div class="skeleton" style="height:10px;width:45%;"></div>
      </div>
    </li>`;
  }

  function renderSkeletons(count = 6) {
    list.innerHTML = Array(count).fill(0).map(skeletonRow).join('');
  }

  function fmtDuration(sec) {
    const m = Math.floor(sec / 60);
    const s = String(sec % 60).padStart(2, '0');
    return `${m}:${s}`;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  const SOURCE_BADGE = {
    jamendo: '',
    spotify: '<span class="src-badge src-spotify">30s</span>',
    youtube: '<span class="src-badge src-youtube">YT</span>',
  };

  function rowHtml(t, index) {
    return `
      <li class="track-item" data-index="${index}">
        <img src="${t.cover || ''}" loading="lazy" alt="" onerror="this.style.opacity=0" />
        <div class="meta">
          <div class="t">${escapeHtml(t.title)} ${SOURCE_BADGE[t.source] || ''}</div>
          <div class="a">${escapeHtml(t.artist)}</div>
        </div>
        <span class="dur mono">${fmtDuration(t.duration)}</span>
      </li>
    `;
  }

  function renderAll() {
    if (!allItems.length) {
      list.innerHTML = '';
      return;
    }
    list.innerHTML = allItems.map(rowHtml).join('');
  }

  function appendLoadingRow() {
    const li = document.createElement('li');
    li.className = 'track-item';
    li.id = 'feed-loading-row';
    li.innerHTML = `<div class="skeleton" style="width:52px;height:52px;"></div>
      <div class="meta" style="flex:1"><div class="skeleton" style="height:12px;width:60%;"></div></div>`;
    list.appendChild(li);
  }

  function removeLoadingRow() {
    document.getElementById('feed-loading-row')?.remove();
  }

  // ===== Feed (recomendaciones, scroll infinito) =====
  async function loadFeed(reset = false) {
    if (reset) {
      requestSeq++;
      loadingMore = false;
      feedOffset = 0;
      allItems = [];
      feedExhausted = false;
      renderSkeletons();
      status.textContent = '';
    }
    if (loadingMore || feedExhausted) return;
    const token = requestSeq;
    loadingMore = true;
    if (!reset) appendLoadingRow();
    try {
      const { results = [] } = await DcpiApi.getFeed(feedSeed, feedOffset, 10);
      if (token !== requestSeq) return;
      if (!results.length) feedExhausted = true;
      else { allItems = allItems.concat(results); feedOffset += results.length; }
      removeLoadingRow();
      renderAll();
      if (!allItems.length) status.textContent = 'El feed no devolvió canciones. Revisa la conexión del catálogo.';
    } catch (err) {
      if (token !== requestSeq) return;
      removeLoadingRow();
      if (!allItems.length) { status.textContent = err.message || 'No se pudo cargar el feed.'; list.innerHTML = ''; }
    } finally {
      if (token === requestSeq) loadingMore = false;
    }
  }

  function setFeedSeed(trackId) {
    feedSeed = trackId;
  }

  // ===== Búsqueda (por texto) =====
  async function runSearch(q) {
    const token = ++requestSeq;
    status.textContent = '';
    if (searchCache.has(q)) { allItems = searchCache.get(q); renderAll(); return; }
    renderSkeletons(4);
    try {
      const { results = [] } = await DcpiApi.search(q);
      if (token !== requestSeq) return;
      allItems = results;
      searchCache.set(q, results);
      if (searchCache.size > 30) searchCache.delete(searchCache.keys().next().value);
      renderAll();
      if (!results.length) status.textContent = 'Sin resultados.';
    } catch (err) {
      if (token !== requestSeq) return;
      status.textContent = err.message || 'Error al buscar.';
      list.innerHTML = '';
    }
  }

  input.addEventListener('input', () => {
    const q = input.value.trim();
    clearTimeout(debounceTimer);

    if (q.length < 2) {
      mode = 'feed';
      status.textContent = '';
      loadFeed(true);
      return;
    }

    debounceTimer = setTimeout(() => {
      if (q === lastQuery && mode === 'search') return;
      lastQuery = q;
      mode = 'search';
      runSearch(q);
    }, 180);
  });

  // Scroll infinito: solo activo en modo feed
  screen.addEventListener('scroll', () => {
    if (mode !== 'feed') return;
    const nearBottom = screen.scrollTop + screen.clientHeight >= screen.scrollHeight - 300;
    if (nearBottom) loadFeed(false);
  });

  list.addEventListener('pointerover', e => {
    const item = e.target.closest('.track-item');
    if (!item || item.id === 'feed-loading-row') return;
    const track = allItems[Number(item.dataset.index)];
    const url = track && (track.preview_url || track._audio_url);
    if (!url || warmedPreview === url) return;
    warmedPreview = url;
    const warm = new Audio();
    warm.preload = 'auto';
    warm.src = url;
    warm.load();
    window.__dcpiWarmPreview = warm;
  }, { passive: true });

  list.addEventListener('click', (e) => {
    const item = e.target.closest('.track-item');
    if (!item || item.id === 'feed-loading-row') return;
    const track = allItems[Number(item.dataset.index)];
    if (track) {
      DcpiRouter.go('player');
      DcpiPlayer.playTrack(track, allItems);
    }
  });

  // Carga inicial del feed al abrir la app
  loadFeed(true);

  return { setFeedSeed };
})();
