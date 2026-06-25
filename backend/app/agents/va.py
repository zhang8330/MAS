"""
VA — Verification Agent
职责：分层验证 + 失败分类 + 闭环路由建议
- 静态残留扫描（平台相关）
- 交叉编译验证
- 可选 QEMU 运行对比（与 GT 同输入同输出）
"""
import os
import re
import subprocess
import tempfile
from typing import Optional

# 平台残留规则（架构 + OS）
_PLATFORM_PATTERNS: dict[str, str] = {
    "arm64 标识符": r"\barm64\b",
    "amd64 标识符": r"\bamd64\b",
    "x86 指令": r"\b(SSE|AVX|MMX)\b",
    "NEON 指令": r"\bNEON\b",
    "ARM Plan9 汇编": r"TEXT\s+·|NOSPLIT|LDAXR|STLXR",
    "ARM 硬件特性": r"cpu\.ARM64\.",
    "linux 标识符": r"\blinux\b",
    "windows 标识符": r"\bwindows\b",
    "darwin 标识符": r"\bdarwin\b",
    "GOOS 分支": r"runtime\.GOOS",
    "平台 build tag": r"//go:build.*(arm64|amd64|linux|windows|darwin)",
}


def _scan_residues(code: str, migration_type: str = "arch", target_os: str = "linux", target_arch: str = "riscv64") -> list[str]:
    hits = [
        name for name, pat in _PLATFORM_PATTERNS.items() if re.search(pat, code, re.IGNORECASE)
    ]

    # 目标平台标记不应计为“残留”
    normalized_target_arch = (target_arch or "").lower()
    normalized_target_os = (target_os or "").lower()

    filtered = []
    for h in hits:
        if migration_type == "arch":
            # arch 任务中，目标架构相关标识允许存在
            if normalized_target_arch == "riscv64" and h in {"平台 build tag"} and re.search(r"//go:build.*riscv64", code, re.IGNORECASE):
                continue
        if migration_type == "os":
            # os 任务中，目标OS标识允许存在
            if normalized_target_os == "windows" and h == "windows 标识符":
                continue
            if normalized_target_os == "linux" and h == "linux 标识符":
                continue
            if normalized_target_os == "darwin" and h == "darwin 标识符":
                continue
        filtered.append(h)

    return filtered


def _ensure_go_file(code: str) -> str:
    if "package " in code:
        return code
    return f"package main\n\n{code}\n"


def _cross_compile(
    code: str,
    target_os: str = "linux",
    target_arch: str = "riscv64",
    out_bin: Optional[str] = None,
) -> tuple[bool, str]:
    tmp = None
    try:
        full = _ensure_go_file(code)
        with tempfile.NamedTemporaryFile(suffix=".go", mode="w", delete=False, encoding="utf-8") as f:
            f.write(full)
            tmp = f.name

        env = {**os.environ, "GOOS": target_os, "GOARCH": target_arch}
        cmd = ["go", "build"]
        if out_bin:
            cmd += ["-o", out_bin]
        cmd.append(tmp)

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
        return proc.returncode == 0, (proc.stderr or "")[:500]
    except subprocess.TimeoutExpired:
        return False, "编译超时"
    except FileNotFoundError:
        return False, "Go 未安装"
    except Exception as e:
        return False, str(e)
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def _has_main_func(code: str) -> bool:
    return bool(re.search(r"\bfunc\s+main\s*\(", code or ""))


def _run_binary_with_qemu(bin_path: str, qemu_bin: str, timeout_sec: int) -> tuple[bool, str]:
    try:
        proc = subprocess.run([qemu_bin, bin_path], capture_output=True, text=True, timeout=timeout_sec)
        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "").strip()
            return False, f"QEMU运行失败: {msg[:300]}"
        return True, (proc.stdout or "")
    except subprocess.TimeoutExpired:
        return False, "QEMU运行超时"
    except FileNotFoundError:
        return False, f"QEMU未找到: {qemu_bin}"
    except Exception as e:
        return False, str(e)


def _run_binary_native(bin_path: str, timeout_sec: int) -> tuple[bool, str]:
    try:
        proc = subprocess.run([bin_path], capture_output=True, text=True, timeout=timeout_sec)
        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "").strip()
            return False, f"本机运行失败: {msg[:300]}"
        return True, (proc.stdout or "")
    except subprocess.TimeoutExpired:
        return False, "本机运行超时"
    except Exception as e:
        return False, str(e)


