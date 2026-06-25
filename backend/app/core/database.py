"""
数据库访问层（兼容 arch/os 双任务）
"""
import sqlite3
from pathlib import Path
from typing import Optional, Any

from app.config import get_settings


def _resolve_db_path() -> Path:
    settings = get_settings()
    db_path = Path(settings.ccg_dataset_db_path)
    if db_path.is_absolute():
        return db_path
    return Path(__file__).resolve().parents[2] / db_path


def get_db() -> sqlite3.Connection:
    db_path = _resolve_db_path()
    if db_path.exists():
        return sqlite3.connect(str(db_path), check_same_thread=False)
    _backend_dir = Path(__file__).resolve().parents[2]
    candidates = [
        _backend_dir / "dataset.db",
        Path("dataset.db"),
    ]
    for p in candidates:
        if p.exists():
            return sqlite3.connect(str(p), check_same_thread=False)
    raise FileNotFoundError(f"找不到 dataset.db，已搜索路径：{[str(p) for p in candidates]}")


def _get_columns(conn: sqlite3.Connection, table: str = "func_pairs") -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def _pick(cols: set[str], *names: str) -> Optional[str]:
    for n in names:
        if n in cols:
            return n
    return None


def _ensure_planning_columns(conn: sqlite3.Connection) -> None:
    cols = _get_columns(conn)
    alters = [
        ("risk_level", "TEXT"),
        ("fr_count", "INTEGER DEFAULT 0"),
        ("nfr_count", "INTEGER DEFAULT 0"),
        ("interface_constraint_count", "INTEGER DEFAULT 0"),
        ("estimated_story_points", "INTEGER DEFAULT 0"),
        ("suggested_test_cases", "INTEGER DEFAULT 0"),
        ("last_rga_avg_score", "REAL DEFAULT 0"),
        ("last_rga_updated_at", "TEXT DEFAULT ''"),
        ("last_rga_status", "TEXT DEFAULT ''"),
        ("rga_error_msg", "TEXT DEFAULT ''"),
        ("rga_retry_count", "INTEGER DEFAULT 0"),
    ]
    for name, ddl in alters:
        if name not in cols:
            conn.execute(f"ALTER TABLE func_pairs ADD COLUMN {name} {ddl}")
    conn.commit()


def _to_nonneg_int(v: Any) -> int:
    if isinstance(v, bool):
        return 0
    try:
        n = int(v)
    except (TypeError, ValueError):
        return 0
    return n if n >= 0 else 0


def upsert_rga_planning(func_id: int, rga_quality: dict) -> bool:
    if not isinstance(rga_quality, dict):
        return False

    planning = rga_quality.get("requirement_planning") or {}
    test_plan = rga_quality.get("test_plan") or {}
    avg_score = rga_quality.get("avg_score", 0)

    risk = planning.get("risk_level", "Medium")
    if risk not in {"Low", "Medium", "High"}:
        risk = "Medium"

    conn = get_db()
    try:
        _ensure_planning_columns(conn)
        cur = conn.execute("SELECT 1 FROM func_pairs WHERE id=?", (func_id,))
        if not cur.fetchone():
            return False

        conn.execute(
            """
            UPDATE func_pairs
            SET risk_level=?,
                fr_count=?,
                nfr_count=?,
                interface_constraint_count=?,
                estimated_story_points=?,
                suggested_test_cases=?,
                last_rga_avg_score=?,
                last_rga_updated_at=datetime('now'),
                last_rga_status='ok',
                rga_error_msg=''
            WHERE id=?
            """,
            (
                risk,
                _to_nonneg_int(planning.get("fr_count")),
                _to_nonneg_int(planning.get("nfr_count")),
                _to_nonneg_int(planning.get("interface_constraint_count")),
                _to_nonneg_int(planning.get("estimated_story_points")),
                _to_nonneg_int(test_plan.get("suggested_test_cases")),
                float(avg_score or 0),
                func_id,
            ),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def mark_rga_planning_failed(func_id: int, error_msg: str, increase_retry: bool = True) -> bool:
    conn = get_db()
    try:
        _ensure_planning_columns(conn)
        cur = conn.execute("SELECT rga_retry_count FROM func_pairs WHERE id=?", (func_id,))
        row = cur.fetchone()
        if not row:
            return False
        retry_count = _to_nonneg_int(row[0]) + (1 if increase_retry else 0)
        conn.execute(
            """
            UPDATE func_pairs
            SET last_rga_status='failed',
                rga_error_msg=?,
                rga_retry_count=?,
                last_rga_updated_at=datetime('now')
            WHERE id=?
            """,
            ((error_msg or "").strip()[:500], retry_count, func_id),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_backfill_candidates(limit: int = 50, migration_type: Optional[str] = "arch", only_missing: bool = True, max_retry: int = 2) -> list[dict]:
    conn = get_db()
    try:
        _ensure_planning_columns(conn)
        cols = _get_columns(conn)

        quality_col = _pick(cols, "quality")
        migration_col = _pick(cols, "migration_type")
        source_code_col = _pick(cols, "source_code", "arm64_code")
        generic_code_col = _pick(cols, "generic_code")
        target_code_col = _pick(cols, "target_code", "riscv64_code")

        where = ["1=1"]
        params: list[Any] = []

        if quality_col:
            where.append(f"{quality_col}='ok'")
        if migration_type and migration_col:
            where.append(f"{migration_col}=?")
            params.append(migration_type)

        if only_missing:
            where.append("(risk_level IS NULL OR risk_level='' OR last_rga_status!='ok')")

        where.append("COALESCE(rga_retry_count, 0) <= ?")
        params.append(max_retry)

        rows = conn.execute(
            f"""
            SELECT id,
                   {source_code_col or 'NULL'} as source_code,
                   {generic_code_col or 'NULL'} as generic_code,
                   {target_code_col or 'NULL'} as target_code,
                   {migration_col or "'arch'"} as migration_type,
                   source_platform,
                   target_platform,
                   COALESCE(rga_retry_count, 0) as rga_retry_count
            FROM func_pairs
            WHERE {' AND '.join(where)}
            ORDER BY id DESC
            LIMIT ?
            """,
            params + [limit],
        ).fetchall()

        return [
            {
                "id": r[0],
                "source_code": r[1] or "",
                "generic_code": r[2] or "",
                "ground_truth": r[3] or "",
                "migration_type": r[4] or "arch",
                "source_platform": r[5],
                "target_platform": r[6],
                "rga_retry_count": _to_nonneg_int(r[7]),
            }
            for r in rows
            if (r[1] or "").strip()
        ]
    finally:
        conn.close()


def get_backfill_status() -> dict:
    conn = get_db()
    try:
        _ensure_planning_columns(conn)

        total = conn.execute("SELECT COUNT(*) FROM func_pairs").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM func_pairs WHERE last_rga_status='ok'").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM func_pairs WHERE last_rga_status='failed'").fetchone()[0]
        pending = max(total - completed, 0)

        failed_rows = conn.execute(
            """
            SELECT id, rga_error_msg, rga_retry_count, last_rga_updated_at
            FROM func_pairs
            WHERE last_rga_status='failed'
            ORDER BY last_rga_updated_at DESC, id DESC
            LIMIT 20
            """
        ).fetchall()

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "recent_failures": [
                {
                    "id": r[0],
                    "error": r[1],
                    "retry_count": _to_nonneg_int(r[2]),
                    "updated_at": r[3],
                }
                for r in failed_rows
            ],
        }
    finally:
        conn.close()


