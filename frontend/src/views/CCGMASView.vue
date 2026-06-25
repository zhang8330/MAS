<template>
  <div class="ccg-page">
    <a-row :gutter="16">
      <a-col :span="11">
        <a-card title="CCGMAS 代码迁移" :body-style="{ padding: '16px 20px' }">
          <a-form layout="vertical">
            <a-form-item label="source_code">
              <a-textarea
                v-model:value="state.input.source_code"
                :rows="10"
                :style="codeAreaStyle"
                placeholder="粘贴源平台实现代码"
              />
            </a-form-item>

            <a-form-item label="generic_code">
              <a-textarea
                v-model:value="state.input.generic_code"
                :rows="5"
                :style="codeAreaStyle"
                placeholder="可选：通用实现代码"
              />
            </a-form-item>

            <a-form-item label="project_context">
              <a-textarea
                v-model:value="state.input.project_context_text"
                :rows="6"
                :style="codeAreaStyle"
                placeholder="可选：粘贴同包相关 Go 文件或项目上下文；可用 --- filename: xxx.go --- 分段"
              />
            </a-form-item>

            <a-row :gutter="10">
              <a-col :span="8">
                <a-form-item label="migration_type">
                  <a-select v-model:value="state.input.migration_type">
                    <a-select-option value="arch">arch</a-select-option>
                    <a-select-option value="os">os</a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="source_platform">
                  <a-input v-model:value="state.input.source_platform" disabled />
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="target_platform">
                  <a-select v-model:value="state.input.target_platform" :options="targetPlatformOptions" />
                </a-form-item>
              </a-col>
            </a-row>

            <a-row :gutter="10">
              <a-col :span="12">
                <a-form-item label="生成模型配置">
                  <a-select
                    v-model:value="state.modelConfig.generationProfileId"
                    :options="profileOptions"
                    placeholder="选择生成模型配置"
                  />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="评审模型配置">
                  <a-select
                    v-model:value="state.modelConfig.evalProfileIds"
                    mode="multiple"
                    :max-tag-count="3"
                    :options="profileOptions"
                    placeholder="选择 RGA 评审模型配置"
                  />
                </a-form-item>
              </a-col>
            </a-row>

            <a-row :gutter="10">
              <a-col :span="12">
                <a-form-item label="pass@k">
                  <a-input-number v-model:value="state.input.k" :min="1" :max="5" style="width: 100%" />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="RGA 轮次">
                  <a-input-number v-model:value="state.input.rga_max_iter" :min="0" :max="5" style="width: 100%" />
                </a-form-item>
              </a-col>
            </a-row>
          </a-form>

          <a-divider style="margin: 12px 0" />
          <a-space wrap>
            <a-button type="primary" ghost :loading="state.ui.loading && state.ui.runningStep === 'PAA'" :disabled="!canRun('PAA')" @click="runStepPAA">运行 PAA</a-button>
            <a-button type="primary" ghost :loading="state.ui.loading && state.ui.runningStep === 'RGA'" :disabled="!canRun('RGA')" @click="runStepRGA">运行 RGA</a-button>
            <a-button type="primary" ghost :loading="state.ui.loading && state.ui.runningStep === 'CGA'" :disabled="!canRun('CGA')" @click="runStepCGA">运行 CGA</a-button>
            <a-button type="primary" ghost :loading="state.ui.loading && state.ui.runningStep === 'VA'" :disabled="!canRun('VA')" @click="runStepVA">运行 VA</a-button>
          </a-space>

          <a-alert v-if="state.ui.error" type="error" show-icon style="margin-top: 10px" :message="state.ui.error" />
        </a-card>
      </a-col>

      <a-col :span="13">
        <a-card title="执行过程" :body-style="{ padding: '16px 20px' }" style="margin-bottom: 16px">
          <a-space style="margin-bottom: 8px">
            <a-tag color="geekblue">耗时: {{ state.pipeline.elapsed_sec > 0 ? `${state.pipeline.elapsed_sec.toFixed(1)}s` : '-' }}</a-tag>
          </a-space>
          <a-steps :current="currentStep" size="small">
            <a-step v-for="s in steps" :key="s.key" :status="s.status" :description="s.desc">
              <template #title>
                <a-tooltip :title="stepExplain[s.key] || ''">
                  <span>{{ s.title }}</span>
                </a-tooltip>
              </template>
            </a-step>
          </a-steps>
        </a-card>

        <a-card title="评估指标" :body-style="{ padding: '12px 16px' }" style="margin-bottom: 16px">
          <a-row :gutter="10">
            <a-col :span="8"><a-tag color="blue">Compile@k: {{ compileAtK }}</a-tag></a-col>
            <a-col :span="8"><a-tag color="green">残留率: {{ residueRate }}</a-tag></a-col>
            <a-col :span="8"><a-tag color="purple">测试通过: {{ testPassRate }}</a-tag></a-col>
          </a-row>
        </a-card>

        <a-card v-if="state.pipeline.rga_quality" title="RGA 需求质量" :body-style="{ padding: '12px 16px' }" style="margin-bottom: 16px">
          <a-space style="margin-bottom: 8px" wrap>
            <a-tag color="blue">平均分: {{ Number(state.pipeline.rga_quality?.avg_score || 0).toFixed(2) }}</a-tag>
            <a-tag color="green">质量等级: {{ state.pipeline.rga_quality?.overall_quality || '-' }}</a-tag>
            <a-tag color="purple">评审模型: {{ ensembleEffective }}/{{ ensembleTotal }}</a-tag>
          </a-space>
          <a-alert
            v-if="ensembleLowConfidence"
            type="warning"
            show-icon
            :message="ensembleMsg || '有效评审模型数不足，建议重试'"
            style="margin-bottom: 10px"
          />
          <a-table
            :data-source="rgaScoreRows"
            :pagination="false"
            size="small"
            :columns="rgaScoreColumns"
            row-key="key"
          />
          <a-divider v-if="hasRgaRoundDetail" style="margin: 12px 0" />
          <a-space v-if="hasRgaRoundDetail" style="margin-bottom: 8px" wrap>
            <a-tag>Round1 平均分: {{ rgaRoundAvgSummary.round1 }}</a-tag>
            <a-tag v-if="hasRound2">Round2 平均分: {{ rgaRoundAvgSummary.round2 }}</a-tag>
            <a-tag v-if="hasRound2" :color="rgaRoundAvgSummary.deltaColor">变化(2-1): {{ rgaRoundAvgSummary.delta }}</a-tag>
          </a-space>
          <a-table
            v-if="hasRgaRoundDetail"
            :data-source="rgaRoundCompareRows"
            :pagination="false"
            size="small"
            :columns="rgaRoundCompareColumns"
            row-key="key"
          />
        </a-card>

        <a-card v-if="state.pipeline.va" title="最佳候选代码" :body-style="{ padding: '12px 16px' }" style="margin-bottom: 16px">
          <pre class="code-block">{{ state.pipeline.va?.best?.code || '' }}</pre>
        </a-card>

        <a-card
          v-if="state.pipeline.arp || state.pipeline.srs || state.pipeline.semantic_info || state.pipeline.rga_quality || state.pipeline.candidates.length || state.pipeline.va"
          title="中间产物"
          :body-style="{ padding: '12px 16px' }"
        >
          <a-space wrap>
            <a-button size="small" :disabled="!state.pipeline.arp" @click="downloadJson('01_paa_arp.json', state.pipeline.arp)">下载 PAA JSON</a-button>
            <a-button size="small" :disabled="!state.pipeline.srs" @click="downloadText('02_rga_srs.md', state.pipeline.srs)">下载 SRS.md</a-button>
            <a-button size="small" :disabled="!state.pipeline.semantic_info" @click="downloadJson('03_semantic.json', state.pipeline.semantic_info)">下载 Semantic JSON</a-button>
            <a-button size="small" :disabled="!state.pipeline.rga_quality" @click="downloadJson('04_rga_quality.json', state.pipeline.rga_quality)">下载 RGA Quality JSON</a-button>
            <a-button size="small" :disabled="!state.pipeline.candidates.length" @click="downloadJson('05_cga_candidates.json', state.pipeline.candidates)">下载 CGA 候选 JSON</a-button>
            <a-button size="small" :disabled="!state.pipeline.va" @click="downloadJson('06_va_report.json', state.pipeline.va)">下载 VA JSON</a-button>
          </a-space>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, watch } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { getFunction, runPAA, runRGA, runCGA, runVA } from '../api'

