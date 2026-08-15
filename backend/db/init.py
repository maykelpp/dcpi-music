import os
import sqlite3
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "./db/dcpi.sqlite")
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


_conn = get_conn()
_conn.executescript(
    """
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT NOT NULL,
        track_id TEXT NOT NULL,
        title TEXT NOT NULL,
        artist TEXT NOT NULL,
        cover_url TEXT,
        played_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT NOT NULL,
        track_id TEXT NOT NULL,
        title TEXT NOT NULL,
        artist TEXT NOT NULL,
        album TEXT,
        cover_url TEXT,
        duration INTEGER,
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(telegram_id, track_id)
    );

    CREATE INDEX IF NOT EXISTS idx_history_user ON history(telegram_id, played_at DESC);
    CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(telegram_id);
    """
)
_conn.commit()


def db():
    return _conn
