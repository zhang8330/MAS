import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path

from openai import OpenAI

from .config import get_settings

settings = get_settings()
BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent


def _resolve_pro_mas_root() -> Path:
    env_path = os.getenv("PRO_MAS_ROOT", "").strip()
    if env_path:
        return Path(env_path)

    candidates = [
        PROJECT_ROOT / "pro-mas-crewai",
        Path(r"D:\projects\GraduationProjects\zx\crewAI\pro-mas-crewai"),
        Path(r"D:\projects\GraduationProjects\zx\crewAI\pro-mas-crewai\src\pro_mas_crewai").parents[2],
    ]
    for p in candidates:
        try:
            if p.exists() and p.is_dir():
                return p
        except Exception:
            continue

    return PROJECT_ROOT / "pro-mas-crewai"


PRO_MAS_ROOT = _resolve_pro_mas_root()
PRO_MAS_PYTHON = os.getenv("PRO_MAS_PYTHON", "").strip()
PRO_MAS_OUTPUT_ROOT = PRO_MAS_ROOT / "outputs"
PRO_MAS_LEGACY_OUTPUT_ROOT = PRO_MAS_ROOT / "src" / "pro_mas_crewai" / "output"
RUNS_DIR = BACKEND_ROOT / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

RUN_STATUS: dict[str, dict] = {}
RUN_PROCS: dict[str, subprocess.Popen] = {}
RUN_CACHE_INDEX = RUNS_DIR / "run_cache_index.json"


def _validate_runtime_paths(case_dir: str | None) -> tuple[bool, str]:
    if not PRO_MAS_ROOT.exists() or not PRO_MAS_ROOT.is_dir():
        return False, f"PRO_MAS_ROOT 不存在或不是目录: {PRO_MAS_ROOT}"

    entry = PRO_MAS_ROOT / "src" / "pro_mas_crewai" / "main.py"
    if not entry.exists() or not entry.is_file():
        return False, f"入口脚本不存在: {entry}"

    # 强校验：KnoMAS 必须显式指定 PRO_MAS_PYTHON，避免落到当前环境 python
    python_bin = (settings.pro_mas_python or os.getenv("PRO_MAS_PYTHON") or PRO_MAS_PYTHON or "").strip()
    if not python_bin:
        return False, "PRO_MAS_PYTHON 未配置或未生效，请在 backend/.env 设置 pro-mas 环境的 python.exe 并重启后端"

    py = Path(python_bin)
    if not py.exists() or not py.is_file():
        return False, f"PRO_MAS_PYTHON 不存在或不是文件: {python_bin}"

    if case_dir:
        case_path = PRO_MAS_ROOT / case_dir
        if not case_path.exists() or not case_path.is_dir():
            return False, f"case_dir 无效（相对 PRO_MAS_ROOT）: {case_dir} -> {case_path}"

    return True, "ok"


def _extract_ccgmas_metrics_from_log(log_text: str) -> dict:
    metrics = {
        "compile_at_k": None,
        "residue_rate": None,
        "test_pass": None,
        "stage_hint": "queued",
        "metric_parse_note": "",
    }
    patterns = {
        "compile_at_k": [r"compile[@\s]*k\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)", r"compile\s*success\s*rate\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)"],
        "residue_rate": [r"residue\s*rate\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)"],
        "test_pass": [r"test\s*pass\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)", r"test\s*pass\s*rate\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)"],
    }
    low = log_text.lower()
    for key, pats in patterns.items():
        for p in pats:
            m = re.search(p, low)
            if m:
                try:
                    metrics[key] = float(m.group(1))
                    break
                except Exception:
                    pass

    if "paa" in low:
        metrics["stage_hint"] = "paa"
    if "rga" in low:
        metrics["stage_hint"] = "rga"
    if "cga" in low:
        metrics["stage_hint"] = "cga"
    if "va" in low or "validate" in low or "validation" in low:
        metrics["stage_hint"] = "va"
    if "collecting_artifacts" in low or "finalizing" in low:
        metrics["stage_hint"] = "finalizing"

    missing = [k for k in ("compile_at_k", "residue_rate", "test_pass") if metrics[k] is None]
    if missing:
        metrics["metric_parse_note"] = f"missing_from_log:{','.join(missing)}"

    return metrics


