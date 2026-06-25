"""
CGA — Code Generation Agent
职责：在代码上下文 + 高质量需求文档 + ARP 约束下，多候选生成 *_riscv64.go
对应论文 §4.3.4
"""
from app.core.llm import call_llm, extract_code
from app.core.database import get_fewshot_examples

_SYSTEM_TMPL = """你是专精 RISC-V 架构的 Go 工程师，任务是将 ARM64/X86 Go 代码迁移为 riscv64 实现。

=== 严格约束（违反任何一条均视为失败）===
1. 文件开头必须使用 //go:build riscv64（或无 build tag，不得使用 arm64 tag）
2. 禁止任何架构标识：arm64、amd64、x86、ARM、NEON、AVX、SSE
3. 所有汇编函数（TEXT 符号、NOSPLIT、Plan9 指令）必须用纯 Go 标准库重写
4. 禁止调用任何不存在于标准库中的 ARM/X86 专用函数
5. 函数签名必须与 ARM64/X86 版本完全一致（包名、函数名、参数类型、返回值类型）
6. Low 复杂度迁移（仅 build tag 或通用逻辑）：直接复制通用实现并更新架构标识即可

=== 本次迁移的架构残留信息（AAA 分析结果）===
迁移复杂度：{migration_complexity}
具体残留类型：{residue_types}
迁移处理建议：{migration_advice}

=== Few-shot 参考示例 ===
{fewshot}

=== 输出格式 ===
用 ```go ... ``` 包裹完整 Go 源文件，包含 package 声明和 import。"""

_USER_TMPL = """将以下 ARM64/X86 代码迁移为 riscv64 实现（候选 {idx}/{k}，策略：{hint}）：

ARM64/X86 实现：
```go
{arm64_code}
```
{generic_sec}
{context_sec}
SRS 需求文档（请严格遵守每条 FR 约束）：
{srs}

请输出完整 Go 源文件。"""

_HINTS = ["标准实现，注重正确性", "简洁实现，减少冗余", "保守实现，优先兼容性"]


def run_cga(
    arm64_code: str,
    generic_code: str,
    srs: str,
    arp: dict,
    model: str,
    k: int,
    arm_patterns: list[str] | None = None,
    migration_type: str = "arch",
    target_os: str = "linux",
    target_arch: str = "riscv64",
    project_context_files: list[dict] | None = None,
) -> list[str]:
    """生成 k 个候选 riscv64 实现"""
    fewshot = get_fewshot_examples(arm_patterns or [], n=2)
    normalized_type = "os" if str(migration_type).lower() == "os" else "arch"
    normalized_os = (target_os or "linux").lower()
    normalized_arch = (target_arch or "riscv64").lower()
    target_label = f"GOOS={normalized_os}, GOARCH={normalized_arch}"
    task_label = "OS migration" if normalized_type == "os" else "architecture migration"

    system = _SYSTEM_TMPL.format(
        migration_complexity=arp.get("migration_complexity", "Low"),
        residue_types=[r.get("type", "") for r in arp.get("residues", [])],
        migration_advice=arp.get("migration_advice", []),
        fewshot=fewshot,
    )
    system = (
        f"{system}\n\n"
        f"Target task: {task_label}\n"
        f"Target platform: {target_label}\n"
        "Do not preserve source platform build tags, architecture literals, OS-only APIs, or syscall constants that are unavailable on the target platform.\n"
    )

    generic_sec = (
        f"\n通用实现参考：\n```go\n{generic_code}\n```"
        if generic_code else ""
    )
    context_sec = ""
    if project_context_files:
        blocks = []
        for j, item in enumerate(project_context_files[:8], start=1):
            name = str((item or {}).get("filename") or f"context_{j}.go")
            ctx_code = str((item or {}).get("code") or "")[:6000]
            if ctx_code.strip():
                blocks.append(f"[{name}]\n```go\n{ctx_code}\n```")
        if blocks:
            context_sec = "\n项目上下文参考（同包辅助类型/函数）：\n" + "\n\n".join(blocks)

    candidates = []
    for i in range(k):
        user = _USER_TMPL.format(
            idx=i + 1,
            k=k,
            hint=_HINTS[i % len(_HINTS)],
            arm64_code=arm64_code,
            generic_sec=generic_sec,
            context_sec=context_sec,
            srs=srs,
        )
        user = f"{user}\n\nTarget platform: {target_label}\n"
        result = call_llm(system, user, model)
        candidates.append(extract_code(result))

    return candidates