const route = useRoute()
const PROFILES_KEY = 'ccgmas_llm_profiles'

const codeAreaStyle = { fontFamily: 'Consolas,monospace', fontSize: '12px' }
const state = reactive({
  input: {
    func_id: null,
    source_code: '',
    generic_code: '',
    project_context_text: '',
    ground_truth: '',
    migration_type: 'arch',
    source_platform: 'amd64',
    target_platform: 'riscv64',
    k: 3,
    rga_max_iter: 2,
  },
  modelConfig: {
    profiles: [],
    generationProfileId: '',
    evalProfileIds: [],
  },
  pipeline: {
    arp: null,
    srs: '',
    semantic_info: null,
    rga_quality: null,
    candidates: [],
    va: null,
    feedback_trace: [],
    elapsed_sec: 0,
  },
  ui: {
    loading: false,
    error: '',
    runningStep: '',
    stepStatus: { PAA: 'wait', RGA: 'wait', CGA: 'wait', VA: 'wait' },
    stepDesc: {
      PAA: '平台残留分析',
      RGA: '需求语义建模',
      CGA: '候选代码生成',
      VA: '验证与评估',
    },
  },
})

const stepExplain = {
  PAA: '分析源平台残留和迁移范围。',
  RGA: '构建迁移需求和语义约束。',
  CGA: '生成目标平台候选实现。',
  VA: '执行编译、残留扫描、测试和指标计算。',
}

