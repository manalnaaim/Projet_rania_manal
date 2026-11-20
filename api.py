"""API web FastAPI pour l'agent DBA."""
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from agent import DBAgent

DB_PATH = "demo.db"
THRESHOLD_MS = 50.0

# Instance partagée (SQLite + check_same_thread=False → OK)
_agent: DBAgent | None = None


def get_agent() -> DBAgent:
    global _agent
    if _agent is None:
        _agent = DBAgent(DB_PATH, slow_threshold_ms=THRESHOLD_MS)
    return _agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Au démarrage : crée la base si absente
    import os, sqlite3
    if not os.path.exists(DB_PATH):
        from main import create_demo_db
        create_demo_db()
    get_agent()
    yield
    if _agent:
        _agent.close()


app = FastAPI(title="DBA Agent Web", lifespan=lifespan)

# Templates + static
BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


# ----- Schémas Pydantic -----
class DiagnosticRequest(BaseModel):
    query: str


class NL2SQLRequest(BaseModel):
    question: str


# ----- Routes -----
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    try:
        return templates.TemplateResponse(request, "index.html")
    except Exception as e:
        print("[api] Erreur rendu index.html :", e)
        traceback.print_exc()
        return HTMLResponse(
            f"<h1>Erreur template</h1><pre>{e}</pre>"
            f"<p>Vérifie que templates/index.html existe.</p>",
            status_code=500,
        )

@app.get("/api/tables")
async def list_tables():
    agent = get_agent()
    tables = agent.db.list_tables()
    result = []
    for t in tables:
        info = agent.db.get_table_info(t)
        result.append({
            "name": t,
            "row_count": info.row_count,
            "columns": info.columns,
            "indexes": info.indexes,
        })
    return {"tables": result}


@app.post("/api/diagnostic")
async def diagnostic(req: DiagnosticRequest):
    agent = get_agent()
    try:
        result = agent.full_diagnostic(req.query)
        # Conversion JSON-safe des tuples/rows
        return JSONResponse(content={
            "report": result["report"],
            "verdict": result["benchmark"]["verdict"],
            "elapsed_ms": result["benchmark"]["elapsed_ms"],
            "is_slow": result["benchmark"]["is_slow"],
            "plan": result["benchmark"]["plan"],
            "full_scans_count": len(result["benchmark"]["full_scans"]),
            "issues": result["analysis"]["issues"],
            "index_suggestions": result["index_suggestions"],
            "llm_advice": result.get("llm_advice"),
        })
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/nl2sql")
async def nl2sql(req: NL2SQLRequest):
    agent = get_agent()
    try:
        return agent.nl2sql(req.question)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/health")
async def health():
    agent = get_agent()
    return {
        "status": "ok",
        "llm_available": agent.llm.is_available(),
        "tables": agent.db.list_tables(),
    }