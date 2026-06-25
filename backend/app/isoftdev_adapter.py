import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path

from .knomas_dataset import create_knomas_case, get_knomas_case_detail, update_knomas_case


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ISD_ROOT = Path(r"D:\projects\iSoftDevAgent")
DEFAULT_ISD_PYTHON = Path(r"D:\anaconda3\envs\iSoftDevAgent\python.exe")
INPUT_ARCHIVE_ROOT = BACKEND_ROOT / "runs" / "isoftdev_inputs"
ISOFTDEV_APPDATA_ROOT = BACKEND_ROOT / "runs" / "isoftdev_appdata"
ISOFTDEV_CREWAI_STORAGE_ROOT = BACKEND_ROOT / "runs" / "isoftdev_crewai"
ISOFTDEV_LOG_ROOT = BACKEND_ROOT / "runs" / "isoftdev_logs"
GENERATED_DATASET = "generated"
TEXT_OUTPUT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".log", ".py", ".java", ".puml"}
REQUIREMENTS_KEY_ARTIFACTS = {
    "use_case.md": {"maps_to": "use_case.md", "label": "Use Cases"},
    "entity_relationship_diagram.md": {"maps_to": "entity_relationship_diagram.md", "label": "Entity Relationship Diagram"},
    "SRS.md": {"maps_to": "", "label": "Software Requirements Specification"},
    "functional_requirements.md": {"maps_to": "", "label": "Functional Requirements"},
    "non_functional_requirements.md": {"maps_to": "", "label": "Non-functional Requirements"},
    "data_dictionary.md": {"maps_to": "", "label": "Data Dictionary"},
}
ARCHITECTURE_KEY_ARTIFACTS = {
    "class_design_raw.md": {"maps_to": "class_diagram.md", "label": "Class Design"},
    "class_design_structured.json": {"maps_to": "class_diagram.md", "label": "Structured Class Design"},
    "component_design.json": {"maps_to": "component_diagram.md", "label": "Component Design"},
    "modeling-3.static_design_output.txt": {"maps_to": "package_diagram.md", "label": "Static Design / Package Diagram"},
    "modeling-1.tech_stack_selection_output.txt": {"maps_to": "tech_stack.json", "label": "Tech Stack Selection"},
    "modeling-2.architecture_design_output.txt": {"maps_to": "", "label": "Architecture Design"},
}


def _isd_root() -> Path:
    return Path(os.getenv("ISOFTDEV_ROOT", str(DEFAULT_ISD_ROOT))).expanduser()


def _requirements_root() -> Path:
    return _isd_root() / "Requirements Agent" / "reagent"


def _architecture_root() -> Path:
    return _isd_root() / "Architecture Agent"


def _requirements_output_root() -> Path:
    return _requirements_root() / "output"


def _architecture_output_root() -> Path:
    return _architecture_root() / "data" / "output"


def _artifact_config(kind: str) -> tuple[Path, dict[str, dict[str, str]]]:
    if kind == "requirements":
        return _requirements_output_root(), REQUIREMENTS_KEY_ARTIFACTS
    if kind == "architecture":
        return _architecture_output_root(), ARCHITECTURE_KEY_ARTIFACTS
    raise ValueError("kind must be requirements or architecture")


def _resolve_output_file(kind: str, output_dir: str, rel_path: str) -> tuple[Path, Path]:
    root, _ = _artifact_config(kind)
    base = Path(output_dir).expanduser().resolve()
    allowed_root = root.resolve()
    if allowed_root not in [base, *base.parents]:
        raise ValueError(f"output_dir is outside {kind} output root")
    target = (base / rel_path).resolve()
    if base not in [target, *target.parents]:
        raise ValueError("artifact path escapes output_dir")
    if not target.is_file():
        raise FileNotFoundError(rel_path)
    return base, target


def _is_text_output(path: Path) -> bool:
    return path.suffix.lower() in TEXT_OUTPUT_SUFFIXES or path.name in {"SRS", "BRD"}


def list_isd_output_artifacts(kind: str, output_dir: str) -> dict:
    root, key_config = _artifact_config(kind)
    base = Path(output_dir).expanduser().resolve()
    allowed_root = root.resolve()
    if allowed_root not in [base, *base.parents]:
        raise ValueError(f"output_dir is outside {kind} output root")
    if not base.exists() or not base.is_dir():
        raise ValueError(f"output_dir not found: {base}")

    items = []
    for path in sorted([p for p in base.rglob("*") if p.is_file()]):
        rel = path.relative_to(base).as_posix()
        key = path.name in key_config
        stat = path.stat()
        cfg = key_config.get(path.name, {})
        items.append({
            "name": path.name,
            "rel_path": rel,
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "key": key,
            "editable": _is_text_output(path) and stat.st_size <= 2_000_000,
            "maps_to": cfg.get("maps_to", ""),
            "label": cfg.get("label", path.name),
        })

    key_items = [x for x in items if x["key"]]
    return {
        "kind": kind,
        "output_dir": str(base).replace("\\", "/"),
        "root": str(root).replace("\\", "/"),
        "items": items,
        "key_items": key_items,
        "key_definitions": key_config,
    }


def read_isd_output_artifact(kind: str, output_dir: str, rel_path: str) -> dict:
    _, target = _resolve_output_file(kind, output_dir, rel_path)
    editable = _is_text_output(target) and target.stat().st_size <= 2_000_000
    if not editable:
        raise ValueError("artifact is not a readable text file")
    text = target.read_text(encoding="utf-8", errors="replace")
    return {
        "kind": kind,
        "rel_path": rel_path,
        "name": target.name,
        "content": text,
        "editable": editable,
    }


def save_isd_output_artifact(kind: str, output_dir: str, rel_path: str, content: str) -> dict:
    _, target = _resolve_output_file(kind, output_dir, rel_path)
    if not _is_text_output(target):
        raise ValueError("artifact is not editable")
    target.write_text(str(content or ""), encoding="utf-8")
    return {
        "ok": True,
        "kind": kind,
        "rel_path": rel_path,
        "size": target.stat().st_size,
        "mtime": target.stat().st_mtime,
    }


def _slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_\-\u4e00-\u9fff]+", "_", value.strip())
    text = text.strip("_")
    return text[:80] or f"case_{uuid.uuid4().hex[:8]}"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _write_input_file(project_name: str, description: str) -> Path:
    INPUT_ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    path = INPUT_ARCHIVE_ROOT / f"{int(time.time())}_{_slug(project_name)}.md"
    path.write_text(description, encoding="utf-8")
    return path


