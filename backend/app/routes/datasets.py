from fastapi import APIRouter, HTTPException

import threading
import time
import traceback
import uuid

from ..ccg_dataset import (
    create_function,
    delete_function,
    get_function_by_id,
    get_stats,
    list_functions,
    list_repos,
    list_tables,
    update_function,
)
from ..knomas_dataset import (
    create_knomas_case,
    delete_knomas_case,
    get_knomas_case_detail,
    get_knomas_root_info,
    knomas_dataset_exists,
    list_knomas_cases,
    update_knomas_case,
)
from ..isoftdev_adapter import (
    generate_architecture_from_requirements,
    generate_knomas_case_from_input,
    generate_requirements_from_input,
    import_knomas_case_from_isd_outputs,
    list_isd_output_artifacts,
    read_isd_output_artifact,
    save_isd_output_artifact,
)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])
_KNOMAS_INPUT_JOBS: dict[str, dict] = {}
_KNOMAS_INPUT_JOBS_LOCK = threading.Lock()


def _api_error(code: str, message: str, detail: str | None = None):
    return {"code": code, "message": message, "detail": detail or ""}


def _append_input_job_log(job_id: str, line: str):
    ts = time.strftime("%H:%M:%S")
    with _KNOMAS_INPUT_JOBS_LOCK:
        job = _KNOMAS_INPUT_JOBS.get(job_id)
        if not job:
            return
        job.setdefault("logs", []).append(f"[{ts}] {line}")
        job["updated_at"] = time.time()


def _run_input_job(job_id: str, payload: dict):
    with _KNOMAS_INPUT_JOBS_LOCK:
        _KNOMAS_INPUT_JOBS[job_id]["status"] = "running"
        _KNOMAS_INPUT_JOBS[job_id]["updated_at"] = time.time()
    try:
        result = generate_knomas_case_from_input(payload, logger=lambda line: _append_input_job_log(job_id, line))
        with _KNOMAS_INPUT_JOBS_LOCK:
            _KNOMAS_INPUT_JOBS[job_id]["status"] = "finished"
            _KNOMAS_INPUT_JOBS[job_id]["result"] = result
            _KNOMAS_INPUT_JOBS[job_id]["updated_at"] = time.time()
    except Exception as exc:
        _append_input_job_log(job_id, f"需求建模失败: {exc}")
        _append_input_job_log(job_id, traceback.format_exc(limit=8))
        with _KNOMAS_INPUT_JOBS_LOCK:
            _KNOMAS_INPUT_JOBS[job_id]["status"] = "failed"
            _KNOMAS_INPUT_JOBS[job_id]["error"] = str(exc)
            _KNOMAS_INPUT_JOBS[job_id]["updated_at"] = time.time()


def _run_requirements_job(job_id: str, payload: dict):
    with _KNOMAS_INPUT_JOBS_LOCK:
        _KNOMAS_INPUT_JOBS[job_id]["status"] = "running"
        _KNOMAS_INPUT_JOBS[job_id]["updated_at"] = time.time()
    try:
        result = generate_requirements_from_input(payload, logger=lambda line: _append_input_job_log(job_id, line))
        with _KNOMAS_INPUT_JOBS_LOCK:
            _KNOMAS_INPUT_JOBS[job_id]["status"] = "finished"
            _KNOMAS_INPUT_JOBS[job_id]["result"] = result
            _KNOMAS_INPUT_JOBS[job_id]["updated_at"] = time.time()
    except Exception as exc:
        _append_input_job_log(job_id, f"需求文档生成失败: {exc}")
        _append_input_job_log(job_id, traceback.format_exc(limit=8))
        with _KNOMAS_INPUT_JOBS_LOCK:
            _KNOMAS_INPUT_JOBS[job_id]["status"] = "failed"
            _KNOMAS_INPUT_JOBS[job_id]["error"] = str(exc)
            _KNOMAS_INPUT_JOBS[job_id]["updated_at"] = time.time()


