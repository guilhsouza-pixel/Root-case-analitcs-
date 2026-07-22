from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd


SCHEMA = """
CREATE TABLE IF NOT EXISTS mappings (
  name TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ishikawa (
  id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT, problem TEXT, category TEXT,
  cause TEXT, subcause TEXT, status TEXT, evidence TEXT, owner TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS why5 (
  id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT, problem TEXT, chain TEXT,
  root_cause TEXT, evidence TEXT, validation TEXT, action TEXT, owner TEXT, due_date TEXT, status TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS fmea (
  id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT, process TEXT, step TEXT, failure_mode TEXT,
  effect TEXT, potential_cause TEXT, current_control TEXT, severity INTEGER, occurrence INTEGER,
  detection INTEGER, recommended_action TEXT, owner TEXT, due_date TEXT,
  final_severity INTEGER, final_occurrence INTEGER, final_detection INTEGER, status TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT, what_action TEXT, why_action TEXT, where_action TEXT,
  when_date TEXT, who TEXT, how_action TEXT, expected_cost REAL, actual_cost REAL, status TEXT,
  progress REAL, evidence TEXT, expected_result TEXT, actual_result TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS dmaic (
  id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT, phase TEXT, item TEXT, content TEXT,
  completed INTEGER DEFAULT 0, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    def __init__(self, path: str | Path = "root_cause_analytics.db") -> None:
        self.path = str(path)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def execute(self, sql: str, params: tuple = ()) -> None:
        with self.connect() as conn:
            conn.execute(sql, params)
            conn.commit()

    def dataframe(self, table: str, project: str | None = None) -> pd.DataFrame:
        allowed = {"ishikawa", "why5", "fmea", "actions", "dmaic", "mappings"}
        if table not in allowed:
            raise ValueError("Tabela inválida")
        with self.connect() as conn:
            if project and table != "mappings":
                return pd.read_sql_query(f"SELECT * FROM {table} WHERE project = ? ORDER BY id DESC", conn, params=(project,))
            return pd.read_sql_query(f"SELECT * FROM {table} ORDER BY rowid DESC", conn)

    def save_mapping(self, name: str, mapping: dict[str, str | None]) -> None:
        self.execute(
            "INSERT INTO mappings(name, payload) VALUES(?, ?) ON CONFLICT(name) DO UPDATE SET payload=excluded.payload, created_at=CURRENT_TIMESTAMP",
            (name, json.dumps(mapping, ensure_ascii=False)),
        )

    def load_mappings(self) -> dict[str, dict[str, str | None]]:
        frame = self.dataframe("mappings")
        return {row["name"]: json.loads(row["payload"]) for _, row in frame.iterrows()}