def _latest_output(root: Path, project_name: str, started_at: float) -> Path | None:
    if not root.exists():
        return None

    slug = _slug(project_name).lower()
    candidates: list[Path] = []
    for path in root.iterdir():
        if not path.is_dir():
            continue
        try:
            if path.stat().st_mtime < started_at - 5:
                continue
        except OSError:
            continue

        name_l = path.name.lower()
        if slug in name_l or project_name.lower() in name_l:
            candidates.append(path)

    if not candidates:
        for path in root.iterdir():
            if path.is_dir():
                try:
                    if path.stat().st_mtime >= started_at - 5:
                        candidates.append(path)
                except OSError:
                    continue

    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0] if candidates else None


def _proc_note(proc: subprocess.CompletedProcess[str]) -> str:
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    parts = []
    if stdout:
        parts.append("STDOUT:\n" + stdout[-3000:])
    if stderr:
        parts.append("STDERR:\n" + stderr[-3000:])
    return "\n\n".join(parts).strip()


def _build_isd_env(extra_env: dict[str, str] | None = None) -> dict[str, str]:
    ISOFTDEV_APPDATA_ROOT.mkdir(parents=True, exist_ok=True)
    ISOFTDEV_CREWAI_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({
        "LOCALAPPDATA": str(ISOFTDEV_APPDATA_ROOT),
        "APPDATA": str(ISOFTDEV_APPDATA_ROOT),
        "CREWAI_STORAGE_DIR": str(ISOFTDEV_CREWAI_STORAGE_ROOT),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    })
    if extra_env:
        env.update(extra_env)
    return env


def _run_command(
    cmd: list[str],
    cwd: Path,
    timeout_sec: int,
    extra_env: dict[str, str] | None = None,
    stdin_text: str | None = None,
) -> tuple[bool, str]:
    env = _build_isd_env(extra_env)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            input=stdin_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
    except Exception as exc:
        return False, f"Command failed before completion: {exc}"

    note = _proc_note(proc)
    if proc.returncode != 0:
        return False, f"Command exited with {proc.returncode}\n{note}"
    return True, note


def _tail_text(path: Path, max_chars: int = 3000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:]


def _run_command_with_artifact_progress(
    cmd: list[str],
    cwd: Path,
    timeout_sec: int,
    project_name: str,
    logger=None,
    extra_env: dict[str, str] | None = None,
    stdin_text: str | None = None,
) -> tuple[bool, str, Path | None]:
    ISOFTDEV_LOG_ROOT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    stdout_path = ISOFTDEV_LOG_ROOT / f"{int(started)}_{_slug(project_name)}_requirements.stdout.log"
    stderr_path = ISOFTDEV_LOG_ROOT / f"{int(started)}_{_slug(project_name)}_requirements.stderr.log"
    env = _build_isd_env(extra_env)
    tracked_files = (
        "business_scope.md",
        "BRD.md",
        "use_case.md",
        "non_functional_requirements.md",
        "functional_requirements.md",
        "data_flow_diagram.md",
        "dialog_map.md",
        "entity_relationship_diagram.md",
        "usage_scenario.md",
        "state_transition_diagram.md",
        "srs_planning.md",
        "SRS.md",
    )

    with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout_f, stderr_path.open("w", encoding="utf-8", errors="replace") as stderr_f:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdin=subprocess.PIPE if stdin_text is not None else None,
            stdout=stdout_f,
            stderr=stderr_f,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        if stdin_text is not None and proc.stdin:
            try:
                proc.stdin.write(stdin_text)
                proc.stdin.close()
            except OSError:
                pass

        seen_files: set[str] = set()
        while True:
            ret = proc.poll()
            out_dir = _latest_output(_requirements_output_root(), project_name, started)
            if out_dir and logger:
                for name in tracked_files:
                    if name not in seen_files and (out_dir / name).is_file():
                        seen_files.add(name)
                        logger(f"Requirements artifact generated: {name}")

            if ret is not None:
                note = "\n\n".join([
                    "STDOUT:\n" + _tail_text(stdout_path),
                    "STDERR:\n" + _tail_text(stderr_path),
                ]).strip()
                return ret == 0, note if ret == 0 else f"Command exited with {ret}\n{note}", out_dir

            if timeout_sec > 0 and time.time() - started > timeout_sec:
                try:
                    proc.kill()
                finally:
                    proc.wait(timeout=5)
                note = "\n\n".join([
                    f"Command timed out after {timeout_sec} seconds.",
                    "STDOUT:\n" + _tail_text(stdout_path),
                    "STDERR:\n" + _tail_text(stderr_path),
                ]).strip()
                return False, note, out_dir

            time.sleep(2)


def _run_command_with_architecture_progress(
    cmd: list[str],
    cwd: Path,
    timeout_sec: int,
    project_name: str,
    logger=None,
    extra_env: dict[str, str] | None = None,
) -> tuple[bool, str, Path | None]:
    ISOFTDEV_LOG_ROOT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    stdout_path = ISOFTDEV_LOG_ROOT / f"{int(started)}_{_slug(project_name)}_architecture.stdout.log"
    stderr_path = ISOFTDEV_LOG_ROOT / f"{int(started)}_{_slug(project_name)}_architecture.stderr.log"
    env = _build_isd_env(extra_env)
    tracked_files = (
        "analysis_task_output.txt",
        "extractor_output.txt",
        "modeling-1.tech_stack_selection_output.txt",
        "modeling-2.architecture_design_output.txt",
        "modeling-3.static_design_output.txt",
        "component_design.json",
        "class_design_raw.md",
        "class_design_structured.json",
    )

    with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout_f, stderr_path.open("w", encoding="utf-8", errors="replace") as stderr_f:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=stdout_f,
            stderr=stderr_f,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        seen_files: set[str] = set()
        while True:
            ret = proc.poll()
            out_dir = _latest_output(_architecture_output_root(), project_name, started)
            if out_dir and logger:
                for name in tracked_files:
                    if name not in seen_files and (out_dir / name).is_file():
                        seen_files.add(name)
                        logger(f"Architecture artifact generated: {name}")

            if ret is not None:
                note = "\n\n".join([
                    "STDOUT:\n" + _tail_text(stdout_path),
                    "STDERR:\n" + _tail_text(stderr_path),
                ]).strip()
                return ret == 0, note if ret == 0 else f"Command exited with {ret}\n{note}", out_dir

            if timeout_sec > 0 and time.time() - started > timeout_sec:
                try:
                    proc.kill()
                finally:
                    proc.wait(timeout=5)
                note = "\n\n".join([
                    f"Command timed out after {timeout_sec} seconds.",
                    "STDOUT:\n" + _tail_text(stdout_path),
                    "STDERR:\n" + _tail_text(stderr_path),
                ]).strip()
                return False, note, out_dir

            time.sleep(2)