def _run_architecture_job(job_id: str, payload: dict):
    with _KNOMAS_INPUT_JOBS_LOCK:
        _KNOMAS_INPUT_JOBS[job_id]["status"] = "running"
        _KNOMAS_INPUT_JOBS[job_id]["updated_at"] = time.time()
    try:
        result = generate_architecture_from_requirements(payload, logger=lambda line: _append_input_job_log(job_id, line))
        with _KNOMAS_INPUT_JOBS_LOCK:
            _KNOMAS_INPUT_JOBS[job_id]["status"] = "finished"
            _KNOMAS_INPUT_JOBS[job_id]["result"] = result
            _KNOMAS_INPUT_JOBS[job_id]["updated_at"] = time.time()
    except Exception as exc:
        _append_input_job_log(job_id, f"架构产物生成失败: {exc}")
        _append_input_job_log(job_id, traceback.format_exc(limit=8))
        with _KNOMAS_INPUT_JOBS_LOCK:
            _KNOMAS_INPUT_JOBS[job_id]["status"] = "failed"
            _KNOMAS_INPUT_JOBS[job_id]["error"] = str(exc)
            _KNOMAS_INPUT_JOBS[job_id]["updated_at"] = time.time()


@router.get("/ccg/tables")
def ccg_dataset_tables():
    return {"tables": list_tables()}


@router.get("/ccg/stats")
def ccg_dataset_stats(migration_type: str | None = None):
    if migration_type and migration_type not in {"arch", "os"}:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "migration_type 必须是 arch 或 os"))
    try:
        return get_stats(migration_type=migration_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("CCG_DB_ERROR", "读取 CCGMAS 统计失败", str(e)))


@router.get("/ccg/repos")
def ccg_dataset_repos():
    try:
        return list_repos()
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("CCG_DB_ERROR", "读取 CCGMAS 仓库列表失败", str(e)))


@router.get("/ccg/functions/{function_id}")
def ccg_dataset_function_detail(function_id: int):
    if function_id < 1:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "function_id 必须 >= 1"))
    try:
        item = get_function_by_id(function_id)
        if not item:
            raise HTTPException(status_code=404, detail=_api_error("NOT_FOUND", "函数样本不存在"))
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("CCG_DB_ERROR", "读取 CCGMAS 函数详情失败", str(e)))


@router.post("/ccg/functions")
def ccg_dataset_create_function(payload: dict):
    required = ["repo", "func_name", "source_code", "migration_type", "source_platform", "target_platform"]
    missing = [k for k in required if not str(payload.get(k, "")).strip()]
    if missing:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", f"缺少必填字段: {', '.join(missing)}"))
    if payload.get("migration_type") not in {"arch", "os"}:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "migration_type 必须是 arch 或 os"))
    try:
        new_id = create_function(payload)
        return {"id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("CCG_DB_ERROR", "新增 CCGMAS 样本失败", str(e)))


@router.put("/ccg/functions/{function_id}")
def ccg_dataset_update_function(function_id: int, payload: dict):
    if function_id < 1:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "function_id 必须 >= 1"))
    if "migration_type" in payload and payload.get("migration_type") not in {"arch", "os"}:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "migration_type 必须是 arch 或 os"))
    try:
        ok = update_function(function_id, payload)
        if not ok:
            raise HTTPException(status_code=404, detail=_api_error("NOT_FOUND", "函数样本不存在或未发生变更"))
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("CCG_DB_ERROR", "更新 CCGMAS 样本失败", str(e)))


@router.delete("/ccg/functions/{function_id}")
def ccg_dataset_delete_function(function_id: int):
    if function_id < 1:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "function_id 必须 >= 1"))
    try:
        ok = delete_function(function_id)
        if not ok:
            raise HTTPException(status_code=404, detail=_api_error("NOT_FOUND", "函数样本不存在"))
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("CCG_DB_ERROR", "删除 CCGMAS 样本失败", str(e)))


@router.get("/ccg/functions")
def ccg_dataset_functions(
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
):
    if page < 1:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "page 必须 >= 1"))
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "page_size 必须在 1~100 之间"))
    if migration_type and migration_type not in {"arch", "os"}:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "migration_type 必须是 arch 或 os"))
    try:
        return list_functions(
            page=page,
            page_size=page_size,
            migration_type=migration_type,
            repo=repo,
            complexity=complexity,
            split=split,
            has_gt=has_gt,
            source_platform=source_platform,
            target_platform=target_platform,
            risk_level=risk_level,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("CCG_DB_ERROR", "读取 CCGMAS 函数列表失败", str(e)))


