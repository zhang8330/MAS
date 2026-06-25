import asyncio
import json
import mimetypes
import os
import subprocess
from collections import deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from .config import get_settings
from .schemas import (
    ArtifactItem,
    ArtifactPreviewResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    RunArtifactsResponse,
    RunProjectRequest,
    RunProjectResponse,
    RunStatusResponse,
)
from .services import (
    PRO_MAS_LEGACY_OUTPUT_ROOT,
    PRO_MAS_OUTPUT_ROOT,
    PRO_MAS_PYTHON,
    PRO_MAS_ROOT,
    chat_with_llm,
    collect_artifacts,
    create_run,
    get_run_log_path,
    get_run_status,
    stop_run,
)
from .routes.datasets import router as datasets_router
from .routes.generate import router as generate_router
from .routes.metrics import router as metrics_router

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[item.strip() for item in settings.cors_origins.split(",") if item.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets_router)
app.include_router(generate_router)
app.include_router(metrics_router)


def _case_name_from_dir(case_dir: str) -> str:
    raw = str(case_dir or "").replace("\\", "/").strip("/")
    return raw.split("/")[-1].strip() if raw else ""


def _resolve_runtime_case_dir(case_dir: str) -> Path:
    raw = str(case_dir or "").replace("\\", "/").strip("/")
    if not raw:
        raise HTTPException(status_code=400, detail="case_dir is required")
    root = PRO_MAS_ROOT.resolve()
    target = (root / raw).resolve()
    if not str(target).lower().startswith(str(root).lower()):
        raise HTTPException(status_code=400, detail="case_dir must be under PRO_MAS_ROOT")
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail=f"case_dir not found: {case_dir}")
    return target


def _collect_case_copa_artifacts(case_dir: str) -> list[dict]:
    case_name = _case_name_from_dir(case_dir)
    if not case_name:
        return []
    case_name_l = case_name.lower()
    rows: list[dict] = []
    seen: set[str] = set()

    def add(path: Path, root: Path, kind: str, display_name: str | None = None, scope: str = "module"):
        if not path.exists() or not path.is_file():
            return
        try:
            rel = path.relative_to(root).as_posix()
        except Exception:
            return
        artifact_id = f"case_copa__{rel.replace('/', '__')}"
        if artifact_id in seen:
            return
        seen.add(artifact_id)
        stat = path.stat()
        rows.append({
            "artifact_id": artifact_id,
            "name": display_name or path.name,
            "rel_path": f"output/{rel}",
            "source_rel_path": rel,
            "kind": kind,
            "scope": scope,
            "size": stat.st_size,
            "updated_at": stat.st_mtime,
        })

    for root in (PRO_MAS_OUTPUT_ROOT, PRO_MAS_LEGACY_OUTPUT_ROOT):
        cip_ps_root = root / "cip_ps"
        if not cip_ps_root.exists():
            continue
        merged_candidates = [
            cip_ps_root / f"{case_name}.json",
            cip_ps_root / f"{case_name_l}.json",
            cip_ps_root / case_name / f"{case_name}.json",
            cip_ps_root / case_name_l / f"{case_name_l}.json",
        ]
        for path in merged_candidates:
            add(path, root, "cip_ps", scope="merged")
        for path in (cip_ps_root / "cip.json", cip_ps_root / case_name / "cip.json", cip_ps_root / case_name_l / "cip.json"):
            add(path, root, "cip", "cip.json", "merged")
        for path in (cip_ps_root / "ps.json", cip_ps_root / case_name / "ps.json", cip_ps_root / case_name_l / "ps.json"):
            add(path, root, "ps", "ps.json", "merged")
        for name in (case_name, case_name_l):
            cip_dir = cip_ps_root / "cip_modules" / name
            if cip_dir.exists():
                for path in sorted(cip_dir.glob("*.json")):
                    add(path, root, "cip", scope="module")
            ps_dir = cip_ps_root / "ps_modules" / name
            if ps_dir.exists():
                for path in sorted(ps_dir.glob("*.json")):
                    add(path, root, "ps", scope="module")
        if not any(x["kind"] == "cip" for x in rows):
            for path in (cip_ps_root / f"{case_name}.json", cip_ps_root / f"{case_name_l}.json"):
                add(path, root, "cip", f"{path.stem}.merged.json", "merged")
        if not any(x["kind"] == "ps" for x in rows):
            for path in (cip_ps_root / "ps.json",):
                add(path, root, "ps", scope="merged")
        if rows:
            break

    return rows


