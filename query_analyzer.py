"""Analyse statique et dynamique des requêtes SQL."""
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Comparison
from sqlparse.tokens import Keyword, DML
from db_connector import DBConnector

class QueryAnalyzer:
    def __init__(self, db: DBConnector):
        self.db = db

    def analyze(self, query: str) -> dict:
        parsed = sqlparse.parse(query)
        if not parsed:
            return {"error": "Requête vide ou invalide"}
        stmt = parsed[0]

        result = {
            "query": query,
            "query_type": stmt.get_type(),          # SELECT, INSERT...
            "tables": self._extract_tables(stmt),
            "columns": self._extract_select_columns(stmt),
            "has_where": self._has_where(stmt),
            "joins": self._count_joins(stmt),
            "has_order_by": "ORDER BY" in query.upper(),
            "has_group_by": "GROUP BY" in query.upper(),
            "has_wildcard": "SELECT *" in query.upper().replace(" ", " "),
            "issues": [],
        }
        result["issues"] = self._detect_static_issues(result)
        return result

    # ---------- helpers ----------
    def _extract_tables(self, stmt) -> list[str]:
        tables = []
        from_seen = False
        for token in stmt.tokens:
            if from_seen:
                if isinstance(token, IdentifierList):
                    for ident in token.get_identifiers():
                        tables.append(ident.get_real_name() or str(ident))
                elif isinstance(token, Identifier):
                    tables.append(token.get_real_name() or str(token))
                elif token.ttype is Keyword:
                    from_seen = False
            if token.ttype is Keyword and token.value.upper() == "FROM":
                from_seen = True
        return [t for t in tables if t]

    def _extract_select_columns(self, stmt) -> list[str]:
        cols = []
        select_seen = False
        for token in stmt.tokens:
            if select_seen:
                if isinstance(token, IdentifierList):
                    cols = [str(i) for i in token.get_identifiers()]
                    break
                elif isinstance(token, Identifier):
                    cols = [str(token)]
                    break
            if token.ttype is DML and token.value.upper() == "SELECT":
                select_seen = True
        return cols

    def _has_where(self, stmt) -> bool:
        return any(isinstance(t, Where) for t in stmt.tokens)

    def _count_joins(self, stmt) -> int:
        count = 0
        for token in stmt.flatten():
            if token.ttype is Keyword and "JOIN" in token.value.upper():
                count += 1
        return count

    def _detect_static_issues(self, info: dict) -> list[str]:
        issues = []
        if info["has_wildcard"]:
            issues.append("SELECT * détecté : sélectionner uniquement les colonnes nécessaires.")
        if not info["has_where"] and info["query_type"] == "SELECT":
            issues.append("Aucune clause WHERE : risque de scan complet de table.")
        if info["joins"] >= 3:
            issues.append(f"{info['joins']} jointures : vérifier l'ordre et les index de jointure.")
        if info["has_order_by"] and not info["has_where"]:
            issues.append("ORDER BY sans filtre : tri sur toutes les lignes.")
        return issues