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

  function rowHtml(t, index) {
    return `
      <li class="track-item" data-index="${index}">
        <img src="${t.cover || ''}" loading="lazy" alt="" onerror="this.style.opacity=0" />
        <div class="meta">
          <div class="t">${escapeHtml(t.title)}</div>
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
      feedOffset = 0;
      allItems = [];
      feedExhausted = false;
      renderSkeletons();
      status.textContent = '';
    }
    if (loadingMore || feedExhausted) return;
    loadingMore = true;
    if (!reset) appendLoadingRow();

    try {
      const { results } = await DcpiApi.getFeed(feedSeed, feedOffset, 10);
      if (!results.length) {
        feedExhausted = true;
      } else {
        allItems = allItems.concat(results);
        feedOffset += results.length;
      }
      removeLoadingRow();
      renderAll();
      if (!allItems.length) status.textContent = 'No se pudo cargar el feed por ahora.';
    } catch (err) {
      removeLoadingRow();
      if (!allItems.length) {
        status.textContent = err.message || 'No se pudo cargar el feed.';
        list.innerHTML = '';
      }
    } finally {
      loadingMore = false;
    }
  }

  function setFeedSeed(trackId) {
    feedSeed = trackId;
  }

  // ===== Búsqueda (por texto) =====
  async function runSearch(q) {
    renderSkeletons();
    status.textContent = '';
    try {
      const { results } = await DcpiApi.search(q);
      allItems = results;
      renderAll();
      if (!results.length) status.textContent = 'Sin resultados.';
    } catch (err) {
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
    }, 350);
  });

  // Scroll infinito: solo activo en modo feed
  screen.addEventListener('scroll', () => {
    if (mode !== 'feed') return;
    const nearBottom = screen.scrollTop + screen.clientHeight >= screen.scrollHeight - 300;
    if (nearBottom) loadFeed(false);
  });

  list.addEventListener('click', (e) => {
    const item = e.target.closest('.track-item');
    if (!item || item.id === 'feed-loading-row') return;
    const track = allItems[Number(item.dataset.index)];
    if (track) {
      DcpiPlayer.playTrack(track, allItems);
      DcpiRouter.go('player');
    }
  });

  // Carga inicial del feed al abrir la app
  loadFeed(true);

  return { setFeedSeed };
})();