@router.get("/knomas/info")
def knomas_dataset_info():
    try:
        return get_knomas_root_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("KNOMAS_DATA_ERROR", "读取 KnoMAS 根目录信息失败", str(e)))


@router.get("/knomas/cases")
def knomas_dataset_cases(dataset: str | None = None, keyword: str | None = None, limit: int = 500):
    if dataset and not knomas_dataset_exists(dataset):
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", f"dataset 不存在: {dataset}"))
    if limit < 1 or limit > 5000:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "limit 必须在 1~5000 之间"))
    try:
        return {"items": list_knomas_cases(limit=limit, dataset=dataset, keyword=keyword)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("KNOMAS_DATA_ERROR", "读取 KnoMAS 案例列表失败", str(e)))


@router.get("/knomas/cases/{dataset}/{case_name}")
def knomas_case_detail(dataset: str, case_name: str):
    if not knomas_dataset_exists(dataset):
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", f"dataset 不存在: {dataset}"))
    try:
        item = get_knomas_case_detail(dataset, case_name)
        if not item:
            raise HTTPException(status_code=404, detail=_api_error("NOT_FOUND", "案例不存在"))
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("KNOMAS_DATA_ERROR", "读取 KnoMAS 案例详情失败", str(e)))


@router.post("/knomas/cases")
def knomas_case_create(payload: dict):
    dataset = str(payload.get("dataset") or "")
    case_name = str(payload.get("case_name") or "")
    if not dataset.strip():
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "dataset 不能为空"))
    if not case_name.strip():
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "case_name 不能为空"))
    try:
        return create_knomas_case(dataset, case_name, payload.get("files") or {})
    except FileExistsError:
        raise HTTPException(status_code=409, detail=_api_error("ALREADY_EXISTS", "案例已存在"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("KNOMAS_DATA_ERROR", "创建 KnoMAS 案例失败", str(e)))


@router.post("/knomas/cases/from-input")
def knomas_case_from_input(payload: dict):
    case_name = str(payload.get("case_name") or payload.get("project_name") or "")
    description = str(payload.get("description") or payload.get("input_text") or "")
    if not case_name.strip():
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "case_name/project_name 不能为空"))
    if not description.strip():
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "原始输入不能为空"))
    try:
        return generate_knomas_case_from_input(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", str(e)))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("ISD_ADAPTER_ERROR", "从输入生成 KnoMAS 案例失败", str(e)))


@router.post("/knomas/cases/from-input/jobs")
def knomas_case_from_input_job(payload: dict):
    case_name = str(payload.get("case_name") or payload.get("project_name") or "")
    description = str(payload.get("description") or payload.get("input_text") or "")
    if not case_name.strip():
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "case_name/project_name 不能为空"))
    if not description.strip():
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "原始输入不能为空"))

    job_id = f"input_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    with _KNOMAS_INPUT_JOBS_LOCK:
        _KNOMAS_INPUT_JOBS[job_id] = {
            "job_id": job_id,
            "status": "accepted",
            "logs": [],
            "result": None,
            "error": "",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
    _append_input_job_log(job_id, "需求建模任务已提交，等待后台执行")
    thread = threading.Thread(target=_run_input_job, args=(job_id, dict(payload)), daemon=True)
    thread.start()
    return {"job_id": job_id, "status": "accepted"}


@router.post("/knomas/cases/from-input/requirements/jobs")
def knomas_case_requirements_job(payload: dict):
    case_name = str(payload.get("case_name") or payload.get("project_name") or "")
    description = str(payload.get("description") or payload.get("input_text") or "")
    if not case_name.strip():
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "case_name/project_name 不能为空"))
    if not description.strip():
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "原始输入不能为空"))

    job_id = f"requirements_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    with _KNOMAS_INPUT_JOBS_LOCK:
        _KNOMAS_INPUT_JOBS[job_id] = {
            "job_id": job_id,
            "status": "accepted",
            "logs": [],
            "result": None,
            "error": "",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
    _append_input_job_log(job_id, "需求规格生成任务已提交，等待后台执行")
    thread = threading.Thread(target=_run_requirements_job, args=(job_id, dict(payload)), daemon=True)
    thread.start()
    return {"job_id": job_id, "status": "accepted"}


@router.post("/knomas/cases/from-input/architecture/jobs")
def knomas_case_architecture_job(payload: dict):
    case_name = str(payload.get("case_name") or payload.get("project_name") or "")
    req_dir = str(payload.get("requirements_output_dir") or "")
    if not case_name.strip():
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "case_name/project_name 不能为空"))
    if not req_dir.strip():
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "requirements_output_dir 不能为空"))

    job_id = f"architecture_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    with _KNOMAS_INPUT_JOBS_LOCK:
        _KNOMAS_INPUT_JOBS[job_id] = {
            "job_id": job_id,
            "status": "accepted",
            "logs": [],
            "result": None,
            "error": "",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
    _append_input_job_log(job_id, "架构设计生成任务已提交，等待后台执行")
    thread = threading.Thread(target=_run_architecture_job, args=(job_id, dict(payload)), daemon=True)
    thread.start()
    return {"job_id": job_id, "status": "accepted"}


@router.get("/knomas/cases/from-input/jobs/{job_id}")
def knomas_case_from_input_job_status(job_id: str):
    with _KNOMAS_INPUT_JOBS_LOCK:
        job = _KNOMAS_INPUT_JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=_api_error("NOT_FOUND", "需求建模任务不存在"))
        return {
            "job_id": job_id,
            "status": job.get("status", "unknown"),
            "logs": list(job.get("logs") or [])[-200:],
            "result": job.get("result"),
            "error": job.get("error", ""),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
        }