def get_fewshot_examples(platform_patterns: list[str], migration_type: Optional[str] = None, n: int = 2) -> str:
    try:
        conn = get_db()
        cols = _get_columns(conn)

        quality_col = _pick(cols, "quality")
        has_gt_col = _pick(cols, "has_gt", "has_riscv64")
        split_col = _pick(cols, "split", "eval_type")
        patterns_col = _pick(cols, "platform_patterns", "arm_patterns")
        src_code_col = _pick(cols, "source_code", "arm64_code")
        tgt_code_col = _pick(cols, "target_code", "riscv64_code")
        migration_col = _pick(cols, "migration_type")

        where_base = ["1=1"]
        params_base = []
        if quality_col:
            where_base.append(f"{quality_col}='ok'")
        if has_gt_col:
            where_base.append(f"{has_gt_col}=1")
        if split_col:
            where_base.append(f"{split_col} IN ('eval', 'full', 'gt_identical')")
        if migration_type and migration_col:
            where_base.append(f"{migration_col}=?")
            params_base.append(migration_type)

        examples = []
        for pattern in platform_patterns or []:
            if len(examples) >= n:
                break
            where = where_base.copy()
            params = params_base.copy()
            if patterns_col:
                where.append(f"{patterns_col} LIKE ?")
                params.append(f"%{pattern}%")
            rows = conn.execute(
                f"SELECT {src_code_col or 'NULL'}, {tgt_code_col or 'NULL'}, func_name, repo FROM func_pairs WHERE {' AND '.join(where)} ORDER BY RANDOM() LIMIT ?",
                params + [n - len(examples)],
            ).fetchall()
            examples.extend(rows)

        if len(examples) < n:
            rows = conn.execute(
                f"SELECT {src_code_col or 'NULL'}, {tgt_code_col or 'NULL'}, func_name, repo FROM func_pairs WHERE {' AND '.join(where_base)} ORDER BY RANDOM() LIMIT ?",
                params_base + [n - len(examples)],
            ).fetchall()
            examples.extend(rows)

        conn.close()

        if not examples:
            return ""
        parts = ["以下是跨平台迁移参考示例（学习模式，不要复制）：\n"]
        for src_code, tgt_code, fname, repo in examples[:n]:
            parts.append(f"# 示例：{(repo or '').split('/')[-1]}/{fname}")
            parts.append(f"# 源平台实现：\n```go\n{(src_code or '').strip()}\n```")
            parts.append(f"# 目标平台实现：\n```go\n{(tgt_code or '').strip()}\n```\n")
        return "\n".join(parts)
    except Exception:
        return ""
