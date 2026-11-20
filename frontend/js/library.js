const DcpiLibrary = (() => {
  const DB_NAME = 'dcpi-music-library-v1';
  const STORE = 'tracks';
  let dbPromise;

  function open() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => {
        if (!req.result.objectStoreNames.contains(STORE)) {
          req.result.createObjectStore(STORE, { keyPath: 'id' });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => { dbPromise = null; reject(req.error); };
    });
    return dbPromise;
  }

  async function put(track, blob) {
    const db = await open();
    const item = {
      id: track.id, title: track.title, artist: track.artist,
      album: track.album || '', cover: track.cover || '',
      duration: track.duration || 0, source: track.source,
      blob, size: blob.size, mime: blob.type || 'audio/mpeg',
      savedAt: new Date().toISOString()
    };
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).put(item);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
    return item;
  }

  async function all() {
    const db = await open();
    return new Promise((resolve, reject) => {
      const req = db.transaction(STORE, 'readonly').objectStore(STORE).getAll();
      req.onsuccess = () => resolve((req.result || []).sort((a, b) => b.savedAt.localeCompare(a.savedAt)));
      req.onerror = () => reject(req.error);
    });
  }

  async function remove(id) {
    const db = await open();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).delete(id);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }

  function playable(item) {
    return { ...item, localUrl: URL.createObjectURL(item.blob), isLocal: true };
  }

  return { put, all, remove, playable };
})();