def _run_requirements_agent(project_name: str, input_file: Path, timeout_sec: int, logger=None) -> tuple[Path | None, str]:
    root = _requirements_root()
    if not root.exists():
        return None, f"Requirements Agent not found: {root}"

    python_bin = (
        os.getenv("ISOFTDEV_REQUIREMENTS_PYTHON")
        or os.getenv("ISOFTDEV_PYTHON")
        or str(DEFAULT_ISD_PYTHON)
    )
    cmd = [
        python_bin,
        str(BACKEND_ROOT / "app" / "isoftdev_requirements_runner.py"),
        str(root),
        "--project_name",
        project_name,
        "--description_file",
        str(input_file),
        "--srs_example_path",
        "util/doc_template/document_example.md",
    ]
    if logger:
        logger(f"Starting Requirements Agent: {root}")
        logger(f"Input file: {input_file}")
        logger("Requirements Agent is running in non-interactive mode; feedback prompts are skipped")
    auto_feedback = "no\n\n" * int(os.getenv("ISOFTDEV_AUTO_FEEDBACK_COUNT", "20"))
    ok, note, out_dir = _run_command_with_artifact_progress(
        cmd,
        root,
        timeout_sec,
        project_name,
        logger=logger,
        stdin_text=auto_feedback,
    )
    if logger:
        status = "completed" if ok else "failed"
        logger(f"Requirements Agent {status}")
        logger(f"Requirements output directory: {out_dir if out_dir else '-'}")
        if not ok and note:
            logger("Requirements error summary:")
            for line in note[-1200:].splitlines()[-20:]:
                logger(line)
    return out_dir, ("OK\n" if ok else "FAILED\n") + note

def _run_architecture_agent(project_name: str, requirements_doc: Path, timeout_sec: int, logger=None) -> tuple[Path | None, str]:
    root = _architecture_root()
    if not root.exists():
        return None, f"Architecture Agent not found: {root}"
    if not requirements_doc.exists():
        return None, f"Requirements document not found for Architecture Agent: {requirements_doc}"

    python_bin = (
        os.getenv("ISOFTDEV_ARCHITECTURE_PYTHON")
        or os.getenv("ISOFTDEV_PYTHON")
        or str(DEFAULT_ISD_PYTHON)
    )
    cmd = [python_bin, "-m", "arch_agent.main", str(requirements_doc), project_name]
    env = {"PYTHONPATH": str(root / "src")}
    if logger:
        logger(f"启动 Architecture Agent: {root}")
        logger(f"需求文档: {requirements_doc}")
    ok, note, out_dir = _run_command_with_architecture_progress(
        cmd,
        root,
        timeout_sec,
        project_name,
        logger=logger,
        extra_env=env,
    )
    if logger:
        logger(f"Architecture Agent {'完成' if ok else '失败'}")
        logger(f"Architecture 输出目录: {out_dir if out_dir else '-'}")
        if not ok and note:
            logger("Architecture 错误摘要:")
            for line in note[-1200:].splitlines()[-20:]:
                logger(line)
    return out_dir, ("OK\n" if ok else "FAILED\n") + note


def _extract_fenced_block(text: str, lang: str | None = None) -> str:
    if lang:
        pattern = rf"```{re.escape(lang)}\s*([\s\S]*?)```"
    else:
        pattern = r"```[A-Za-z0-9_-]*\s*([\s\S]*?)```"
    match = re.search(pattern, text or "", flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _extract_section_fence(text: str, heading_pattern: str, lang: str = "plantuml") -> str:
    heading = re.search(heading_pattern, text or "", flags=re.IGNORECASE)
    scoped = text[heading.start():] if heading else text
    return _extract_fenced_block(scoped, lang)


def _extract_section_fence_any(text: str, heading_pattern: str) -> tuple[str, str]:
    heading = re.search(heading_pattern, text or "", flags=re.IGNORECASE)
    scoped = text[heading.start():] if heading else text
    match = re.search(r"```([A-Za-z0-9_-]*)\s*([\s\S]*?)```", scoped or "")
    if not match:
        return "", ""
    return (match.group(1) or "text").lower(), match.group(2).strip()


def _wrap_fence(body: str, lang: str, title: str) -> str:
    clean = (body or "").strip()
    if not clean:
        return ""
    if clean.startswith("```"):
        return f"# {title}\n\n{clean}\n"
    return f"# {title}\n\n```{lang}\n{clean}\n```\n"


def _limit_text(text: str, max_chars: int = 12000) -> str:
    clean = (text or "").strip()
    if len(clean) <= max_chars:
        return clean
    return clean[:max_chars].rstrip() + "\n\n<!-- Truncated for KnoMAS prompt budget. Full iSoftDevAgent artifact remains available in the source output directory. -->"


def _short_value(value, max_chars: int = 800):
    if isinstance(value, str):
        return _limit_text(value, max_chars)
    if isinstance(value, list):
        return [_short_value(x, max_chars) for x in value[:8]]
    if isinstance(value, dict):
        return {str(k): _short_value(v, max_chars) for k, v in value.items()}
    return value


def _compact_use_cases(path: Path, max_cases: int = 8) -> str:
    data = json.loads(_read_text(path))
    rows = data if isinstance(data, list) else [data]
    keep_keys = [
        "use_case_name",
        "primary_actor",
        "secondary_actor",
        "use_case_description",
        "trigger",
        "preconditions",
        "postconditions",
        "main_flow",
        "alternative_flows",
        "exception_flows",
        "priority",
        "business_rules",
        "assumptions",
        "other_constraints",
    ]
    compact = []
    for row in rows[:max_cases]:
        if not isinstance(row, dict):
            continue
        compact.append({
            key: _short_value(row.get(key), 1000)
            for key in keep_keys
            if row.get(key) not in (None, "", [], {})
        })
    return json.dumps(compact, ensure_ascii=False, indent=2)


def _class_diagram_from_structured(path: Path, max_chars: int = 12000) -> str:
    rows = json.loads(_read_text(path))
    blocks = []
    current_len = len("# Class Diagram\n\n")
    for row in (rows if isinstance(rows, list) else []):
        name = str(row.get("component_name") or "Component").strip()
        design = row.get("class_design") or {}
        diagram = str(design.get("class_diagram") or "").strip()
        if not diagram:
            continue
        lang = "plantuml" if "@startuml" in diagram.lower() else "mermaid"
        block = f"## {name}\n\n```{lang}\n{diagram}\n```"
        next_len = current_len + len(block) + 2
        if blocks and next_len > max_chars:
            blocks.append("<!-- Additional class diagram components omitted for KnoMAS prompt budget. Full artifact remains in iSoftDevAgent output. -->")
            break
        if not blocks and next_len > max_chars:
            block = _limit_text(block, max_chars - current_len)
        blocks.append(block)
        current_len += len(block) + 2
    return "# Class Diagram\n\n" + "\n\n".join(blocks) + "\n" if blocks else ""


def _sentences(text: str, limit: int = 8) -> list[str]:
    parts = re.split(r"[\n。！？；;.!?]+", text or "")
    rows = [p.strip(" -\t\r") for p in parts if p.strip(" -\t\r")]
    return rows[:limit]


def _extract_terms(text: str, limit: int = 8) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}|[\u4e00-\u9fff]{2,8}", text or "")
    stop = {"系统", "用户", "功能", "需求", "支持", "进行", "管理", "实现", "提供", "通过", "数据", "服务"}
    seen: list[str] = []
    for token in tokens:
        if token in stop or token.lower() in {"the", "and", "for", "with", "from"}:
            continue
        if token not in seen:
            seen.append(token)
        if len(seen) >= limit:
            break
    return seen or ["User", "Project", "Record", "Service"]


