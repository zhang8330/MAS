<template>
  <a-space direction="vertical" style="width: 100%" :size="16">
    <a-card :bordered="false" class="hero-card">
      <div class="hero-title">数据集管理</div>
      <div class="hero-sub">集中管理 KnoMAS 代码生成案例与 CCGMAS 迁移评估样本。</div>
    </a-card>

    <a-card :bordered="false">
      <a-tabs v-model:activeKey="activeTab">
        <a-tab-pane key="knomas" tab="KnoMAS">
          <a-row :gutter="12" style="margin-bottom: 12px">
            <a-col :span="8" v-for="c in knStatsCards" :key="c.label">
              <a-card :body-style="{ padding: '14px 18px' }">
                <a-statistic :title="c.label" :value="c.value" :value-style="{ color: c.color, fontSize: '20px' }" />
                <div class="muted">{{ c.sub }}</div>
              </a-card>
            </a-col>
          </a-row>

          <a-card size="small" title="KnoMAS 案例库">
            <a-space style="margin-bottom: 10px">
              <a-select v-model:value="knDataset" style="width: 220px">
                <a-select-option v-for="dataset in knDatasets" :key="dataset" :value="dataset">{{ dataset }}</a-select-option>
              </a-select>
              <a-button type="primary" @click="openKnoCreate">新建案例</a-button>
              <a-button @click="openInputGenerate">需求建模生成案例</a-button>
              <a-button @click="openISDImport">同步 iSoftDevAgent 产物</a-button>
            </a-space>
            <a-table :columns="knColumns" :data-source="knFilteredCases" row-key="path" :pagination="{ pageSize: 10 }" size="small">
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'key_artifacts'">
                  <a-space wrap>
                    <a-tag v-for="k in artifactOrder" :key="k" :color="record.artifacts_presence?.[k] ? 'blue' : 'default'">
                      {{ artifactLabelMap[k] }}
                    </a-tag>
                  </a-space>
                </template>
                <template v-else-if="column.key === 'actions'">
                  <a-space>
                    <a-button type="link" size="small" @click="openKnoEdit(record)">编辑</a-button>
                    <a-popconfirm title="确认删除这个案例？" ok-text="删除" cancel-text="取消" @confirm="deleteKnoCase(record)">
                      <a-button type="link" danger size="small">删除</a-button>
                    </a-popconfirm>
                    <a-button type="link" size="small" @click="goKnoMASRun(record)">进入生成</a-button>
                  </a-space>
                </template>
              </template>
            </a-table>
          </a-card>
        </a-tab-pane>

        <a-tab-pane key="ccgmas" tab="CCGMAS">
          <a-row :gutter="12" style="margin-bottom:16px">
            <a-col :span="6" v-for="c in ccgStatCards" :key="c.label">
              <a-card :body-style="{ padding: '16px 20px' }">
                <a-statistic :title="c.label" :value="c.value" :value-style="{ color: c.color, fontSize: '22px' }" />
                <div class="muted">{{ c.sub }}</div>
              </a-card>
            </a-col>
          </a-row>

          <a-card :body-style="{ padding: '16px 20px' }">
            <div class="table-toolbar">
              <span class="toolbar-title">函数样本</span>
              <a-space wrap>
                <a-button type="primary" @click="openCCGCreate">新建样本</a-button>
                <a-select v-model:value="ccgFilters.migration_type" placeholder="type" allow-clear style="width:120px" @change="onCCGFilterChange">
                  <a-select-option value="arch">arch</a-select-option>
                  <a-select-option value="os">os</a-select-option>
                </a-select>
                <a-select v-model:value="ccgFilters.complexity" placeholder="complexity" allow-clear style="width:120px" @change="onCCGFilterChange">
                  <a-select-option value="High">High</a-select-option>
                  <a-select-option value="Medium">Medium</a-select-option>
                  <a-select-option value="Low">Low</a-select-option>
                </a-select>
                <a-select v-model:value="ccgFilters.repo" placeholder="repo" show-search allow-clear style="width:190px" @change="onCCGFilterChange">
                  <a-select-option v-for="r in ccgRepos" :key="r.repo" :value="r.repo">{{ r.repo }} ({{ r.count }})</a-select-option>
                </a-select>
                <a-select v-model:value="ccgFilters.split" placeholder="split" allow-clear style="width:130px" @change="onCCGFilterChange">
                  <a-select-option value="full">full</a-select-option>
                  <a-select-option value="gt_identical">gt_identical</a-select-option>
                  <a-select-option value="compile_only">compile_only</a-select-option>
                  <a-select-option value="test">test</a-select-option>
                  <a-select-option value="eval">eval</a-select-option>
                </a-select>
                <a-select v-model:value="ccgFilters.has_gt" placeholder="GT" allow-clear style="width:100px" @change="onCCGFilterChange">
                  <a-select-option :value="true">有 GT</a-select-option>
                  <a-select-option :value="false">无 GT</a-select-option>
                </a-select>
                <a-select v-model:value="ccgFilters.source_platform" placeholder="source" allow-clear style="width:120px" @change="onCCGFilterChange">
                  <a-select-option v-for="p in ccgSourcePlatformOptions" :key="p" :value="p">{{ p }}</a-select-option>
                </a-select>
                <a-select v-model:value="ccgFilters.target_platform" placeholder="target" allow-clear style="width:120px" @change="onCCGFilterChange">
                  <a-select-option v-for="p in ccgTargetPlatformOptions" :key="p" :value="p">{{ p }}</a-select-option>
                </a-select>
                <a-select v-model:value="ccgFilters.risk_level" placeholder="risk" allow-clear style="width:110px" @change="onCCGFilterChange">
                  <a-select-option value="High">High</a-select-option>
                  <a-select-option value="Medium">Medium</a-select-option>
                  <a-select-option value="Low">Low</a-select-option>
                </a-select>
              </a-space>
            </div>

            <a-table
              :columns="ccgColumns"
              :data-source="ccgTableData"
              :loading="ccgLoading"
              size="small"
              row-key="id"
              :scroll="{ x: 1180 }"
              :pagination="{ total: ccgTotal, current: ccgPage, pageSize: ccgPageSize, showTotal: t => `共 ${t} 条`, onChange: onCCGPageChange, size:'small' }"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'func_name'"><code>{{ record.func_name }}</code></template>
                <template v-else-if="column.key === 'repo'"><span class="repo-text">{{ record.repo }}</span></template>
                <template v-else-if="column.key === 'migration_type'"><a-tag>{{ record.migration_type }}</a-tag></template>
                <template v-else-if="column.key === 'source_platform'"><a-tag color="geekblue">{{ record.source_platform || '-' }}</a-tag></template>
                <template v-else-if="column.key === 'target_platform'"><a-tag color="purple">{{ record.target_platform || '-' }}</a-tag></template>
                <template v-else-if="column.key === 'complexity'"><a-tag :color="levelColor(record.complexity)">{{ record.complexity || 'Unknown' }}</a-tag></template>
                <template v-else-if="column.key === 'split'"><a-tag>{{ record.split || '-' }}</a-tag></template>
                <template v-else-if="column.key === 'has_gt'"><a-tag :color="record.has_gt ? 'green' : 'default'">{{ record.has_gt ? 'GT' : '-' }}</a-tag></template>
                <template v-else-if="column.key === 'risk_level'"><a-tag :color="levelColor(record.risk_level)">{{ record.risk_level || '-' }}</a-tag></template>
                <template v-else-if="column.key === 'actions'">
                  <a-space>
                    <a-button type="link" size="small" @click="openCCGEdit(record)">编辑</a-button>
                    <a-popconfirm title="确认删除这个样本？" ok-text="删除" cancel-text="取消" @confirm="deleteCCGFunction(record)">
                      <a-button type="link" danger size="small">删除</a-button>
                    </a-popconfirm>
                    <a-button type="link" size="small" @click="goCCGMASRun(record)">运行</a-button>
                  </a-space>
                </template>
              </template>
            </a-table>
          </a-card>
        </a-tab-pane>
      </a-tabs>
    </a-card>

    <a-modal v-model:open="knEditorOpen" :title="knEditorMode === 'create' ? '新建 KnoMAS 案例' : '编辑 KnoMAS 案例'" width="1080" @ok="saveKnoCase">
      <a-form layout="vertical">
        <a-row :gutter="10">
          <a-col :span="8">
            <a-form-item label="数据集">
              <a-select v-model:value="knEditor.dataset" :disabled="knEditorMode !== 'create'">
                <a-select-option v-for="dataset in knDatasets" :key="dataset" :value="dataset">{{ dataset }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="16">
            <a-form-item label="案例标识">
              <a-input v-model:value="knEditor.case_name" :disabled="knEditorMode !== 'create'" placeholder="例如 exam_platform / campus_service。将作为 data/cases/数据集/案例标识 的目录名。" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-alert
          type="info"
          show-icon
          class="case-editor-tip"
          message="KnoMAS 案例格式说明"
          description="这些文件会作为 COPA、Memory、CA 和 TA 的上游输入：用例与 ER 生成 PDM，类图/组件图/包图辅助拆分模块并生成 CIP/PS，技术栈决定项目目录、语言框架和后续代码生成策略。"
        />
        <a-tabs>
          <a-tab-pane v-for="name in artifactOrder" :key="name" :tab="artifactLabelMap[name] || name">
            <div class="artifact-editor-head">
              <div>
                <div class="artifact-editor-title">{{ artifactEditorMeta[name]?.title || name }}</div>
                <div class="artifact-editor-desc">{{ artifactEditorMeta[name]?.description || '填写该案例的辅助输入文件内容。' }}</div>
              </div>
              <a-tag>{{ name }}</a-tag>
            </div>

            <template v-if="name === 'tech_stack.json'">
              <a-row :gutter="12" class="tech-stack-picker">
                <a-col :xs="24" :md="12" v-for="option in techStackOptions" :key="option.key">
                  <button
                    type="button"
                    class="tech-stack-card"
                    :class="{ active: selectedTechStack === option.key }"
                    @click="selectTechStack(option.key)"
                  >
                    <span class="tech-stack-name">{{ option.label }}</span>
                    <span class="tech-stack-desc">{{ option.description }}</span>
                  </button>
                </a-col>
              </a-row>
              <a-textarea
                v-model:value="knEditor.files[name]"
                :rows="8"
                :placeholder="artifactEditorMeta[name]?.placeholder"
              />
            </template>

            <a-textarea
              v-else
              v-model:value="knEditor.files[name]"
              :rows="artifactEditorMeta[name]?.rows || 10"
              :placeholder="artifactEditorMeta[name]?.placeholder"
            />
          </a-tab-pane>
        </a-tabs>
      </a-form>
    </a-modal>

    <a-modal v-model:open="inputGenerateOpen" title="需求建模生成 KnoMAS 案例" width="920" :confirm-loading="inputGenerating" ok-text="生成设计产物" @ok="generateFromInput">
      <a-form layout="vertical">
        <a-row :gutter="10">
          <a-col :span="24">
            <a-form-item label="案例标识">
              <a-input v-model:value="inputGenerate.case_name" placeholder="例如 campus_security / exam_platform" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="业务需求说明">
          <a-textarea v-model:value="inputGenerate.description" :rows="12" placeholder="请描述系统目标、用户角色、核心业务流程、关键数据对象、约束条件和预期输出。系统会生成用例、ER 图、类图、组件图、包图和技术栈，并整理为 KnoMAS 可执行案例。" />
        </a-form-item>
        <a-alert type="info" show-icon message="生成完成后将自动进入 KnoMAS 的 COPA 规划阶段，继续生成 PDM、CIP 和 PS。" />
      </a-form>
    </a-modal>

    <a-modal v-model:open="isdImportOpen" title="同步 iSoftDevAgent 产物" width="920" :confirm-loading="isdImporting" ok-text="同步到 generated" @ok="importISDOutputs">
      <a-form layout="vertical">
        <a-row :gutter="10">
          <a-col :span="12">
            <a-form-item label="案例标识">
              <a-input v-model:value="isdImport.case_name" placeholder="例如 exam" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="项目名称">
              <a-input v-model:value="isdImport.project_name" placeholder="例如 exam" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="Requirements Agent 输出目录">
          <a-input v-model:value="isdImport.requirements_output_dir" placeholder="D:\projects\iSoftDevAgent\Requirements Agent\reagent\output\20260623_1918_exam" />
        </a-form-item>
        <a-form-item label="Architecture Agent 输出目录">
          <a-input v-model:value="isdImport.architecture_output_dir" placeholder="D:\projects\iSoftDevAgent\Architecture Agent\data\output\20260623_1828_exam" />
        </a-form-item>
        <a-form-item label="补充说明">
          <a-textarea v-model:value="isdImport.description" :rows="4" placeholder="可选。用于记录该案例的自然语言来源或导入说明，不影响已有图表产物的同步。" />
        </a-form-item>
        <a-alert type="info" show-icon message="同步后会写入 generated 数据集，形成 generated/案例标识，并可直接进入 KnoMAS 的 COPA 规划阶段。" />
      </a-form>
    </a-modal>

    <a-modal v-model:open="ccgEditorOpen" :title="ccgEditorMode === 'create' ? '新建 CCGMAS 样本' : '编辑 CCGMAS 样本'" width="900" @ok="saveCCGFunction">
      <a-form layout="vertical">
        <a-row :gutter="10">
          <a-col :span="12"><a-form-item label="repo"><a-input v-model:value="ccgEditor.repo" /></a-form-item></a-col>
          <a-col :span="12"><a-form-item label="func_name"><a-input v-model:value="ccgEditor.func_name" /></a-form-item></a-col>
        </a-row>
        <a-row :gutter="10">
          <a-col :span="8"><a-form-item label="migration_type"><a-select v-model:value="ccgEditor.migration_type"><a-select-option value="arch">arch</a-select-option><a-select-option value="os">os</a-select-option></a-select></a-form-item></a-col>
          <a-col :span="8"><a-form-item label="source_platform"><a-input v-model:value="ccgEditor.source_platform" /></a-form-item></a-col>
          <a-col :span="8"><a-form-item label="target_platform"><a-input v-model:value="ccgEditor.target_platform" /></a-form-item></a-col>
        </a-row>
        <a-row :gutter="10">
          <a-col :span="8"><a-form-item label="complexity"><a-select v-model:value="ccgEditor.complexity"><a-select-option value="High">High</a-select-option><a-select-option value="Medium">Medium</a-select-option><a-select-option value="Low">Low</a-select-option></a-select></a-form-item></a-col>
          <a-col :span="8"><a-form-item label="has_gt"><a-select v-model:value="ccgEditor.has_gt"><a-select-option :value="false">false</a-select-option><a-select-option :value="true">true</a-select-option></a-select></a-form-item></a-col>
          <a-col :span="8"><a-form-item label="split"><a-input v-model:value="ccgEditor.split" /></a-form-item></a-col>
        </a-row>
        <a-row :gutter="10">
          <a-col :span="12"><a-form-item label="risk_level"><a-select v-model:value="ccgEditor.risk_level" allow-clear><a-select-option value="High">High</a-select-option><a-select-option value="Medium">Medium</a-select-option><a-select-option value="Low">Low</a-select-option></a-select></a-form-item></a-col>
        </a-row>
        <a-form-item label="source_code"><a-textarea v-model:value="ccgEditor.source_code" :rows="8" /></a-form-item>
        <a-form-item label="generic_code"><a-textarea v-model:value="ccgEditor.generic_code" :rows="5" /></a-form-item>
        <a-form-item label="target_code"><a-textarea v-model:value="ccgEditor.target_code" :rows="5" /></a-form-item>
      </a-form>
    </a-modal>
  </a-space>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { http } from '../api/http'

const activeTab = ref('knomas')
const router = useRouter()

const knInfo = ref({})
const knCases = ref([])
const knDataset = ref('DevEval')
const knDatasets = computed(() => knInfo.value.datasets?.length ? knInfo.value.datasets : ['DevEval', 'CodeProjectEval'])

const artifactOrder = [
  'class_diagram.md',
  'component_diagram.md',
  'package_diagram.md',
  'use_case.md',
  'entity_relationship_diagram.md',
  'tech_stack.json',
  'input_source.md',
  'isoftdev_generation_report.md',
]
const artifactLabelMap = {
  'class_diagram.md': '类图',
  'component_diagram.md': '组件图',
  'package_diagram.md': '包图',
  'use_case.md': '用例',
  'entity_relationship_diagram.md': 'ER',
  'tech_stack.json': '技术栈',
  'input_source.md': '原始输入',
  'isoftdev_generation_report.md': '生成报告',
}
const techStackTemplates = {
  python: JSON.stringify({
    backend: { language: 'python', version: 'python3' },
    frontend: { language: 'vue', version: 'vue3' },
  }, null, 2),
  java: JSON.stringify({
    backend: { language: 'java', version: 'springboot3' },
    frontend: { language: 'vue', version: 'vue3' },
  }, null, 2),
}
const techStackOptions = [
  {
    key: 'python',
    label: 'Python',
    description: '生成 Python 项目结构，适合脚本、服务端业务逻辑和轻量后端案例。',
  },
  {
    key: 'java',
    label: 'Java / Spring Boot',
    description: '生成 Java Spring Boot 风格项目结构，适合分层后端服务案例。',
  },
]
const artifactEditorMeta = {
  'use_case.md': {
    title: '用例说明',
    rows: 12,
    description: '描述系统功能边界、参与者、主流程、异常流程和业务规则。PDM 会用它补充持久化约束，CIP/PS 会用它建立需求追踪。',
    placeholder: `推荐格式：JSON 数组，每个对象表示一个用例。
[
  {
    "use_case_name": "用户登录",
    "primary_actor": "普通用户",
    "secondary_actor": "认证服务",
    "trigger": "用户提交账号和密码",
    "use_case_description": "系统校验用户身份并返回登录结果。",
    "preconditions": ["用户已注册"],
    "postconditions": ["系统创建登录会话"],
    "main_flow": ["用户输入账号密码", "系统校验凭证", "系统返回用户信息"],
    "alternative_flows": [],
    "exception_flows": ["凭证错误时返回失败原因"],
    "priority": "High",
    "business_rules": ["账号必须唯一"]
  }
]`,
  },
  'entity_relationship_diagram.md': {
    title: '实体关系图',
    rows: 10,
    description: '定义持久化实体、属性、主键和实体关系。COPA 的 PDM 阶段会把它作为数据库结构的主要依据。',
    placeholder: `推荐使用 mermaid erDiagram。
# Entity Relationship Diagram

\`\`\`mermaid
erDiagram
  USER {
    string id
    string username
    string password_hash
  }
  ORDER {
    string id
    string user_id
    decimal total_amount
  }
  USER ||--o{ ORDER : places
\`\`\``,
  },
  'class_diagram.md': {
    title: '类图',
    rows: 12,
    description: '定义主要类、接口、字段和方法。CIP/PS 会用它确定可生成的类、方法、DTO/实体等结构，避免凭空造类。',
    placeholder: `推荐使用 mermaid classDiagram 或 PlantUML。
# Class Diagram

\`\`\`mermaid
classDiagram
  class UserController {
    +login(LoginRequest request) LoginResponse
  }
  class UserService {
    +authenticate(username, password) User
  }
  class UserRepository {
    +findByUsername(username) User
  }
  UserController --> UserService
  UserService --> UserRepository
\`\`\``,
  },
  'component_diagram.md': {
    title: '组件图',
    rows: 10,
    description: '描述业务模块及模块依赖方向。COPA 会用它拆分模块并校验 CIP 的 depends_on 关系。',
    placeholder: `推荐使用 mermaid flowchart 或 PlantUML。
# Component Diagram

\`\`\`mermaid
flowchart LR
  auth[auth_module]
  user[user_profile_module]
  audit[audit_module]
  auth --> user
  auth --> audit
\`\`\``,
  },
  'package_diagram.md': {
    title: '包图',
    rows: 10,
    description: '描述包、层次和代码归属。PS 阶段会用它确定文件路径、分层关系和模块归属。',
    placeholder: `推荐使用 PlantUML package 或 mermaid。
# Package Diagram

\`\`\`plantuml
@startuml
package "auth" {
  class UserController
  class UserService
  class UserRepository
}
package "common" {
  class ApiResponse
}
UserController --> UserService
UserService --> UserRepository
@enduml
\`\`\``,
  },
  'tech_stack.json': {
    title: '技术栈',
    rows: 8,
    description: '选择后会自动生成 JSON。PS 和代码生成会根据它决定语言、框架、源码根目录与 Memory 使用方式。',
    placeholder: techStackTemplates.python,
  },
  'input_source.md': {
    title: '原始需求输入',
    rows: 8,
    description: '记录案例来源、自然语言需求或人工整理说明。它主要用于追溯，不直接替代上面的结构化产物。',
    placeholder: `示例：
本案例来自用户对在线考试系统的自然语言描述。
系统需要支持教师组卷、学生答题、自动评分、成绩统计和管理员配置。`,
  },
  'isoftdev_generation_report.md': {
    title: '生成/导入报告',
    rows: 8,
    description: '记录该案例是否来自 iSoftDevAgent、每个文件的映射来源和过滤规则。手动新建时可留空或写简短说明。',
    placeholder: `示例：
# Case Preparation Report

- source: manual
- dataset: generated
- note: 手工录入 KnoMAS 所需的结构化设计产物。`,
  },
}

const knFilteredCases = computed(() => (knCases.value || []).filter((x) => (x.dataset || '') === knDataset.value))
const knStatsCards = computed(() => [
  { label: '数据根目录', value: knInfo.value.exists ? 1 : 0, color: knInfo.value.exists ? '#52c41a' : '#cf1322', sub: knInfo.value.data_root || '-' },
  { label: '案例目录', value: knInfo.value.cases_exists ? 1 : 0, color: knInfo.value.cases_exists ? '#52c41a' : '#cf1322', sub: knInfo.value.cases_root || '-' },
  { label: '案例数', value: (knCases.value || []).length, color: '#1d1d1f', sub: '来自 data/cases' },
])
const knColumns = [
  { title: '案例', dataIndex: 'name', key: 'name', width: 180 },
  { title: '文件数', dataIndex: 'file_count', key: 'file_count', width: 90 },
  { title: '产物', dataIndex: 'key_artifacts', key: 'key_artifacts' },
  { title: '路径', dataIndex: 'path', key: 'path', ellipsis: true },
  { title: '操作', key: 'actions', width: 210 },
]
const knEditorOpen = ref(false)
const knEditorMode = ref('create')
const knEditor = reactive({
  dataset: 'DevEval',
  case_name: '',
  files: Object.fromEntries(artifactOrder.map((name) => [name, name === 'tech_stack.json' ? techStackTemplates.python : (name.endsWith('.json') ? '{}' : '')])),
})
const selectedTechStack = ref('python')
const inputGenerateOpen = ref(false)
const inputGenerating = ref(false)
const inputGenerate = reactive({
  case_name: '',
  description: '',
})
const isdImportOpen = ref(false)
const isdImporting = ref(false)
const isdImport = reactive({
  case_name: 'exam',
  project_name: 'exam',
  requirements_output_dir: 'D:\\projects\\iSoftDevAgent\\Requirements Agent\\reagent\\output\\20260623_1918_exam',
  architecture_output_dir: 'D:\\projects\\iSoftDevAgent\\Architecture Agent\\data\\output\\20260623_1828_exam',
  description: '',
})

const ccgLoading = ref(false)
const ccgStats = ref({ total: 0, has_gt: 0, by_repo: [] })
const ccgRepos = ref([])
const ccgTableData = ref([])
const ccgTotal = ref(0)
const ccgPage = ref(1)
const ccgPageSize = ref(20)
const ccgFilters = ref({
  migration_type: 'arch',
  repo: null,
  complexity: null,
  split: null,
  has_gt: null,
  source_platform: null,
  target_platform: null,
  risk_level: null,
})
const ccgEditorOpen = ref(false)
const ccgEditorMode = ref('create')
const ccgEditor = reactive({
  id: null,
  repo: '',
  func_name: '',
  migration_type: 'arch',
  source_platform: 'amd64',
  target_platform: 'riscv64',
  complexity: 'Medium',
  has_gt: false,
  split: '',
  risk_level: '',
  source_code: '',
  generic_code: '',
  target_code: '',
})

const ccgSourcePlatformOptions = computed(() => Object.keys(ccgStats.value.by_source_platform || {}).filter(Boolean).sort())
const ccgTargetPlatformOptions = computed(() => Object.keys(ccgStats.value.by_target_platform || {}).filter(Boolean).sort())
const ccgStatCards = computed(() => {
  const s = ccgStats.value || {}
  return [
    { label: '样本数', value: s.total || 0, color: '#1d1d1f', sub: '当前筛选范围' },
    { label: '有 GT', value: s.has_gt || 0, color: '#52c41a', sub: '可用于参考评估' },
    { label: '仓库数', value: s.by_repo?.length || 0, color: '#1890ff', sub: '当前可见仓库' },
    { label: '数据划分', value: Object.keys(s.by_split || {}).length, color: '#722ed1', sub: Object.keys(s.by_split || {}).join(', ') || '-' },
  ]
})
const ccgColumns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 70 },
  { title: '函数', dataIndex: 'func_name', key: 'func_name', width: 180 },
  { title: 'Repo', dataIndex: 'repo', key: 'repo', width: 180 },
  { title: '类型', dataIndex: 'migration_type', key: 'migration_type', width: 90 },
  { title: '源平台', dataIndex: 'source_platform', key: 'source_platform', width: 110 },
  { title: '目标平台', dataIndex: 'target_platform', key: 'target_platform', width: 110 },
  { title: '复杂度', dataIndex: 'complexity', key: 'complexity', width: 110 },
  { title: 'Split', dataIndex: 'split', key: 'split', width: 120 },
  { title: 'GT', dataIndex: 'has_gt', key: 'has_gt', width: 80 },
  { title: '风险', dataIndex: 'risk_level', key: 'risk_level', width: 90 },
  { title: '操作', key: 'actions', width: 150, fixed: 'right' },
]
const levelColor = (value) => ({ High: 'red', Medium: 'orange', Low: 'green' }[value] || 'default')

