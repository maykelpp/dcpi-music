const DcpiLyrics = (() => {
  const linesEl = document.getElementById('lyrics-lines');
  const emptyEl = document.getElementById('lyrics-empty');
  const viewEl = document.getElementById('lyrics-view');

  let lines = [];       // [{ time, text }]
  let activeIndex = -1;

  function load(lyricsData) {
    linesEl.innerHTML = '';
    activeIndex = -1;
    lines = [];

    if (!lyricsData || (!lyricsData.synced && !lyricsData.text)) {
      emptyEl.textContent = lyricsData?.note || 'Sin letras disponibles para esta canción.';
      emptyEl.style.display = 'block';
      return;
    }

    if (lyricsData.synced && lyricsData.lines?.length) {
      emptyEl.style.display = 'none';
      lines = lyricsData.lines;
      lines.forEach((line, i) => {
        const p = document.createElement('p');
        p.className = 'lyrics-line';
        p.textContent = line.text;
        p.dataset.index = i;
        linesEl.appendChild(p);
      });
      return;
    }

    // Letra sin sincronizar (fallback tipo Genius): se muestra completa, sin resaltado.
    emptyEl.style.display = 'none';
    const p = document.createElement('p');
    p.className = 'lyrics-line active';
    p.style.whiteSpace = 'pre-line';
    p.textContent = lyricsData.text || (lyricsData.externalUrl ? 'Ver letra completa en Genius (enlace externo).' : '');
    linesEl.appendChild(p);
  }

  /** Se llama en cada `timeupdate` del audio con el tiempo actual en segundos. */
  function sync(currentTime) {
    if (!lines.length) return;

    let newIndex = activeIndex;
    for (let i = 0; i < lines.length; i++) {
      if (currentTime >= lines[i].time) newIndex = i;
      else break;
    }

    if (newIndex !== activeIndex) {
      const prevEl = linesEl.children[activeIndex];
      if (prevEl) prevEl.classList.remove('active');

      activeIndex = newIndex;
      const curEl = linesEl.children[activeIndex];
      if (curEl) {
        curEl.classList.add('active');
        curEl.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }
    }
  }

  function reset() {
    linesEl.innerHTML = '';
    lines = [];
    activeIndex = -1;
    emptyEl.style.display = 'block';
    emptyEl.textContent = 'Sin letras sincronizadas para esta canción.';
  }

  return { load, sync, reset };
})();