def _mermaid_safe(name: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_\u4e00-\u9fff]", "_", name)
    if re.match(r"^\d", clean):
        clean = f"N_{clean}"
    return clean or "Node"


def _pascal_name(value: str, fallback: str = "Core") -> str:
    raw = str(value or "").strip()
    if not raw:
        return fallback
    if re.fullmatch(r"[A-Z0-9_]+", raw):
        raw = raw.lower()
    parts = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", raw)
    if not parts:
        return fallback
    mapping = [
        ("登录", "Auth"), ("认证", "Auth"), ("注册", "Auth"),
        ("用户", "User"), ("考试", "Exam"), ("题目", "Question"),
        ("提交", "Submission"), ("成绩", "Grade"), ("库存", "Stock"),
        ("订单", "Order"), ("资产", "Asset"), ("校园", "Campus"),
        ("请假", "Leave"), ("加班", "Overtime"), ("排班", "Schedule"),
        ("考勤", "Attendance"), ("计算", "Calculation"), ("表达式", "Expression"),
        ("剪贴板", "Clipboard"), ("复制", "Clipboard"), ("粘贴", "Clipboard"),
        ("反馈", "Feedback"), ("历史", "History"), ("设备", "Device"),
    ]
    result: list[str] = []
    for part in parts:
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            for needle, name in mapping:
                if needle in part and name not in result:
                    result.append(name)
            continue
        for token in re.split(r"[_\-\s]+", part):
            if token:
                result.append(token[:1].upper() + token[1:])
    return "".join(result) or fallback


def _parse_tech_language(files: dict[str, str]) -> str:
    try:
        tech = json.loads(files.get("tech_stack.json") or "{}")
        backend = tech.get("backend") or {}
        return str(backend.get("language") or "").lower()
    except Exception:
        return ""


def _diagram_body(text: str) -> str:
    return _extract_fenced_block(text or "") or (text or "")


def _parse_er_entities(er_text: str) -> list[dict]:
    body = _diagram_body(er_text)
    entities: list[dict] = []
    lines = body.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        match = re.match(r"^([A-Za-z][A-Za-z0-9_]*)\s*\{\s*$", line)
        if not match:
            idx += 1
            continue
        raw_name = match.group(1)
        fields: list[tuple[str, str]] = []
        idx += 1
        while idx < len(lines) and "}" not in lines[idx]:
            field_line = lines[idx].strip()
            field_match = re.match(r"^([A-Za-z][A-Za-z0-9_<>,]*)\s+([A-Za-z][A-Za-z0-9_]*)", field_line)
            if field_match:
                fields.append((field_match.group(2), field_match.group(1).lower()))
            idx += 1
        entities.append({
            "raw": raw_name,
            "name": _pascal_name(raw_name, "Entity"),
            "fields": fields[:8],
        })
        idx += 1
    return entities[:10]


def _parse_use_case_capabilities(use_case_text: str) -> list[str]:
    names: list[str] = []
    try:
        data = json.loads(use_case_text or "[]")
        rows = data if isinstance(data, list) else [data]
        for row in rows:
            if isinstance(row, dict):
                names.append(str(row.get("use_case_name") or row.get("use_case_description") or ""))
    except Exception:
        names = re.findall(r"use_case_name[\"'\s:：]+([^,\n\"']+)", use_case_text or "")
    capabilities: list[str] = []
    for name in names:
        cap = _pascal_name(name, "")
        if cap and cap not in capabilities:
            capabilities.append(cap)
        if len(capabilities) >= 5:
            break
    return capabilities


def _domain_capabilities(files: dict[str, str], entities: list[dict]) -> list[str]:
    capabilities = _parse_use_case_capabilities(files.get("use_case.md", ""))
    for entity in entities:
        name = str(entity.get("name") or "")
        for suffix in ("State", "Result", "Record", "Request", "Data", "Expression", "Command"):
            if name.endswith(suffix) and len(name) > len(suffix):
                name = name[:-len(suffix)]
                break
        if name and name not in capabilities:
            capabilities.append(name)
        if len(capabilities) >= 5:
            break
    return capabilities or ["Core"]


def _field_type(raw_type: str, language: str) -> str:
    lower = (raw_type or "").lower()
    if language == "java":
        if lower in {"int", "integer"}:
            return "Integer"
        if lower in {"float", "double", "decimal"}:
            return "BigDecimal"
        if lower in {"bool", "boolean"}:
            return "Boolean"
        if lower in {"date", "datetime", "timestamp"}:
            return "LocalDateTime"
        return "String"
    if lower in {"int", "integer"}:
        return "int"
    if lower in {"float", "double", "decimal"}:
        return "float"
    if lower in {"bool", "boolean"}:
        return "bool"
    if lower in {"date", "datetime", "timestamp"}:
        return "datetime"
    return "str"