const defaultArtifactContent = (name) => {
  if (name === 'tech_stack.json') return techStackTemplates.python
  return name.endsWith('.json') ? '{}' : ''
}

const inferTechStackKey = (raw) => {
  try {
    const data = JSON.parse(raw || '{}')
    const language = String(data?.backend?.language || '').toLowerCase()
    if (language.includes('java')) return 'java'
    return 'python'
  } catch {
    return 'python'
  }
}

const selectTechStack = (key) => {
  selectedTechStack.value = key
  knEditor.files['tech_stack.json'] = techStackTemplates[key] || techStackTemplates.python
}

const fetchKnoMAS = async () => {
  const [info, cases] = await Promise.all([
    http.get('/api/datasets/knomas/info'),
    http.get('/api/datasets/knomas/cases', { params: { dataset: knDataset.value, limit: 2000 } }),
  ])
  knInfo.value = info.data || {}
  knCases.value = cases.data.items || []
}

const ccgParams = () => ({
  page: ccgPage.value,
  page_size: ccgPageSize.value,
  migration_type: ccgFilters.value.migration_type || undefined,
  repo: ccgFilters.value.repo || undefined,
  complexity: ccgFilters.value.complexity || undefined,
  split: ccgFilters.value.split || undefined,
  has_gt: ccgFilters.value.has_gt === null ? undefined : ccgFilters.value.has_gt,
  source_platform: ccgFilters.value.source_platform || undefined,
  target_platform: ccgFilters.value.target_platform || undefined,
  risk_level: ccgFilters.value.risk_level || undefined,
})

