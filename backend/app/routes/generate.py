"""
代码迁移路由：
- POST /api/generate （全流程）
- POST /api/run/paa
- POST /api/run/rga
- POST /api/run/cga
- POST /api/run/va
"""
import time
from fastapi import APIRouter, HTTPException

from app.agents.paa import run_paa
from app.agents.rga import run_rga
from app.agents.cga import run_cga
from app.agents.va import run_va
from app.agents.va_test_validation import run_va_test_validation
from app.core.llm import call_llm, extract_code, set_runtime_llm_config, reset_runtime_llm_config
from app.core import database as db
from app.routes.metrics import CandidateRecord, MetricsRequest, SampleRecord, evaluate_metrics

router = APIRouter(prefix="/api", tags=["generate"])


def _ensure_go_file(code: str) -> str:
    if "package " in code:
        return code
    return "package main\n\n" + code


def _repair_candidates_by_feedback(candidates: list[str], feedback: str, model: str, k: int) -> list[str]:
    if not candidates:
        return candidates
    system = "你是Go代码修复工程师，根据验证反馈修复目标平台代码。"
    user = (
        "请根据以下反馈修复候选代码，输出完整Go代码：\n\n"
        f"反馈:\n{feedback}\n\n"
        f"候选代码:\n```go\n{candidates[0]}\n```\n"
    )
    fixed = _ensure_go_file(extract_code(call_llm(system, user, model)))
    return [fixed] + candidates[1:k]


def _regenerate_with_stronger_constraints(
    arm64_code: str,
    generic_code: str,
    srs: str,
    arp: dict,
    model: str,
    k: int,
    migration_type: str = "arch",
    target_os: str = "linux",
    target_arch: str = "riscv64",
    project_context_files: list[dict] | None = None,
) -> list[str]:
    extra = (
        "\n\n[闭环强化约束]\n"
        "- 严禁源平台残留标识（架构/OS/build tag/syscall常量）\n"
        "- 保持函数签名一致\n"
        "- 仅输出可编译的目标平台实现\n"
    )
    arm_pats = [r.get("type", "") for r in arp.get("residues", [])]
    cands = run_cga(
        arm64_code,
        generic_code,
        srs + extra,
        arp,
        model,
        k,
        arm_pats,
        migration_type=migration_type,
        target_os=target_os,
        target_arch=target_arch,
        project_context_files=project_context_files,
    )
    return [_ensure_go_file(c) for c in cands]


def _merge_test_validation_into_va(va: dict, test_validation: dict) -> dict:
    va = va or {}
    test_validation = test_validation or {}
    by_id = {x.get("id"): x for x in (test_validation.get("candidates") or [])}

    for c in (va.get("candidates") or []):
        tc = by_id.get(c.get("id")) or {}
        c["test_validation"] = tc
        test_failed = bool(tc.get("executed")) and not bool(tc.get("passed"))
        if test_failed and c.get("failure_type") == "none":
            c["failure_type"] = "test_failure"
            c["route_suggestion"] = "route:CGA_patch"
            reason = tc.get("reason", "test_failed")
            out = (tc.get("test_output") or "")[:500]
            c["feedback_for_cga"] = (
                "上一次生成在测试验证阶段失败，请修复以下问题：\n"
                f"- 测试原因：{reason}\n"
                f"- go test 输出：{out}\n"
                "- 请保持函数签名不变，修复逻辑/边界处理后返回完整 Go 代码。"
            )

    va["test_validation"] = {
        "n_test_executed": test_validation.get("n_test_executed", 0),
        "n_test_pass": test_validation.get("n_test_pass", 0),
        "test_pass_rate": test_validation.get("test_pass_rate", 0),
        "total": test_validation.get("total", 0),
    }
    return va