def _render_entity_block(entity: dict, language: str) -> list[str]:
    lines = [f"  class {entity['name']} {{"]
    fields = entity.get("fields") or [("id", "string"), ("name", "string")]
    for field, raw_type in fields[:8]:
        lines.append(f"    +{field}: {_field_type(raw_type, language)}")
    lines.append("  }")
    return lines


def _java_package_diagram() -> str:
    return """```mermaid
graph TD
    controller["controller"] --> service["service"]
    service --> serviceImpl["service.impl"]
    serviceImpl --> dao["dao"]
    serviceImpl --> entity["entity"]
    serviceImpl --> pojo["pojo"]
    dao --> entity
    dao --> db["database"]
    controller --> pojo
```"""


def _python_package_diagram() -> str:
    return """```mermaid
graph TD
    routes["routes"] --> controller["controller"]
    controller --> service["service"]
    service --> repository["repository"]
    repository --> model["model"]
    controller --> schema["schema"]
    service --> schema
    routes --> app["app"]
    config["config"] --> app
```"""


def _java_class_diagram(capabilities: list[str], entities: list[dict]) -> str:
    primary_entities = entities[:6] or [{"name": "Record", "fields": [("id", "string"), ("name", "string")]}]
    lines = [
        "```plantuml",
        "@startuml",
        "skinparam classAttributeIconSize 0",
        "skinparam packageStyle rectangle",
        "skinparam shadowing false",
        "",
        'package "controller" {',
    ]
    for cap in capabilities:
        lines += [f"  class {cap}Controller {{", f"    +handle(req: {cap}Request): ApiResponse<{cap}VO>", "  }", ""]
    lines += ['}', '', 'package "service" {']
    for cap in capabilities:
        lines += [f"  interface {cap}Service {{", f"    +handle(req: {cap}Request): {cap}VO", "  }", ""]
    lines += ['}', '', 'package "service.impl" {']
    for cap in capabilities:
        lines += [f"  class {cap}ServiceImpl {{", f"    +handle(req: {cap}Request): {cap}VO", "    -validate(req): Boolean", "  }", ""]
    lines += ['}', '', 'package "dao" {']
    for entity in primary_entities:
        lines += [f"  interface {entity['name']}Dao {{", f"    +findById(id: String): {entity['name']}", f"    +save(entity: {entity['name']}): Integer", "  }", ""]
    lines += ['}', '', 'package "entity" {']
    for entity in primary_entities:
        lines += _render_entity_block(entity, "java") + [""]
    lines += ['}', '', 'package "pojo" {']
    for cap in capabilities:
        lines += [
            f"  class {cap}Request {{",
            "    +userId: String",
            "    +payload: String",
            "  }",
            "",
            f"  class {cap}VO {{",
            "    +id: String",
            "    +status: String",
            "  }",
            "",
        ]
    lines += ["  class ApiResponse<T> {", "    +code: String", "    +message: String", "    +data: T", "  }", "}"]
    lines.append("")
    for cap in capabilities:
        lines += [
            f"{cap}ServiceImpl ..|> {cap}Service",
            f"{cap}Controller --> {cap}Service",
        ]
    for cap, entity in zip(capabilities, primary_entities):
        lines += [
            f"{cap}ServiceImpl --> {entity['name']}Dao",
            f"{entity['name']}Dao --> {entity['name']}",
        ]
    lines += ["", "@enduml", "```"]
    return "\n".join(lines) + "\n"


def _python_class_diagram(capabilities: list[str], entities: list[dict]) -> str:
    primary_entities = entities[:6] or [{"name": "Record", "fields": [("id", "string"), ("name", "string")]}]
    lines = [
        "```plantuml",
        "@startuml",
        "skinparam classAttributeIconSize 0",
        "skinparam packageStyle rectangle",
        "skinparam shadowing false",
        "",
        'package "routes" {',
        "  class RouteRegistry {",
        "    +register_routes(app)",
        "  }",
        "}",
        "",
        'package "controller" {',
    ]
    for cap in capabilities:
        lines += [f"  class {cap}Controller {{", "    +handle_request(): dict", "  }", ""]
    lines += ['}', '', 'package "service" {']
    for cap in capabilities:
        lines += [f"  class {cap}Service {{", "    +handle(payload: dict): dict", "    -validate(payload: dict): bool", "  }", ""]
    lines += ['}', '', 'package "repository" {']
    for entity in primary_entities:
        lines += [f"  class {entity['name']}Repository {{", f"    +get_by_id(id: str): {entity['name']}", f"    +save(model: {entity['name']}): int", "  }", ""]
    lines += ['}', '', 'package "model" {']
    for entity in primary_entities:
        lines += _render_entity_block(entity, "python") + [""]
    lines += ['}', '', 'package "schema" {']
    for cap in capabilities:
        lines += [
            f"  class {cap}RequestSchema {{",
            "    +user_id: str",
            "    +payload: dict",
            "  }",
            "",
            f"  class {cap}ResponseSchema {{",
            "    +id: str",
            "    +status: str",
            "  }",
            "",
        ]
    lines += ["  class ApiResponse {", "    +code: int", "    +message: str", "    +data: dict", "  }", "}"]
    lines.append("")
    for cap in capabilities:
        lines += [f"{cap}Controller --> {cap}Service", f"{cap}Controller --> {cap}RequestSchema"]
    for cap, entity in zip(capabilities, primary_entities):
        lines += [f"{cap}Service --> {entity['name']}Repository", f"{entity['name']}Repository --> {entity['name']}"]
    lines += ["RouteRegistry --> " + capabilities[0] + "Controller", "", "@enduml", "```"]
    return "\n".join(lines) + "\n"


def _apply_knomas_style_diagrams(files: dict[str, str]) -> list[str]:
    language = _parse_tech_language(files)
    if language not in {"java", "python"}:
        language = "python"
    entities = _parse_er_entities(files.get("entity_relationship_diagram.md", ""))
    capabilities = _domain_capabilities(files, entities)
    if language == "java":
        files["package_diagram.md"] = _java_package_diagram() + "\n"
        files["class_diagram.md"] = _java_class_diagram(capabilities, entities)
        layer = "Java/SpringBoot controller-service-service.impl-dao-entity-pojo"
    else:
        files["package_diagram.md"] = _python_package_diagram() + "\n"
        files["class_diagram.md"] = _python_class_diagram(capabilities, entities)
        layer = "Python/Flask routes-controller-service-repository-model-schema"
    return [
        f"package_diagram.md <- generated from tech_stack.json and LTM layer rules ({layer})",
        f"class_diagram.md <- generated from use_case.md/entity_relationship_diagram.md and LTM layer rules ({layer})",
    ]