const fetchCCGStats = async () => {
  const { data } = await http.get('/api/datasets/ccg/stats', { params: { migration_type: ccgFilters.value.migration_type || undefined } })
  ccgStats.value = data || {}
}
const fetchCCGRepos = async () => {
  const { data } = await http.get('/api/datasets/ccg/repos')
  ccgRepos.value = data || []
}
const fetchCCGFunctions = async () => {
  ccgLoading.value = true
  try {
    const { data } = await http.get('/api/datasets/ccg/functions', { params: ccgParams() })
    ccgTableData.value = data.items || []
    ccgTotal.value = data.total || 0
  } finally {
    ccgLoading.value = false
  }
}
const refreshCCG = async () => {
  await Promise.all([fetchCCGStats(), fetchCCGRepos(), fetchCCGFunctions()])
}
const onCCGFilterChange = async () => {
  ccgPage.value = 1
  await refreshCCG()
}
const onCCGPageChange = async (page) => {
  ccgPage.value = page
  await fetchCCGFunctions()
}

const openKnoCreate = () => {
  knEditorMode.value = 'create'
  knEditor.dataset = knDataset.value
  knEditor.case_name = ''
  selectedTechStack.value = 'python'
  artifactOrder.forEach((name) => { knEditor.files[name] = defaultArtifactContent(name) })
  knEditorOpen.value = true
}
const openInputGenerate = () => {
  inputGenerate.case_name = ''
  inputGenerate.description = ''
  inputGenerateOpen.value = true
}
const openISDImport = () => {
  isdImportOpen.value = true
}
const openKnoEdit = async (record) => {
  const { data } = await http.get(`/api/datasets/knomas/cases/${record.dataset}/${record.name}`)
  knEditorMode.value = 'edit'
  knEditor.dataset = data.dataset
  knEditor.case_name = data.case_name
  artifactOrder.forEach((name) => { knEditor.files[name] = data.files?.[name] || defaultArtifactContent(name) })
  selectedTechStack.value = inferTechStackKey(knEditor.files['tech_stack.json'])
  knEditorOpen.value = true
}
const saveKnoCase = async () => {
  if (!knEditor.case_name.trim()) return message.warning('请填写案例标识')
  const payload = { dataset: knEditor.dataset, case_name: knEditor.case_name, files: { ...knEditor.files } }
  if (knEditorMode.value === 'create') {
    await http.post('/api/datasets/knomas/cases', payload)
  } else {
    await http.put(`/api/datasets/knomas/cases/${knEditor.dataset}/${knEditor.case_name}`, payload)
  }
  knEditorOpen.value = false
  await fetchKnoMAS()
}
const generateFromInput = async () => {
  if (!inputGenerate.case_name.trim()) return message.warning('请填写案例标识')
  if (!inputGenerate.description.trim()) return message.warning('请填写业务需求说明')
  inputGenerating.value = true
  try {
    const { data } = await http.post('/api/datasets/knomas/cases/from-input', {
      ...inputGenerate,
      project_name: inputGenerate.case_name,
      run_isd: true,
    })
    inputGenerateOpen.value = false
    const caseName = data.case_name || inputGenerate.case_name
    knDataset.value = data.dataset || 'generated'
    message.success('设计产物已生成，正在进入 COPA 规划')
    await fetchKnoMAS()
    router.push({ path: '/run', query: { case_dir: data.case_dir || `data/cases/generated/${caseName}`, tab: 'copa' } })
  } finally {
    inputGenerating.value = false
  }
}
const importISDOutputs = async () => {
  if (!isdImport.case_name.trim()) return message.warning('请填写案例标识')
  if (!isdImport.requirements_output_dir.trim() && !isdImport.architecture_output_dir.trim()) {
    return message.warning('请至少填写一个 iSoftDevAgent 输出目录')
  }
  isdImporting.value = true
  try {
    const { data } = await http.post('/api/datasets/knomas/cases/import-isoftdev', { ...isdImport })
    isdImportOpen.value = false
    knDataset.value = data.dataset || 'generated'
    message.success('iSoftDevAgent 产物已同步到 generated 数据集')
    await fetchKnoMAS()
    router.push({ path: '/run', query: { case_dir: data.case_dir || `data/cases/generated/${data.case_name || isdImport.case_name}`, tab: 'copa' } })
  } finally {
    isdImporting.value = false
  }
}
const deleteKnoCase = async (record) => {
  await http.delete(`/api/datasets/knomas/cases/${record.dataset}/${record.name}`)
  await fetchKnoMAS()
}
const goKnoMASRun = (record) => {
  router.push({ path: '/run', query: { case_dir: record.case_dir || `data/cases/${record.dataset}/${record.name}` } })
}