def _resolve_case_copa_artifact(case_dir: str, artifact_id: str) -> tuple[dict, Path]:
    rows = _collect_case_copa_artifacts(case_dir)
    target = next((x for x in rows if x["artifact_id"] == artifact_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="COPA artifact not found")
    source_rel = str(target.get("source_rel_path") or "").replace("\\", "/").strip("/")
    for root in (PRO_MAS_OUTPUT_ROOT, PRO_MAS_LEGACY_OUTPUT_ROOT):
        path = root / source_rel
        if path.exists() and path.is_file():
            return target, path
    raise HTTPException(status_code=404, detail="COPA artifact file missing")


def _collect_case_project_artifacts(case_dir: str) -> list[dict]:
    case_name = _case_name_from_dir(case_dir)
    if not case_name:
        return []
    case_name_l = case_name.lower()
    rows: list[dict] = []
    seen: set[str] = set()

    def add(path: Path, root: Path, kind: str, display_name: str | None = None):
        if not path.exists() or not path.is_file():
            return
        try:
            rel = path.relative_to(root).as_posix()
        except Exception:
            return
        artifact_id = f"case_project__{rel.replace('/', '__')}"
        if artifact_id in seen:
            return
        seen.add(artifact_id)
        stat = path.stat()
        rows.append({
            "artifact_id": artifact_id,
            "name": display_name or path.name,
            "rel_path": f"output/{rel}",
            "source_rel_path": rel,
            "kind": kind,
            "scope": "case",
            "size": stat.st_size,
            "updated_at": stat.st_mtime,
        })

    for root in (PRO_MAS_OUTPUT_ROOT, PRO_MAS_LEGACY_OUTPUT_ROOT):
        if not root.exists():
            continue
        for pdm_path in (
            root / "pdm" / f"{case_name}_pdm.json",
            root / "pdm" / f"{case_name}.pdm.json",
            root / "pdm" / f"{case_name_l}_pdm.json",
            root / "pdm" / f"{case_name_l}.pdm.json",
        ):
            add(pdm_path, root, "pdm")

        for zip_path in (
            root / "project_code" / f"{case_name}.final.zip",
            root / "project_code" / f"{case_name}.zip",
            root / "project_code" / f"{case_name_l}.final.zip",
            root / "project_code" / f"{case_name_l}.zip",
        ):
            add(zip_path, root, "zip")

        for project_root in (root / "project_code" / case_name, root / "project_code" / case_name_l):
            if not project_root.exists() or not project_root.is_dir():
                continue
            for path in sorted(project_root.rglob("*")):
                if not path.is_file():
                    continue
                if path.name == "metrics.json":
                    continue
                if path.suffix.lower() in {".pyc", ".class", ".zip"}:
                    continue
                add(path, root, "code", path.relative_to(project_root).as_posix())
            break
        if rows:
            break
    return rows


def _resolve_case_project_artifact(case_dir: str, artifact_id: str) -> tuple[dict, Path]:
    rows = _collect_case_project_artifacts(case_dir)
    target = next((x for x in rows if x["artifact_id"] == artifact_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Project artifact not found")
    source_rel = str(target.get("source_rel_path") or "").replace("\\", "/").strip("/")
    for root in (PRO_MAS_OUTPUT_ROOT, PRO_MAS_LEGACY_OUTPUT_ROOT):
        path = root / source_rel
        if path.exists() and path.is_file():
            return target, path
    raise HTTPException(status_code=404, detail="Project artifact file missing")


def _memory_data_root() -> Path:
    return PRO_MAS_ROOT / "src" / "pro_mas_crewai" / "memory" / "data"


def _collect_case_memory_artifacts(case_dir: str = "") -> list[dict]:
    case_name = _case_name_from_dir(case_dir)
    case_name_l = case_name.lower()
    root = _memory_data_root()
    rows: list[dict] = []
    seen: set[str] = set()

    def add(path: Path, kind: str):
        if not path.exists() or not path.is_file():
            return
        resolved = str(path.resolve()).lower()
        if resolved in seen:
            return
        seen.add(resolved)
        stat = path.stat()
        try:
            rel = path.relative_to(root).as_posix()
        except Exception:
            rel = path.name
        rows.append({
            "artifact_id": f"memory__{kind}__{rel.replace('/', '__')}",
            "name": path.name,
            "rel_path": f"{kind}/{rel}",
            "source_rel_path": str(path),
            "kind": kind,
            "scope": "memory",
            "size": stat.st_size,
            "updated_at": stat.st_mtime,
        })

    add(root / "ltm.json", "ltm")
    if case_name:
        for path in [
            root / f"wm_structure_{case_name}.json",
            root / f"wm_structure_{case_name_l}.json",
        ]:
            add(path, "wm")
    return rows


def _resolve_case_memory_artifact(case_dir: str, artifact_id: str) -> tuple[dict, Path]:
    rows = _collect_case_memory_artifacts(case_dir)
    target = next((x for x in rows if x["artifact_id"] == artifact_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Memory artifact not found")
    path = Path(str(target.get("source_rel_path") or ""))
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Memory artifact file missing")
    return target, path


def _find_case_merged_cip_ps(case_dir: str) -> Path | None:
    case_name = _case_name_from_dir(case_dir)
    if not case_name:
        return None
    case_name_l = case_name.lower()
    for root in (PRO_MAS_OUTPUT_ROOT, PRO_MAS_LEGACY_OUTPUT_ROOT):
        cip_ps_root = root / "cip_ps"
        for path in [
            cip_ps_root / f"{case_name}.json",
            cip_ps_root / f"{case_name_l}.json",
            cip_ps_root / case_name / f"{case_name}.json",
            cip_ps_root / case_name_l / f"{case_name_l}.json",
        ]:
            if path.exists() and path.is_file():
                return path
    return None


def _ltm_path() -> Path:
    return _memory_data_root() / "ltm.json"


def _load_ltm_data() -> dict:
    path = _ltm_path()
    if not path.exists():
        return {"architecture_knowledge": [], "code_generation_experience": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Invalid ltm.json: {exc}")
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="ltm.json root must be an object")
    data.setdefault("architecture_knowledge", [])
    data.setdefault("code_generation_experience", [])
    return data


def _save_ltm_data(data: dict) -> None:
    _ltm_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _as_label(value) -> str:
    if isinstance(value, list):
        return " / ".join(str(x) for x in value)
    return str(value or "")


def _next_ltm_id(prefix: str, entries: list[dict]) -> str:
    base = prefix.upper().strip("-") or "LTM"
    nums = []
    for row in entries:
        raw = str((row or {}).get("id") or "")
        if raw.startswith(base):
            tail = raw.replace(base, "").strip("-_")
            if tail.isdigit():
                nums.append(int(tail))
    return f"{base}-{(max(nums) + 1) if nums else 1:03d}"


def _next_priority(entries: list[dict]) -> int:
    vals = []
    for row in entries:
        try:
            vals.append(int((row or {}).get("priority")))
        except Exception:
            pass
    return (max(vals) + 1) if vals else 0


def _ltm_profiles(data: dict, category: str) -> list[dict]:
    key = "architecture_knowledge" if category == "architecture" else "code_generation_experience"
    return data.setdefault(key, [])


def _entry_key(category: str) -> str:
    return "knowledge" if category == "architecture" else "experience"


def _serialize_ltm(data: dict) -> dict:
    result = {"architecture": [], "experience": []}
    for category, source_key in [("architecture", "architecture_knowledge"), ("experience", "code_generation_experience")]:
        entry_key = _entry_key(category)
        for profile_index, profile in enumerate(data.get(source_key, []) or []):
            entries = profile.get(entry_key, []) or []
            result[category].append({
                "profile_index": profile_index,
                "language": profile.get("language"),
                "version": profile.get("version"),
                "label": f"{_as_label(profile.get('language'))} · {_as_label(profile.get('version'))}",
                "entries": [
                    {
                        **entry,
                        "_category": category,
                        "_profile_index": profile_index,
                        "_entry_index": entry_index,
                    }
                    for entry_index, entry in enumerate(entries)
                    if isinstance(entry, dict)
                ],
            })
    return result


def _stack_side_from_ltm_profile(profile: dict) -> dict:
    language = profile.get("language")
    version = profile.get("version")
    return {
        "language": language if language not in (None, "") else "",
        "version": version if version not in (None, "") else "",
    }


def _profile_text(profile: dict) -> str:
    return f"{_as_label(profile.get('language'))} {_as_label(profile.get('version'))}".lower()


def _norm_values(value) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip().lower() for x in value if str(x).strip()]
    text = str(value or "").strip().lower()
    return [text] if text else []


def _find_ltm_profile_for_stack(profiles: list[dict], side: dict) -> int | None:
    side_lang = set(_norm_values((side or {}).get("language")))
    side_ver = set(_norm_values((side or {}).get("version")))
    if not side_lang:
        return None
    language_matches: list[int] = []
    for index, profile in enumerate(profiles):
        profile_lang = set(_norm_values(profile.get("language")))
        profile_ver = set(_norm_values(profile.get("version")))
        if not (side_lang & profile_lang):
            continue
        if side_ver and profile_ver and side_ver & profile_ver:
            return index
        language_matches.append(index)
    return language_matches[0] if language_matches else None


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    reply = chat_with_llm(payload.message)
    return ChatResponse(reply=reply)


@app.post("/api/project/run", response_model=RunProjectResponse)
def run_project(payload: RunProjectRequest, request: Request) -> RunProjectResponse:
    model_name = payload.model_name or request.headers.get("X-Model-Name") or ""
    model_base_url = payload.model_base_url or request.headers.get("X-LLM-Base-URL") or ""
    model_api_key = payload.model_api_key or request.headers.get("X-API-Key") or ""

    function_payload = {
        "source_code": getattr(payload, "source_code", "") or "",
        "generic_code": getattr(payload, "generic_code", "") or "",
        "migration_type": getattr(payload, "migration_type", "") or "",
        "source_platform": getattr(payload, "source_platform", "") or "",
        "target_platform": getattr(payload, "target_platform", "") or "",
    }

    try:
        run_id, message = create_run(
            payload.run_type,
            payload.run_stage,
            payload.case_dir,
            payload.test_loop,
            payload.ta_project_root,
            payload.model_profile,
            model_name,
            model_base_url,
            model_api_key,
            function_payload,
            bool(getattr(payload, "prefer_cache", True)),
            str(getattr(payload, "cache_version", "v1") or "v1"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RunProjectResponse(accepted=True, message=message, run_id=run_id)


@app.post("/api/project/runs/{run_id}/stop")
def stop_project_run(run_id: str):
    ok, msg = stop_run(run_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg, "run_id": run_id}


@app.get("/api/project/runs/{run_id}/status", response_model=RunStatusResponse)
def run_status(run_id: str) -> RunStatusResponse:
    status = get_run_status(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunStatusResponse(
        run_id=run_id,
        status=status.get("status", "unknown"),
        stage=status.get("stage", "queued"),
        progress=status.get("progress", 0),
        run_type=status.get("run_type", "knomas"),
        model_profile=status.get("model_profile", "default"),
        model_name=status.get("model_name", ""),
        model_base_url=status.get("model_base_url", ""),
        model_api_key_masked=status.get("model_api_key_masked", ""),
        return_code=status.get("return_code"),
        started_at=status.get("started_at", 0),
        finished_at=status.get("finished_at"),
        log_file=status.get("log_file", "run.log"),
        metrics=status.get("metrics", {}),
    )


@app.get("/api/project/runs/{run_id}/logs/stream")
async def stream_run_logs(run_id: str):
    log_path = get_run_log_path(run_id)
    if log_path is None:
        raise HTTPException(status_code=404, detail="Run log not found")

    async def event_generator():
        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(0, 0)
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line.rstrip()}\n\n"
                else:
                    status = get_run_status(run_id)
                    if status and status.get("status") in {"finished", "failed", "stopped"}:
                        yield "event: done\ndata: run finished\n\n"
                        break
                    await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/project/runs/{run_id}/logs/tail")
def tail_run_logs(run_id: str, limit: int = 80):
    log_path = get_run_log_path(run_id)
    if log_path is None:
        raise HTTPException(status_code=404, detail="Run log not found")

    limit = max(1, min(int(limit or 80), 300))
    keywords = (
        "[INFO]", "[START]", "[OK]", "[FAIL]", "[WARN]", "[ERROR]",
        "[PDM", "[CIP", "[PS", "[metrics]", "Loading case:", "Command:",
    )
    rows: deque[str] = deque(maxlen=limit)
    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            text = line.rstrip()
            if not text:
                continue
            if any(k in text for k in keywords):
                rows.append(text)
    return {"run_id": run_id, "lines": list(rows)}


@app.get("/api/project/runs/{run_id}/artifacts", response_model=RunArtifactsResponse)
def list_run_artifacts(run_id: str) -> RunArtifactsResponse:
    base_dir, outputs, logs, memory = collect_artifacts(run_id)
    if base_dir is None:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunArtifactsResponse(
        run_id=run_id,
        base_dir=str(base_dir),
        outputs=[ArtifactItem(**item) for item in outputs],
        logs=[ArtifactItem(**item) for item in logs],
        memory=[ArtifactItem(**item) for item in memory],
    )


@app.get("/api/project/copa-artifacts")
def list_case_copa_artifacts(case_dir: str):
    rows = _collect_case_copa_artifacts(case_dir)
    return {
        "case_dir": case_dir,
        "case_name": _case_name_from_dir(case_dir),
        "items": [ArtifactItem(**item) for item in rows],
    }


@app.get("/api/project/copa-artifacts/{artifact_id}/preview", response_model=ArtifactPreviewResponse)
def preview_case_copa_artifact(artifact_id: str, case_dir: str) -> ArtifactPreviewResponse:
    target, path = _resolve_case_copa_artifact(case_dir, artifact_id)
    allowed_preview_ext = {".json", ".md", ".txt", ".log", ".sql", ".yaml", ".yml", ".py"}
    if path.suffix.lower() not in allowed_preview_ext:
        raise HTTPException(status_code=400, detail="Preview only supports text-like artifacts")

    max_chars = 20000
    raw = path.read_text(encoding="utf-8", errors="replace")
    truncated = len(raw) > max_chars
    preview = raw[:max_chars]
    content_type = mimetypes.guess_type(str(path))[0] or "text/plain"
    return ArtifactPreviewResponse(
        artifact_id=artifact_id,
        name=target["name"],
        rel_path=target["rel_path"],
        content_type=content_type,
        preview=preview,
        truncated=truncated,
    )


@app.get("/api/project/code-artifacts")
def list_case_project_artifacts(case_dir: str):
    rows = _collect_case_project_artifacts(case_dir)
    return {
        "case_dir": case_dir,
        "case_name": _case_name_from_dir(case_dir),
        "items": [ArtifactItem(**item) for item in rows],
    }


@app.get("/api/project/code-artifacts/{artifact_id}/preview", response_model=ArtifactPreviewResponse)
def preview_case_project_artifact(artifact_id: str, case_dir: str) -> ArtifactPreviewResponse:
    target, path = _resolve_case_project_artifact(case_dir, artifact_id)
    allowed_preview_ext = {
        ".json", ".md", ".txt", ".log", ".sql", ".yaml", ".yml",
        ".py", ".java", ".xml", ".properties", ".toml", ".ini", ".cfg",
        ".gradle", ".kt", ".kts",
    }
    if path.suffix.lower() not in allowed_preview_ext:
        raise HTTPException(status_code=400, detail="Preview only supports text-like artifacts")

    max_chars = 20000
    raw = path.read_text(encoding="utf-8", errors="replace")
    truncated = len(raw) > max_chars
    preview = raw[:max_chars]
    content_type = mimetypes.guess_type(str(path))[0] or "text/plain"
    return ArtifactPreviewResponse(
        artifact_id=artifact_id,
        name=target["name"],
        rel_path=target["rel_path"],
        content_type=content_type,
        preview=preview,
        truncated=truncated,
    )


@app.get("/api/project/memory-artifacts")
def list_case_memory_artifacts(case_dir: str = ""):
    rows = _collect_case_memory_artifacts(case_dir)
    return {
        "case_dir": case_dir,
        "case_name": _case_name_from_dir(case_dir),
        "items": [ArtifactItem(**item) for item in rows],
    }


@app.get("/api/project/memory-artifacts/{artifact_id}/preview", response_model=ArtifactPreviewResponse)
def preview_case_memory_artifact(artifact_id: str, case_dir: str = "") -> ArtifactPreviewResponse:
    target, path = _resolve_case_memory_artifact(case_dir, artifact_id)
    max_chars = 20000
    raw = path.read_text(encoding="utf-8", errors="replace")
    truncated = len(raw) > max_chars
    preview = raw[:max_chars]
    content_type = mimetypes.guess_type(str(path))[0] or "text/plain"
    return ArtifactPreviewResponse(
        artifact_id=artifact_id,
        name=target["name"],
        rel_path=target["rel_path"],
        content_type=content_type,
        preview=preview,
        truncated=truncated,
    )


@app.put("/api/project/memory-artifacts/{artifact_id}/content")
def save_case_memory_artifact(artifact_id: str, payload: dict):
    case_dir = str(payload.get("case_dir") or "")
    target, path = _resolve_case_memory_artifact(case_dir, artifact_id)
    content = str(payload.get("content") or "")
    path.write_text(content, encoding="utf-8")
    return {
        "ok": True,
        "artifact_id": artifact_id,
        "name": target["name"],
        "rel_path": target["rel_path"],
        "size": path.stat().st_size,
        "updated_at": path.stat().st_mtime,
    }


@app.get("/api/project/ltm")
def get_ltm_entries():
    return _serialize_ltm(_load_ltm_data())


@app.post("/api/project/ltm-stack/apply")
def apply_ltm_stack_to_case(payload: dict):
    case_dir = str(payload.get("case_dir") or "")
    backend_profile_index = int(payload.get("backend_profile_index") if payload.get("backend_profile_index") not in (None, "") else -1)
    frontend_profile_index = int(payload.get("frontend_profile_index") if payload.get("frontend_profile_index") not in (None, "") else -1)
    case_path = _resolve_runtime_case_dir(case_dir)

    data = _load_ltm_data()
    profiles = data.get("architecture_knowledge", []) or []
    if backend_profile_index < 0 or backend_profile_index >= len(profiles):
        raise HTTPException(status_code=404, detail="Backend LTM profile not found")
    if frontend_profile_index < 0 or frontend_profile_index >= len(profiles):
        raise HTTPException(status_code=404, detail="Frontend LTM profile not found")

    backend_profile = profiles[backend_profile_index]
    frontend_profile = profiles[frontend_profile_index]
    backend_text = _profile_text(backend_profile)
    frontend_text = _profile_text(frontend_profile)
    if not any(x in backend_text for x in ("java", "python")):
        raise HTTPException(status_code=400, detail="Backend LTM profile must be Java or Python")
    if "vue" not in frontend_text:
        raise HTTPException(status_code=400, detail="Frontend LTM profile must be Vue")

    tech_stack = {
        "backend": _stack_side_from_ltm_profile(backend_profile),
        "frontend": _stack_side_from_ltm_profile(frontend_profile),
    }
    source = {
        "type": "ltm_profile_selection",
        "backend_profile": {
            "profile_index": backend_profile_index,
            "label": f"{_as_label(backend_profile.get('language'))} · {_as_label(backend_profile.get('version'))}",
        },
        "frontend_profile": {
            "profile_index": frontend_profile_index,
            "label": f"{_as_label(frontend_profile.get('language'))} · {_as_label(frontend_profile.get('version'))}",
        },
    }
    target = case_path / "tech_stack.json"
    target.write_text(json.dumps(tech_stack, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "case_dir": case_dir,
        "case_name": _case_name_from_dir(case_dir),
        "tech_stack": tech_stack,
        "source": source,
    }


@app.get("/api/project/ltm-stack/current")
def get_current_ltm_stack(case_dir: str):
    case_path = _resolve_runtime_case_dir(case_dir)
    target = case_path / "tech_stack.json"
    if not target.exists():
        return {
            "ok": True,
            "case_dir": case_dir,
            "case_name": _case_name_from_dir(case_dir),
            "tech_stack": {},
            "backend_profile_index": None,
            "frontend_profile_index": None,
        }
    try:
        tech_stack = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Invalid case tech_stack.json: {exc}")
    if not isinstance(tech_stack, dict):
        raise HTTPException(status_code=500, detail="case tech_stack.json root must be an object")

    profiles = (_load_ltm_data().get("architecture_knowledge") or [])
    backend_index = _find_ltm_profile_for_stack(profiles, tech_stack.get("backend") or {})
    frontend_index = _find_ltm_profile_for_stack(profiles, tech_stack.get("frontend") or {})
    return {
        "ok": True,
        "case_dir": case_dir,
        "case_name": _case_name_from_dir(case_dir),
        "tech_stack": tech_stack,
        "backend_profile_index": backend_index,
        "frontend_profile_index": frontend_index,
    }


@app.post("/api/project/ltm/entries")
def add_ltm_entry(payload: dict):
    category = str(payload.get("category") or "").strip()
    if category not in {"architecture", "experience"}:
        raise HTTPException(status_code=400, detail="category must be architecture or experience")
    profile_index = int(payload.get("profile_index") or 0)
    data = _load_ltm_data()
    profiles = _ltm_profiles(data, category)
    if profile_index < 0 or profile_index >= len(profiles):
        raise HTTPException(status_code=404, detail="LTM profile not found")
    profile = profiles[profile_index]
    entry_key = _entry_key(category)
    entries = profile.setdefault(entry_key, [])
    raw = payload.get("entry") or {}
    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="entry must be an object")

    if category == "architecture":
        entry = {
            "id": raw.get("id") or _next_ltm_id("AK", entries),
            "package": str(raw.get("package") or "").strip(),
            "priority": int(raw.get("priority") if raw.get("priority") not in (None, "") else _next_priority(entries)),
            "description": str(raw.get("description") or "").strip(),
            "template": str(raw.get("template") or "").strip(),
        }
        if not entry["package"] or not entry["description"]:
            raise HTTPException(status_code=400, detail="package and description are required")
    else:
        path_rule = str(raw.get("path") or raw.get("match_path") or "").strip()
        entry = {
            "id": raw.get("id") or _next_ltm_id("LTM", entries),
            "type": str(raw.get("type") or "pattern").strip(),
            "scope": str(raw.get("scope") or "module").strip(),
            "match": {"path": path_rule or "**/*"},
            "rule": str(raw.get("rule") or "").strip(),
            "example": str(raw.get("example") or "").strip(),
        }
        if not entry["rule"]:
            raise HTTPException(status_code=400, detail="rule is required")

    entries.append(entry)
    _save_ltm_data(data)
    return {"ok": True, "ltm": _serialize_ltm(data)}


@app.put("/api/project/ltm/entries")
def update_ltm_entry(payload: dict):
    category = str(payload.get("category") or "").strip()
    if category not in {"architecture", "experience"}:
        raise HTTPException(status_code=400, detail="category must be architecture or experience")
    profile_index = int(payload.get("profile_index") or 0)
    entry_index = int(payload.get("entry_index") or 0)
    data = _load_ltm_data()
    profiles = _ltm_profiles(data, category)
    if profile_index < 0 or profile_index >= len(profiles):
        raise HTTPException(status_code=404, detail="LTM profile not found")
    entries = profiles[profile_index].setdefault(_entry_key(category), [])
    if entry_index < 0 or entry_index >= len(entries):
        raise HTTPException(status_code=404, detail="LTM entry not found")
    raw = payload.get("entry") or {}
    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="entry must be an object")

    if category == "architecture":
        entries[entry_index] = {
            "id": raw.get("id") or entries[entry_index].get("id") or _next_ltm_id("AK", entries),
            "package": str(raw.get("package") or "").strip(),
            "priority": int(raw.get("priority") if raw.get("priority") not in (None, "") else entries[entry_index].get("priority", entry_index)),
            "description": str(raw.get("description") or "").strip(),
            "template": str(raw.get("template") or "").strip(),
        }
    else:
        match = raw.get("match") if isinstance(raw.get("match"), dict) else {}
        path_rule = str(raw.get("path") or raw.get("match_path") or match.get("path") or "").strip()
        entries[entry_index] = {
            "id": raw.get("id") or entries[entry_index].get("id") or _next_ltm_id("LTM", entries),
            "type": str(raw.get("type") or "pattern").strip(),
            "scope": str(raw.get("scope") or "module").strip(),
            "match": {"path": path_rule or "**/*"},
            "rule": str(raw.get("rule") or "").strip(),
            "example": str(raw.get("example") or "").strip(),
        }

    _save_ltm_data(data)
    return {"ok": True, "ltm": _serialize_ltm(data)}


@app.post("/api/project/memory/build")
def build_case_working_memory(payload: dict):
    case_dir = str(payload.get("case_dir") or "")
    case_name = _case_name_from_dir(case_dir)
    if not case_name:
        raise HTTPException(status_code=400, detail="case_dir is required")
    merged = _find_case_merged_cip_ps(case_dir)
    if merged is None:
        raise HTTPException(status_code=404, detail=f"Merged CIP/PS not found for case: {case_name}")

    python_bin = (settings.pro_mas_python or os.getenv("PRO_MAS_PYTHON") or PRO_MAS_PYTHON or "").strip()
    if not python_bin:
        raise HTTPException(status_code=400, detail="PRO_MAS_PYTHON is not configured")

    code = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "from pro_mas_crewai.core.workflow import build_wm_structure\n"
        "case_name = sys.argv[1]\n"
        "merged_path = Path(sys.argv[2])\n"
        "data = json.loads(merged_path.read_text(encoding='utf-8'))\n"
        "wm = build_wm_structure(data, case_name)\n"
        "print('WM_BUILT', case_name, len((wm.get('project_graph') or {}).get('file_states', {}) or {}))\n"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PRO_MAS_ROOT / "src")
    proc = subprocess.run(
        [python_bin, "-c", code, case_name, str(merged)],
        cwd=str(PRO_MAS_ROOT / "src"),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=(proc.stderr or proc.stdout or "Working Memory build failed")[-2000:])

    return {
        "ok": True,
        "case_dir": case_dir,
        "case_name": case_name,
        "merged_cip_ps": str(merged),
        "stdout": (proc.stdout or "")[-4000:],
        "items": [ArtifactItem(**item) for item in _collect_case_memory_artifacts(case_dir)],
    }


@app.get("/api/project/runs/{run_id}/artifacts/{artifact_id}/preview", response_model=ArtifactPreviewResponse)
def preview_artifact(run_id: str, artifact_id: str) -> ArtifactPreviewResponse:
    base_dir, outputs, logs, memory = collect_artifacts(run_id)
    if base_dir is None:
        raise HTTPException(status_code=404, detail="Run not found")

    artifacts = [*outputs, *logs, *memory]
    target = next((a for a in artifacts if a["artifact_id"] == artifact_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Artifact not found")

    path = _resolve_artifact_path(base_dir, target, run_id)

    allowed_preview_ext = {".json", ".md", ".txt", ".log", ".sql", ".yaml", ".yml", ".py"}
    if path.suffix.lower() not in allowed_preview_ext:
        raise HTTPException(status_code=400, detail="Preview only supports text-like artifacts")

    max_chars = 20000
    raw = path.read_text(encoding="utf-8", errors="replace")
    truncated = len(raw) > max_chars
    preview = raw[:max_chars]
    content_type = mimetypes.guess_type(str(path))[0] or "text/plain"

    return ArtifactPreviewResponse(
        artifact_id=artifact_id,
        name=target["name"],
        rel_path=target["rel_path"],
        content_type=content_type,
        preview=preview,
        truncated=truncated,
    )


@app.put("/api/project/runs/{run_id}/artifacts/{artifact_id}/content")
def save_artifact_content(run_id: str, artifact_id: str, payload: dict):
    base_dir, outputs, logs, memory = collect_artifacts(run_id)
    if base_dir is None:
        raise HTTPException(status_code=404, detail="Run not found")

    artifacts = [*outputs, *logs, *memory]
    target = next((a for a in artifacts if a["artifact_id"] == artifact_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Artifact not found")

    path = _resolve_artifact_path(base_dir, target, run_id)
    allowed_edit_ext = {".json", ".md", ".txt", ".log", ".sql", ".yaml", ".yml", ".py"}
    if path.suffix.lower() not in allowed_edit_ext:
        raise HTTPException(status_code=400, detail="Edit only supports text-like artifacts")

    content = str(payload.get("content") or "")
    path.write_text(content, encoding="utf-8")
    return {
        "ok": True,
        "artifact_id": artifact_id,
        "name": target["name"],
        "rel_path": target["rel_path"],
        "size": path.stat().st_size,
        "updated_at": path.stat().st_mtime,
    }




def _resolve_artifact_path(base_dir: Path, target: dict, run_id: str) -> Path:
    source_raw = str(target.get("source_rel_path") or "")
    if not source_raw:
        raise HTTPException(status_code=404, detail="Artifact source path missing")

    source_path = Path(source_raw)
    if source_path.is_absolute():
        if source_path.exists() and source_path.is_file():
            return source_path
        raise HTTPException(status_code=404, detail=f"Artifact file missing: {source_raw}")

    source_rel_path = source_raw.replace("\\", "/").strip("/")
    snapshot_path = base_dir / "artifacts" / "output" / source_rel_path
    if snapshot_path.exists() and snapshot_path.is_file():
        return snapshot_path

    for root in (PRO_MAS_OUTPUT_ROOT, PRO_MAS_LEGACY_OUTPUT_ROOT):
        path = root / source_rel_path
        if path.exists() and path.is_file():
            return path

    raise HTTPException(status_code=404, detail=f"Artifact file missing: {source_rel_path}")


@app.get("/api/project/runs/{run_id}/artifacts/{artifact_id}/download")
def download_artifact(run_id: str, artifact_id: str):
    base_dir, outputs, logs, memory = collect_artifacts(run_id)
    if base_dir is None:
        raise HTTPException(status_code=404, detail="Run not found")

    artifacts = [*outputs, *logs, *memory]
    target = next((a for a in artifacts if a["artifact_id"] == artifact_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Artifact not found")

    path = _resolve_artifact_path(base_dir, target, run_id)
    media_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    return FileResponse(path=str(path), filename=path.name, media_type=media_type)