def _metrics_from_va(
    va: dict,
    pass_k: int,
    migration_type: str,
    target_os: str,
    target_arch: str,
    ground_truth: str = "",
) -> dict:
    candidates = []
    for c in va.get("candidates") or []:
        tv = c.get("test_validation") or {}
        rt = c.get("runtime") or {}
        candidates.append(CandidateRecord(
            code=c.get("code") or "",
            compile_ok=c.get("compile_ok"),
            residues=c.get("residues") or [],
            residue=bool(c.get("residues")),
            test_pass=tv.get("passed") if tv else None,
            runtime_pass=rt.get("passed") if rt else None,
            selected=(va.get("best") or {}).get("id") == c.get("id"),
        ))

    sample = SampleRecord(
        migration_type=migration_type,
        has_gt=bool((ground_truth or "").strip()),
        target_code=ground_truth or "",
        target_os=target_os,
        target_arch=target_arch,
        candidates=candidates,
    )
    return evaluate_metrics(MetricsRequest(samples=[sample], pass_k=pass_k)).get("overall", {})


def _apply_runtime_config(req: dict):
    runtime_token = None
    runtime_llm_config = req.get("runtime_llm_config")
    if runtime_llm_config:
        runtime_token = set_runtime_llm_config(runtime_llm_config)
    return runtime_token


def _extract_common(req: dict):
    arm64_code = str(req.get("source_code") or req.get("arm64_code") or "")
    if not arm64_code.strip():
        raise HTTPException(status_code=400, detail={"code": "INVALID_PARAM", "message": "source_code 不能为空（函数级输入）"})

    migration_type = str(req.get("migration_type") or "arch")
    source_platform = str(req.get("source_platform") or "")
    target_platform = str(req.get("target_platform") or "")

    return {
        "arm64_code": arm64_code,
        "generic_code": str(req.get("generic_code") or ""),
        "ground_truth": str(req.get("ground_truth") or ""),
        "model": str(req.get("model") or "glm-5"),
        "eval_profiles": req.get("eval_profiles") or None,
        "k": int(req.get("k") or 3),
        "rga_max_iter": int(req.get("rga_max_iter") or 2),
        "max_feedback_rounds": int(req.get("max_feedback_rounds") or 1),
        "migration_type": migration_type,
        "source_platform": source_platform,
        "target_platform": target_platform,
        "target_os": str(req.get("target_os") or ("linux" if migration_type == "arch" else (target_platform or "windows"))),
        "target_arch": str(req.get("target_arch") or ("riscv64" if migration_type == "arch" else "amd64")),
        "enable_runtime": bool(req.get("enable_runtime", False)),
        "qemu_bin": str(req.get("qemu_bin") or r"E:\qemu\qemu-riscv64.exe"),
        "runtime_timeout_sec": int(req.get("runtime_timeout_sec") or 5),
        "enable_test_validation": bool(req.get("enable_test_validation", True)),
        "test_timeout_sec": int(req.get("test_timeout_sec") or 30),
        "project_context_files": req.get("project_context_files") or None,
        "func_id": req.get("func_id"),
    }


