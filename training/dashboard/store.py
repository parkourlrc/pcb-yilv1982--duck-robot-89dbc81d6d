from __future__ import annotations

import json
import sqlite3
import threading
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2), encoding='utf-8')
    for attempt in range(12):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 11:
                raise
            time.sleep(.01 * (attempt + 1))


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return default


def read_jsonl(path):
    records, warnings = [], []
    try:
        raw = Path(path).read_bytes()
    except OSError:
        return records, warnings
    lines = raw.splitlines(keepends=True)
    for number, line in enumerate(lines, 1):
        try:
            records.append(json.loads(line))
        except (ValueError, UnicodeDecodeError):
            if number == len(lines) and not line.endswith(b'\n'):
                continue
            warnings.append(f'{Path(path).name}:{number}: invalid JSON')
    return records, warnings


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS objects(kind TEXT, id TEXT, data TEXT NOT NULL, PRIMARY KEY(kind,id));
            CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, kind TEXT NOT NULL, object_id TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, data TEXT NOT NULL);
        ''')
        self.db.commit()

    def put(self, kind, identifier, data):
        with self.lock:
            self.db.execute('INSERT OR REPLACE INTO objects VALUES(?,?,?)', (kind, identifier, json.dumps(data, allow_nan=False)))
            self.db.commit()
        return data

    def get(self, kind, identifier):
        with self.lock:
            row = self.db.execute('SELECT data FROM objects WHERE kind=? AND id=?', (kind, identifier)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self, kind):
        with self.lock:
            rows = self.db.execute('SELECT data FROM objects WHERE kind=? ORDER BY rowid DESC', (kind,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def request(self, identifier):
        with self.lock:
            row = self.db.execute('SELECT fingerprint,kind,object_id FROM requests WHERE id=?', (identifier,)).fetchone()
        return row

    def remember(self, identifier, fingerprint, kind, object_id):
        with self.lock:
            self.db.execute('INSERT INTO requests VALUES(?,?,?,?)', (identifier, fingerprint, kind, object_id))
            self.db.commit()

    def event(self, run_id, event):
        event = dict(event)
        if 'seq' in event:
            event['source_seq'] = event.pop('seq')
        event = {'time_utc': event.get('utc', utcnow()), 'level': 'info', 'type': event.get('phase', 'event'), 'message': event.get('error', event.get('phase', '')), **event}
        with self.lock:
            cursor = self.db.execute('INSERT INTO events(run_id,data) VALUES(?,?)', (run_id, json.dumps(event)))
            self.db.commit()
            return {**event, 'seq': cursor.lastrowid}

    def events(self, run_id, after=0, limit=200):
        with self.lock:
            rows = self.db.execute('SELECT seq,data FROM events WHERE run_id=? AND seq>? ORDER BY seq LIMIT ?', (run_id, after, limit)).fetchall()
        return [{**json.loads(row[1]), 'seq': row[0]} for row in rows]