def _runtime_compare_with_gt(
    code: str,
    ground_truth: str,
    target_os: str,
    target_arch: str,
    qemu_bin: str,
    timeout_sec: int,
) -> dict:
    if not ground_truth or not ground_truth.strip():
        return {"enabled": True, "executed": False, "passed": None, "reason": "no_ground_truth"}

    if not _has_main_func(code) or not _has_main_func(ground_truth):
        return {
            "enabled": True,
            "executed": False,
            "passed": None,
            "reason": "no_main_function",
        }

    # 支持两类 runtime：
    # 1) linux/riscv64 -> qemu-riscv64 user mode
    # 2) windows/amd64 -> Windows 本机直接执行
    if not ((target_os == "linux" and target_arch == "riscv64") or (target_os == "windows" and target_arch == "amd64")):
        return {
            "enabled": True,
            "executed": False,
            "passed": None,
            "reason": f"unsupported_target:{target_os}/{target_arch}",
        }

    with tempfile.TemporaryDirectory() as td:
        suffix = ".exe" if target_os == "windows" else ""
        cand_bin = os.path.join(td, f"cand_target{suffix}")
        gt_bin = os.path.join(td, f"gt_target{suffix}")

        ok1, err1 = _cross_compile(code, target_os=target_os, target_arch=target_arch, out_bin=cand_bin)
        if not ok1:
            return {"enabled": True, "executed": False, "passed": None, "reason": f"cand_compile_fail:{err1}"}

        ok2, err2 = _cross_compile(ground_truth, target_os=target_os, target_arch=target_arch, out_bin=gt_bin)
        if not ok2:
            return {"enabled": True, "executed": False, "passed": None, "reason": f"gt_compile_fail:{err2}"}

        if target_os == "windows" and target_arch == "amd64":
            ok_cand, out_cand = _run_binary_native(cand_bin, timeout_sec)
            if not ok_cand:
                return {"enabled": True, "executed": True, "passed": False, "reason": out_cand}

            ok_gt, out_gt = _run_binary_native(gt_bin, timeout_sec)
            if not ok_gt:
                return {"enabled": True, "executed": True, "passed": False, "reason": f"gt:{out_gt}"}
        else:
            ok_cand, out_cand = _run_binary_with_qemu(cand_bin, qemu_bin, timeout_sec)
            if not ok_cand:
                return {"enabled": True, "executed": True, "passed": False, "reason": out_cand}

            ok_gt, out_gt = _run_binary_with_qemu(gt_bin, qemu_bin, timeout_sec)
            if not ok_gt:
                return {"enabled": True, "executed": True, "passed": False, "reason": f"gt:{out_gt}"}

        passed = (out_cand.strip() == out_gt.strip())
        return {
            "enabled": True,
            "executed": True,
            "passed": passed,
            "reason": "output_match" if passed else "output_mismatch",
            "candidate_output": out_cand[:300],
            "ground_truth_output": out_gt[:300],
        }


def _looks_like_placeholder(code: str, compile_error: str) -> bool:
    t = (code or "") + "\n" + (compile_error or "")
    s = t.lower()
    keys = ["yourpkg", "your/module/path", "todo: replace", "replace with the actual", "not in std"]
    return any(k in s for k in keys)


def _classify_failure(compile_ok: bool, compile_error: str, residues: list[str], code: str = "") -> str:
    if residues:
        return "residue"
    if not compile_ok:
        e = (compile_error or "").lower()
        if _looks_like_placeholder(code, compile_error):
            return "placeholder_import_or_package"
        if "undefined: syscall.sys_" in e:
            return "platform_symbol_missing"
        if "missing function body" in e or "undefined: syscall_syscall" in e or "undefined: libc_" in e or "undefined: errnoerr" in e:
            return "incomplete_stub_or_external_symbol"
        syntax_keys = ["syntax error", "undefined", "cannot find", "imported and not used", "missing"]
        if any(k in e for k in syntax_keys):
            return "syntax_or_dependency"
        return "semantic_or_runtime"
    return "none"


def _route_suggestion(failure_type: str) -> str:
    if failure_type == "placeholder_import_or_package":
        return "route:RGA_rebuild_then_CGA"
    if failure_type == "platform_symbol_missing":
        return "route:RGA_rebuild_then_CGA"
    if failure_type == "incomplete_stub_or_external_symbol":
        return "route:RGA_rebuild_then_CGA"
    if failure_type == "syntax_or_dependency":
        return "route:CGA_patch"
    if failure_type == "semantic_or_runtime":
        return "route:RGA_rebuild_then_CGA"
    if failure_type == "residue":
        return "route:strengthen_platform_constraints_then_regenerate"
    return "route:none"


