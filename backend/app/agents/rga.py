"""
RGA — Requirement Generation Agent
职责：
  1. 函数语义抽取
  2. 需求文档生成
  3. 需求质量评价与迭代优化

"""
import json
import re
from app.core.llm import call_llm, set_runtime_llm_config, reset_runtime_llm_config

# ── 需求质量评价标准（8个维度，Likert 5分制）────────────────────────────
QUALITY_CRITERIA = """
统一量化方式：Likert 5分制
- 1：很差（远远低于预期标准）
- 2：较差（需要较大改进才能达到预期标准）
- 3：一般（符合正在评估的特定参数的预期标准，但文档遗漏了一些细节）
- 4：良好（总体上达到或略高于预期标准，但有一些小的需要改进的地方）
- 5：优秀（完全达到或超过被评估参数的预期标准）

单条需求级指标：
- 无歧义性（Unambiguous）：每条需求只有一种解释
- 可理解性（Understandable）：不同背景读者均能理解
- 正确性（Correctness）：准确反映函数应具备的功能
- 可验证性（Verifiable）：存在可行的技术手段验证是否满足

文档级指标：
- 内部一致性（Internal Consistency）：需求之间无逻辑冲突
- 无冗余性（Non-redundancy）：无重复表达的需求
- 完整性（Completeness）：覆盖所有功能、输入输出和约束
- 简洁性（Conciseness）：在不损失信息的前提下表达简洁
"""


# ══════════════════════════════════════════════════════════
#  Step 1：函数语义抽取
# ══════════════════════════════════════════════════════════
_EXTRACT_SYSTEM = """你是一名代码语义分析专家，擅长从多源代码中提取函数的结构化语义信息。
你的任务不是生成需求，而是准确描述函数"是什么"和"做什么"，为后续需求生成提供结构化原材料。"""

_EXTRACT_USER_TMPL = """请从以下代码中提取函数的结构化语义信息：

X86/ARM64 架构实现（xxx_arm64/amd64/386.go）：
```go
{arm64_code}
```
{generic_sec}

提取以下语义要素，以 JSON 输出（只输出 JSON）：
{{
  "function_purpose": "函数的核心功能，用一句话描述它解决什么问题",
  "input_output": {{
    "params": [{{"name": "参数名", "type": "类型", "meaning": "语义含义"}}],
    "returns": [{{"type": "类型", "meaning": "语义含义"}}],
    "relationship": "输入与输出的关系描述"
  }},
  "constraints": ["边界条件1", "输入限制2", "异常处理逻辑3"],
  "implementation_strategy": "主要实现方式：循环/递归/位运算/批量处理等",
  "arm64_optimizations": ["AMD64/ARM64 特有优化点，如 NEON 批量处理/原子操作/内存对齐等"],
  "riscv64_portable_logic": "哪些逻辑可直接移植到 riscv64，哪些需要替换"
}}"""


def run_semantic_extract(arm64_code: str, generic_code: str, model: str, project_context_files: list[dict] | None = None) -> dict:
    """执行 Step1 语义抽取。

    功能：
    - 从 ARM64/X86 代码、可选通用实现和同包上下文中抽取结构化语义；
    - 生成后续 SRS 的“语义事实底座”，间接支撑 correctness/completeness 评分。

    输入：
    - arm64_code: 架构相关实现代码；
    - generic_code: 通用实现（可为空）；
    - model: 抽取模型名；
    - project_context_files: 同包辅助文件列表（可为空）。

    输出：
    - dict: 结构化语义 JSON；失败时返回兜底结构。
    """
    system = """你是一名代码语义分析专家，擅长从多源代码中提取函数的结构化语义信息。
你的任务不是生成需求，而是准确描述函数"是什么"和"做什么"，为后续需求生成提供结构化原材料。"""
    
    generic_sec = f"\n通用实现代码（xxx.go）：\n```go\n{generic_code}\n```" if generic_code else ""
    context_sec = ""
    if project_context_files:
        blocks = []
        for i, f in enumerate(project_context_files[:8], start=1):
            name = str((f or {}).get("filename") or f"context_{i}.go")
            code = str((f or {}).get("code") or "")[:6000]
            if code.strip():
                blocks.append(f"[{name}]\n```go\n{code}\n```")
        if blocks:
            context_sec = "\n项目上下文代码（同包其他文件）：\n" + "\n\n".join(blocks)

    user = f"""请从以下代码中提取函数的结构化语义信息，以JSON格式输出：

X86/ARM64 架构实现（xxx_arm64/amd64/386.go）：
```go
{arm64_code}
```
{generic_sec}
{context_sec}

提取以下语义要素，以JSON输出：
{{
  "function_purpose": "函数的核心功能，用一句话描述它解决什么问题",
  "input_output": {{
    "params": [{{"name":"参数名","type":"类型","meaning":"语义含义"}}],
    "returns": [{{"type":"类型","meaning":"语义含义"}}],
    "relationship": "输入与输出的关系描述"
  }},
  "constraints": ["边界条件1", "输入限制2", "异常处理逻辑3"],
  "implementation_strategy": "主要实现方式：如循环/递归/位运算/批量处理等",
  "arm64_optimizations": ["ARM64特有的优化点，如NEON批量处理/原子操作/内存对齐等"],
  "riscv64_portable_logic": "哪些逻辑可以直接移植到riscv64，哪些需要替换"
}}

只输出JSON，不要其他内容。"""
    
    result = call_llm(system, user, model)
    try:
        m = re.search(r"\{.*\}", result, re.DOTALL)
        if m:
            return json.loads(m.group())
    except:
        pass
    return {"function_purpose": result, "constraints": [], "arm64_optimizations": []}