def _fallback_artifacts(project_name: str, description: str) -> dict[str, str]:
    points = _sentences(description, limit=8)
    terms = _extract_terms(description, limit=6)
    components = terms[:4]

    use_case = [{
        "use_case_name": f"{project_name}核心业务流程",
        "primary_actor": "用户",
        "secondary_actor": "系统管理员",
        "trigger": points[0] if points else "用户发起业务请求",
        "use_case_description": points[0] if points else description[:300],
        "preconditions": ["用户具备访问系统的权限"],
        "postconditions": ["系统完成业务处理并保存必要状态"],
        "main_flow": points[:6] or ["用户提交请求", "系统校验输入", "系统执行业务规则", "系统返回处理结果"],
        "alternative_flows": [],
        "exception_flows": [],
        "priority": "High",
        "business_rules": [],
        "assumptions": ["需求描述可进一步细化为完整设计文档"],
        "other_constraints": [],
    }]

    class_lines = ["classDiagram"]
    for term in terms:
        cls = _mermaid_safe(term)
        class_lines += [f"  class {cls} {{", "    +id", "    +validate()", "    +execute()", "  }"]
    for left, right in zip(terms, terms[1:]):
        class_lines.append(f"  {_mermaid_safe(left)} --> {_mermaid_safe(right)}")

    comp_lines = ["flowchart LR"]
    for idx, comp in enumerate(components, start=1):
        comp_lines.append(f"  C{idx}[{comp}]")
    for idx in range(1, len(components)):
        comp_lines.append(f"  C{idx} --> C{idx + 1}")

    pkg_lines = ["flowchart TB"]
    for idx, comp in enumerate(components, start=1):
        pkg_lines.append(f"  P{idx}[{_mermaid_safe(comp).lower()}]")
    for idx in range(1, len(components)):
        pkg_lines.append(f"  P{idx} --> P{idx + 1}")

    er_lines = ["erDiagram"]
    for term in terms[:5]:
        ent = _mermaid_safe(term).upper()
        er_lines += [f"  {ent} {{", "    string id", "    string name", "  }"]
    for left, right in zip(terms[:4], terms[1:5]):
        er_lines.append(f"  {_mermaid_safe(left).upper()} ||--o{{ {_mermaid_safe(right).upper()} : relates")

    return {
        "use_case.md": json.dumps(use_case, ensure_ascii=False, indent=2),
        "class_diagram.md": _wrap_fence("\n".join(class_lines), "mermaid", "Class Diagram"),
        "component_diagram.md": _wrap_fence("\n".join(comp_lines), "mermaid", "Component Diagram"),
        "package_diagram.md": _wrap_fence("\n".join(pkg_lines), "mermaid", "Package Diagram"),
        "entity_relationship_diagram.md": _wrap_fence("\n".join(er_lines), "mermaid", "Entity Relationship Diagram"),
        "tech_stack.json": _tech_stack_json(description),
    }


def _tech_stack_json(source_text: str) -> str:
    text = (source_text or "").lower()
    if "spring" in text or "java" in text:
        backend = {"language": "java", "version": "springboot3"}
    else:
        backend = {"language": "python", "version": "python3"}
    frontend = {"language": "vue", "version": "vue3"}
    return json.dumps({"backend": backend, "frontend": frontend}, ensure_ascii=False, indent=2)


def _apply_requirements_outputs(files: dict[str, str], req_dir: Path | None) -> list[str]:
    changes: list[str] = []
    if not req_dir or not req_dir.exists():
        return changes

    use_case = req_dir / "use_case.md"
    if use_case.exists():
        try:
            files["use_case.md"] = _compact_use_cases(use_case).strip() + "\n"
            changes.append(f"use_case.md <- {use_case} (compact use-case fields)")
        except Exception:
            files["use_case.md"] = _limit_text(_read_text(use_case), 12000).strip() + "\n"
            changes.append(f"use_case.md <- {use_case} (truncated fallback)")

    er = req_dir / "entity_relationship_diagram.md"
    if er.exists():
        content = _read_text(er)
        mermaid = _extract_fenced_block(content, "mermaid")
        files["entity_relationship_diagram.md"] = _wrap_fence(mermaid, "mermaid", "Entity Relationship Diagram") if mermaid else _limit_text(content, 12000).strip() + "\n"
        changes.append(f"entity_relationship_diagram.md <- {er} (filtered mermaid block when available)")

    return changes


def _apply_architecture_outputs(files: dict[str, str], arch_dir: Path | None) -> list[str]:
    changes: list[str] = []
    if not arch_dir or not arch_dir.exists():
        return changes

    component_json = arch_dir / "component_design.json"
    if component_json.exists():
        try:
            data = json.loads(_read_text(component_json))
            diagram = (data.get("component_diagram") or "").strip()
            if diagram:
                lang = "plantuml" if "@startuml" in diagram.lower() else "mermaid"
                files["component_diagram.md"] = _wrap_fence(diagram, lang, "Component Diagram")
                changes.append(f"component_diagram.md <- {component_json}: component_diagram")
        except Exception as exc:
            changes.append(f"component_design.json skipped: {exc}")

    class_json = arch_dir / "class_design_structured.json"
    if class_json.exists():
        try:
            content = _class_diagram_from_structured(class_json)
            if content:
                files["class_diagram.md"] = content
                changes.append(f"class_diagram.md <- {class_json}: class_design.class_diagram (prompt-sized)")
        except Exception as exc:
            changes.append(f"class_design_structured.json skipped: {exc}")

    if not files.get("class_diagram.md", "").strip():
        class_raw = arch_dir / "class_design_raw.md"
        if class_raw.exists():
            files["class_diagram.md"] = _limit_text(_read_text(class_raw), 12000).strip() + "\n"
            changes.append(f"class_diagram.md <- {class_raw} (truncated for prompt budget)")

    static_design = arch_dir / "modeling-3.static_design_output.txt"
    if static_design.exists():
        content = _read_text(static_design)
        package_lang, package = _extract_section_fence_any(content, r"UML\s+Package\s+Diagram|Package\s+Diagram")
        if package:
            files["package_diagram.md"] = _wrap_fence(package, package_lang or "mermaid", "Package Diagram")
            changes.append(f"package_diagram.md <- {static_design}: UML Package Diagram")

    tech_candidates = [
        arch_dir / "modeling-1.tech_stack_selection_output.txt",
        arch_dir / "modeling-3.static_design_output.txt",
    ]
    tech_text = "\n".join(_read_text(p) for p in tech_candidates if p.exists())
    existing_backend = ""
    try:
        existing_backend = (json.loads(files.get("tech_stack.json") or "{}").get("backend") or {}).get("language") or ""
    except Exception:
        existing_backend = ""
    if tech_text and not existing_backend:
        files["tech_stack.json"] = _tech_stack_json(tech_text)
        changes.append("tech_stack.json <- inferred from Architecture Agent outputs")
    elif tech_text:
        changes.append("tech_stack.json kept from original input/default; Architecture Agent tech stack recorded only in source artifacts")

    return changes