const openCCGCreate = () => {
  ccgEditorMode.value = 'create'
  Object.assign(ccgEditor, {
    id: null,
    repo: '',
    func_name: '',
    migration_type: ccgFilters.value.migration_type || 'arch',
    source_platform: ccgFilters.value.migration_type === 'os' ? 'linux' : 'amd64',
    target_platform: ccgFilters.value.migration_type === 'os' ? 'windows' : 'riscv64',
    complexity: 'Medium',
    has_gt: false,
    split: 'test',
    risk_level: '',
    source_code: '',
    generic_code: '',
    target_code: '',
  })
  ccgEditorOpen.value = true
}
const openCCGEdit = async (record) => {
  const { data } = await http.get(`/api/datasets/ccg/functions/${record.id}`)
  ccgEditorMode.value = 'edit'
  Object.assign(ccgEditor, {
    id: data.id,
    repo: data.repo || '',
    func_name: data.func_name || '',
    migration_type: data.migration_type || 'arch',
    source_platform: data.source_platform || '',
    target_platform: data.target_platform || '',
    complexity: data.complexity || 'Medium',
    has_gt: Boolean(data.has_gt),
    split: data.split || '',
    risk_level: data.risk_level || '',
    source_code: data.source_code || '',
    generic_code: data.generic_code || '',
    target_code: data.target_code || '',
  })
  ccgEditorOpen.value = true
}
const saveCCGFunction = async () => {
  if (!ccgEditor.repo.trim() || !ccgEditor.func_name.trim() || !ccgEditor.source_code.trim()) {
    return message.warning('repo、func_name 和 source_code 不能为空')
  }
  const payload = { ...ccgEditor }
  if (ccgEditorMode.value === 'create') {
    await http.post('/api/datasets/ccg/functions', payload)
  } else {
    await http.put(`/api/datasets/ccg/functions/${ccgEditor.id}`, payload)
  }
  ccgEditorOpen.value = false
  await refreshCCG()
}
const deleteCCGFunction = async (record) => {
  await http.delete(`/api/datasets/ccg/functions/${record.id}`)
  await refreshCCG()
}
const goCCGMASRun = (record) => {
  router.push({
    path: '/ccgmas',
    query: {
      id: record?.id,
      migration_type: record?.migration_type || 'arch',
      source_platform: record?.source_platform || '',
      target_platform: record?.target_platform || '',
    },
  })
}