def _project_case_name(case_dir: str | None) -> str:
    if not case_dir:
        return ""
    raw = str(case_dir).replace("\\", "/").strip("/")
    if not raw:
        return ""
    if "/" in raw:
        return raw.split("/")[-1].strip().lower()
    return Path(raw).name.strip().lower()



def _find_project_metrics_json(case_dir: str | None) -> Path | None:
    case_name = _project_case_name(case_dir)
    if not case_name:
        return None

    candidates = [
        PRO_MAS_OUTPUT_ROOT / "project_code" / case_name / "metrics.json",
        PRO_MAS_OUTPUT_ROOT / "project_code" / case_name / case_name / "metrics.json",
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return p

    if PRO_MAS_OUTPUT_ROOT.exists():
        for p in PRO_MAS_OUTPUT_ROOT.rglob("metrics.json"):
            try:
                rel = p.relative_to(PRO_MAS_OUTPUT_ROOT).as_posix().lower()
            except Exception:
                continue
            if rel.endswith(f"project_code/{case_name}/metrics.json") or rel.endswith(f"project_code/{case_name}/{case_name}/metrics.json"):
                return p
    return None



def _load_project_metrics_json(case_dir: str | None) -> dict:
    metrics_path = _find_project_metrics_json(case_dir)
    if metrics_path is None:
        return {}
    try:
        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        token_usage = payload.get("token_usage") or {}
        cost_usd = payload.get("cost_usd") or {}
        return {
            "metrics_json_path": str(metrics_path),
            "runtime_seconds": payload.get("runtime_seconds"),
            "generated_file_count": payload.get("generated_file_count"),
            "code_line_count": payload.get("code_line_count"),
            "compile_error_count": payload.get("compile_error_count"),
            "token_total": token_usage.get("total"),
            "cost_usd": cost_usd.get("total"),
        }
    except Exception:
        return {}


def chat_with_llm(message: str) -> str:
    if not settings.openai_api_key:
        return f"[mock reply] You said: {message}"

    client_kwargs = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        client_kwargs["base_url"] = settings.openai_base_url

    client = OpenAI(**client_kwargs)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant for ArchMAS system."},
            {"role": "user", "content": message},
        ],
    )
    return response.choices[0].message.content or ""