# ══════════════════════════════════════════════════════════
#  Step 2：需求文档生成
# ══════════════════════════════════════════════════════════
_REQ_SYSTEM = """你是软件需求工程专家，专门将代码语义信息转化为面向 RISC-V 架构的结构化需求规格（SRS）。
你的输出将直接用于指导代码生成 Agent 生成 *_riscv64.go 文件，因此需求必须精确、完整、可直接指导实现。"""

_REQ_USER_TMPL = """基于以下信息，生成面向 RISC-V 架构实现的 SRS 需求文档：

ARM64/X86 实现代码：
```go
{arm64_code}
```
{generic_sec}
函数语义信息（已提取）：
{semantic_info}

架构残留分析（ARP）：
- 迁移复杂度：{migration_complexity}
- ARM64/X86 特性：{arm_features}
- 迁移策略建议：{riscv64_strategy}

生成包含以下条目的 SRS，每条用 FR-N 编号：
FR-1 功能主描述：核心功能目标
FR-2 输入输出规范：参数含义、返回值含义、合法范围
FR-3 行为约束：边界条件、异常处理、状态变化
FR-4 RISC-V 架构约束：
  - 禁止保留任何 ARM64 特有标识（amd64/arm64 build tag、NEON、LDAXR 等）
  - 优先使用标准 Go 库实现，避免内联汇编
  - 符合 riscv64 内存对齐规范
  - build tag 改为 //go:build riscv64（或无 build tag）
FR-5 接口一致性要求：与 xxx_arm64.go/xxx_amd64.go/xxx_386.go 保持完全相同的函数签名和包名"""


def _generate_srs(
    arm64_code: str,
    generic_code: str,
    arp: dict,
    semantic_info: dict,
    model: str,
) -> str:
    """执行 Step2 需求生成（LLM_req）。

    功能：
    - 基于代码+语义抽取结果+ARP分析生成 FR 编号化 SRS；
    - 明确输入输出、行为约束、RISC-V 约束与接口一致性。

    指标关联建议：
    - 通过 FR 结构化表达提升 unambiguous / completeness；
    - 通过“可测试语句”提升 verifiable；
    - 通过架构约束显式化降低 internal_consistency 风险。
    """
    generic_sec = (
        f"\n通用实现代码：\n```go\n{generic_code}\n```"
        if generic_code else ""
    )
    user = _REQ_USER_TMPL.format(
        arm64_code=arm64_code,
        generic_sec=generic_sec,
        semantic_info=json.dumps(semantic_info, ensure_ascii=False, indent=2),
        migration_complexity=arp.get("migration_complexity", "Low"),
        arm_features=arp.get("arm_features", []),
        riscv64_strategy=arp.get("riscv64_strategy", "直接移植通用逻辑"),
    )
    return call_llm(_REQ_SYSTEM, user, model)


# ══════════════════════════════════════════════════════════
#  Step 3：需求质量评价与迭代优化
# ══════════════════════════════════════════════════════════
_EVAL_SYSTEM = "你是需求质量审查专家，按照 SRS 质量评价标准对需求文档进行逐条分析。"

_Q_NORM_FIELDS = {
    "completeness_decomposition",
    "completeness_coverage",
    "agreement_ratio",
    "correctness_ratio",
    "consistency_ratio",
    "verifiability_index",
    "conciseness_index",
    "readability_norm",
    "sentence_length_norm",
    "vague_ratio",
    "subjectivity_ratio",
    "structure_depth_norm",
    "continuation_ratio",
    "multiplicity_ratio",
}