@router.post("/generate")
def generate(req: dict):
    t_all = time.time()
    runtime_token = None
    try:
        p = _extract_common(req)
        runtime_token = _apply_runtime_config(req)

        arp = run_paa(
            p["arm64_code"],
            p["model"],
            expected_scope=p["migration_type"],
            generic_code=p["generic_code"],
            project_context_files=p["project_context_files"],
        )
        srs, semantic_info, rga_quality = run_rga(
            p["arm64_code"],
            p["generic_code"],
            arp,
            p["model"],
            max_iter=p["rga_max_iter"],
            eval_profiles=p["eval_profiles"],
            project_context_files=p["project_context_files"],
        )

        arm_pats = [r.get("type", "") for r in arp.get("residues", [])]
        candidates = run_cga(
            p["arm64_code"],
            p["generic_code"],
            srs,
            arp,
            p["model"],
            p["k"],
            arm_pats,
            migration_type=p["migration_type"],
            target_os=p["target_os"],
            target_arch=p["target_arch"],
            project_context_files=p["project_context_files"],
        )
        candidates = [_ensure_go_file(c) for c in candidates]

        va = run_va(
            candidates,
            migration_type=p["migration_type"],
            target_os=p["target_os"],
            target_arch=p["target_arch"],
            ground_truth=p["ground_truth"],
            enable_runtime=p["enable_runtime"],
            qemu_bin=p["qemu_bin"],
            runtime_timeout_sec=p["runtime_timeout_sec"],
        )
        if p["enable_test_validation"]:
            test_validation = run_va_test_validation(
                candidates=va.get("candidates", []),
                srs=srs,
                semantic_info=semantic_info,
                model=p["model"],
                target_os=p["target_os"],
                target_arch=p["target_arch"],
                timeout_sec=p["test_timeout_sec"],
            )
            va = _merge_test_validation_into_va(va, test_validation)
        va["experiment_metrics"] = _metrics_from_va(
            va,
            pass_k=p["k"],
            migration_type=p["migration_type"],
            target_os=p["target_os"],
            target_arch=p["target_arch"],
            ground_truth=p["ground_truth"],
        )

        feedback_trace = []
        for r in range(p["max_feedback_rounds"]):
            first = (va.get("candidates") or [{}])[0]
            failure_type = first.get("failure_type", "none")
            route = first.get("route_suggestion", "route:none")
            if failure_type == "none":
                break

            if route == "route:CGA_patch":
                feedback = first.get("feedback_for_cga", "请修复编译错误")
                candidates = _repair_candidates_by_feedback(candidates, feedback, p["model"], p["k"])
            elif route == "route:RGA_rebuild_then_CGA":
                srs, _, rga_quality = run_rga(p["arm64_code"], p["generic_code"], arp, p["model"], max_iter=p["rga_max_iter"], eval_profiles=p["eval_profiles"], project_context_files=p["project_context_files"])
                candidates = _regenerate_with_stronger_constraints(
                    p["arm64_code"],
                    p["generic_code"],
                    srs,
                    arp,
                    p["model"],
                    p["k"],
                    migration_type=p["migration_type"],
                    target_os=p["target_os"],
                    target_arch=p["target_arch"],
                    project_context_files=p["project_context_files"],
                )
            elif route == "route:strengthen_platform_constraints_then_regenerate":
                candidates = _regenerate_with_stronger_constraints(
                    p["arm64_code"],
                    p["generic_code"],
                    srs,
                    arp,
                    p["model"],
                    p["k"],
                    migration_type=p["migration_type"],
                    target_os=p["target_os"],
                    target_arch=p["target_arch"],
                    project_context_files=p["project_context_files"],
                )
            else:
                break

            va = run_va(candidates, migration_type=p["migration_type"], target_os=p["target_os"], target_arch=p["target_arch"], ground_truth=p["ground_truth"], enable_runtime=p["enable_runtime"], qemu_bin=p["qemu_bin"], runtime_timeout_sec=p["runtime_timeout_sec"])
            if p["enable_test_validation"]:
                test_validation = run_va_test_validation(candidates=va.get("candidates", []), srs=srs, semantic_info=semantic_info, model=p["model"], target_os=p["target_os"], target_arch=p["target_arch"], timeout_sec=p["test_timeout_sec"])
                va = _merge_test_validation_into_va(va, test_validation)
            va["experiment_metrics"] = _metrics_from_va(
                va,
                pass_k=p["k"],
                migration_type=p["migration_type"],
                target_os=p["target_os"],
                target_arch=p["target_arch"],
                ground_truth=p["ground_truth"],
            )

            tv = va.get("test_validation") or {}
            feedback_trace.append({"round": r + 1, "route": route, "n_compile_ok": va.get("n_compile_ok", 0), "n_residue": va.get("n_residue", 0), "n_test_executed": tv.get("n_test_executed", 0), "n_test_pass": tv.get("n_test_pass", 0)})

        persist_ok = False
        if p["func_id"] is not None:
            persist_ok = db.upsert_rga_planning(int(p["func_id"]), rga_quality)
            if not persist_ok:
                db.mark_rga_planning_failed(int(p["func_id"]), "自动写回失败：upsert 返回 false", increase_retry=False)

        return {
            "arp": arp,
            "srs": srs,
            "semantic_info": semantic_info,
            "rga_quality": rga_quality,
            "candidates": candidates,
            "va": va,
            "feedback_trace": feedback_trace,
            "persist": {"func_id": p["func_id"], "planning_saved": persist_ok},
            "elapsed_sec": round(time.time() - t_all, 2),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "GENERATE_ERROR", "message": "生成流程失败", "detail": str(e)})
    finally:
        if runtime_token is not None:
            reset_runtime_llm_config(runtime_token)


