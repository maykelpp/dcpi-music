const DcpiPlayer = (() => {
  const audio = new Audio();
  audio.preload = 'metadata';

  const els = {
    cover: document.getElementById('cover-img'),
    bg: document.getElementById('player-bg'),
    title: document.getElementById('track-title'),
    artist: document.getElementById('track-artist'),
    progress: document.getElementById('progress-bar'),
    timeCurrent: document.getElementById('time-current'),
    timeTotal: document.getElementById('time-total'),
    playBtn: document.getElementById('btn-play'),
    iconPlay: document.getElementById('icon-play'),
    iconPause: document.getElementById('icon-pause'),
    prevBtn: document.getElementById('btn-prev'),
    nextBtn: document.getElementById('btn-next'),
    shuffleBtn: document.getElementById('btn-shuffle'),
    repeatBtn: document.getElementById('btn-repeat'),
    volume: document.getElementById('volume-bar'),
    favBtn: document.getElementById('btn-favorite'),
    downloadBtn: document.getElementById('btn-download'),
    miniPlayer: document.getElementById('mini-player'),
    miniCover: document.getElementById('mini-cover'),
    miniTitle: document.getElementById('mini-title'),
    miniArtist: document.getElementById('mini-artist'),
    miniPlayBtn: document.getElementById('mini-play'),
    miniIconPlay: document.getElementById('mini-icon-play'),
    miniIconPause: document.getElementById('mini-icon-pause'),
  };

  // Preferencias guardadas localmente en el navegador (no en el servidor)
  const savedVolume = parseFloat(localStorage.getItem('dcpi_volume'));
  if (!isNaN(savedVolume)) {
    audio.volume = savedVolume;
    els.volume.value = savedVolume;
  }

  let queue = [];
  let queueIndex = -1;
  let currentTrack = null;
  let shuffle = false;
  let repeat = false; // repetir la canción actual
  let isSeeking = false;

  function fmtTime(sec) {
    if (!isFinite(sec) || sec < 0) return '0:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  async function playTrack(track, newQueue = null) {
    currentTrack = track;
    if (newQueue) {
      queue = newQueue;
      queueIndex = queue.findIndex((t) => t.id === track.id);
    }

    els.title.textContent = track.title;
    els.artist.textContent = track.artist;
    els.cover.src = track.cover || '';
    els.bg.style.backgroundImage = track.cover ? `url(${track.cover})` : 'none';
    els.timeTotal.textContent = fmtTime(track.duration || 0);

    els.miniTitle.textContent = track.title;
    els.miniArtist.textContent = track.artist;
    els.miniCover.src = track.cover || '';
    els.miniPlayer.classList.remove('hidden');

    audio.src = DcpiApi.streamUrl(track.id);
    audio.play().catch(() => {});
    setPlayingUI(true);

    DcpiLyrics.reset();
    DcpiApi.getLyrics(track.id).then(DcpiLyrics.load).catch(() => DcpiLyrics.reset());

    updateFavoriteUI();
    DcpiSearch?.setFeedSeed?.(track.id);
    {
      DcpiApi.addHistory({ track_id: track.id, title: track.title, artist: track.artist, cover_url: track.cover }).catch(() => {});
    }
  }

  function setPlayingUI(playing) {
    els.iconPlay.hidden = playing;
    els.iconPause.hidden = !playing;
    els.miniIconPlay.hidden = playing;
    els.miniIconPause.hidden = !playing;
  }

  function togglePlay() {
    if (audio.paused) {
      audio.play().catch(() => {});
      setPlayingUI(true);
    } else {
      audio.pause();
      setPlayingUI(false);
    }
    DcpiTelegram.hapticImpact('light');
  }

  function playNext() {
    if (!queue.length) return;
    if (shuffle) {
      queueIndex = Math.floor(Math.random() * queue.length);
    } else {
      queueIndex = (queueIndex + 1) % queue.length;
    }
    playTrack(queue[queueIndex]);
  }

  function playPrev() {
    if (!queue.length) return;
    if (audio.currentTime > 3) {
      audio.currentTime = 0;
      return;
    }
    queueIndex = (queueIndex - 1 + queue.length) % queue.length;
    playTrack(queue[queueIndex]);
  }

  audio.addEventListener('timeupdate', () => {
    if (isSeeking) return;
    const dur = audio.duration || currentTrack?.duration || 0;
    els.timeCurrent.textContent = fmtTime(audio.currentTime);
    if (dur) els.progress.value = (audio.currentTime / dur) * 100;
    DcpiLyrics.sync(audio.currentTime);
  });

  audio.addEventListener('loadedmetadata', () => {
    els.timeTotal.textContent = fmtTime(audio.duration);
  });

  audio.addEventListener('ended', () => {
    if (repeat) {
      audio.currentTime = 0;
      audio.play();
    } else {
      playNext();
    }
  });

  els.progress.addEventListener('input', () => { isSeeking = true; });
  els.progress.addEventListener('change', () => {
    const dur = audio.duration || currentTrack?.duration || 0;
    audio.currentTime = (els.progress.value / 100) * dur;
    isSeeking = false;
  });

  els.volume.addEventListener('input', () => {
    audio.volume = Number(els.volume.value);
    localStorage.setItem('dcpi_volume', els.volume.value);
  });

  els.miniPlayBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    togglePlay();
  });
  els.miniPlayer.addEventListener('click', () => {
    if (currentTrack) DcpiRouter.go('player');
  });

  els.playBtn.addEventListener('click', togglePlay);
  els.nextBtn.addEventListener('click', playNext);
  els.prevBtn.addEventListener('click', playPrev);

  els.shuffleBtn.addEventListener('click', () => {
    shuffle = !shuffle;
    els.shuffleBtn.classList.toggle('active', shuffle);
    DcpiTelegram.hapticImpact('light');
  });

  els.repeatBtn.addEventListener('click', () => {
    repeat = !repeat;
    els.repeatBtn.classList.toggle('active', repeat);
    DcpiTelegram.hapticImpact('light');
  });

  // ===== Favoritos =====
  let favoriteIds = new Set();

  async function loadFavoriteIds() {
    try {
      const { favorites } = await DcpiApi.getFavorites();
      favoriteIds = new Set(favorites.map((f) => f.track_id));
    } catch (_) {}
  }

  function updateFavoriteUI() {
    const isFav = currentTrack && favoriteIds.has(currentTrack.id);
    els.favBtn.style.color = isFav ? 'var(--accent)' : '';
  }

  els.favBtn.addEventListener('click', async () => {
    if (!currentTrack) return;
    const isFav = favoriteIds.has(currentTrack.id);
    try {
      if (isFav) {
        await DcpiApi.removeFavorite(currentTrack.id);
        favoriteIds.delete(currentTrack.id);
      } else {
        await DcpiApi.addFavorite({
          track_id: currentTrack.id, title: currentTrack.title, artist: currentTrack.artist,
          album: currentTrack.album, cover_url: currentTrack.cover, duration: currentTrack.duration,
        });
        favoriteIds.add(currentTrack.id);
      }
      updateFavoriteUI();
      DcpiTelegram.hapticImpact('medium');
    } catch (_) {}
  });

  // ===== Descargas =====
  const modal = document.getElementById('download-modal');
  const qualityOptions = document.getElementById('quality-options');
  const downloadLabel = document.getElementById('download-btn-label');
  let selectedQuality = 320;

  els.downloadBtn.addEventListener('click', async () => {
    if (!currentTrack) return;
    downloadLabel.textContent = 'Comprobando…';
    try {
      const { qualities } = await DcpiApi.getQualities(currentTrack.id);
      if (!qualities.length) {
        alert('El autor de esta canción no habilitó descargas.');
        return;
      }
      selectedQuality = qualities[qualities.length - 1];

      document.getElementById('format-options').innerHTML = '';
      qualityOptions.innerHTML = qualities.map((q) =>
        `<button class="chip ${q === selectedQuality ? 'selected' : ''}" data-quality="${q}">${q} kbps</button>`
      ).join('');

      modal.classList.remove('hidden');
    } catch (e) {
      if (e.message && e.message.includes('no tiene descarga habilitada')) {
        alert('El autor de esta canción no habilitó descargas.');
      } else {
        alert(e.message || 'No se pudo comprobar la disponibilidad de descarga. Intenta de nuevo.');
      }
    } finally {
      downloadLabel.textContent = 'Descargar';
    }
  });

  modal.addEventListener('click', (e) => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    if (chip.dataset.format) {
      selectedFormat = chip.dataset.format;
      formatOptions.querySelectorAll('.chip').forEach((c) => c.classList.toggle('selected', c === chip));
    }
    if (chip.dataset.quality) {
      selectedQuality = Number(chip.dataset.quality);
      qualityOptions.querySelectorAll('.chip').forEach((c) => c.classList.toggle('selected', c === chip));
    }
  });

  document.getElementById('cancel-download').addEventListener('click', () => modal.classList.add('hidden'));
  document.getElementById('confirm-download').addEventListener('click', () => {
    if (!currentTrack) return;
    window.location.href = DcpiApi.downloadUrl(currentTrack.id, selectedQuality);
    modal.classList.add('hidden');
  });

  loadFavoriteIds();

  return { playTrack, togglePlay, get currentTrack() { return currentTrack; } };
})();