_EVAL_USER_TMPL = """请按照以下 8 项质量标准对 SRS 进行评价：

{criteria}

注意：
1) 最终打分只允许使用这8个核心维度（Likert 1~5）
2) 下面提供的 Appendix A 量化子指标不单独评分，但必须作为打分依据

Appendix A 量化子指标（结构化输入）：
{metric_summary}

指标原始 JSON：
{metrics_json}

待评价的 SRS：
{srs}

输出 JSON（只输出 JSON）：
{{
  "overall_quality": "High|Medium|Low",
  "scores": {{
    "unambiguous": 1,
    "understandable": 1,
    "correctness": 1,
    "verifiable": 1,
    "internal_consistency": 1,
    "non_redundancy": 1,
    "completeness": 1,
    "conciseness": 1
  }},
  "avg_score": 1.0,
  "score_rationale": {{
    "unambiguous": "基于 agreement_ratio/vague_ratio 的判断",
    "understandable": "基于 readability/句长/结构",
    "correctness": "基于 correctness_ratio 与语义一致性",
    "verifiable": "基于 verifiability_index 与可测性",
    "internal_consistency": "基于 consistency_ratio 与跨FR逻辑冲突检查",
    "non_redundancy": "基于重复表达/同义堆叠与信息密度判断",
    "completeness": "基于 completeness_decomposition/completeness_coverage",
    "conciseness": "基于 conciseness_index 与句法负担"
  }},
  "test_plan": {{
    "suggested_test_cases": 0,
    "coverage_focus": ["边界条件", "异常处理", "接口一致性"],
    "high_priority_cases": ["case-1", "case-2"]
  }},
  "issues": [
    {{"fr_id": "FR-2", "criterion": "可验证性", "problem": "参数范围未明确", "suggestion": "补充具体数值范围"}}
  ],
  "needs_revision": true
}}

要求：scores 每项必须是 1~5 的整数（Likert 5分制）；test_plan 中数量必须为非负整数。"""

_OPT_SYSTEM = "你是需求文档优化专家，根据质量审查意见对 SRS 进行精准修订。"

_OPT_USER_TMPL = """根据以下质量审查意见，修订 SRS 文档：

原始 SRS：
{srs}

审查意见：
{issues}

修订要求（必须严格遵守）：
1. 仅允许修改 issues 中明确点名的 FR 条目（例如 FR-2、FR-4）
2. 未在 issues 中出现的 FR 条目，文本必须逐字保持不变（禁止改写、重排、增删）
3. 保持 FR-N 编号结构不变，不新增/删除 FR 编号
4. 若某个 issue 未指明 FR 编号，只允许在最小必要范围内补充，不得影响其他 FR 原文
5. 不引入新的歧义或冗余
6. 输出完整的修订后 SRS"""


def _clamp01(x: float) -> float:
    """将数值裁剪到 [0,1]。

    用途：保证 Appendix A 归一化指标稳定，避免越界影响评分解释。
    """
    return max(0.0, min(1.0, x))


def _safe_div(a: float, b: float) -> float:
    """安全除法，分母为 0 时返回 0。

    用途：防止统计指标计算异常，确保评价链路鲁棒。
    """
    if b == 0:
        return 0.0
    return a / b


def _smooth_ratio(x: float, n: float, alpha: float = 1.0, beta: float = 1.0) -> float:
    """Beta 平滑比率。

    功能：
    - 对比例指标做小样本平滑，避免 0/1 极端值主导模型判断；
    - 提升 completeness/consistency/verifiable 等维度在小样本下的稳定性。
    """
    if n <= 0:
        return 0.5
    return _clamp01((x + alpha) / (n + alpha + beta))


def _extract_requirements(srs: str) -> list[str]:
    """从 SRS 文本中提取 FR 级需求条目列表。

    功能：
    - 识别 `FR-N` 开头段落并聚合为单条需求；
    - 若无 FR 结构则降级为按非空行提取。

    指标关联建议：
    - 为 completeness_decomposition / structure_depth 等结构指标提供基础样本。
    """
    lines = [ln.strip() for ln in (srs or "").splitlines()]
    reqs = []
    cur = []
    for ln in lines:
        if re.match(r"^FR-\d+", ln):
            if cur:
                reqs.append(" ".join(cur).strip())
            cur = [ln]
        elif ln:
            cur.append(ln)
    if cur:
        reqs.append(" ".join(cur).strip())
    if not reqs:
        reqs = [x for x in lines if x]
    return reqs


