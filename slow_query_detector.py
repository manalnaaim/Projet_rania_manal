"""Détecte les requêtes lentes via mesure réelle + plan d'exécution."""
from db_connector import DBConnector
from safety import assert_safe

class SlowQueryDetector:
    def __init__(self, db: DBConnector, threshold_ms: float = 100.0):
        self.db = db
        self.threshold_ms = threshold_ms

    def benchmark(self, query: str) -> dict:
        assert_safe(query)
        _, _, elapsed = self.db.execute(query)
        plan = self.db.explain_query_plan(query)
        slow = elapsed >= self.threshold_ms

        # Détection de scan complet dans le plan SQLite
        full_scans = [step for step in plan
                      if "SCAN" in str(step.get("detail", "")).upper()
                      and "USING INDEX" not in str(step.get("detail", "")).upper()]

        return {
            "query": query,
            "elapsed_ms": round(elapsed, 2),
            "threshold_ms": self.threshold_ms,
            "is_slow": slow,
            "plan": plan,
            "full_scans": full_scans,
            "verdict": self._verdict(slow, full_scans, elapsed),
        }

    def _verdict(self, slow, full_scans, elapsed) -> str:
        if slow and full_scans:
            return f"REQUÊTE LENTE ({elapsed:.2f} ms) avec {len(full_scans)} scan(s) complet(s)."
        if slow:
            return f"REQUÊTE LENTE ({elapsed:.2f} ms) sans scan complet — vérifier jointures/tri."
        if full_scans:
            return "Rapide sur petit volume mais scan complet présent — risque à grande échelle."
        return "Performance correcte."