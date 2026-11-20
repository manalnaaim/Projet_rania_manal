"""Connexion à la base et récupération des métadonnées."""
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any

@dataclass
class TableInfo:
    name: str
    columns: list[dict] = field(default_factory=list)
    indexes: list[dict] = field(default_factory=list)
    row_count: int = 0

class DBConnector:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    # ---------- introspection ----------
    def list_tables(self) -> list[str]:
        cur = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        return [r[0] for r in cur.fetchall()]

    def get_table_info(self, table: str) -> TableInfo:
        info = TableInfo(name=table)
        # colonnes
        cur = self.conn.execute(f"PRAGMA table_info({table})")
        for row in cur.fetchall():
            info.columns.append({
                "name": row["name"], "type": row["type"],
                "notnull": bool(row["notnull"]), "pk": bool(row["pk"]),
            })
        # index
        cur = self.conn.execute(f"PRAGMA index_list({table})")
        for idx in cur.fetchall():
            idx_name = idx["name"]
            cols_cur = self.conn.execute(f"PRAGMA index_info({idx_name})")
            cols = [c["name"] for c in cols_cur.fetchall()]
            info.indexes.append({"name": idx_name, "columns": cols, "unique": bool(idx["unique"])})
        # nombre de lignes
        try:
            info.row_count = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            info.row_count = -1
        return info

    def get_schema_summary(self) -> str:
        lines = []
        for t in self.list_tables():
            ti = self.get_table_info(t)
            cols = ", ".join(f"{c['name']} {c['type']}" for c in ti.columns)
            lines.append(f"- {t} ({ti.row_count} lignes) : {cols}")
            for idx in ti.indexes:
                lines.append(f"    index {idx['name']} sur ({', '.join(idx['columns'])})")
        return "\n".join(lines)

    # ---------- exécution ----------
    def explain_query_plan(self, query: str) -> list[dict]:
        cur = self.conn.execute(f"EXPLAIN QUERY PLAN {query}")
        return [dict(r) for r in cur.fetchall()]

    def execute(self, query: str) -> tuple[list[str], list[tuple], float]:
        start = time.perf_counter()
        cur = self.conn.execute(query)
        rows = cur.fetchall()
        elapsed = (time.perf_counter() - start) * 1000  # ms
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, [tuple(r) for r in rows], elapsed

    def close(self):
        self.conn.close()