def _compute_appendix_metrics(srs: str) -> dict:
    """计算 Appendix A 量化子指标（核心量表支撑函数）。

    功能：
    - 计算结构/语义、NLP 质量、结构形态三类指标；
    - 输出统一 JSON，供 LLM_eval 打分时作为“证据输入”；
    - 对小样本进行置信度保护，避免分值失真。

    指标关联建议：
    - unambiguous：重点看 agreement_ratio 与 vague_ratio；
    - understandable：重点看 readability_norm / sentence_length_norm；
    - correctness：重点看 correctness_ratio 与语义一致性；
    - verifiable：重点看 verifiability_index。
    """
    text = srs or ""
    reqs = _extract_requirements(text)

    n_req = max(len(reqs), 1)
    n_sent = max(len(re.findall(r"[。！？.!?]", text)), 1)

    # 统一符号（近似映射）
    nr = n_req
    nui = sum(1 for r in reqs if re.search(r"\b(必须|应当|shall|must)\b", r, re.IGNORECASE))
    nc = sum(1 for r in reqs if re.search(r"\b(输入|输出|返回|error|错误|边界|约束)\b", r, re.IGNORECASE))
    nn = sum(1 for r in reqs if re.search(r"\b(同时|但是|除非|except|unless)\b", r, re.IGNORECASE))

    n_wea = len(re.findall(r"\b(try|尽量|尽可能|适当|合理)\b", text, re.IGNORECASE))
    n_vag = len(re.findall(r"\b(可能|若干|某些|some|various|approximately)\b", text, re.IGNORECASE))
    n_opt = len(re.findall(r"\b(可选|optional|may|可以)\b", text, re.IGNORECASE))
    n_imp = len(re.findall(r"\b(它|其|this|that)\b", text, re.IGNORECASE))

    # (1) 结构/语义类（平滑 + 小样本保护）
    decomposition_raw = _safe_div(len([r for r in reqs if re.match(r"^FR-\d+", r)]), nr)
    decomposition = _smooth_ratio(decomposition_raw * nr, nr)
    coverage = _smooth_ratio(nc, nr)
    agreement_ratio = _smooth_ratio(nui, nr)
    correctness_ratio = _smooth_ratio(nc, nr)
    consistency_ratio = _smooth_ratio((nr - nn), nr)

    cost_idx = 1.0 - _smooth_ratio(n_vag + n_opt, max(nr, 1))
    time_idx = 1.0 - _smooth_ratio(n_imp, max(nr, 1))
    verifiability_index = _clamp01((cost_idx + time_idx) / 2)
    conciseness_index = _clamp01(1.0 / (max(len(text), 1) / 1000.0 + 1.0))

    # (2) NLP（短文本裁剪）
    words = re.findall(r"\w+", text)
    avg_sentence_len = _safe_div(len(words), n_sent)
    sentence_length_norm = _clamp01(1.0 - abs(avg_sentence_len - 18.0) / 30.0)

    letters = sum(1 for ch in text if ch.isalpha())
    cli_raw = 0.0588 * _safe_div(letters * 100, max(len(words), 1)) - 0.296 * _safe_div(n_sent * 100, max(len(words), 1)) - 15.8
    cli = max(-5.0, min(20.0, cli_raw))
    readability_norm = _clamp01(1.0 - abs(cli - 10.0) / 20.0)

    vague_ratio = _smooth_ratio(n_wea + n_vag + n_opt + n_imp, nr * 2)
    subjectivity_ratio = _smooth_ratio(
        len(re.findall(r"\b(好|优秀|最佳|适合|合理|good|best)\b", text, re.IGNORECASE)),
        nr,
    )

    # (3) 结构性
    max_depth = max((r.count(".") + r.count("-") for r in reqs), default=1)
    structure_depth_norm = _clamp01(1.0 - abs(max_depth - 2) / 6.0)
    n_con = len(re.findall(r"\b(then|随后|接着|下一步|再)\b", text, re.IGNORECASE))
    n_mul = len(re.findall(r"\b(and|以及|同时|并且)\b", text, re.IGNORECASE))
    continuation_ratio = _smooth_ratio(n_con, nr)
    multiplicity_ratio = _smooth_ratio(n_mul, nr)

    # 小样本保护：Nreq < 3 时，降低 NLP/结构形态指标的影响，避免极端值主导
    small_sample = nr < 3
    confidence = _clamp01(min(1.0, nr / 3.0))
    if small_sample:
        sentence_length_norm = 0.5 * (1.0 - confidence) + sentence_length_norm * confidence
        readability_norm = 0.5 * (1.0 - confidence) + readability_norm * confidence
        structure_depth_norm = 0.5 * (1.0 - confidence) + structure_depth_norm * confidence

    metrics = {
        "notation": {
            "n": nr,
            "nu": len(set(reqs)),
            "ni": len(re.findall(r"\b(input|输入|param|参数)\b", text, re.IGNORECASE)),
            "ns": len(re.findall(r"\b(state|状态)\b", text, re.IGNORECASE)),
            "nr": nr,
            "nui": nui,
            "nc": nc,
            "nn": nn,
            "Nreq": nr,
            "Nwea": n_wea,
            "Nvag": n_vag,
            "Nopt": n_opt,
            "Nimp": n_imp,
        },
        "structural_semantic": {
            "completeness_decomposition": decomposition,
            "completeness_coverage": coverage,
            "agreement_ratio": agreement_ratio,
            "correctness_ratio": correctness_ratio,
            "consistency_ratio": consistency_ratio,
            "verifiability_index": verifiability_index,
            "conciseness_index": conciseness_index,
        },
        "nlp_quality": {
            "readability_coleman_liau": round(cli, 3),
            "readability_norm": readability_norm,
            "avg_sentence_length": round(avg_sentence_len, 3),
            "sentence_length_norm": sentence_length_norm,
            "vague_ratio": vague_ratio,
            "subjectivity_ratio": subjectivity_ratio,
        },
        "structural_shape": {
            "structure_depth": max_depth,
            "structure_depth_norm": structure_depth_norm,
            "continuation_ratio": continuation_ratio,
            "multiplicity_ratio": multiplicity_ratio,
        },
        "sample_guard": {
            "small_sample": small_sample,
            "sample_confidence": round(confidence, 3),
            "nreq": nr,
        },
    }
    return metrics


