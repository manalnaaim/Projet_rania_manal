"""Garde-fous : garantit qu'aucune requête destructive n'est exécutée."""
import re
import unicodedata

FORBIDDEN_PATTERNS = [
    r"\bDROP\s+TABLE\b", r"\bDROP\s+DATABASE\b", r"\bTRUNCATE\b",
    r"\bDELETE\s+FROM\b(?!.*\bWHERE\b)", r"\bALTER\s+TABLE\b.*\bDROP\b",
    r"\bUPDATE\b(?!.*\bWHERE\b)", r"\bINSERT\s+INTO\b", r"\bCREATE\s+USER\b",
    r"\bGRANT\b", r"\bREVOKE\b",
]


def _normalize(query: str) -> str:
    if query is None:
        return ""
    q = str(query)
    q = "".join(ch for ch in q if unicodedata.category(ch)[0] != "C")
    q = unicodedata.normalize("NFKC", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def is_safe(query: str) -> tuple[bool, str]:
    q = _normalize(query)
    print(f"[safety] longueur brute={len(str(query))} | normalisee={q[:80]!r}")
    if not q:
        return False, "Requete vide apres nettoyage."
    upper = q.upper()
    if not (upper.startswith("SELECT")
            or upper.startswith("WITH")
            or upper.startswith("EXPLAIN")):
        return False, f"Seules les requetes SELECT/WITH/EXPLAIN sont autorisees. Recu : {q[:40]!r}"
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, upper, re.IGNORECASE):
            return False, f"Motif interdit detecte : {pattern}"
    return True, "OK"


def assert_safe(query: str) -> None:
    safe, reason = is_safe(query)
    if not safe:
        raise PermissionError(f"Requete refusee : {reason}")