const profileOptions = computed(() => state.modelConfig.profiles.map((p) => ({ value: p.id, label: `${p.name} | ${p.model}` })))
const generationProfile = computed(() => state.modelConfig.profiles.find((p) => p.id === state.modelConfig.generationProfileId) || null)
const evalProfiles = computed(() => state.modelConfig.profiles.filter((p) => state.modelConfig.evalProfileIds.includes(p.id)))

function uniqueOptions(values) {
  return [...new Set(values.filter(Boolean))].map((x) => ({ label: x, value: x }))
}

const targetPlatformOptions = computed(() => {
  const defaults = state.input.migration_type === 'os' ? ['windows', 'darwin'] : ['riscv64']
  return uniqueOptions([state.input.target_platform, ...defaults])
})

const steps = computed(() => [
  { key: 'PAA', title: 'PAA', status: state.ui.stepStatus.PAA, desc: state.ui.stepDesc.PAA },
  { key: 'RGA', title: 'RGA', status: state.ui.stepStatus.RGA, desc: state.ui.stepDesc.RGA },
  { key: 'CGA', title: 'CGA', status: state.ui.stepStatus.CGA, desc: state.ui.stepDesc.CGA },
  { key: 'VA', title: 'VA', status: state.ui.stepStatus.VA, desc: state.ui.stepDesc.VA },
])
const currentStep = computed(() => {
  const order = ['PAA', 'RGA', 'CGA', 'VA']
  const processing = order.findIndex((k) => state.ui.stepStatus[k] === 'process')
  return processing >= 0 ? processing : order.filter((k) => state.ui.stepStatus[k] === 'finish').length
})

const compileAtK = computed(() => {
  const va = state.pipeline.va
  return va ? `${va.n_compile_ok || 0}/${va.total || 0}` : '-'
})
const residueRate = computed(() => {
  const va = state.pipeline.va
  return va ? `${(Number(va.residue_rate || 0) * 100).toFixed(0)}%` : '-'
})
const testPassRate = computed(() => {
  const tv = state.pipeline.va?.test_validation
  if (!tv || !Number(tv.n_test_executed || 0)) return 'N/A'
  return `${(Number(tv.test_pass_rate || 0) * 100).toFixed(0)}%`
})