def _appendix_metric_summary(metrics: dict) -> str:
    """将 Appendix A 指标压平成可读摘要文本。

    功能：
    - 供评审提示词直接引用，提升模型对量化证据的利用率；
    - 避免只给原始 JSON 导致解释分散。
    """
    flat = {}
    for k, v in (metrics.get("structural_semantic") or {}).items():
        flat[k] = v
    for k, v in (metrics.get("nlp_quality") or {}).items():
        if k.endswith("_norm") or k in {"avg_sentence_length", "vague_ratio", "subjectivity_ratio", "readability_coleman_liau"}:
            flat[k] = v
    for k, v in (metrics.get("structural_shape") or {}).items():
        flat[k] = v
    return "\n".join([f"- {k}: {v}" for k, v in flat.items()])


def _normalize_eval_result(eval_result: object) -> dict:
    """规范化质量评估输出，确保前端可稳定展示。

    功能：
    - 补齐缺失字段与默认值；
    - 强制关键字段类型一致（如分数 int、数量非负 int）；
    - 约束输出结构，便于前端统一渲染与后续统计。
    """
    if not isinstance(eval_result, dict):
        eval_result = {}

    scores = eval_result.get("scores") or {}
    test_plan = eval_result.get("test_plan") or {}

    def _to_nonneg_int(v: object) -> int:
        if isinstance(v, bool):
            return 0
        try:
            n = int(v)
        except (TypeError, ValueError):
            return 0
        return n if n >= 0 else 0

    rationale = eval_result.get("score_rationale") or {}
    if not isinstance(rationale, dict):
        rationale = {}

    normalized = {
        "overall_quality": eval_result.get("overall_quality", "Medium"),
        "scores": {
            "unambiguous": int(scores.get("unambiguous", 0) or 0),
            "understandable": int(scores.get("understandable", 0) or 0),
            "correctness": int(scores.get("correctness", 0) or 0),
            "verifiable": int(scores.get("verifiable", 0) or 0),
            "internal_consistency": int(scores.get("internal_consistency", 0) or 0),
            "non_redundancy": int(scores.get("non_redundancy", 0) or 0),
            "completeness": int(scores.get("completeness", 0) or 0),
            "conciseness": int(scores.get("conciseness", 0) or 0),
        },
        "avg_score": float(eval_result.get("avg_score", 0) or 0),
        "score_rationale": {
            "unambiguous": str(rationale.get("unambiguous", "")),
            "understandable": str(rationale.get("understandable", "")),
            "correctness": str(rationale.get("correctness", "")),
            "verifiable": str(rationale.get("verifiable", "")),
            "internal_consistency": str(rationale.get("internal_consistency", "")),
            "non_redundancy": str(rationale.get("non_redundancy", "")),
            "completeness": str(rationale.get("completeness", "")),
            "conciseness": str(rationale.get("conciseness", "")),
        },
        "test_plan": {
            "suggested_test_cases": _to_nonneg_int(test_plan.get("suggested_test_cases", 0)),
            "coverage_focus": test_plan.get("coverage_focus", []) if isinstance(test_plan.get("coverage_focus", []), list) else [],
            "high_priority_cases": test_plan.get("high_priority_cases", []) if isinstance(test_plan.get("high_priority_cases", []), list) else [],
        },
        "issues": eval_result.get("issues", []) if isinstance(eval_result.get("issues", []), list) else [],
        "needs_revision": bool(eval_result.get("needs_revision", False)),
    }

    return normalized