def _select_requirements_doc(req_dir: Path | None, input_file: Path) -> Path:
    if req_dir and (req_dir / "SRS.md").exists():
        return req_dir / "SRS.md"
    if req_dir and (req_dir / "use_case.md").exists():
        return req_dir / "use_case.md"
    return input_file


def _case_files_from_isd_outputs(
    case_name: str,
    project_name: str,
    description: str,
    req_dir: Path | None,
    arch_dir: Path | None,
    report_prefix: list[str] | None = None,
) -> dict[str, str]:
    files = _fallback_artifacts(project_name, description or project_name)
    source_changes: list[str] = []
    source_changes += _apply_requirements_outputs(files, req_dir)
    source_changes += _apply_architecture_outputs(files, arch_dir)
    source_changes += _apply_knomas_style_diagrams(files)
    files["input_source.md"] = (description or f"Imported iSoftDevAgent outputs for {project_name}").strip() + "\n"

    report_lines = list(report_prefix or [])
    report_lines += [
        f"- dataset: {GENERATED_DATASET}",
        f"- case_name: {case_name}",
        f"- requirements_output_dir: {str(req_dir).replace(chr(92), '/') if req_dir else '-'}",
        f"- architecture_output_dir: {str(arch_dir).replace(chr(92), '/') if arch_dir else '-'}",
        "",
        "## KnoMAS Artifact Mapping",
        "",
    ]
    report_lines += [f"- {line}" for line in source_changes] or ["- MAS fallback artifacts were used."]
    files["isoftdev_generation_report.md"] = "\n".join(report_lines).strip() + "\n"
    return files


def import_knomas_case_from_isd_outputs(payload: dict) -> dict:
    case_name = _slug(str(payload.get("case_name") or payload.get("project_name") or "generated_case"))
    project_name = str(payload.get("project_name") or case_name).strip()
    description = str(payload.get("description") or payload.get("input_text") or "").strip()
    req_raw = str(payload.get("requirements_output_dir") or "").strip()
    arch_raw = str(payload.get("architecture_output_dir") or "").strip()
    req_dir = Path(req_raw) if req_raw else None
    arch_dir = Path(arch_raw) if arch_raw else None
    overwrite = bool(payload.get("overwrite", False))

    if req_dir and not req_dir.exists():
        raise ValueError(f"Requirements Agent output not found: {req_dir}")
    if arch_dir and not arch_dir.exists():
        raise ValueError(f"Architecture Agent output not found: {arch_dir}")
    if not req_dir and not arch_dir:
        raise ValueError("requirements_output_dir or architecture_output_dir is required")

    files = _case_files_from_isd_outputs(
        case_name=case_name,
        project_name=project_name,
        description=description,
        req_dir=req_dir,
        arch_dir=arch_dir,
        report_prefix=[
            "# iSoftDevAgent Import Report",
            "",
            f"- project_name: {project_name}",
            "- source: existing iSoftDevAgent outputs",
        ],
    )

    try:
        result = create_knomas_case(GENERATED_DATASET, case_name, files)
    except FileExistsError:
        if overwrite:
            result = update_knomas_case(GENERATED_DATASET, case_name, files)
        else:
            existing = get_knomas_case_detail(GENERATED_DATASET, case_name)
            if not existing:
                raise
            result = {
                "ok": True,
                "dataset": GENERATED_DATASET,
                "case_name": case_name,
                "path": existing.get("path", ""),
                "case_dir": f"data/cases/{GENERATED_DATASET}/{case_name}",
                "already_exists": True,
            }

    result.update({
        "files": files,
        "requirements_output_dir": str(req_dir).replace("\\", "/") if req_dir else "",
        "architecture_output_dir": str(arch_dir).replace("\\", "/") if arch_dir else "",
    })
    return result


def generate_requirements_from_input(payload: dict, logger=None) -> dict:
    case_name = _slug(str(payload.get("case_name") or payload.get("project_name") or "generated_case"))
    project_name = str(payload.get("project_name") or case_name).strip()
    description = str(payload.get("description") or payload.get("input_text") or "").strip()
    timeout_sec = int(
        payload.get("requirements_timeout_sec")
        or os.getenv("ISOFTDEV_REQUIREMENTS_TIMEOUT_SEC", "0")
    )

    if not description:
        raise ValueError("description cannot be empty")

    if logger:
        logger(f"需求文档生成任务已接收: {case_name}")
        logger("归档自然语言需求输入")
    input_file = _write_input_file(project_name, description)
    req_dir, req_note = _run_requirements_agent(project_name, input_file, timeout_sec, logger)
    if logger:
        logger("需求文档生成完成，等待下一步架构设计")

    return {
        "dataset": GENERATED_DATASET,
        "case_name": case_name,
        "project_name": project_name,
        "description": description,
        "input_file": str(input_file).replace("\\", "/"),
        "requirements_output_dir": str(req_dir).replace("\\", "/") if req_dir else "",
        "requirements_note": req_note[-4000:],
    }