const rgaScoreKeyMap = [
  { key: 'unambiguous', label: '无歧义性' },
  { key: 'understandable', label: '可理解性' },
  { key: 'correctness', label: '正确性' },
  { key: 'verifiable', label: '可验证性' },
  { key: 'internal_consistency', label: '内部一致性' },
  { key: 'non_redundancy', label: '无冗余性' },
  { key: 'completeness', label: '完整性' },
  { key: 'conciseness', label: '简洁性' },
]
const rgaScoreRows = computed(() => {
  const scores = state.pipeline.rga_quality?.scores || {}
  const rationale = state.pipeline.rga_quality?.score_rationale || {}
  return rgaScoreKeyMap.map(({ key, label }) => {
    const n = Number(scores[key])
    return {
      key,
      metric: label,
      score: Number.isFinite(n) ? n : 'N/A',
      rationale: rationale[key] || '',
    }
  })
})
const rgaScoreColumns = [
  { title: '维度', dataIndex: 'metric', key: 'metric', width: 130 },
  { title: '得分', dataIndex: 'score', key: 'score', width: 80 },
  { title: '简要说明', dataIndex: 'rationale', key: 'rationale', ellipsis: true },
]
const hasRound2 = computed(() => {
  const scores = state.pipeline.rga_quality?.round2?.scores || {}
  return rgaScoreKeyMap.some(({ key }) => Number.isFinite(Number(scores[key])))
})
const hasRgaRoundDetail = computed(() => Boolean(state.pipeline.rga_quality?.round1 || state.pipeline.rga_quality?.round2))
const rgaRoundCompareRows = computed(() => {
  const r1 = state.pipeline.rga_quality?.round1?.scores || {}
  const r2 = state.pipeline.rga_quality?.round2?.scores || {}
  return rgaScoreKeyMap.map(({ key, label }) => {
    const v1 = Number.isFinite(Number(r1[key])) ? Number(r1[key]) : null
    const v2 = Number.isFinite(Number(r2[key])) ? Number(r2[key]) : null
    const delta = v1 != null && v2 != null ? v2 - v1 : null
    return {
      key,
      metric: label,
      round1: v1 == null ? 'N/A' : v1,
      round2: v2 == null ? 'N/A' : v2,
      delta: delta == null ? 'N/A' : (delta > 0 ? `+${delta}` : `${delta}`),
    }
  })
})
const rgaRoundCompareColumns = computed(() => {
  const base = [
    { title: '维度', dataIndex: 'metric', key: 'metric', width: 130 },
    { title: '第 1 轮', dataIndex: 'round1', key: 'round1', width: 90 },
  ]
  if (hasRound2.value) {
    base.push(
      { title: '第 2 轮', dataIndex: 'round2', key: 'round2', width: 90 },
      { title: '变化(2-1)', dataIndex: 'delta', key: 'delta', width: 110 },
    )
  }
  return base
})
const rgaRoundAvgSummary = computed(() => {
  const a1 = Number(state.pipeline.rga_quality?.round1?.avg_score)
  const a2 = Number(state.pipeline.rga_quality?.round2?.avg_score)
  const has1 = Number.isFinite(a1)
  const has2 = Number.isFinite(a2)
  if (!has1 && !has2) return { round1: 'N/A', round2: 'N/A', delta: 'N/A', deltaColor: 'default' }
  if (!has2) return { round1: has1 ? a1.toFixed(2) : 'N/A', round2: 'N/A', delta: 'N/A', deltaColor: 'default' }
  const d = a2 - a1
  return {
    round1: has1 ? a1.toFixed(2) : 'N/A',
    round2: a2.toFixed(2),
    delta: d > 0 ? `+${d.toFixed(2)}` : d.toFixed(2),
    deltaColor: d > 0 ? 'green' : (d < 0 ? 'red' : 'blue'),
  }
})
const ensembleTotal = computed(() => state.pipeline.rga_quality?.review_ensemble?.num_models_total ?? state.pipeline.rga_quality?.review_ensemble?.models?.length ?? 0)
const ensembleEffective = computed(() => state.pipeline.rga_quality?.review_ensemble?.num_models_effective ?? state.pipeline.rga_quality?.review_ensemble?.num_models ?? 0)
const ensembleLowConfidence = computed(() => Boolean(state.pipeline.rga_quality?.review_ensemble?.low_confidence))
const ensembleMsg = computed(() => String(state.pipeline.rga_quality?.review_ensemble?.confidence_msg || ''))

watch(() => state.input.migration_type, (mt) => {
  if (mt === 'os') {
    state.input.source_platform = state.input.source_platform || 'linux'
    state.input.target_platform = state.input.target_platform || 'windows'
  } else {
    state.input.source_platform = state.input.source_platform || 'amd64'
    state.input.target_platform = state.input.target_platform || 'riscv64'
  }
})