def _is_complete_score(scores: dict) -> bool:
    """校验 8 维核心分数是否完整且在 Likert 1~5。

    功能：
    - 作为评审结果准入门槛；
    - 防止模型输出越界或缺项导致统计污染。
    """
    keys = [
        "unambiguous", "understandable", "correctness", "verifiable",
        "internal_consistency", "non_redundancy", "completeness", "conciseness",
    ]
    for k in keys:
        v = scores.get(k)
        if not isinstance(v, int) or v < 1 or v > 5:
            return False
    return True


def _fill_rationale_if_missing(rationale: dict) -> dict:
    """补齐缺失的维度评分理由文本。

    功能：
    - 保证 8 个维度均有可展示解释；
    - 提升评审可追溯性，便于人工复核“怎么打的分”。
    """
    keys = [
        "unambiguous", "understandable", "correctness", "verifiable",
        "internal_consistency", "non_redundancy", "completeness", "conciseness",
    ]
    out = {}
    for k in keys:
        txt = str((rationale or {}).get(k, "") or "").strip()
        out[k] = txt if txt else "未返回该维解释，建议重试评审模型"
    return out


def _eval_srs(srs: str, model: str, appendix_metrics: dict | None = None) -> dict:
    """执行单模型 SRS 质量评价（LLM_eval）。

    功能：
    - 将 8 维核心量表 + Appendix A 子指标注入评审提示词；
    - 解析并校验模型输出 JSON；
    - 对 API/解析失败返回可识别状态，保证流程可恢复。

    指标关联建议：
    - 分数必须是 1~5 整数；
    - rationale 建议与 Appendix A 指标一一对应，增强可解释性。
    """
    appendix_metrics = appendix_metrics or _compute_appendix_metrics(srs)
    user = _EVAL_USER_TMPL.format(
        criteria=QUALITY_CRITERIA,
        srs=srs,
        metric_summary=_appendix_metric_summary(appendix_metrics),
        metrics_json=json.dumps(appendix_metrics, ensure_ascii=False, indent=2),
    )
    try:
        result = call_llm(_EVAL_SYSTEM, user, model)
    except Exception as e:
        return {
            "status": "api_failed",
            "model": model,
            "error": str(e),
            **_normalize_eval_result({"needs_revision": False, "issues": []}),
        }

    try:
        m = re.search(r"\{.*\}", result, re.DOTALL)
        if not m:
            return {
                "status": "parse_failed",
                "model": model,
                **_normalize_eval_result({"needs_revision": False, "issues": []}),
            }
        normalized = _normalize_eval_result(json.loads(m.group()))
        scores = normalized.get("scores") or {}
        if not _is_complete_score(scores):
            return {
                "status": "schema_incomplete",
                "model": model,
                **normalized,
            }
        normalized["score_rationale"] = _fill_rationale_if_missing(normalized.get("score_rationale") or {})
        normalized["status"] = "ok"
        normalized["model"] = model
        return normalized
    except Exception:
        return {
            "status": "parse_failed",
            "model": model,
            **_normalize_eval_result({"needs_revision": False, "issues": []}),
        }