def _persist_run_meta(run_dir: Path, payload: dict) -> None:
    (run_dir / "run_meta.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_run_cache_index() -> dict:
    if not RUN_CACHE_INDEX.exists():
        return {}
    try:
        return json.loads(RUN_CACHE_INDEX.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_run_cache_index(index_data: dict) -> None:
    RUN_CACHE_INDEX.write_text(json.dumps(index_data, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_run_cache_key(case_dir: str | None, model_profile: str, test_loop: int, version: str = "v1") -> str:
    return f"{version}|{case_dir or ''}|{model_profile or ''}|{int(test_loop or 0)}"


def _is_valid_cached_knomas_run(run_id: str) -> bool:
    _, artifacts, _, _ = collect_artifacts(run_id)
    if not artifacts:
        return False
    rels = [str(a.get("rel_path") or "").replace("\\", "/").lower() for a in artifacts]
    required_hints = ["output/pdm/", "output/cip_ps/", "output/project_code/"]
    return any(any(h in r for h in required_hints) for r in rels)


def _update_stage(run_id: str, run_dir: Path, stage: str, progress: int) -> None:
    RUN_STATUS[run_id]["stage"] = stage
    RUN_STATUS[run_id]["progress"] = progress
    _persist_run_meta(run_dir, RUN_STATUS[run_id])


def _snapshot_output_index() -> dict[str, tuple[int, int]]:
    if not PRO_MAS_OUTPUT_ROOT.exists():
        return {}
    return {
        p.relative_to(PRO_MAS_OUTPUT_ROOT).as_posix(): (p.stat().st_mtime_ns, p.stat().st_size)
        for p in PRO_MAS_OUTPUT_ROOT.rglob("*")
        if p.is_file()
    }


def _copy_new_outputs_to_run(run_dir: Path, before: dict[str, tuple[int, int]]) -> int:
    # preserve legacy compatibility, but the source of truth remains PRO_MAS_OUTPUT_ROOT
    if not PRO_MAS_OUTPUT_ROOT.exists():
        return 0

    copied = 0
    for p in PRO_MAS_OUTPUT_ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(PRO_MAS_OUTPUT_ROOT).as_posix()
        stat = p.stat()
        current_sig = (stat.st_mtime_ns, stat.st_size)
        if before.get(rel) == current_sig:
            continue

        dest = run_dir / "artifacts" / "output" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(p, dest)
            copied += 1
        except Exception:
            continue
    return copied


def _run_pipeline_in_thread(
    run_type: str,
    run_stage: str,
    run_id: str,
    run_dir: Path,
    case_dir: str | None,
    test_loop: int,
    ta_project_root: str,
    model_profile: str,
    model_name: str,
    model_base_url: str,
    model_api_key: str,
    cache_key: str = "",
) -> None:
    log_path = run_dir / "run.log"
    src_root = PRO_MAS_ROOT / "src"
    with log_path.open("a", encoding="utf-8", errors="replace") as logf:
        proc: subprocess.Popen | None = None
        try:
            RUN_STATUS[run_id]["status"] = "running"
            _persist_run_meta(run_dir, RUN_STATUS[run_id])
            _update_stage(run_id, run_dir, "snapshot_output", 5)
            before = _snapshot_output_index()

            python_bin = (settings.pro_mas_python or os.getenv("PRO_MAS_PYTHON") or PRO_MAS_PYTHON or "").strip()
            resolved_case_dir = str((PRO_MAS_ROOT / str(case_dir or "")).resolve()) if case_dir else ""
            stage_alias = {
                "copa": "planning",
                "planning": "planning",
                "ca": "codegen",
                "codegen": "codegen",
                "testgen": "testgen",
                "ta": "ta",
                "all": "all",
            }
            stage = stage_alias.get(str(run_stage or "all").strip().lower(), "all")

            cmd = [
                python_bin,
                "-m",
                "pro_mas_crewai.main",
                "--stage",
                stage,
            ]
            if int(test_loop or 0) > 0:
                cmd.extend(["-testloop", str(int(test_loop or 0))])
            if stage in {"testgen", "ta"} or int(test_loop or 0) > 0:
                if ta_project_root:
                    cmd.extend(["--ta-project-root", ta_project_root])
            if resolved_case_dir:
                cmd.append(resolved_case_dir)

            env = os.environ.copy()
            env["PYTHONPATH"] = str(src_root)
            env.setdefault("OTEL_SDK_DISABLED", "true")
            env.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
            env.setdefault("CREWAI_LOG_LEVEL", "ERROR")
            if model_api_key:
                env["OPENAI_API_KEY"] = model_api_key
                env["LLM_API_KEY"] = model_api_key
            if model_base_url:
                env["OPENAI_BASE_URL"] = model_base_url
                env["LLM_BASE_URL"] = model_base_url
            if model_name:
                env["OPENAI_MODEL"] = model_name
                env["LLM_MODEL"] = model_name

            _update_stage(run_id, run_dir, "running_pipeline", 15)
            logf.write(f"[INFO] Starting KnoMAS workflow in {src_root}\n")
            logf.write(f"[INFO] Command: {' '.join(cmd)}\n")
            logf.flush()

            proc = subprocess.Popen(
                cmd,
                cwd=str(src_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            RUN_PROCS[run_id] = proc

            progress = 20
            stage_hint = "running_pipeline"
            assert proc.stdout is not None
            for line in proc.stdout:
                logf.write(line)
                logf.flush()
                low = line.lower()
                if "planning" in low or "pdm" in low:
                    stage_hint, progress = "planning", max(progress, 30)
                elif "codegen" in low or "execution" in low or "project_code" in low:
                    stage_hint, progress = "codegen", max(progress, 55)
                elif "ta-gen" in low or "test case generation" in low:
                    stage_hint, progress = "testgen", max(progress, 70)
                elif "testagent" in low or " ta " in low or "test-fix" in low:
                    stage_hint, progress = "ta", max(progress, 75)
                elif "metrics" in low or "final" in low or "bundle" in low:
                    stage_hint, progress = "finalizing", max(progress, 90)
                _update_stage(run_id, run_dir, stage_hint, min(progress, 95))

            return_code = proc.wait()
            _update_stage(run_id, run_dir, "collecting_artifacts", 95)
            copied = _copy_new_outputs_to_run(run_dir, before)
            RUN_STATUS[run_id]["copied_artifacts"] = copied
            RUN_STATUS[run_id]["return_code"] = return_code
            if RUN_STATUS[run_id].get("status") != "stopped":
                RUN_STATUS[run_id]["status"] = "finished" if return_code == 0 else "failed"
            RUN_STATUS[run_id]["metrics"] = _load_project_metrics_json(case_dir)

            if return_code == 0 and cache_key and RUN_STATUS[run_id].get("status") != "stopped":
                cache_index = _load_run_cache_index()
                cache_index[cache_key] = {"run_id": run_id, "updated_at": time.time()}
                _save_run_cache_index(cache_index)

            logf.write(f"[INFO] KnoMAS workflow exited with code {return_code}; copied_artifacts={copied}\n")
        except Exception as exc:
            logf.write(f"[ERROR] KnoMAS workflow failed: {exc}\n")
            RUN_STATUS[run_id]["status"] = "failed"
            RUN_STATUS[run_id]["return_code"] = -1
        finally:
            RUN_PROCS.pop(run_id, None)
            RUN_STATUS[run_id]["finished_at"] = time.time()
            RUN_STATUS[run_id]["stage"] = "completed"
            RUN_STATUS[run_id]["progress"] = 100
            _persist_run_meta(run_dir, RUN_STATUS[run_id])


def _prepare_ccgmas_case_dir_from_payload(payload: dict) -> str:
    # CCGMAS runner (pro-mas-crewai main.py) expects case path under PRO_MAS_ROOT/data/cases
    cases_root = PRO_MAS_ROOT / "data" / "cases" / "CodeProjectEval"
    case_name = f"ccg_func_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    case_dir = cases_root / case_name
    case_dir.mkdir(parents=True, exist_ok=True)

    source_code = str(payload.get("source_code") or "")
    generic_code = str(payload.get("generic_code") or "")
    migration_type = str(payload.get("migration_type") or "arch")
    source_platform = str(payload.get("source_platform") or "")
    target_platform = str(payload.get("target_platform") or "")

    (case_dir / "source_code.go").write_text(source_code, encoding="utf-8")
    if generic_code.strip():
        (case_dir / "generic_code.go").write_text(generic_code, encoding="utf-8")

    (case_dir / "tech_stack.json").write_text(
        json.dumps(
            {
                "migration_type": migration_type,
                "source_platform": source_platform,
                "target_platform": target_platform,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return f"data/cases/CodeProjectEval/{case_name}"


def create_run(
    run_type: str,
    run_stage: str,
    case_dir: str | None,
    test_loop: int,
    ta_project_root: str,
    model_profile: str = "default",
    model_name: str = "",
    model_base_url: str = "",
    model_api_key: str = "",
    function_payload: dict | None = None,
    prefer_cache: bool = True,
    cache_version: str = "v1",
) -> tuple[str, str]:
    if run_type == "ccgmas" and not case_dir:
        if not function_payload or not str(function_payload.get("source_code") or "").strip():
            raise ValueError("ccgmas 运行缺少 source_code（函数级输入）")
        case_dir = _prepare_ccgmas_case_dir_from_payload(function_payload)

    run_id = f"run_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    masked_api_key = "" if not model_api_key else f"{model_api_key[:4]}***{model_api_key[-4:]}"

    cache_key = ""
    normalized_run_stage = str(run_stage or "all").strip().lower()
    if normalized_run_stage in {"copa", "planning"}:
        normalized_run_stage = "planning"
    elif normalized_run_stage in {"ca", "codegen"}:
        normalized_run_stage = "codegen"
    elif normalized_run_stage in {"testgen", "testcases"}:
        normalized_run_stage = "testgen"
    elif normalized_run_stage == "ta":
        normalized_run_stage = "ta"
    else:
        normalized_run_stage = "all"

    if run_type == "knomas" and normalized_run_stage in {"testgen", "ta"} and not str(ta_project_root or "").strip():
        raise ValueError("TA 阶段需要配置 ta_project_root")

    if run_type == "knomas" and prefer_cache and normalized_run_stage == "all":
        cache_key = _build_run_cache_key(case_dir, model_profile, test_loop, cache_version)
        cache_index = _load_run_cache_index()
        hit = cache_index.get(cache_key) or {}
        cached_run_id = hit.get("run_id")
        if cached_run_id:
            cached = get_run_status(cached_run_id)
            if cached and cached.get("status") == "finished" and _is_valid_cached_knomas_run(cached_run_id):
                return cached_run_id, f"命中缓存：复用历史运行 {cached_run_id}"

    ok, reason = _validate_runtime_paths(case_dir)

    meta = {
        "run_id": run_id,
        "run_type": run_type,
        "run_stage": normalized_run_stage,
        "started_at": time.time(),
        "finished_at": None,
        "case_dir": case_dir,
        "test_loop": test_loop,
        "ta_project_root": ta_project_root,
        "model_profile": model_profile,
        "model_name": model_name,
        "model_base_url": model_base_url,
        "model_api_key_masked": masked_api_key,
        "status": "accepted",
        "stage": "queued",
        "progress": 0,
        "return_code": None,
        "log_file": "run.log",
        "copied_artifacts": 0,
        "metrics": {"path_validation_error": ""},
    }
    RUN_STATUS[run_id] = meta

    if not ok:
        err_msg = f"运行路径预校验失败：{reason}"
        RUN_STATUS[run_id]["status"] = "failed"
        RUN_STATUS[run_id]["stage"] = "completed"
        RUN_STATUS[run_id]["progress"] = 100
        RUN_STATUS[run_id]["return_code"] = -1
        RUN_STATUS[run_id]["finished_at"] = time.time()
        RUN_STATUS[run_id]["metrics"] = {"path_validation_error": err_msg}
        _persist_run_meta(run_dir, RUN_STATUS[run_id])
        (run_dir / "run.log").write_text(f"[ERROR] {err_msg}\n", encoding="utf-8")
        return run_id, err_msg

    _persist_run_meta(run_dir, meta)

    (run_dir / "run.log").write_text("Run accepted and queued.\n", encoding="utf-8")

    threading.Thread(
        target=_run_pipeline_in_thread,
        args=(
            run_type,
            normalized_run_stage,
            run_id,
            run_dir,
            case_dir,
            test_loop,
            ta_project_root,
            model_profile,
            model_name,
            model_base_url,
            model_api_key,
            cache_key,
        ),
        daemon=True,
    ).start()

    return run_id, "Run request received."


def get_run_status(run_id: str) -> dict | None:
    if run_id in RUN_STATUS:
        return RUN_STATUS[run_id]

    meta_path = RUNS_DIR / run_id / "run_meta.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def get_run_log_path(run_id: str) -> Path | None:
    run_dir = RUNS_DIR / run_id
    log_path = run_dir / "run.log"
    if log_path.exists() and log_path.is_file():
        return log_path
    return None


def stop_run(run_id: str) -> tuple[bool, str]:
    status = get_run_status(run_id)
    if status is None:
        return False, "Run not found"
    if status.get("status") not in {"accepted", "running"}:
        return False, f"Run is not running (status={status.get('status')})"

    proc = RUN_PROCS.get(run_id)
    run_dir = RUNS_DIR / run_id
    log_path = run_dir / "run.log"
    if proc is None:
        RUN_STATUS[run_id]["status"] = "stopped"
        RUN_STATUS[run_id]["stage"] = "completed"
        RUN_STATUS[run_id]["progress"] = 100
        RUN_STATUS[run_id]["finished_at"] = time.time()
        RUN_STATUS[run_id]["return_code"] = -15
        _persist_run_meta(run_dir, RUN_STATUS[run_id])
        try:
            with log_path.open("a", encoding="utf-8", errors="replace") as logf:
                logf.write("[WARN] Run stopped before process handle was available.\n")
        except Exception:
            pass
        return True, "Run stopped"

    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    except Exception as e:
        return False, f"Terminate failed: {e}"

    RUN_STATUS[run_id]["status"] = "stopped"
    RUN_STATUS[run_id]["stage"] = "completed"
    RUN_STATUS[run_id]["progress"] = 100
    RUN_STATUS[run_id]["finished_at"] = time.time()
    RUN_STATUS[run_id]["return_code"] = -15
    _persist_run_meta(run_dir, RUN_STATUS[run_id])
    try:
        with log_path.open("a", encoding="utf-8", errors="replace") as logf:
            logf.write("[WARN] Run terminated by user.\n")
    except Exception:
        pass
    return True, "Run terminated"


def collect_artifacts(run_id: str) -> tuple[Path | None, list[dict], list[dict], list[dict]]:
    run_dir = RUNS_DIR / run_id
    meta = get_run_status(run_id) or {}
    snapshot_output_root = run_dir / "artifacts" / "output"
    if snapshot_output_root.exists() and snapshot_output_root.is_dir():
        output_root = snapshot_output_root
        output_is_run_snapshot = True
    elif not PRO_MAS_OUTPUT_ROOT.exists() or not PRO_MAS_OUTPUT_ROOT.is_dir():
        if PRO_MAS_LEGACY_OUTPUT_ROOT.exists() and PRO_MAS_LEGACY_OUTPUT_ROOT.is_dir():
            output_root = PRO_MAS_LEGACY_OUTPUT_ROOT
            output_is_run_snapshot = False
        else:
            return None, [], [], []
    else:
        output_root = PRO_MAS_OUTPUT_ROOT
        output_is_run_snapshot = False

    if not output_root.exists() or not output_root.is_dir():
        return None, [], [], []

    if not run_dir.exists() or not run_dir.is_dir():
        run_dir = RUNS_DIR / run_id

    outputs: list[dict] = []
    logs: list[dict] = []
    memory: list[dict] = []
    seen: set[str] = set()

    ta_project_root = Path(str(meta.get("ta_project_root") or "D:/projects/TestAgent"))
    ta_memory_root = ta_project_root / "memory" / "working_memory"
    knomas_memory_root = PRO_MAS_ROOT / "src" / "pro_mas_crewai" / "memory" / "data"

    case_dir = str(meta.get("case_dir") or "").replace("\\", "/")
    case_name = case_dir.split("/")[-1].strip() if case_dir else ""
    case_name_l = case_name.lower()
    started_at = float(meta.get("started_at") or 0)

    def is_current_run_output(path: Path) -> bool:
        if output_is_run_snapshot:
            return True
        if started_at <= 0:
            return True
        try:
            return path.stat().st_mtime >= started_at - 5
        except Exception:
            return False

    def add_output(path: Path, kind: str, display_name: str | None = None):
        if not path.exists() or not path.is_file():
            return
        if not is_current_run_output(path):
            return
        source_rel = path.relative_to(output_root).as_posix()
        rel_path = f"output/{source_rel}"
        artifact_id = f"output__{source_rel.replace('/', '__')}"
        if artifact_id in seen:
            return
        seen.add(artifact_id)
        stat = path.stat()
        outputs.append(
            {
                "artifact_id": artifact_id,
                "name": display_name or path.name,
                "rel_path": rel_path,
                "source_rel_path": source_rel,
                "kind": kind,
                "size": stat.st_size,
                "updated_at": stat.st_mtime,
            }
        )

    def first_existing(paths: list[Path]) -> Path | None:
        for p in paths:
            if p.exists() and p.is_file() and is_current_run_output(p):
                return p
        return None

    # COPA: PDM includes the domain model JSON and its generated database schema.
    if case_name:
        pdm_path = first_existing([
            output_root / "pdm" / f"{case_name}_pdm.json",
            output_root / "pdm" / f"{case_name}.pdm.json",
            output_root / "pdm" / f"{case_name_l}_pdm.json",
            output_root / "pdm" / f"{case_name_l}.pdm.json",
        ])
        if pdm_path:
            add_output(pdm_path, "pdm")

        sql_path = first_existing([
            output_root / "sql" / f"{case_name}_refined_schema.sql",
            output_root / "sql" / f"{case_name}_schema.sql",
            output_root / "sql" / f"{case_name_l}_refined_schema.sql",
            output_root / "sql" / f"{case_name_l}_schema.sql",
            output_root / "sql" / f"{case_name}.sql",
            output_root / "sql" / f"{case_name_l}.sql",
            output_root / "sql" / "schema.sql",
        ])
        if sql_path:
            add_output(sql_path, "pdm")

        cip_path = first_existing([
            output_root / "cip_ps" / f"{case_name}.json",
            output_root / "cip_ps" / f"{case_name_l}.json",
            output_root / "cip_ps" / case_name / "cip.json",
            output_root / "cip_ps" / case_name_l / "cip.json",
            output_root / "cip_ps" / "cip.json",
        ])
        if cip_path:
            add_output(cip_path, "cip")

        ps_path = first_existing([
            output_root / "cip_ps" / f"{case_name}.json",
            output_root / "cip_ps" / f"{case_name_l}.json",
            output_root / "cip_ps" / case_name / "ps.json",
            output_root / "cip_ps" / case_name_l / "ps.json",
            output_root / "cip_ps" / "ps.json",
        ])
        if ps_path:
            add_output(ps_path, "ps")

    # CA: expose the final project bundle and generated source tree.
    if case_name:
        zip_path = first_existing([
            output_root / "project_code" / f"{case_name}.final.zip",
            output_root / "project_code" / f"{case_name}.zip",
            output_root / "project_code" / f"{case_name_l}.final.zip",
            output_root / "project_code" / f"{case_name_l}.zip",
        ])
        if zip_path:
            add_output(zip_path, "zip")

        for project_root in (
            output_root / "project_code" / case_name,
            output_root / "project_code" / case_name_l,
        ):
            if not project_root.exists() or not project_root.is_dir():
                continue
            for path in sorted(project_root.rglob("*")):
                if not path.is_file():
                    continue
                if path.name == "metrics.json":
                    continue
                if path.suffix.lower() in {".pyc", ".class", ".zip"}:
                    continue
                add_output(path, "code", path.relative_to(project_root).as_posix())
            break

    # Logs: expose only textual logs
    logs_root = output_root / "logs"
    if logs_root.exists() and logs_root.is_dir():
        for p in sorted(logs_root.rglob("*")):
            if not p.is_file():
                continue
            if not is_current_run_output(p):
                continue
            stat = p.stat()
            rel = p.relative_to(output_root).as_posix()
            logs.append({
                "artifact_id": f"output__{rel.replace('/', '__')}",
                "name": p.name,
                "rel_path": f"output/{rel}",
                "source_rel_path": rel,
                "kind": "log",
                "size": stat.st_size,
                "updated_at": stat.st_mtime,
            })

    def add_memory(path: Path, root: Path, kind: str):
        if not path.is_file():
            return
        stat = path.stat()
        rel = path.relative_to(root).as_posix()
        memory.append({
            "artifact_id": f"{kind}__{rel.replace('/', '__')}",
            "name": path.name,
            "rel_path": f"{kind}/{rel}",
            "source_rel_path": str(path),
            "kind": kind,
            "size": stat.st_size,
            "updated_at": stat.st_mtime,
        })

    ltm_path = knomas_memory_root / "ltm.json"
    if ltm_path.exists():
        add_memory(ltm_path, knomas_memory_root, "ltm")

    if case_name and knomas_memory_root.exists() and knomas_memory_root.is_dir():
        wm_candidates = [
            knomas_memory_root / f"wm_structure_{case_name}.json",
            knomas_memory_root / f"wm_structure_{case_name_l}.json",
        ]
        for p in wm_candidates:
            if p.exists():
                add_memory(p, knomas_memory_root, "wm")

    if ta_memory_root.exists() and ta_memory_root.is_dir():
        for p in sorted(ta_memory_root.rglob("*")):
            if not p.is_file():
                continue
            add_memory(p, ta_memory_root, "ta")

    return run_dir, outputs, logs, memory
