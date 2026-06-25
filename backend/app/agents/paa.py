"""
PAA — Platform Analysis Agent
职责：识别平台残留，构建 PRP（兼容历史 ARP 字段）
- 支持 ISA 残留（arm64/amd64/x86 等）
- 支持 OS 残留（linux/windows/darwin、GOOS、syscall 等）
"""
import json
import re
from app.core.llm import call_llm

_SYSTEM = """你是一名资深 Go 平台迁移工程师，专注识别平台残留并构建 Platform Residue Profile（PRP）。

请从以下维度识别残留：
1) ISA残留：arm64/amd64/386、NEON/AVX/SSE、汇编指令、cpu特性检测
2) OS残留：_linux/_windows/_darwin 后缀、build tag(go:build linux等)、runtime.GOOS 分支、syscall/平台API
3) 工程残留：仅平台启用的测试/注释/优化路径

输出严格 JSON：
{
  "residues": [
    {
      "type": "ISA残留|OS残留|构建约束残留|运行时分支残留|底层实现残留|工程辅助残留",
      "location": "位置描述",
      "description": "具体残留",
      "risk": "High|Medium|Low",
      "migration_note": "迁移建议"
    }
  ],
  "migration_complexity": "High|Medium|Low",
  "complexity_reason": "判断依据",
  "migration_advice": ["建议1", "建议2"],
  "platform_scope": "arch|os|hybrid",
  "isa_features": ["NEON", "LDAXR"],
  "os_features": ["GOOS-linux", "syscall-unix"],
  "target_strategy": "总体迁移策略"
}
"""

_USER_TMPL = """分析以下 Go 代码的平台残留，输出严格 JSON：
```go
{code}
```
{extra_context}
"""

_FALLBACK = {
    "residues": [],
    "migration_complexity": "Low",
    "complexity_reason": "未检测到明显平台特化",
    "migration_advice": ["优先保留通用Go逻辑，补齐目标平台build约束"],
    "platform_scope": "arch",
    "isa_features": [],
    "os_features": [],
    "target_strategy": "优先通用实现，移除源平台标识",
}

_ISA_HINTS = [r"\barm64\b", r"\bamd64\b", r"\b386\b", r"\bNEON\b", r"\bAVX\b", r"\bcpu\.ARM64\."]
_OS_HINTS = [r"\blinux\b", r"\bwindows\b", r"\bdarwin\b", r"runtime\.GOOS", r"//go:build", r"\bsyscall\."]


def _detect_scope(code: str) -> str:
    has_isa = any(re.search(p, code, re.IGNORECASE) for p in _ISA_HINTS)
    has_os = any(re.search(p, code, re.IGNORECASE) for p in _OS_HINTS)
    if has_isa and has_os:
        return "hybrid"
    if has_os:
        return "os"
    return "arch"


def _normalize_prp(prp: dict, code: str, expected_scope: str | None = None) -> dict:
    scope = prp.get("platform_scope") or _detect_scope(code)
    if expected_scope in {"arch", "os", "hybrid"}:
        scope = expected_scope
    out = {
        "residues": prp.get("residues", []),
        "migration_complexity": prp.get("migration_complexity", "Low"),
        "complexity_reason": prp.get("complexity_reason", ""),
        "migration_advice": prp.get("migration_advice", []),
        "platform_scope": scope,
        "isa_features": prp.get("isa_features") or prp.get("arm_features", []),
        "os_features": prp.get("os_features", []),
        "target_strategy": prp.get("target_strategy") or prp.get("riscv64_strategy", "优先通用实现"),
    }

    # 兼容历史字段（ARP）
    out["arm_features"] = out["isa_features"]
    out["riscv64_strategy"] = out["target_strategy"]
    return out


def _format_context(generic_code: str = "", project_context_files: list[dict] | None = None) -> str:
    parts = []
    if generic_code:
        parts.append(f"\n通用实现参考：\n```go\n{generic_code}\n```")
    if project_context_files:
        blocks = []
        for i, item in enumerate(project_context_files[:8], start=1):
            name = str((item or {}).get("filename") or f"context_{i}.go")
            ctx_code = str((item or {}).get("code") or "")[:6000]
            if ctx_code.strip():
                blocks.append(f"[{name}]\n```go\n{ctx_code}\n```")
        if blocks:
            parts.append("\n项目上下文文件（同包辅助代码）：\n" + "\n\n".join(blocks))
    return "\n".join(parts)


def run_paa(
    code: str,
    model: str,
    expected_scope: str | None = None,
    generic_code: str = "",
    project_context_files: list[dict] | None = None,
) -> dict:
    result = call_llm(
        _SYSTEM,
        _USER_TMPL.format(
            code=code,
            extra_context=_format_context(generic_code, project_context_files),
        ),
        model,
    )
    try:
        m = re.search(r"\{.*\}", result, re.DOTALL)
        if m:
            data = json.loads(m.group())
            return _normalize_prp(data, code, expected_scope=expected_scope)
    except Exception:
        pass
    return _normalize_prp(_FALLBACK.copy(), code, expected_scope=expected_scope)