def _merge_eval_results(results: list[dict], eval_models: list[str]) -> dict:
    """汇总多模型评审结果。

    功能：
    - 聚合多模型 8 维分数、平均分、质量等级投票；
    - 合并 issue 列表与测试建议；
    - 输出 ensemble 置信信息（有效模型数、失败模型等）。

    指标关联建议：
    - 可降低单模型偶然偏差，提升评分稳健性；
    - 当有效模型数 < 2 时标记 low_confidence，建议重试。
    """
    all_rows = [r for r in results if isinstance(r, dict)]
    valid = [r for r in all_rows if r.get("status") == "ok"]
    failed = [r for r in all_rows if r.get("status") != "ok"]

    if not valid:
        base = _normalize_eval_result({"needs_revision": False, "issues": []})
        base["review_ensemble"] = {
            "models": eval_models,
            "num_models_total": len(eval_models),
            "num_models_effective": 0,
            "per_model": all_rows,
            "failed_models": [{"model": r.get("model"), "status": r.get("status")} for r in failed],
            "low_confidence": True,
            "confidence_msg": "没有可用评审模型，结果不可用",
        }
        return base

    score_keys = [
        "unambiguous",
        "understandable",
        "correctness",
        "verifiable",
        "internal_consistency",
        "non_redundancy",
        "completeness",
        "conciseness",
    ]

    avg_scores = {}
    for k in score_keys:
        vals = [int((r.get("scores") or {}).get(k, 0) or 0) for r in valid]
        avg_scores[k] = round(sum(vals) / len(vals)) if vals else 0

    avg_score_vals = [float(r.get("avg_score", 0) or 0) for r in valid]
    merged_avg = round(sum(avg_score_vals) / len(avg_score_vals), 2) if avg_score_vals else 0.0

    quality_votes = [str(r.get("overall_quality", "Medium") or "Medium") for r in valid]
    high_n = sum(1 for q in quality_votes if q == "High")
    low_n = sum(1 for q in quality_votes if q == "Low")
    if high_n > len(valid) / 2:
        overall_quality = "High"
    elif low_n > len(valid) / 2:
        overall_quality = "Low"
    else:
        overall_quality = "Medium"

    issues = []
    for r in valid:
        for it in (r.get("issues") or []):
            if isinstance(it, dict):
                issues.append(it)

    test_case_vals = [
        int(((r.get("test_plan") or {}).get("suggested_test_cases", 0) or 0))
        for r in valid
    ]
    test_plan = {
        "suggested_test_cases": round(sum(test_case_vals) / len(test_case_vals)) if test_case_vals else 0,
        "coverage_focus": (valid[0].get("test_plan") or {}).get("coverage_focus", []),
        "high_priority_cases": (valid[0].get("test_plan") or {}).get("high_priority_cases", []),
    }

    # 维度原因：拼接多模型理由，便于前端展示“分析原因和具体内容”
    score_rationale = {}
    for k in score_keys:
        snippets = []
        for r in valid:
            text = ((r.get("score_rationale") or {}).get(k) or "").strip()
            if text:
                snippets.append(text)
        score_rationale[k] = " | ".join(snippets[:3])

    merged = {
        "overall_quality": overall_quality,
        "scores": avg_scores,
        "avg_score": merged_avg,
        "score_rationale": score_rationale,
        "test_plan": test_plan,
        "issues": issues[:12],
        "needs_revision": any(bool(r.get("needs_revision", False)) for r in valid),
        "review_ensemble": {
            "models": eval_models,
            "num_models_total": len(eval_models),
            "num_models_effective": len(valid),
            "per_model": all_rows,
            "failed_models": [{"model": r.get("model"), "status": r.get("status")} for r in failed],
            "low_confidence": len(valid) < 2,
            "confidence_msg": "有效评审模型数少于2，建议重试" if len(valid) < 2 else "",
        },
    }
    return _normalize_eval_result(merged) | {"review_ensemble": merged["review_ensemble"]}


def _eval_srs_multi(
    srs: str,
    model: str,
    appendix_metrics: dict | None = None,
    eval_profiles: list[dict] | None = None,
) -> dict:
    """执行多模型评审并汇总平均结果。

    功能：
    - 默认使用主模型 + 两个评审模型进行合议；
    - 或按 eval_profiles 注入一组自定义评审配置；
    - 统一输出可被前端展示的汇总评估结构。

    指标关联建议：
    - 适用于正式评估场景，建议至少 2 个有效模型后再采信结论。
    """
    eval_models = [model, "gpt-3.5-turbo", "gpt-4.1-mini"]
    dedup_models = []
    for m in eval_models:
        if m not in dedup_models:
            dedup_models.append(m)

    metrics = appendix_metrics or _compute_appendix_metrics(srs)

    results = []
    if eval_profiles:
        # 按用户配置的 profile 与模型一一对应
        for p in eval_profiles:
            cfg_model = str((p or {}).get("model") or "").strip()
            if not cfg_model:
                continue
            cfg = {
                "provider": str((p or {}).get("provider") or "custom"),
                "base_url": str((p or {}).get("base_url") or "").strip(),
                "api_key": str((p or {}).get("api_key") or "").strip(),
                "model": cfg_model,
            }
            token = None
            try:
                token = set_runtime_llm_config(cfg)
                results.append(_eval_srs(srs, cfg_model, appendix_metrics=metrics))
            except Exception:
                results.append({"status": "api_failed", "model": cfg_model})
            finally:
                if token is not None:
                    reset_runtime_llm_config(token)
        used_models = [str((p or {}).get("model") or "") for p in eval_profiles if str((p or {}).get("model") or "").strip()]
        return _merge_eval_results(results, used_models)

    results = [_eval_srs(srs, m, appendix_metrics=metrics) for m in dedup_models]
    return _merge_eval_results(results, dedup_models)


def _optimize_srs(srs: str, issues: list, model: str) -> str:
    """执行 Step3 修订优化（LLM_opt）。

    功能：
    - 严格依据 issues 定向修订 SRS；
    - 尽量保持未点名 FR 原文不变，减少连带回归风险。

    指标关联建议：
    - 优先修复影响 unambiguous / verifiable / completeness 的高优先问题。
    """
    user = _OPT_USER_TMPL.format(
        srs=srs,
        issues=json.dumps(issues, ensure_ascii=False, indent=2),
    )
    return call_llm(_OPT_SYSTEM, user, model)