def _validation_strategy(migration_type: str, enable_runtime: bool) -> str:
    if migration_type == "os":
        base = "os_validation: target-OS build/test preferred"
    else:
        base = "arch_validation: cross-compile"
    if enable_runtime:
        return f"{base} + optional_qemu_runtime_compare"
    return base


def _build_feedback(candidate: dict) -> str:
    parts = ["上一次生成失败，请修正以下问题："]
    if candidate["residues"]:
        parts.append(f"- 残留问题：{candidate['residues']}")
    if not candidate["compile_ok"] and candidate["compile_error"]:
        parts.append(f"- 编译错误：{candidate['compile_error'][:300]}")
    if candidate.get("failure_type") == "platform_symbol_missing":
        parts.append("- 平台符号缺失：目标平台不存在所用 syscall.SYS_* 常量，请改为目标平台可用实现（优先 x/sys/unix 或兼容替代路径）")
    if candidate.get("failure_type") == "incomplete_stub_or_external_symbol":
        parts.append("- 候选代码是半成品桩或外部依赖未闭合：禁止仅声明不实现；禁止引用未定义的 syscall/libc/errno 符号；请生成单文件自洽、可编译实现。")
    rt = candidate.get("runtime") or {}
    if rt.get("executed") and rt.get("passed") is False:
        parts.append(f"- 运行对比失败：{rt.get('reason', 'output_mismatch')}")
    parts.append(f"- 失败类型：{candidate['failure_type']}")
    parts.append(f"- 闭环路由建议：{candidate['route_suggestion']}")
    return "\n".join(parts)


def run_va(
    candidates: list[str],
    migration_type: str = "arch",
    target_os: str = "linux",
    target_arch: str = "riscv64",
    ground_truth: str = "",
    enable_runtime: bool = True,
    qemu_bin: str = r"D:\qemu\qemu-riscv64.exe",
    runtime_timeout_sec: int = 5,
) -> dict:
    results = []
    for i, code in enumerate(candidates):
        residues = _scan_residues(code, migration_type=migration_type, target_os=target_os, target_arch=target_arch)
        compile_ok, compile_err = _cross_compile(code, target_os=target_os, target_arch=target_arch)
        failure_type = _classify_failure(compile_ok, compile_err, residues, code=code)
        route = _route_suggestion(failure_type)

        runtime_info = {
            "enabled": enable_runtime,
            "executed": False,
            "passed": None,
            "reason": "disabled",
        }
        if enable_runtime and compile_ok:
            runtime_info = _runtime_compare_with_gt(
                code,
                ground_truth,
                target_os,
                target_arch,
                qemu_bin,
                runtime_timeout_sec,
            )

        entry = {
            "id": i + 1,
            "code": code,
            "residues": residues,
            "compile_ok": compile_ok,
            "compile_error": compile_err,
            "failure_type": failure_type,
            "route_suggestion": route,
            "runtime": runtime_info,
        }
        if failure_type != "none" or (runtime_info.get("executed") and runtime_info.get("passed") is False):
            entry["feedback_for_cga"] = _build_feedback(entry)
        results.append(entry)

    total = len(results)
    n_ok = sum(1 for r in results if r["compile_ok"])
    n_res = sum(1 for r in results if r["residues"])
    n_runtime_exec = sum(1 for r in results if (r.get("runtime") or {}).get("executed"))
    n_runtime_pass = sum(1 for r in results if (r.get("runtime") or {}).get("passed") is True)

    best = (
        next((r for r in results if r["compile_ok"] and not r["residues"]), None)
        or next((r for r in results if r["compile_ok"]), None)
        or (results[0] if results else None)
    )

    return {
        "candidates": results,
        "compile_at_k": round(n_ok / total, 2) if total else 0,
        "residue_rate": round(n_res / total, 2) if total else 0,
        "runtime_pass_rate": round(n_runtime_pass / n_runtime_exec, 2) if n_runtime_exec else 0,
        "n_compile_ok": n_ok,
        "n_residue": n_res,
        "n_runtime_executed": n_runtime_exec,
        "n_runtime_pass": n_runtime_pass,
        "total": total,
        "best": best,
        "validation_strategy": _validation_strategy(migration_type, enable_runtime),
        "migration_type": migration_type,
    }