@router.get("/knomas/isoftdev/artifacts")
def knomas_isoftdev_artifacts(kind: str, output_dir: str):
    try:
        return list_isd_output_artifacts(kind, output_dir)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", str(e)))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("ISD_ARTIFACT_ERROR", "读取 iSoftDevAgent 产物列表失败", str(e)))


@router.get("/knomas/isoftdev/artifacts/content")
def knomas_isoftdev_artifact_content(kind: str, output_dir: str, rel_path: str):
    try:
        return read_isd_output_artifact(kind, output_dir, rel_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=_api_error("NOT_FOUND", "产物文件不存在"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", str(e)))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("ISD_ARTIFACT_ERROR", "读取 iSoftDevAgent 产物内容失败", str(e)))


@router.put("/knomas/isoftdev/artifacts/content")
def knomas_isoftdev_artifact_save(payload: dict):
    try:
        return save_isd_output_artifact(
            str(payload.get("kind") or ""),
            str(payload.get("output_dir") or ""),
            str(payload.get("rel_path") or ""),
            str(payload.get("content") or ""),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=_api_error("NOT_FOUND", "产物文件不存在"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", str(e)))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("ISD_ARTIFACT_ERROR", "保存 iSoftDevAgent 产物失败", str(e)))


@router.post("/knomas/cases/import-isoftdev")
def knomas_case_import_isoftdev(payload: dict):
    case_name = str(payload.get("case_name") or payload.get("project_name") or "")
    if not case_name.strip():
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", "case_name/project_name 不能为空"))
    try:
        return import_knomas_case_from_isd_outputs(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", str(e)))
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("ISD_ADAPTER_ERROR", "同步 iSoftDevAgent 产物失败", str(e)))


@router.put("/knomas/cases/{dataset}/{case_name}")
def knomas_case_update(dataset: str, case_name: str, payload: dict):
    if not knomas_dataset_exists(dataset):
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", f"dataset 不存在: {dataset}"))
    try:
        ret = update_knomas_case(dataset, case_name, payload.get("files") or {})
        if not ret.get("ok"):
            raise HTTPException(status_code=404, detail=_api_error("NOT_FOUND", "案例不存在"))
        return ret
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("KNOMAS_DATA_ERROR", "更新 KnoMAS 案例失败", str(e)))


@router.delete("/knomas/cases/{dataset}/{case_name}")
def knomas_case_delete(dataset: str, case_name: str):
    if not knomas_dataset_exists(dataset):
        raise HTTPException(status_code=400, detail=_api_error("INVALID_PARAM", f"dataset 不存在: {dataset}"))
    try:
        ret = delete_knomas_case(dataset, case_name)
        if not ret.get("ok"):
            raise HTTPException(status_code=404, detail=_api_error("NOT_FOUND", "案例不存在"))
        return ret
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_api_error("KNOMAS_DATA_ERROR", "删除 KnoMAS 案例失败", str(e)))
