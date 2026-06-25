import sqlite3
from pathlib import Path

from .config import get_settings


def _resolve_db_path() -> Path:
    settings = get_settings()
    p = Path(settings.ccg_dataset_db_path)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    return p


def _connect():
    db = _resolve_db_path()
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    return conn


def list_tables() -> list[str]:
    db = _resolve_db_path()
    if not db.exists():
        return []
    conn = _connect()
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def _resolve_data_table(conn: sqlite3.Connection) -> str | None:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    tables = [r[0] for r in rows]
    for name in ["func_pairs", "functions", "function_samples", "samples", "cases", "repos"]:
        if name in tables:
            return name
    return tables[0] if tables else None


def _get_table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(r[1]) for r in rows}


def _pick(cols: set[str], *names: str) -> str | None:
    for name in names:
        if name in cols:
            return name
    return None


def _normalize_platform(value: str | None) -> str:
    raw = str(value or "").strip()
    if "/" in raw:
        return raw.split("/")[-1].strip()
    return raw


def _normalize_row(r: dict) -> dict:
    patterns_raw = r.get("platform_patterns") or r.get("arm_patterns") or ""
    patterns = [p for p in str(patterns_raw).split(",") if p]
    has_gt = r.get("has_gt")
    if has_gt is None:
        has_gt = r.get("has_riscv64")

    return {
        "id": r.get("id"),
        "repo": r.get("repo") or r.get("full_name") or "",
        "func_name": r.get("func_name") or r.get("name") or r.get("path") or "",
        "source_file": r.get("source_file") or r.get("arm64_file") or "",
        "arm64_file": r.get("source_file") or r.get("arm64_file") or "",
        "migration_type": r.get("migration_type") or "unknown",
        "complexity": r.get("complexity") or "Unknown",
        "split": r.get("split") or r.get("eval_type") or "",
        "has_gt": bool(has_gt) if has_gt is not None else False,
        "source_platform": _normalize_platform(r.get("source_platform")),
        "target_platform": _normalize_platform(r.get("target_platform")),
        "risk_level": r.get("risk_level") or "",
        "platform_patterns": patterns,
        "arm_patterns": patterns,
        "source_code": r.get("source_code") or r.get("arm64_code") or "",
        "arm64_code": r.get("source_code") or r.get("arm64_code") or "",
        "generic_code": r.get("generic_code") or "",
        "target_code": r.get("target_code") or r.get("riscv64_code") or "",
        "riscv64_code": r.get("target_code") or r.get("riscv64_code") or "",
    }


def _base_where(cols: set[str], table_alias: str = "") -> tuple[list[str], list]:
    prefix = f"{table_alias}." if table_alias else ""
    where = ["1=1"]
    params: list = []
    quality_col = _pick(cols, "quality")
    if quality_col:
        where.append(f"{prefix}{quality_col} = ?")
        params.append("ok")
    return where, params


def get_stats(migration_type: str | None = None) -> dict:
    db = _resolve_db_path()
    if not db.exists():
        return {"total": 0, "has_gt": 0, "by_complexity": {}, "by_repo": []}

    conn = _connect()
    try:
        table = _resolve_data_table(conn)
        if not table:
            return {"total": 0, "has_gt": 0, "by_complexity": {}, "by_repo": []}

        cols = _get_table_columns(conn, table)
        where, args = _base_where(cols)
        migration_col = _pick(cols, "migration_type")
        if migration_type and migration_col:
            where.append(f"{migration_col} = ?")
            args.append(migration_type)
        where_sql = " AND ".join(where)

        total = int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where_sql}", args).fetchone()[0] or 0)

        has_gt = 0
        has_gt_col = _pick(cols, "has_gt", "has_riscv64")
        if has_gt_col:
            has_gt = int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where_sql} AND {has_gt_col}=1", args).fetchone()[0] or 0)

        by_complexity = {}
        if "complexity" in cols:
            rows = conn.execute(f"SELECT complexity, COUNT(*) FROM {table} WHERE {where_sql} GROUP BY complexity", args).fetchall()
            by_complexity = {str(r[0] or "Unknown"): int(r[1]) for r in rows}

        by_repo = []
        repo_col = _pick(cols, "repo", "full_name")
        if repo_col:
            rows = conn.execute(
                f"SELECT {repo_col}, COUNT(*) c FROM {table} WHERE {where_sql} GROUP BY {repo_col} ORDER BY c DESC LIMIT 100",
                args,
            ).fetchall()
            by_repo = [{"repo": str(r[0] or ""), "count": int(r[1])} for r in rows]

        def grouped(col_name: str | None) -> dict:
            if not col_name:
                return {}
            rows = conn.execute(f"SELECT {col_name}, COUNT(*) FROM {table} WHERE {where_sql} GROUP BY {col_name}", args).fetchall()
            return {str(r[0] or ""): int(r[1]) for r in rows}

        return {
            "total": total,
            "has_gt": has_gt,
            "by_complexity": by_complexity,
            "by_repo": by_repo,
            "by_migration_type": grouped(migration_col),
            "by_source_platform": grouped(_pick(cols, "source_platform")),
            "by_target_platform": grouped(_pick(cols, "target_platform")),
            "by_split": grouped(_pick(cols, "split", "eval_type")),
            "by_risk_level": grouped(_pick(cols, "risk_level")),
        }
    finally:
        conn.close()