function validateBeforeRun() {
  if (!state.input.source_code.trim()) return 'source_code 不能为空'
  if (!generationProfile.value) return '请先选择生成模型配置'
  if (evalProfiles.value.length < 2) message.warning('评审模型少于 2 个，仍可执行，但 RGA 评分置信度可能偏低。')
  return ''
}
function runtimeConfigFromProfile(p) {
  if (!p) return null
  return { provider: p.provider, base_url: p.base_url, api_key: p.api_key, model: p.model }
}
function parseProjectContextFiles(text) {
  const raw = String(text || '').trim()
  if (!raw) return []
  const segments = raw.split(/---\s*filename:\s*/i).map((x) => x.trim()).filter(Boolean)
  if (segments.length === 1 && !/^[\w./-]+\.go\s*\n/i.test(segments[0])) {
    return [{ filename: 'context_1.go', code: raw }]
  }
  return segments.map((segment, index) => {
    const nl = segment.indexOf('\n')
    if (nl <= 0) return { filename: `context_${index + 1}.go`, code: segment }
    return {
      filename: segment.slice(0, nl).trim() || `context_${index + 1}.go`,
      code: segment.slice(nl + 1).trim(),
    }
  }).filter((x) => x.code)
}
function requestBase() {
  return {
    func_id: state.input.func_id,
    source_code: state.input.source_code,
    generic_code: state.input.generic_code,
    ground_truth: state.input.ground_truth,
    project_context_files: parseProjectContextFiles(state.input.project_context_text),
    migration_type: state.input.migration_type,
    source_platform: state.input.source_platform,
    target_platform: state.input.target_platform,
    model: generationProfile.value?.model,
    k: state.input.k,
    rga_max_iter: state.input.rga_max_iter,
    runtime_llm_config: runtimeConfigFromProfile(generationProfile.value),
    eval_profiles: evalProfiles.value.map(runtimeConfigFromProfile),
  }
}
function withTimeoutConfig(timeoutMs = 600000) {
  return { timeout: timeoutMs }
}
function setStepStatus(step, s, desc = '') {
  state.ui.stepStatus[step] = s
  if (desc) state.ui.stepDesc[step] = desc
}
function setLoading(step, loading = true) {
  state.ui.loading = loading
  state.ui.runningStep = loading ? step : ''
}
function detectNoKeyMessage(rawText = '') {
  const text = String(rawText || '').toLowerCase()
  const hints = ['api key', 'apikey', 'unauthorized', 'authentication', 'invalid_api_key', 'missing api key', '401', 'no key']
  return hints.some((h) => text.includes(h)) ? '未检测到可用模型 API Key，请先配置 provider/base_url/api_key/model。' : ''
}
function normalizeError(e, fallback) {
  const d = e?.response?.data?.detail
  const detailText = d && typeof d === 'object' ? `${d.message || ''} ${d.detail || ''}` : (e?.message || '')
  const noKeyMsg = detectNoKeyMessage(detailText)
  if (noKeyMsg) return noKeyMsg
  if (d && typeof d === 'object') return `[${d.code || 'ERROR'}] ${d.message || fallback}${d.detail ? ` | ${d.detail}` : ''}`
  return e?.message || fallback
}
function canRun(step) {
  if (state.ui.loading) return false
  if (step === 'PAA') return true
  if (!state.input.source_code.trim() || !generationProfile.value) return false
  if (step === 'RGA') return !!state.pipeline.arp
  if (step === 'CGA') return !!state.pipeline.srs
  if (step === 'VA') return state.pipeline.candidates.length > 0
  return false
}
async function runStepPAA() {
  const err = validateBeforeRun()
  if (err) return (state.ui.error = err)
  state.ui.error = ''
  const t0 = performance.now()
  setLoading('PAA', true)
  setStepStatus('PAA', 'process', '执行中')
  try {
    const { data } = await runPAA(requestBase(), withTimeoutConfig())
    state.pipeline.arp = data?.arp || null
    const dt = (performance.now() - t0) / 1000
    state.pipeline.elapsed_sec += dt
    setStepStatus('PAA', 'finish', `完成 ${dt.toFixed(1)}s`)
  } catch (e) {
    setStepStatus('PAA', 'error', '执行失败')
    state.ui.error = normalizeError(e, 'PAA 执行失败')
  } finally {
    setLoading('', false)
  }
}

async function runStepRGA() {
  if (!state.pipeline.arp) return
  state.ui.error = ''
  const t0 = performance.now()
  setLoading('RGA', true)
  setStepStatus('RGA', 'process', '执行中')
  try {
    const { data } = await runRGA({ ...requestBase(), arp: state.pipeline.arp }, withTimeoutConfig())
    state.pipeline.arp = data?.arp || state.pipeline.arp
    state.pipeline.srs = data?.srs || ''
    state.pipeline.semantic_info = data?.semantic_info || null
    state.pipeline.rga_quality = data?.rga_quality || null
    const dt = (performance.now() - t0) / 1000
    state.pipeline.elapsed_sec += dt
    setStepStatus('RGA', 'finish', `完成 ${dt.toFixed(1)}s avg=${Number(state.pipeline.rga_quality?.avg_score || 0).toFixed(2)}`)
  } catch (e) {
    setStepStatus('RGA', 'error', '执行失败')
    state.ui.error = normalizeError(e, 'RGA 执行失败')
  } finally {
    setLoading('', false)
  }
}