# ══════════════════════════════════════════════════════════
#  公开入口
# ══════════════════════════════════════════════════════════
def run_rga(
    arm64_code: str,
    generic_code: str,
    arp: dict,
    model: str,
    max_iter: int = 2,
    eval_profiles: list[dict] | None = None,
    project_context_files: list[dict] | None = None,
) -> tuple[str, dict, dict]:
    """RGA 主流程入口：抽取 → 生成 → 评审 → 迭代 → 门控回滚。

    功能：
    1) 语义抽取：形成实现语义基线；
    2) 初稿生成：输出 FR 结构化 SRS；
    3) 多模型评审：按 8 维量表打分并给出问题；
    4) 定向优化：按 issues 修订并复评；
    5) 分数门控：若新版本 avg_score 下降则回滚。

    返回：
    - srs: 最终需求文档；
    - semantic_info: 语义抽取结果；
    - last_eval: 最终评审结果（含 Appendix A 指标、评分历史、回滚事件）。

    指标落地建议：
    - 建议关注 round1→round2 的 `avg_score` 与 8 维分项变化；
    - 优先处理 `issues` 中可验证性与完整性问题，可显著提升最终质量。
    """
    # 1. 语义抽取
    semantic_info = run_semantic_extract(arm64_code, generic_code, model, project_context_files=project_context_files)

    # 2. 生成初始 SRS
    srs = _generate_srs(arm64_code, generic_code, arp, semantic_info, model)

    # 3. 质量优化迭代（三模型评审 + Appendix A 指标）
    last_eval = {}
    score_history: list[dict] = []
    rollback_events: list[dict] = []

    appendix_metrics = _compute_appendix_metrics(srs)
    eval_result = _eval_srs_multi(srs, model, appendix_metrics=appendix_metrics, eval_profiles=eval_profiles)
    last_eval = eval_result or {}

    baseline_avg = float((eval_result or {}).get("avg_score", 0) or 0)
    if isinstance(eval_result, dict):
        score_history.append({
            "round": 1,
            "stage": "iter_eval",
            "avg_score": baseline_avg,
            "overall_quality": str(eval_result.get("overall_quality", "Medium") or "Medium"),
            "scores": dict(eval_result.get("scores") or {}),
            "needs_revision": bool(eval_result.get("needs_revision", False)),
        })

    for i in range(2, max_iter + 1):
        if not eval_result.get("needs_revision") or not eval_result.get("issues"):
            break

        prev_srs = srs
        prev_eval = eval_result
        prev_avg = float((prev_eval or {}).get("avg_score", 0) or 0)

        candidate_srs = _optimize_srs(srs, eval_result["issues"], model)
        candidate_metrics = _compute_appendix_metrics(candidate_srs)
        candidate_eval = _eval_srs_multi(candidate_srs, model, appendix_metrics=candidate_metrics, eval_profiles=eval_profiles)
        candidate_avg = float((candidate_eval or {}).get("avg_score", 0) or 0)

        accepted = candidate_avg >= prev_avg
        score_history.append({
            "round": i,
            "stage": "iter_eval",
            "avg_score": candidate_avg,
            "overall_quality": str((candidate_eval or {}).get("overall_quality", "Medium") or "Medium"),
            "scores": dict((candidate_eval or {}).get("scores") or {}),
            "needs_revision": bool((candidate_eval or {}).get("needs_revision", False)),
            "accepted": accepted,
            "gate_vs_prev": round(candidate_avg - prev_avg, 3),
        })

        if accepted:
            srs = candidate_srs
            appendix_metrics = candidate_metrics
            eval_result = candidate_eval
            last_eval = candidate_eval or {}
            baseline_avg = candidate_avg
        else:
            rollback_events.append({
                "round": i,
                "reason": "avg_score_decreased",
                "prev_avg": prev_avg,
                "new_avg": candidate_avg,
                "delta": round(candidate_avg - prev_avg, 3),
            })
            srs = prev_srs
            eval_result = prev_eval
            last_eval = prev_eval or {}
            appendix_metrics = _compute_appendix_metrics(srs)
            baseline_avg = prev_avg

    # 方案1：不再做额外最终复评，最终分直接使用最后一轮迭代评估分
    appendix_metrics = _compute_appendix_metrics(srs)

    if isinstance(last_eval, dict):
        last_eval["appendix_metrics"] = appendix_metrics
        last_eval["score_history"] = score_history
        last_eval["round1"] = score_history[0] if len(score_history) >= 1 else None
        last_eval["round2"] = score_history[1] if len(score_history) >= 2 else None
        last_eval["rollback_events"] = rollback_events
        last_eval["score_gate"] = {
            "enabled": True,
            "rule": "rollback_if_avg_score_decreases",
            "final_baseline_avg": baseline_avg,
        }

    return srs, semantic_info, (last_eval or {})
