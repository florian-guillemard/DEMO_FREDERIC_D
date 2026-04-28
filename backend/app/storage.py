from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sqlite3


class TemperatureStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS temperature_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room TEXT NOT NULL,
                    value REAL NOT NULL,
                    measured_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def insert_temperature(self, room: str, value: float, measured_at: datetime | None = None) -> None:
        timestamp = (measured_at or datetime.utcnow()).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO temperature_history (room, value, measured_at) VALUES (?, ?, ?)",
                (room, value, timestamp),
            )
            conn.commit()

    def get_history(self, room: str, from_ts: datetime, to_ts: datetime) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT room, value, measured_at
                FROM temperature_history
                WHERE room = ?
                  AND measured_at >= ?
                  AND measured_at <= ?
                ORDER BY measured_at ASC
                """,
                (room, from_ts.isoformat(), to_ts.isoformat()),
            ).fetchall()
        return [dict(row) for row in rows]