async function runStepCGA() {
  if (!state.pipeline.srs) return
  state.ui.error = ''
  const t0 = performance.now()
  setLoading('CGA', true)
  setStepStatus('CGA', 'process', '执行中')
  try {
    const { data } = await runCGA({ ...requestBase(), arp: state.pipeline.arp, srs: state.pipeline.srs }, withTimeoutConfig())
    state.pipeline.candidates = data?.candidates || []
    const dt = (performance.now() - t0) / 1000
    state.pipeline.elapsed_sec += dt
    setStepStatus('CGA', 'finish', `完成 ${dt.toFixed(1)}s 候选=${state.pipeline.candidates.length}`)
  } catch (e) {
    setStepStatus('CGA', 'error', '执行失败')
    state.ui.error = normalizeError(e, 'CGA 执行失败')
  } finally {
    setLoading('', false)
  }
}

async function runStepVA() {
  if (!state.pipeline.candidates.length) return
  state.ui.error = ''
  const t0 = performance.now()
  setLoading('VA', true)
  setStepStatus('VA', 'process', '执行中')
  try {
    const { data } = await runVA({ ...requestBase(), srs: state.pipeline.srs, semantic_info: state.pipeline.semantic_info || {}, candidates: state.pipeline.candidates, enable_test_validation: true }, withTimeoutConfig())
    state.pipeline.va = data?.va || null
    const dt = (performance.now() - t0) / 1000
    state.pipeline.elapsed_sec += dt
    setStepStatus('VA', 'finish', `完成 ${dt.toFixed(1)}s compile=${state.pipeline.va?.n_compile_ok || 0}/${state.pipeline.va?.total || 0}`)
  } catch (e) {
    setStepStatus('VA', 'error', '执行失败')
    state.ui.error = normalizeError(e, 'VA 执行失败')
  } finally {
    setLoading('', false)
  }
}

function downloadJson(filename, obj) {
  if (!obj) return
  const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
}
function downloadText(filename, text) {
  if (text == null) return
  const blob = new Blob([String(text)], { type: 'text/plain;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
}
function buildDefaultProjectContext(detail, sourceCode) {
  const code = String(sourceCode || '').trim()
  if (!code) return ''
  const rawFile = detail?.source_file || detail?.arm64_file || ''
  const fallbackName = `${detail?.func_name || 'source'}_${detail?.source_platform || 'source'}.go`
  const filename = String(rawFile || fallbackName).split(/[\\/]/).pop() || fallbackName
  return `--- filename: ${filename} ---\n${code}`
}
function applyFunctionDetail(detail) {
  const migrationType = detail?.migration_type === 'os' ? 'os' : 'arch'
  state.input.func_id = Number(detail?.id || route.query.id || 0) || null
  state.input.source_code = detail?.source_code || detail?.arm64_code || ''
  state.input.generic_code = detail?.generic_code || ''
  state.input.project_context_text = detail?.project_context_text || detail?.project_context || buildDefaultProjectContext(detail, state.input.source_code)
  state.input.ground_truth = detail?.target_code || detail?.riscv64_code || ''
  state.input.migration_type = migrationType
  state.input.source_platform = detail?.source_platform || route.query.source_platform || (migrationType === 'os' ? 'linux' : 'amd64')
  state.input.target_platform = detail?.target_platform || route.query.target_platform || (migrationType === 'os' ? 'windows' : 'riscv64')
}

onMounted(() => {
  try {
    state.modelConfig.profiles = JSON.parse(localStorage.getItem(PROFILES_KEY) || '[]') || []
    state.modelConfig.generationProfileId = state.modelConfig.profiles[0]?.id || ''
    state.modelConfig.evalProfileIds = state.modelConfig.profiles.slice(0, 3).map((p) => p.id)
  } catch {
    state.modelConfig.profiles = []
  }
})

watch(() => route.query.id, async (id) => {
  const n = Number(id || 0)
  if (!n) return
  try {
    const res = await getFunction(n)
    applyFunctionDetail(res.data || {})
  } catch {
    state.ui.error = '加载数据集样本详情失败'
  }
}, { immediate: true })
</script>

<style scoped>
.ccg-page {
  width: 100%;
}

.code-block {
  font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
  font-size: 12px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  padding: 12px;
  overflow: auto;
  max-height: 380px;
  line-height: 1.6;
  white-space: pre;
  margin: 0;
}
</style>