@router.post("/run/paa")
def run_paa_only(req: dict):
    runtime_token = None
    try:
        p = _extract_common(req)
        runtime_token = _apply_runtime_config(req)
        arp = run_paa(
            p["arm64_code"],
            p["model"],
            expected_scope=p["migration_type"],
            generic_code=p["generic_code"],
            project_context_files=p["project_context_files"],
        )
        return {"arp": arp}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "PAA_ERROR", "message": "PAA 执行失败", "detail": str(e)})
    finally:
        if runtime_token is not None:
            reset_runtime_llm_config(runtime_token)


@router.post("/run/rga")
def run_rga_only(req: dict):
    runtime_token = None
    try:
        p = _extract_common(req)
        runtime_token = _apply_runtime_config(req)
        arp = req.get("arp") or run_paa(
            p["arm64_code"],
            p["model"],
            expected_scope=p["migration_type"],
            generic_code=p["generic_code"],
            project_context_files=p["project_context_files"],
        )
        srs, semantic_info, rga_quality = run_rga(p["arm64_code"], p["generic_code"], arp, p["model"], max_iter=p["rga_max_iter"], eval_profiles=p["eval_profiles"], project_context_files=p["project_context_files"])
        return {"arp": arp, "srs": srs, "semantic_info": semantic_info, "rga_quality": rga_quality}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "RGA_ERROR", "message": "RGA 执行失败", "detail": str(e)})
    finally:
        if runtime_token is not None:
            reset_runtime_llm_config(runtime_token)


@router.post("/run/cga")
def run_cga_only(req: dict):
    runtime_token = None
    try:
        p = _extract_common(req)
        runtime_token = _apply_runtime_config(req)
        arp = req.get("arp") or run_paa(
            p["arm64_code"],
            p["model"],
            expected_scope=p["migration_type"],
            generic_code=p["generic_code"],
            project_context_files=p["project_context_files"],
        )
        srs = req.get("srs")
        if not srs:
            srs, _, _ = run_rga(p["arm64_code"], p["generic_code"], arp, p["model"], max_iter=p["rga_max_iter"], eval_profiles=p["eval_profiles"], project_context_files=p["project_context_files"])
        arm_pats = [r.get("type", "") for r in arp.get("residues", [])]
        candidates = run_cga(
            p["arm64_code"],
            p["generic_code"],
            srs,
            arp,
            p["model"],
            p["k"],
            arm_pats,
            migration_type=p["migration_type"],
            target_os=p["target_os"],
            target_arch=p["target_arch"],
            project_context_files=p["project_context_files"],
        )
        return {"arp": arp, "srs": srs, "candidates": [_ensure_go_file(c) for c in candidates]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "CGA_ERROR", "message": "CGA 执行失败", "detail": str(e)})
    finally:
        if runtime_token is not None:
            reset_runtime_llm_config(runtime_token)


@router.post("/run/va")
def run_va_only(req: dict):
    runtime_token = None
    try:
        p = _extract_common(req)
        runtime_token = _apply_runtime_config(req)
        candidates = req.get("candidates") or []
        if not candidates:
            raise HTTPException(status_code=400, detail={"code": "INVALID_PARAM", "message": "candidates 不能为空"})
        va = run_va(candidates, migration_type=p["migration_type"], target_os=p["target_os"], target_arch=p["target_arch"], ground_truth=p["ground_truth"], enable_runtime=p["enable_runtime"], qemu_bin=p["qemu_bin"], runtime_timeout_sec=p["runtime_timeout_sec"])
        if p["enable_test_validation"]:
            test_validation = run_va_test_validation(candidates=va.get("candidates", []), srs=str(req.get("srs") or ""), semantic_info=req.get("semantic_info") or {}, model=p["model"], target_os=p["target_os"], target_arch=p["target_arch"], timeout_sec=p["test_timeout_sec"])
            va = _merge_test_validation_into_va(va, test_validation)
        va["experiment_metrics"] = _metrics_from_va(
            va,
            pass_k=len(candidates) or 1,
            migration_type=p["migration_type"],
            target_os=p["target_os"],
            target_arch=p["target_arch"],
            ground_truth=p["ground_truth"],
        )
        return {"va": va}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "VA_ERROR", "message": "VA 执行失败", "detail": str(e)})
    finally:
        if runtime_token is not None:
            reset_runtime_llm_config(runtime_token)