def list_functions(
    page: int = 1,
    page_size: int = 20,
    migration_type: str | None = None,
    repo: str | None = None,
    complexity: str | None = None,
    split: str | None = None,
    has_gt: bool | None = None,
    source_platform: str | None = None,
    target_platform: str | None = None,
    risk_level: str | None = None,
) -> dict:
    db = _resolve_db_path()
    if not db.exists():
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    conn = _connect()
    try:
        table = _resolve_data_table(conn)
        if not table:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

        cols = _get_table_columns(conn, table)
        where, args = _base_where(cols)

        def add_eq(col: str | None, value):
            if col and value not in (None, ""):
                where.append(f"{col} = ?")
                args.append(value)

        add_eq(_pick(cols, "migration_type"), migration_type)
        add_eq(_pick(cols, "repo", "full_name"), repo)
        add_eq(_pick(cols, "complexity"), complexity)
        add_eq(_pick(cols, "split", "eval_type"), split)
        add_eq(_pick(cols, "source_platform"), source_platform)
        add_eq(_pick(cols, "target_platform"), target_platform)
        add_eq(_pick(cols, "risk_level"), risk_level)

        has_gt_col = _pick(cols, "has_gt", "has_riscv64")
        if has_gt is not None and has_gt_col:
            where.append(f"{has_gt_col} = ?")
            args.append(1 if has_gt else 0)

        where_sql = " AND ".join(where)
        total = int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where_sql}", args).fetchone()[0] or 0)

        offset = max(0, (page - 1) * page_size)
        order_by = "id DESC" if "id" in cols else "rowid DESC"
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE {where_sql} ORDER BY {order_by} LIMIT ? OFFSET ?",
            [*args, page_size, offset],
        ).fetchall()
        items = [_normalize_row(dict(row)) for row in rows]
        return {"items": items, "total": total, "page": page, "page_size": page_size}
    finally:
        conn.close()


def get_function_by_id(function_id: int) -> dict | None:
    db = _resolve_db_path()
    if not db.exists():
        return None

    conn = _connect()
    try:
        table = _resolve_data_table(conn)
        if not table:
            return None
        cols = _get_table_columns(conn, table)
        id_col = "id" if "id" in cols else "rowid"
        row = conn.execute(f"SELECT * FROM {table} WHERE {id_col} = ? LIMIT 1", [function_id]).fetchone()
        return _normalize_row(dict(row)) if row else None
    finally:
        conn.close()


def create_function(payload: dict) -> int:
    conn = _connect()
    try:
        table = _resolve_data_table(conn)
        if not table:
            raise RuntimeError("No writable data table found")
        cols = _get_table_columns(conn, table)
        fields = [
            "repo", "func_name", "source_code", "generic_code", "target_code", "migration_type",
            "complexity", "source_platform", "target_platform", "has_gt", "split", "risk_level",
        ]
        alias = {"source_code": ["source_code", "arm64_code"], "target_code": ["target_code", "riscv64_code"], "split": ["split", "eval_type"], "has_gt": ["has_gt", "has_riscv64"]}
        writable: list[tuple[str, str]] = []
        for field in fields:
            column = _pick(cols, *alias.get(field, [field]))
            if column:
                writable.append((field, column))
        if not writable:
            raise RuntimeError("Current data table does not support writing function fields")

        placeholders = ",".join(["?"] * len(writable))
        columns = ",".join([column for _, column in writable])
        values = []
        for field, _ in writable:
            value = payload.get(field)
            if field == "has_gt":
                value = 1 if value else 0
            values.append(value)
        cur = conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values)
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def update_function(function_id: int, payload: dict) -> bool:
    conn = _connect()
    try:
        table = _resolve_data_table(conn)
        if not table:
            return False
        cols = _get_table_columns(conn, table)
        alias = {"source_code": ["source_code", "arm64_code"], "target_code": ["target_code", "riscv64_code"], "split": ["split", "eval_type"], "has_gt": ["has_gt", "has_riscv64"]}
        fields = [
            "repo", "func_name", "source_code", "generic_code", "target_code", "migration_type",
            "complexity", "source_platform", "target_platform", "has_gt", "split", "risk_level",
        ]
        sets: list[str] = []
        values: list = []
        for field in fields:
            if field not in payload:
                continue
            column = _pick(cols, *alias.get(field, [field]))
            if not column:
                continue
            value = payload.get(field)
            if field == "has_gt":
                value = 1 if value else 0
            sets.append(f"{column} = ?")
            values.append(value)
        if not sets:
            return False
        id_col = "id" if "id" in cols else "rowid"
        values.append(function_id)
        cur = conn.execute(f"UPDATE {table} SET {','.join(sets)} WHERE {id_col} = ?", values)
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_function(function_id: int) -> bool:
    conn = _connect()
    try:
        table = _resolve_data_table(conn)
        if not table:
            return False
        cols = _get_table_columns(conn, table)
        id_col = "id" if "id" in cols else "rowid"
        cur = conn.execute(f"DELETE FROM {table} WHERE {id_col} = ?", [function_id])
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def list_repos() -> list[dict]:
    db = _resolve_db_path()
    if not db.exists():
        return []

    conn = _connect()
    try:
        table = _resolve_data_table(conn)
        if not table:
            return []
        cols = _get_table_columns(conn, table)
        repo_col = _pick(cols, "repo", "full_name")
        if not repo_col:
            return []
        where, args = _base_where(cols)
        rows = conn.execute(
            f"SELECT {repo_col}, COUNT(*) c FROM {table} WHERE {' AND '.join(where)} GROUP BY {repo_col} ORDER BY c DESC",
            args,
        ).fetchall()
        return [{"repo": str(r[0] or ""), "count": int(r[1])} for r in rows]
    finally:
        conn.close()
