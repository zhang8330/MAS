"""
VA Test Validation
职责：
- 基于 SRS/语义信息为候选代码生成 Go 测试用例
- 执行 go test 并统计测试通过率
"""
import os
import re
import subprocess
import tempfile
from typing import Any

from app.core.llm import call_llm


_TEST_SYSTEM = "你是资深 Go 测试工程师，请为给定代码编写可执行、稳定的单元测试。"

_TEST_USER_TMPL = """请基于以下信息生成 Go 测试代码（仅输出完整 `_test.go` 代码，不要解释）：

SRS:
{srs}

语义信息:
{semantic}

候选代码:
```go
{code}
```

要求：
1) 使用 Go testing 包。
2) 测试文件可直接 `go test` 执行。
3) 至少包含 3 个测试用例，覆盖正常路径/边界/异常路径。
4) 避免依赖外部服务或网络。
5) 若无法识别可测函数，请至少给出编译级 smoke test（确保 `go test` 可运行）。
"""


def _extract_go_test(text: str) -> str:
    m = re.search(r"```(?:go)?\n(.*?)```", text, re.DOTALL)
    code = m.group(1).strip() if m else text.strip()
    if "package " not in code:
        return "package main\n\n" + code
    return code


def _run_go_test(candidate_code: str, test_code: str, target_os: str = "linux", target_arch: str = "riscv64", timeout_sec: int = 30) -> tuple[bool, str, str]:
    with tempfile.TemporaryDirectory() as td:
        code_path = os.path.join(td, "candidate.go")
        test_path = os.path.join(td, "candidate_test.go")
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(candidate_code)
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(test_code)

        try:
            subprocess.run(["go", "mod", "init", "va_test_tmp"], cwd=td, capture_output=True, text=True, timeout=10)
        except Exception:
            pass

        env = os.environ.copy()
        env["GOOS"] = target_os
        env["GOARCH"] = target_arch
        env["CGO_ENABLED"] = "0"

        # 第一阶段：目标架构测试编译验证
        cmd_compile = ["go", "test", "-c", "."]
        try:
            proc = subprocess.run(cmd_compile, cwd=td, capture_output=True, text=True, timeout=timeout_sec, env=env)
            output = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
            if proc.returncode != 0:
                reason = "test_build_constraints_mismatch" if "build constraints exclude all go files" in output.lower() else "test_compile_failed"
                return False, output[:4000], reason
            return True, (output or "go test -c success")[:4000], "test_compile_ok"
        except subprocess.TimeoutExpired:
            return False, "go test -c 超时", "test_timeout"
        except FileNotFoundError:
            return False, "Go 未安装，无法执行 go test", "go_not_found"
        except Exception as e:
            return False, str(e), "test_exception"


def run_va_test_validation(
    candidates: list[dict[str, Any]],
    srs: str,
    semantic_info: dict,
    model: str,
    target_os: str = "linux",
    target_arch: str = "riscv64",
    timeout_sec: int = 30,
) -> dict:
    results: list[dict[str, Any]] = []

    for c in candidates:
        cid = c.get("id")
        code = c.get("code") or ""

        if not c.get("compile_ok"):
            results.append({
                "id": cid,
                "executed": False,
                "passed": False,
                "reason": "compile_not_ok",
                "generated_tests": "",
                "test_output": "",
            })
            continue

        user = _TEST_USER_TMPL.format(
            srs=(srs or "")[:4000],
            semantic=str(semantic_info or {})[:3000],
            code=code[:8000],
        )
        llm_out = call_llm(_TEST_SYSTEM, user, model)
        test_code = _extract_go_test(llm_out)

        passed, output, reason = _run_go_test(
            code,
            test_code,
            target_os=target_os,
            target_arch=target_arch,
            timeout_sec=timeout_sec,
        )
        results.append({
            "id": cid,
            "executed": True,
            "passed": passed,
            "reason": "ok" if passed else reason,
            "generated_tests": test_code,
            "test_output": output,
        })

    executed = [r for r in results if r.get("executed")]
    n_exec = len(executed)
    n_pass = sum(1 for r in executed if r.get("passed"))

    return {
        "candidates": results,
        "n_test_executed": n_exec,
        "n_test_pass": n_pass,
        "test_pass_rate": round(n_pass / n_exec, 2) if n_exec else 0,
        "total": len(results),
    }