def generate_architecture_from_requirements(payload: dict, logger=None) -> dict:
    case_name = _slug(str(payload.get("case_name") or payload.get("project_name") or "generated_case"))
    project_name = str(payload.get("project_name") or case_name).strip()
    description = str(payload.get("description") or payload.get("input_text") or "").strip()
    req_raw = str(payload.get("requirements_output_dir") or "").strip()
    input_raw = str(payload.get("input_file") or "").strip()
    timeout_sec = int(
        payload.get("architecture_timeout_sec")
        or os.getenv("ISOFTDEV_ARCHITECTURE_TIMEOUT_SEC", os.getenv("ISOFTDEV_TIMEOUT_SEC", "10800"))
    )

    req_dir = Path(req_raw) if req_raw else None
    input_file = Path(input_raw) if input_raw else None
    if req_dir and not req_dir.exists():
        raise ValueError(f"Requirements Agent output not found: {req_dir}")
    if not req_dir:
        raise ValueError("requirements_output_dir is required")

    req_doc = input_file if input_file and input_file.exists() else _select_requirements_doc(req_dir, Path(""))
    if logger:
        logger("架构设计任务已接收")
        logger(f"使用需求产物目录: {req_dir}")
        logger(f"架构设计输入文档: {req_doc}")
        if input_file and input_file.exists():
            logger("架构设计将使用原始业务需求说明，完整 Requirements 产物仅用于案例映射")
    arch_dir, arch_note = _run_architecture_agent(project_name, req_doc, timeout_sec, logger)

    if logger:
        logger("映射 iSoftDevAgent 产物并写入 KnoMAS generated 数据集")
    files = _case_files_from_isd_outputs(
        case_name=case_name,
        project_name=project_name,
        description=description or f"Generated by iSoftDevAgent for {project_name}",
        req_dir=req_dir,
        arch_dir=arch_dir,
        report_prefix=[
            "# iSoftDevAgent Integration Report",
            "",
            f"- project_name: {project_name}",
            "- workflow: split requirements + architecture",
        ],
    )
    files["isoftdev_generation_report.md"] += "\n## Architecture Agent Log\n\n```text\n"
    files["isoftdev_generation_report.md"] += arch_note[-4000:]
    files["isoftdev_generation_report.md"] += "\n```\n"

    try:
        result = create_knomas_case(GENERATED_DATASET, case_name, files)
    except FileExistsError:
        result = update_knomas_case(GENERATED_DATASET, case_name, files)

    result.update({
        "dataset": GENERATED_DATASET,
        "case_name": case_name,
        "files": files,
        "requirements_output_dir": str(req_dir).replace("\\", "/") if req_dir else "",
        "architecture_output_dir": str(arch_dir).replace("\\", "/") if arch_dir else "",
    })
    if logger:
        logger("架构设计完成，已生成 KnoMAS 可执行案例")
    return result


def generate_knomas_case_from_input(payload: dict, logger=None) -> dict:
    case_name = _slug(str(payload.get("case_name") or payload.get("project_name") or "generated_case"))
    dataset = GENERATED_DATASET
    project_name = str(payload.get("project_name") or case_name).strip()
    description = str(payload.get("description") or payload.get("input_text") or "").strip()
    run_isd = bool(payload.get("run_isd", True))
    timeout_sec = int(payload.get("timeout_sec") or os.getenv("ISOFTDEV_TIMEOUT_SEC", "10800"))
    requirements_timeout_sec = int(
        payload.get("requirements_timeout_sec")
        or os.getenv("ISOFTDEV_REQUIREMENTS_TIMEOUT_SEC", "0")
    )
    architecture_timeout_sec = int(
        payload.get("architecture_timeout_sec")
        or os.getenv("ISOFTDEV_ARCHITECTURE_TIMEOUT_SEC", str(timeout_sec))
    )

    if not description:
        raise ValueError("description cannot be empty")

    if logger:
        logger(f"需求建模任务已接收: {case_name}")
        logger("归档自然语言需求输入")
    input_file = _write_input_file(project_name, description)
    if logger:
        logger("准备 fallback 产物，确保失败时也有可检查的案例骨架")
    files = _fallback_artifacts(project_name, description)
    report_lines = [
        "# iSoftDevAgent Integration Report",
        "",
        f"- project_name: {project_name}",
        f"- dataset: {dataset}",
        f"- case_name: {case_name}",
        f"- input_file: {str(input_file).replace(chr(92), '/')}",
        f"- run_isd: {run_isd}",
        "",
    ]

    req_dir: Path | None = None
    arch_dir: Path | None = None
    req_note = "Skipped."
    arch_note = "Skipped."
    source_changes: list[str] = []

    if run_isd:
        req_dir, req_note = _run_requirements_agent(project_name, input_file, requirements_timeout_sec, logger)
        if logger:
            logger("映射 Requirements Agent 产物: use_case / ER")
        source_changes += _apply_requirements_outputs(files, req_dir)

        req_doc = _select_requirements_doc(req_dir, input_file)
        if logger and req_doc == input_file:
            logger("未找到 SRS/use_case 输出，Architecture Agent 将使用原始需求输入继续执行")
        arch_dir, arch_note = _run_architecture_agent(project_name, req_doc, architecture_timeout_sec, logger)
        if logger:
            logger("映射 Architecture Agent 产物: class / component / package / tech stack")
        source_changes += _apply_architecture_outputs(files, arch_dir)
        source_changes += _apply_knomas_style_diagrams(files)

    files["input_source.md"] = description + "\n"
    report_lines += [
        f"- requirements_output_dir: {str(req_dir).replace(chr(92), '/') if req_dir else '-'}",
        f"- architecture_output_dir: {str(arch_dir).replace(chr(92), '/') if arch_dir else '-'}",
        "",
        "## KnoMAS Artifact Mapping",
        "",
    ]
    report_lines += [f"- {line}" for line in source_changes] or ["- MAS fallback artifacts were used."]
    report_lines += [
        "",
        "## Requirements Agent Log",
        "",
        "```text",
        req_note[-4000:],
        "```",
        "",
        "## Architecture Agent Log",
        "",
        "```text",
        arch_note[-4000:],
        "```",
        "",
    ]
    files["isoftdev_generation_report.md"] = "\n".join(report_lines)

    if logger:
        logger(f"写入 KnoMAS 案例: {dataset}/{case_name}")
    try:
        result = create_knomas_case(dataset, case_name, files)
    except FileExistsError:
        if logger:
            logger("案例已存在，更新已有 generated 案例")
        result = update_knomas_case(dataset, case_name, files)

    result.update({
        "dataset": dataset,
        "case_name": case_name,
        "files": files,
        "requirements_output_dir": str(req_dir).replace("\\", "/") if req_dir else "",
        "architecture_output_dir": str(arch_dir).replace("\\", "/") if arch_dir else "",
    })
    if logger:
        logger("需求建模完成，已生成 KnoMAS 可执行案例")
    return result
