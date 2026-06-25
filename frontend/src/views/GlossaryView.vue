<template>
  <a-space direction="vertical" style="width: 100%" :size="16">
    <a-card title="名词解释：Agent（KnoMAS / CCGMAS）" :bordered="false">
      <a-alert
        type="info"
        show-icon
        style="margin-bottom: 12px"
        message="本系统包含 KnoMAS 与 CCGMAS 两套方法，Agent 术语按各自流程解释，不再混用。"
      />
      <a-descriptions :column="1" bordered>
        <a-descriptions-item label="PAA（Platform Residue Analysis Agent）">
          平台残留分析 Agent：识别 ISA 级与 OS 级平台残留，构建 PRP（Platform Residue Profile），为后续语义建模和代码生成提供平台上下文。
        </a-descriptions-item>
        <a-descriptions-item label="RGA（Requirement Generation Agent）">
          需求生成 Agent：融合通用实现、已有平台实现、项目上下文与 PRP，生成结构化需求文档；并执行需求质量评审与迭代优化。
        </a-descriptions-item>
        <a-descriptions-item label="CGA（Code Generation Agent）">
          代码生成 Agent：在需求文档与代码上下文共同约束下生成目标平台代码，支持多候选策略以提升迁移成功率。
        </a-descriptions-item>
        <a-descriptions-item label="VA（Verification Agent）">
          验证 Agent：执行静态残留检测、目标平台构建验证与测试验证，并将失败信息结构化反馈，驱动闭环修复。
        </a-descriptions-item>
        <a-descriptions-item label="cop_agent（COPA，KnoMAS）">
          Code Organization & Planning Agent：负责规划与设计类中间产物，主要产出 PDM、CIP、PS。
        </a-descriptions-item>
        <a-descriptions-item label="code_agent（CA，KnoMAS）">
          Code Generation Agent：根据合并后的 CIP+PS 生成实际代码文件。
        </a-descriptions-item>
        <a-descriptions-item label="reviewer_agent（KnoMAS）">
          Code Reviewer Agent：对生成产物进行一致性与质量审查，给出问题与改进建议。
        </a-descriptions-item>
      </a-descriptions>
    </a-card>

    <a-card title="名词解释：中间产物（你系统里的“可下载/可追踪”输出）" :bordered="false">
      <a-descriptions :column="1" bordered>
        <a-descriptions-item label="PDM（Physical Data Model）">
          物理数据模型产物：表/字段/主外键/约束等，是数据层的结构化“真相源”。
        </a-descriptions-item>
        <a-descriptions-item label="CIP（Code Implementation Plan）">
          代码实施计划：模块拆分、接口边界、职责分配、依赖关系等，用于指导后续生成。
        </a-descriptions-item>
        <a-descriptions-item label="PS（Project Structure）">
          项目结构蓝图：目录/文件/类/方法/签名/语义意图的权威定义。结构冲突时以 PS 为准。
        </a-descriptions-item>
        <a-descriptions-item label="WM（Working Memory）">
          工作记忆：记录文件/方法生成与修复状态、调度进度、失败回收等。WM 不是结构真相源，只是执行态追踪。
        </a-descriptions-item>
        <a-descriptions-item label="Logs（运行日志）">
          运行日志：记录执行阶段、错误上下文、产物收集等。用于排查问题和复现。
        </a-descriptions-item>
        <a-descriptions-item label="Project Code（生成项目代码）">
          根据 PS 生成的可编译项目代码与相关配置输出（例如 backend/frontend 代码）。
        </a-descriptions-item>
        <a-descriptions-item label="Artifacts（系统收集的产物包）">
          在 Web 系统里，后端会把本次运行新增的 output 文件收集到 runs/&lt;run_id&gt;/artifacts/output/，便于前端预览与下载。
        </a-descriptions-item>
      </a-descriptions>
    </a-card>
  </a-space>
</template>
