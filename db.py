"""Capa de datos (SQLite). Un solo archivo local: planeatambo.db"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "planeatambo.db"
GRADOS = [f"{i}°" for i in range(1, 10)]


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS materials(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT, tipo TEXT, grado TEXT, periodo TEXT, tema TEXT,
                params TEXT, content TEXT,
                estado TEXT DEFAULT 'Pendiente de revisión',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS curriculum(
                grado TEXT PRIMARY KEY,
                competencias TEXT DEFAULT '',
                p1 TEXT DEFAULT '', p2 TEXT DEFAULT '', p3 TEXT DEFAULT '', p4 TEXT DEFAULT '',
                ejemplos TEXT DEFAULT ''
            );
            """
        )
        for g in GRADOS:
            c.execute("INSERT OR IGNORE INTO curriculum(grado) VALUES (?)", (g,))


# ---------- Materiales ----------
def create_material(title, tipo, grado, periodo, tema, params, content):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO materials(title,tipo,grado,periodo,tema,params,content) VALUES (?,?,?,?,?,?,?)",
            (title, tipo, grado, periodo, tema, json.dumps(params), json.dumps(content)),
        )
        return cur.lastrowid


def update_material(mid, content=None, estado=None):
    with _conn() as c:
        if content is not None:
            c.execute("UPDATE materials SET content=?, estado='Pendiente de revisión' WHERE id=?",
                      (json.dumps(content), mid))
        if estado is not None:
            c.execute("UPDATE materials SET estado=? WHERE id=?", (estado, mid))


def get_material(mid):
    with _conn() as c:
        r = c.execute("SELECT * FROM materials WHERE id=?", (mid,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["params"] = json.loads(d["params"] or "{}")
    d["content"] = json.loads(d["content"] or "{}")
    return d


def list_materials(search="", tipo=None, grado=None, estado=None, limit=None):
    q, args = "SELECT * FROM materials WHERE 1=1", []
    if search:
        q += " AND (title LIKE ? OR tema LIKE ?)"
        args += [f"%{search}%"] * 2
    for col, val in (("tipo", tipo), ("grado", grado), ("estado", estado)):
        if val:
            q += f" AND {col}=?"
            args.append(val)
    q += " ORDER BY id DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    with _conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


def duplicate_material(mid):
    m = get_material(mid)
    return create_material(f"{m['title']} (copia)", m["tipo"], m["grado"], m["periodo"],
                           m["tema"], m["params"], m["content"])


# ---------- Contexto curricular ----------
def _lines(t):
    return [x.strip() for x in (t or "").splitlines() if x.strip()]


def get_curriculum(grado):
    with _conn() as c:
        r = c.execute("SELECT * FROM curriculum WHERE grado=?", (grado,)).fetchone()
    return {
        "competencias": _lines(r["competencias"]),
        "temas": {str(i): _lines(r[f"p{i}"]) for i in range(1, 5)},
        "ejemplos": _lines(r["ejemplos"]),
    }


def save_curriculum(grado, competencias, p1, p2, p3, p4, ejemplos):
    with _conn() as c:
        c.execute(
            "UPDATE curriculum SET competencias=?,p1=?,p2=?,p3=?,p4=?,ejemplos=? WHERE grado=?",
            (competencias, p1, p2, p3, p4, ejemplos, grado),
        )


def get_curriculum_raw(grado):
    with _conn() as c:
        return dict(c.execute("SELECT * FROM curriculum WHERE grado=?", (grado,)).fetchone())