watch(knDataset, fetchKnoMAS)
onMounted(async () => {
  await fetchKnoMAS()
  await refreshCCG()
})
</script>

<style scoped>
.hero-card { background: #f5f9ff; }
.hero-title { font-size: 20px; font-weight: 700; color: #0f2a55; }
.hero-sub { margin-top: 4px; color: #3f5f8a; }
.muted { font-size: 11px; color: #8c8c8c; margin-top: 4px; word-break: break-all; }
.table-toolbar { display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; gap:8px; flex-wrap:wrap; }
.toolbar-title { font-size:14px; font-weight:500; }
.repo-text { font-size:12px; color:#8c8c8c; }
.case-editor-tip { margin-bottom: 12px; }
.artifact-editor-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  padding: 12px 14px;
  border: 1px solid #edf2f7;
  border-radius: 8px;
  background: #fbfdff;
}
.artifact-editor-title {
  color: #1f2937;
  font-size: 14px;
  font-weight: 600;
}
.artifact-editor-desc {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}
.tech-stack-picker { margin-bottom: 12px; }
.tech-stack-card {
  width: 100%;
  min-height: 92px;
  padding: 14px;
  border: 1px solid #d8e2ef;
  border-radius: 8px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}
.tech-stack-card:hover {
  border-color: #8bb8e8;
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.1);
}
.tech-stack-card.active {
  border-color: #1677ff;
  background: #f0f7ff;
  box-shadow: 0 0 0 2px rgba(22, 119, 255, 0.12);
}
.tech-stack-name {
  display: block;
  color: #10233f;
  font-size: 15px;
  font-weight: 700;
}
.tech-stack-desc {
  display: block;
  margin-top: 8px;
  color: #52677f;
  font-size: 12px;
  line-height: 1.5;
}
</style>

