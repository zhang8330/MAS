<template>
  <a-space direction="vertical" style="width: 100%" :size="16">
    <a-card :bordered="false" class="hero-card">
      <div class="hero-main">
        <div>
          <div class="hero-title">KnoMAS 智能代码生成工作台</div>
          <div class="hero-sub">从需求说明生成架构产物、规划模型、记忆结构与可验证项目代码</div>
        </div>
      </div>
    </a-card>

    <a-card :bordered="false" class="workflow-card">
      <a-tabs v-model:activeKey="activeKnoTab" class="workflow-tabs" :animated="false">
        <a-tab-pane key="input" tab="1. 需求与架构建模">
          <div class="tab-head">
            <div>
              <div class="stage-eyebrow">Stage 01</div>
              <h3>创建 KnoMAS 生成案例</h3>
              <p>输入业务需求后，系统调用 iSoftDevAgent 生成需求与架构产物，并整理为 KnoMAS 后续可执行的案例输入。</p>
            </div>
            <a-tag v-if="modelingJobId || inputGenerating || architectureGenerating" color="blue">耗时 {{ modelingElapsedLabel }}</a-tag>
          </div>

          <div class="stage-section">
            <div class="section-title">输入</div>
            <a-form layout="vertical" class="input-form">
              <a-row :gutter="12">
                <a-col :xs="24" :md="12">
                  <a-form-item label="案例标识">
                    <a-input v-model:value="inputGenerate.case_name" placeholder="例如 exam_platform / campus_service" />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-form-item label="业务需求说明">
                <a-textarea
                  v-model:value="inputGenerate.description"
                  :rows="7"
                  placeholder="请描述系统目标、用户角色、核心业务流程、关键数据对象、约束条件和预期输出。&#10;示例：构建一个在线考试系统，支持教师组卷、学生答题、自动评分、成绩统计和权限管理。"
                />
              </a-form-item>
            </a-form>
          </div>

          <div class="stage-section action-section">
            <div class="section-title">操作</div>
            <a-space wrap>
              <a-button type="primary" :loading="inputGenerating" :disabled="architectureGenerating" @click="generateRequirements">生成需求规格</a-button>
              <a-button type="primary" ghost :loading="architectureGenerating" :disabled="inputGenerating || !requirementsResult" @click="generateArchitecture">生成架构设计</a-button>
            </a-space>
          </div>

          <div class="stage-section">
            <div class="section-title">输出</div>
            <div class="artifact-source output-selector">
              <a-select
                v-model:value="modelingCase.case_dir"
                allow-clear
                show-search
                :loading="caseLoading"
                :options="caseSelectOptions"
                placeholder="可选择已有 KnoMAS 案例查看其需求与架构产物；不选择时展示刚生成的产物"
                style="width: min(520px, 100%)"
                option-filter-prop="label"
                @change="loadModelingCaseArtifacts"
              />
              <span>{{ modelingCase.title || '当前展示：本次生成产物' }}</span>
            </div>
            <a-row :gutter="12" class="modeling-output-row">
              <a-col :xs="24" :lg="12">
                <a-card size="small" title="需求产物" class="asset-card">
                  <div class="artifact-source">
                    <span>{{ modelingRequirementsSourceLabel }}</span>
                    <a-button size="small" :disabled="!!modelingCase.case_dir || !modelingOutputs.requirements.output_dir" @click="loadIsdArtifacts('requirements', modelingOutputs.requirements.output_dir)">刷新</a-button>
                  </div>
                  <a-table :data-source="modelingRequirementItems" :columns="isdArtifactColumns" :pagination="{ pageSize: 6, size: 'small' }" size="small" row-key="rel_path">
                    <template #bodyCell="{ column, record }">
                      <template v-if="column.key === 'usage'">{{ artifactUsage(record) }}</template>
                      <template v-if="column.key === 'actions'">
                        <a-space size="small">
                          <a-button size="small" @click="openModelingArtifact('requirements', record)">预览</a-button>
                          <a-button size="small" type="link" :disabled="record.editable === false" @click="openModelingArtifact('requirements', record, true)">编辑</a-button>
                        </a-space>
                      </template>
                    </template>
                  </a-table>
                </a-card>
              </a-col>
              <a-col :xs="24" :lg="12">
                <a-card size="small" title="架构产物" class="asset-card">
                  <div class="artifact-source">
                    <span>{{ modelingArchitectureSourceLabel }}</span>
                    <a-button size="small" :disabled="!!modelingCase.case_dir || !modelingOutputs.architecture.output_dir" @click="loadIsdArtifacts('architecture', modelingOutputs.architecture.output_dir)">刷新</a-button>
                  </div>
                  <a-table :data-source="modelingArchitectureItems" :columns="isdArtifactColumns" :pagination="{ pageSize: 6, size: 'small' }" size="small" row-key="rel_path">
                    <template #bodyCell="{ column, record }">
                      <template v-if="column.key === 'usage'">{{ artifactUsage(record) }}</template>
                      <template v-if="column.key === 'actions'">
                        <a-space size="small">
                          <a-button size="small" @click="openModelingArtifact('architecture', record)">预览</a-button>
                          <a-button size="small" type="link" :disabled="record.editable === false" @click="openModelingArtifact('architecture', record, true)">编辑</a-button>
                        </a-space>
                      </template>
                    </template>
                  </a-table>
                </a-card>
              </a-col>
            </a-row>
          </div>
        </a-tab-pane>

        <a-tab-pane key="ltm" tab="2. LTM 配置">
          <div class="tab-head">
            <div>
              <div class="stage-eyebrow">Stage 02</div>
              <h3>选择 Long-term Memory 技术组合</h3>
              <p>在 COPA 规划前选择后端与前端的 LTM Profile，用长期架构知识和代码经验约束后续 PS 项目结构。</p>
            </div>
          </div>

          <div class="stage-section">
            <div class="section-title">输入 / 输出</div>
            <a-row :gutter="12">
              <a-col :xs="24" :lg="9">
                <a-card size="small" title="LTM 配置输入" class="asset-card">
                  <a-select
                    v-model:value="form.case_dir"
                    show-search
                    :loading="caseLoading"
                    :options="caseSelectOptions"
                    placeholder="选择一个已有 KnoMAS 案例应用 LTM 配置"
                    style="width: 100%; margin-bottom: 10px"
                    option-filter-prop="label"
                    @change="onCaseChange"
                  />
                  <a-tag v-if="casePreview.title" color="blue">{{ casePreview.title }}</a-tag>
                  <a-divider orientation="left">Profile 组合</a-divider>
                  <a-form layout="vertical" class="ltm-stack-form">
                    <a-form-item label="后端 LTM Profile">
                      <a-select
                        v-model:value="ltmStack.backend_profile_index"
                        :options="ltmBackendOptions"
                        placeholder="选择 Java/SpringBoot 或 Python/Flask"
                      />
                    </a-form-item>
                    <a-form-item label="前端 LTM Profile">
                      <a-select
                        v-model:value="ltmStack.frontend_profile_index"
                        :options="ltmFrontendOptions"
                        placeholder="选择 Vue3"
                      />
                    </a-form-item>
                  </a-form>
                  <div class="ltm-stack-summary">
                    <a-tag color="geekblue">{{ ltmStackLabel }}</a-tag>
                    <a-button size="small" type="primary" :disabled="!canApplyLtmStack" :loading="ltmStack.applying" @click="applyLtmStackToCase()">应用 LTM 配置</a-button>
                  </div>
                </a-card>
              </a-col>
              <a-col :xs="24" :lg="15">
                <a-card size="small" title="LTM 结构预览" class="asset-card">
                  <a-tabs size="small">
                    <a-tab-pane key="backend" tab="后端 Architecture Knowledge">
                      <a-list class="ltm-knowledge-list" size="small" :data-source="selectedBackendArchitectureRows">
                        <template #renderItem="{ item }">
                          <a-list-item>
                            <span class="ltm-package-name">{{ item.package }}</span>
                            <span class="ltm-package-desc">{{ item.description }}</span>
                          </a-list-item>
                        </template>
                      </a-list>
                      <a-empty v-if="!selectedBackendArchitectureRows.length" description="请选择后端 LTM Profile" class="empty-state compact" />
                    </a-tab-pane>
                    <a-tab-pane key="frontend" tab="前端 Architecture Knowledge">
                      <a-list class="ltm-knowledge-list" size="small" :data-source="selectedFrontendArchitectureRows">
                        <template #renderItem="{ item }">
                          <a-list-item>
                            <span class="ltm-package-name">{{ item.package }}</span>
                            <span class="ltm-package-desc">{{ item.description }}</span>
                          </a-list-item>
                        </template>
                      </a-list>
                      <a-empty v-if="!selectedFrontendArchitectureRows.length" description="请选择前端 LTM Profile" class="empty-state compact" />
                    </a-tab-pane>
                    <a-tab-pane key="wm-template" tab="Working Memory 模板">
                      <div class="wm-template-grid">
                        <div class="wm-template-item">
                          <b>project_graph</b>
                          <span>由后续 CIP / PS 合成，记录模块、文件、依赖和生成状态。</span>
                        </div>
                        <div class="wm-template-item">
                          <b>file_states</b>
                          <span>跟踪每个目标文件的 planned / generated / verified 状态。</span>
                        </div>
                        <div class="wm-template-item">
                          <b>generated_context（运行时）</b>
                          <span>代码生成阶段会动态汇总已生成文件信息；PS、LTM Profile 和案例约束分别通过 PS、LTM 与 Working Memory 输入进入代码生成。</span>
                        </div>
                      </div>
                    </a-tab-pane>
                  </a-tabs>
                </a-card>
              </a-col>
            </a-row>
          </div>

          <div class="stage-section">
            <div class="section-title">Long-term Memory 管理</div>
            <a-collapse :bordered="false">
              <a-collapse-panel :header="`Long-term Memory Profile（${ltmData.architecture.length + ltmData.experience.length}）`" key="architecture">
                <div class="memory-panel-actions">
                  <span>Long-term Memory 用于沉淀技术栈规则和可复用工程经验，当前组合会影响后续 PS 结构。</span>
                  <a-space size="small">
                    <a-button size="small" type="primary" ghost @click="openLtmEditor('architecture')">新增 Architecture Knowledge</a-button>
                    <a-button size="small" type="primary" ghost @click="openLtmEditor('experience')">新增 Code Experience</a-button>
                  </a-space>
                </div>
                <a-tabs class="ltm-tabs" size="small">
                  <a-tab-pane key="architecture" tab="Architecture Knowledge">
                    <a-collapse :bordered="false">
                      <a-collapse-panel v-for="profile in ltmData.architecture" :key="`ak-${profile.profile_index}`" :header="`${profile.label}（${profile.entries.length}）`">
                        <a-table :data-source="profile.entries" :columns="ltmArchitectureColumns" :pagination="false" size="small" row-key="id">
                          <template #bodyCell="{ column, record }">
                            <template v-if="column.key === 'actions'">
                              <a-button size="small" type="link" @click="openLtmEditor('architecture', record)">编辑</a-button>
                            </template>
                          </template>
                        </a-table>
                      </a-collapse-panel>
                    </a-collapse>
                  </a-tab-pane>
                  <a-tab-pane key="experience" tab="Code Generation Experience">
                    <a-collapse :bordered="false">
                      <a-collapse-panel v-for="profile in ltmData.experience" :key="`exp-${profile.profile_index}`" :header="`${profile.label}（${profile.entries.length}）`">
                        <a-table :data-source="profile.entries" :columns="ltmExperienceColumns" :pagination="false" size="small" row-key="id">
                          <template #bodyCell="{ column, record }">
                            <template v-if="column.key === 'match'">
                              {{ Array.isArray(record.match?.path) ? record.match.path.join(', ') : record.match?.path }}
                            </template>
                            <template v-if="column.key === 'actions'">
                              <a-button size="small" type="link" @click="openLtmEditor('experience', record)">编辑</a-button>
                            </template>
                          </template>
                        </a-table>
                      </a-collapse-panel>
                    </a-collapse>
                  </a-tab-pane>
                  <a-tab-pane key="raw" tab="Raw JSON">
                    <artifact-table :items="memoryPageGrouped.ltm" :columns="artifactColumns" :run-id="runId" :downloadable="false" @preview="previewMemoryArtifact" />
                  </a-tab-pane>
                </a-tabs>
              </a-collapse-panel>
            </a-collapse>
          </div>

          <div class="stage-section action-section">
            <div class="section-title">操作</div>
            <a-space wrap>
              <a-button :loading="caseLoading" @click="loadCases">刷新案例</a-button>
              <a-button type="primary" :disabled="!canApplyLtmStack" :loading="ltmStack.applying" @click="applyLtmStackToCase()">应用 LTM 配置</a-button>
              <a-button @click="activeKnoTab = 'copa'">进入 COPA 规划</a-button>
            </a-space>
          </div>
        </a-tab-pane>

        <a-tab-pane key="copa" tab="3. COPA 规划">
          <div class="tab-head">
            <div>
              <div class="stage-eyebrow">Stage 03</div>
              <h3>生成 PDM / CIP / PS</h3>
              <p>从已有 KnoMAS 案例中选择需求与架构产物，并结合已选 LTM Profile 组合生成 PDM、CIP 和 PS。</p>
            </div>
          </div>

          <div class="stage-section">
            <div class="section-title">输入 / 输出</div>
            <a-row :gutter="12">
              <a-col :xs="24" :lg="10">
                <a-card size="small" title="COPA 输入案例" class="asset-card">
                  <a-select
                    v-model:value="form.case_dir"
                    show-search
                    :loading="caseLoading"
                    :options="caseSelectOptions"
                    placeholder="选择一个已有 KnoMAS 案例作为 COPA 输入"
                    style="width: 100%; margin-bottom: 10px"
                    option-filter-prop="label"
                    @change="onCaseChange"
                  />
                  <a-tag v-if="casePreview.title" color="blue">{{ casePreview.title }}</a-tag>
                  <a-select
                    v-if="casePreview.fileOptions.length"
                    v-model:value="casePreview.activeFile"
                    :options="casePreview.fileOptions"
                    style="width: 100%; margin-top: 10px"
                    @change="onPreviewFileChange"
                  />
                  <div v-if="casePreview.activeFile" class="case-editor-toolbar read-only">
                    <span>当前文件用于 COPA 规划输入预览，需求与架构产物请在上一阶段编辑。</span>
                  </div>
                  <pre v-if="casePreview.content" class="preview-light">{{ casePreview.content }}</pre>
                  <a-empty v-else description="暂无案例产物，请选择一个已有案例" class="empty-state" />
                  <a-divider orientation="left">当前 LTM 配置</a-divider>
                  <div class="ltm-stack-summary">
                    <a-tag color="geekblue">{{ ltmStackLabel }}</a-tag>
                    <a-button size="small" type="link" @click="activeKnoTab = 'ltm'">调整配置</a-button>
                  </div>
                  <div class="ltm-structure-preview">
                    <a-tabs size="small">
                      <a-tab-pane key="backend" tab="后端结构">
                        <a-list class="ltm-knowledge-list" size="small" :data-source="selectedBackendArchitectureRows.slice(0, 6)">
                          <template #renderItem="{ item }">
                            <a-list-item>
                              <span class="ltm-package-name">{{ item.package }}</span>
                              <span class="ltm-package-desc">{{ item.description }}</span>
                            </a-list-item>
                          </template>
                          <template #emptyText>
                            <a-empty description="请选择后端 LTM Profile" class="empty-state compact" />
                          </template>
                        </a-list>
                      </a-tab-pane>
                      <a-tab-pane key="frontend" tab="前端结构">
                        <a-list class="ltm-knowledge-list" size="small" :data-source="selectedFrontendArchitectureRows.slice(0, 6)">
                          <template #renderItem="{ item }">
                            <a-list-item>
                              <span class="ltm-package-name">{{ item.package }}</span>
                              <span class="ltm-package-desc">{{ item.description }}</span>
                            </a-list-item>
                          </template>
                          <template #emptyText>
                            <a-empty description="请选择前端 LTM Profile" class="empty-state compact" />
                          </template>
                        </a-list>
                      </a-tab-pane>
                    </a-tabs>
                  </div>
                </a-card>
              </a-col>
              <a-col :xs="24" :lg="14">
                <a-card size="small" title="COPA 输出产物" class="asset-card">
                  <a-collapse :bordered="false" accordion>
                    <a-collapse-panel :header="`PDM 问题域模型（${copaGrouped.pdm.length}）`" key="pdm">
                      <artifact-table :items="copaGrouped.pdm" :columns="artifactColumns" :run-id="runId" :downloadable="!copaCaseArtifacts.length" @preview="previewCopaArtifact" />
                    </a-collapse-panel>
                    <a-collapse-panel :header="`CIP 类接口规划（${copaGrouped.cip.length}）`" key="cip">
                      <artifact-table :items="copaGrouped.cip" :columns="artifactColumns" :run-id="runId" :downloadable="!copaCaseArtifacts.length" @preview="previewCopaArtifact" />
                    </a-collapse-panel>
                    <a-collapse-panel :header="`PS 项目结构规划（${copaGrouped.ps.length}）`" key="ps">
                      <artifact-table :items="copaGrouped.ps" :columns="artifactColumns" :run-id="runId" :downloadable="!copaCaseArtifacts.length" @preview="previewCopaArtifact" />
                    </a-collapse-panel>
                  </a-collapse>
                </a-card>
              </a-col>
            </a-row>
          </div>

          <div class="stage-section action-section">
            <div class="section-title">操作</div>
            <a-space wrap>
              <a-button :loading="caseLoading" @click="loadCases">刷新案例</a-button>
              <a-button type="primary" :disabled="!form.case_dir" :loading="loading && runningStageRequest === 'planning'" @click="submitStageRun('planning')">生成 COPA 规划</a-button>
              <a-button @click="enterMemoryTab">进入 Working Memory</a-button>
            </a-space>
          </div>
        </a-tab-pane>

        <a-tab-pane key="wm" tab="4. Working Memory">
          <div class="tab-head">
            <div>
              <div class="stage-eyebrow">Stage 04</div>
              <h3>构建当前案例 Working Memory</h3>
              <p>以 COPA 阶段的 CIP / PS 为输入，构建当前案例的 Working Memory，为代码生成和后续 TA 修复提供依据。</p>
            </div>
          </div>

          <div class="stage-section">
            <div class="section-title">输入</div>
            <a-row :gutter="12" class="memory-input-grid">
              <a-col :xs="24" :md="12" :xl="6">
                <a-card size="small" title="Working Memory 输入案例" class="asset-card">
                  <a-select
                    v-model:value="memoryInput.case_dir"
                    show-search
                    :loading="caseLoading"
                    :options="caseSelectOptions"
                    placeholder="选择已有 KnoMAS 案例作为 Working Memory 构建输入"
                    style="width: 100%; margin-bottom: 10px"
                    option-filter-prop="label"
                    @change="onMemoryCaseChange"
                  />
                  <a-tag v-if="memoryInput.title" color="blue">{{ memoryInput.title }}</a-tag>
                  <a-empty v-else description="请选择一个已有案例" class="empty-state compact" />
                </a-card>
              </a-col>
              <a-col :xs="24" :md="12" :xl="6">
                <a-card size="small" title="合成 CIP / PS" class="asset-card">
                  <artifact-table :items="memoryCopaGrouped.merged" :columns="artifactColumns" :run-id="runId" :downloadable="false" @preview="previewMemoryCopaArtifact" />
                </a-card>
              </a-col>
              <a-col :xs="24" :md="12" :xl="6">
                <a-card size="small" title="CIP 子模块" class="asset-card">
                  <artifact-table :items="memoryCopaGrouped.cipModules" :columns="artifactColumns" :run-id="runId" :downloadable="false" @preview="previewMemoryCopaArtifact" />
                </a-card>
              </a-col>
              <a-col :xs="24" :md="12" :xl="6">
                <a-card size="small" title="PS 子模块" class="asset-card">
                  <artifact-table :items="memoryCopaGrouped.psModules" :columns="artifactColumns" :run-id="runId" :downloadable="false" @preview="previewMemoryCopaArtifact" />
                </a-card>
              </a-col>
            </a-row>
          </div>

          <div class="stage-section action-section">
            <div class="section-title">操作</div>
            <a-space wrap>
              <a-button type="primary" :disabled="!memoryInput.case_dir" @click="buildWorkingMemory">构建 Working Memory</a-button>
              <a-button @click="activeKnoTab = 'ca'">进入代码生成</a-button>
            </a-space>
          </div>

          <div class="stage-section">
            <div class="section-title">输出</div>
            <a-collapse :bordered="false">
              <a-collapse-panel :header="`Working Memory（${memoryPageGrouped.wm.length}）`" key="wm">
                <artifact-table :items="memoryPageGrouped.wm" :columns="artifactColumns" :run-id="runId" editable :downloadable="false" @preview="previewMemoryArtifact" @edit="editMemoryArtifact" />
              </a-collapse-panel>
            </a-collapse>
          </div>
        </a-tab-pane>

        <a-tab-pane key="ca" tab="5. 代码生成">
          <div class="tab-head">
            <div>
              <div class="stage-eyebrow">Stage 05</div>
              <h3>基于 PS 和 Memory 生成项目代码</h3>
              <p>代码生成阶段以 PS 项目结构规划、Long-term Memory 和 Working Memory 为输入，生成可编译的项目代码。</p>
            </div>
          </div>

          <div class="stage-section">
            <div class="section-title">输入</div>
            <a-row :gutter="12" class="memory-input-grid">
              <a-col :xs="24" :md="12" :xl="6">
                <a-card size="small" title="代码生成输入案例" class="asset-card">
                  <a-select
                    v-model:value="memoryInput.case_dir"
                    show-search
                    :loading="caseLoading"
                    :options="caseSelectOptions"
                    placeholder="选择已有 KnoMAS 案例作为代码生成输入"
                    style="width: 100%; margin-bottom: 10px"
                    option-filter-prop="label"
                    @change="onMemoryCaseChange"
                  />
                  <a-tag v-if="memoryInput.title" color="blue">{{ memoryInput.title }}</a-tag>
                  <a-empty v-else description="请选择一个已有案例" class="empty-state compact" />
                </a-card>
              </a-col>
              <a-col :xs="24" :md="12" :xl="6">
                <a-card size="small" title="PS 项目结构规划" class="asset-card">
                  <artifact-table :items="codegenPsArtifacts" :columns="artifactColumns" :run-id="runId" :downloadable="false" @preview="previewCodegenPsArtifact" />
                </a-card>
              </a-col>
              <a-col :xs="24" :md="12" :xl="6">
                <a-card size="small" title="Long-term Memory" class="asset-card">
                  <artifact-table :items="memoryPageGrouped.ltm" :columns="artifactColumns" :run-id="runId" :downloadable="false" @preview="previewMemoryArtifact" />
                </a-card>
              </a-col>
              <a-col :xs="24" :md="12" :xl="6">
                <a-card size="small" title="Working Memory" class="asset-card">
                  <artifact-table :items="memoryPageGrouped.wm" :columns="artifactColumns" :run-id="runId" editable :downloadable="false" @preview="previewMemoryArtifact" @edit="editMemoryArtifact" />
                </a-card>
              </a-col>
            </a-row>
          </div>

          <div class="stage-section action-section">
            <div class="section-title">操作</div>
            <a-space wrap>
              <a-button type="primary" :loading="loading && runningStageRequest === 'codegen'" @click="submitStageRun('codegen')">生成项目代码</a-button>
              <a-button :disabled="!runId" @click="refreshAll">刷新编译结果</a-button>
              <a-tooltip title="只有编译结果存在错误时，才需要基于编译反馈继续修复">
                <span>
                  <a-button
                    :disabled="!canRepairCompile"
                    :loading="loading && runningStageRequest === 'codegen'"
                    @click="submitCompileRepair"
                  >
                    基于编译反馈修复
                  </a-button>
                </span>
              </a-tooltip>
              <a-button @click="activeKnoTab = 'testcases'">进入测试用例生成</a-button>
            </a-space>
          </div>

          <div class="stage-section">
            <div class="section-title">输出</div>
            <a-collapse :bordered="false">
              <a-collapse-panel :header="`项目产物（${projectArtifacts.length}）`" key="project-output">
                <artifact-table
                  :items="projectArtifacts"
                  :columns="artifactColumns"
                  :run-id="runId"
                  :downloadable="!caseProjectArtifacts.length"
                  :pagination="{ pageSize: 8, size: 'small' }"
                  @preview="previewProjectArtifact"
                />
              </a-collapse-panel>
            </a-collapse>
          </div>
        </a-tab-pane>

        <a-tab-pane key="testcases" tab="6. 测试用例生成">
          <div class="tab-head">
            <div>
              <div class="stage-eyebrow">Stage 06</div>
              <h3>生成并查看测试用例</h3>
              <p>基于需求产物、架构产物和已生成项目代码生成测试用例，让后续修复阶段有明确的测试依据。</p>
            </div>
          </div>

          <div class="stage-section">
            <div class="section-title">输入</div>
            <a-row :gutter="12" class="memory-input-grid">
              <a-col :xs="24" :md="10" :xl="8">
                <a-card size="small" title="测试输入案例" class="asset-card">
                  <a-select
                    v-model:value="memoryInput.case_dir"
                    show-search
                    :loading="caseLoading"
                    :options="caseSelectOptions"
                    placeholder="选择已有 KnoMAS 案例作为测试生成输入"
                    style="width: 100%; margin-bottom: 10px"
                    option-filter-prop="label"
                    @change="onMemoryCaseChange"
                  />
                  <a-tag v-if="memoryInput.title" color="blue">{{ memoryInput.title }}</a-tag>
                  <a-empty v-else description="请选择一个已有案例" class="empty-state compact" />
                </a-card>
              </a-col>
              <a-col :xs="24" :md="14" :xl="16">
                <a-card size="small" title="项目代码产物" class="asset-card">
                  <artifact-table
                    :items="projectArtifacts"
                    :columns="artifactColumns"
                    :run-id="runId"
                    :downloadable="!caseProjectArtifacts.length"
                    :pagination="{ pageSize: 8, size: 'small' }"
                    @preview="previewProjectArtifact"
                  />
                  <a-empty v-if="!projectArtifacts.length" description="暂无项目代码产物，请先完成代码生成" class="empty-state compact" />
                </a-card>
              </a-col>
            </a-row>
          </div>

          <div class="stage-section action-section">
            <div class="section-title">操作</div>
            <a-space wrap>
              <a-button
                type="primary"
                :disabled="!memoryInput.case_dir || !projectArtifacts.length"
                :loading="loading && runningStageRequest === 'testgen'"
                @click="submitTestCaseGeneration"
              >
                生成测试用例
              </a-button>
              <a-button @click="activeKnoTab = 'repair'">进入基于测试的修复</a-button>
            </a-space>
          </div>

          <div class="stage-section">
            <div class="section-title">输出</div>
            <a-collapse :bordered="false">
              <a-collapse-panel :header="`测试用例产物（${testCaseArtifacts.length}）`" key="testcase-output">
                <artifact-table :items="testCaseArtifacts" :columns="artifactColumns" :run-id="runId" @preview="previewArtifact" />
                <a-empty v-if="!testCaseArtifacts.length" description="暂无测试用例产物，生成后将在这里展示" class="empty-state" />
              </a-collapse-panel>
            </a-collapse>
          </div>
        </a-tab-pane>

        <a-tab-pane key="repair" tab="7. 基于测试的修复">
          <div class="tab-head">
            <div>
              <div class="stage-eyebrow">Stage 07</div>
              <h3>运行测试并迭代修复</h3>
              <p>使用第 6 阶段生成或已有的测试用例，对项目代码执行测试反馈和 TA 迭代修复，并汇总最终验证结果。</p>
            </div>
          </div>

          <div class="stage-section">
            <div class="section-title">输入</div>
            <a-row :gutter="12" class="repair-input-grid">
              <a-col :xs="24" :lg="7">
                <a-card size="small" title="待修复项目" class="asset-card">
                  <a-select
                    v-model:value="memoryInput.case_dir"
                    show-search
                    :loading="caseLoading"
                    :options="caseSelectOptions"
                    placeholder="选择已生成项目代码的 KnoMAS 案例"
                    style="width: 100%; margin-bottom: 10px"
                    option-filter-prop="label"
                    @change="onMemoryCaseChange"
                  />
                  <a-space size="small" wrap>
                    <a-tag v-if="memoryInput.title" color="blue">{{ memoryInput.title }}</a-tag>
                    <a-tag>项目代码 {{ projectArtifacts.length }}</a-tag>
                    <a-tag>TA Memory {{ memoryGrouped.ta.length }}</a-tag>
                  </a-space>
                </a-card>
              </a-col>
              <a-col :xs="24" :lg="11">
                <a-card size="small" title="测试用例选择" class="asset-card repair-testcase-card">
                  <div class="repair-testcase-toolbar">
                    <a-select
                      v-model:value="repairSelection.test_artifact_id"
                      allow-clear
                      show-search
                      :options="testCaseOptions"
                      placeholder="选择第 6 步生成或已有的测试用例产物"
                      style="width: 100%"
                      option-filter-prop="label"
                    />
                    <a-tag color="geekblue">可用测试产物 {{ testCaseArtifacts.length }}</a-tag>
                  </div>
                  <div v-if="testCaseArtifacts.length" class="repair-testcase-list">
                    <button
                      v-for="item in testCaseArtifacts"
                      :key="item.artifact_id"
                      type="button"
                      class="repair-testcase-item"
                      :class="{ active: item.artifact_id === selectedTestCaseArtifact?.artifact_id }"
                      @click="repairSelection.test_artifact_id = item.artifact_id"
                    >
                      <span class="repair-testcase-main">
                        <b>{{ item.rel_path || item.name }}</b>
                        <small>{{ item.kind || 'test case' }}</small>
                      </span>
                      <span class="repair-testcase-actions">
                        <a-button size="small" type="link" @click.stop="previewArtifact(item)">预览</a-button>
                      </span>
                    </button>
                  </div>
                  <a-empty v-else description="暂无测试用例，请先在第 6 步生成" class="empty-state compact" />
                </a-card>
              </a-col>
              <a-col :xs="24" :lg="6">
                <a-card size="small" title="修复参数" class="asset-card">
                  <a-input-number v-model:value="form.test_loop" :min="0" addon-before="修复轮次" style="width: 100%" />
                  <a-alert
                    type="info"
                    show-icon
                    message="test_loop 为 0 时只运行测试；大于 0 时基于失败用例反馈迭代修复。"
                    style="margin-top: 10px"
                  />
                </a-card>
              </a-col>
            </a-row>
          </div>

          <div class="stage-section action-section">
            <div class="section-title">操作</div>
            <a-space wrap>
              <a-button
                :disabled="!memoryInput.case_dir || !projectArtifacts.length || !selectedTestCaseArtifact"
                :loading="loading && runningStageRequest === 'ta'"
                @click="submitStageRun('ta', 'repair')"
              >
                运行测试
              </a-button>
              <a-button
                type="primary"
                :disabled="!memoryInput.case_dir || !projectArtifacts.length || !selectedTestCaseArtifact || Number(form.test_loop || 0) <= 0"
                :loading="loading && runningStageRequest === 'ta'"
                @click="submitStageRun('ta', 'repair')"
              >
                启动迭代修复
              </a-button>
            </a-space>
          </div>

          <div class="stage-section">
            <div class="section-title">输出</div>
            <a-row :gutter="12" class="metric-row">
              <a-col :xs="24" :md="6"><a-statistic title="测试通过率" :value="testPassRateLabel" /></a-col>
              <a-col :xs="24" :md="6"><a-statistic title="通过/总用例" :value="`${taMetrics.test_passed ?? 0}/${taMetrics.test_total ?? 0}`" /></a-col>
              <a-col :xs="24" :md="6"><a-statistic title="通过特性" :value="taMetrics.feature_passed ?? 0" /></a-col>
              <a-col :xs="24" :md="6"><a-statistic title="失败特性" :value="taMetrics.feature_failed ?? 0" /></a-col>
            </a-row>
            <a-table :data-source="taFeatureRows" :pagination="false" size="small" row-key="feature">
              <a-table-column title="测试特性" data-index="feature" key="feature" />
              <a-table-column title="状态" data-index="status" key="status" width="120" />
              <a-table-column title="通过用例" data-index="passed" key="passed" width="120" />
              <a-table-column title="总用例" data-index="total" key="total" width="120" />
              <a-table-column title="通过率" data-index="rate" key="rate" width="120" />
              <a-table-column title="摘要" data-index="summary" key="summary" />
            </a-table>
            <a-collapse :bordered="false" class="repair-output-collapse">
              <a-collapse-panel :header="`测试与修复产物（${repairArtifacts.length}）`" key="repair-artifacts">
                <artifact-table :items="repairArtifacts" :columns="artifactColumns" :run-id="runId" @preview="previewArtifact" />
              </a-collapse-panel>
              <a-collapse-panel header="关键日志" key="log-tail">
                <pre class="log-block">{{ logTailText }}</pre>
              </a-collapse-panel>
            </a-collapse>
          </div>
        </a-tab-pane>
      </a-tabs>
    </a-card>

    <a-card v-if="preview.title" :title="`预览：${preview.title}`" :bordered="false">
      <pre class="preview-light large">{{ preview.content }}</pre>
      <a-alert v-if="preview.truncated" type="warning" show-icon message="预览已截断，请下载完整文件" />
    </a-card>

    <a-modal
      v-model:open="isdArtifactEditor.open"
      :title="isdArtifactEditor.title"
      width="920px"
      :ok-text="isdArtifactEditor.editMode ? '保存' : '关闭'"
      :cancel-text="isdArtifactEditor.editMode ? '取消' : '关闭'"
      :confirm-loading="isdArtifactEditor.saving"
      @ok="saveIsdArtifact"
    >
      <a-alert
        v-if="artifactEditHint(isdArtifactEditor)"
        type="info"
        show-icon
        :message="artifactEditHint(isdArtifactEditor)"
        style="margin-bottom: 10px"
      />
      <a-textarea
        v-if="isdArtifactEditor.editMode"
        v-model:value="isdArtifactEditor.content"
        :rows="22"
        class="artifact-editor-textarea"
      />
      <pre v-else class="preview-light large">{{ isdArtifactEditor.content }}</pre>
    </a-modal>

    <a-modal
      v-model:open="artifactEditor.open"
      :title="artifactEditor.title"
      width="920px"
      ok-text="保存"
      cancel-text="取消"
      :confirm-loading="artifactEditor.saving"
      @ok="saveArtifactEdit"
    >
      <a-alert
        v-if="artifactEditor.hint"
        type="info"
        show-icon
        :message="artifactEditor.hint"
        style="margin-bottom: 10px"
      />
      <a-textarea
        v-model:value="artifactEditor.content"
        :rows="22"
        class="artifact-editor-textarea"
      />
    </a-modal>

    <a-modal
      v-model:open="ltmEditor.open"
      :title="ltmEditor.title"
      width="860px"
      ok-text="保存"
      cancel-text="取消"
      :confirm-loading="ltmEditor.saving"
      @ok="saveLtmEntry"
    >
      <a-form layout="vertical">
        <a-row :gutter="12">
          <a-col :xs="24" :md="24">
            <a-form-item label="技术栈">
              <a-select v-model:value="ltmEditor.profile_index" :options="ltmProfileOptions" :disabled="ltmEditor.editing" />
            </a-form-item>
          </a-col>
        </a-row>

        <template v-if="ltmEditor.category === 'architecture'">
          <a-row :gutter="12">
            <a-col :xs="24" :md="12">
              <a-form-item label="Package / Layer">
                <a-input v-model:value="ltmEditor.form.package" placeholder="例如 controller / service / mapper / entity / config" />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :md="12">
              <a-form-item>
                <template #label>
                  <span class="field-label-help">
                    Priority
                    <a-tooltip title="优先级用于控制同一技术栈下架构知识的读取和展示顺序。数值越小优先级越高，例如 0 通常表示配置/基础层，后续依次是实体、DAO/Repository、Service、Controller 等。">
                      <span class="help-dot">?</span>
                    </a-tooltip>
                  </span>
                </template>
                <a-input-number v-model:value="ltmEditor.form.priority" style="width: 100%" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-form-item label="Description">
            <a-textarea v-model:value="ltmEditor.form.description" :rows="5" placeholder="例如 service 层负责业务编排和事务边界，可依赖 mapper/entity/dto，不应直接处理 HTTP 请求或返回 Controller 专用响应对象。" />
          </a-form-item>
          <a-form-item label="Template">
            <a-textarea v-model:value="ltmEditor.form.template" :rows="8" placeholder="例如 package {base_package}.service;&#10;&#10;public interface {EntityName}Service {&#10;    {EntityName}DTO getById(Long id);&#10;    void create({EntityName}CreateRequest request);&#10;}" />
          </a-form-item>
        </template>

        <template v-else>
          <a-row :gutter="12">
            <a-col :xs="24" :md="8">
              <a-form-item>
                <template #label>
                  <span class="field-label-help">
                    Type
                    <a-tooltip title="Type 表示经验类型。pattern 适合架构/代码生成规范，pitfall 适合常见错误，fix 适合修复经验，constraint 适合必须遵守的约束。">
                      <span class="help-dot">?</span>
                    </a-tooltip>
                  </span>
                </template>
                <a-select v-model:value="ltmEditor.form.type" :options="ltmTypeOptions" />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :md="8">
              <a-form-item>
                <template #label>
                  <span class="field-label-help">
                    Scope
                    <a-tooltip title="Scope 表示这条经验生效的粒度。module 面向模块或分层，file 面向单个文件，class 面向类，function 面向方法/函数。">
                      <span class="help-dot">?</span>
                    </a-tooltip>
                  </span>
                </template>
                <a-select v-model:value="ltmEditor.form.scope" :options="ltmScopeOptions" />
              </a-form-item>
            </a-col>
            <a-col :xs="24" :md="8">
              <a-form-item label="Match Path">
                <a-input v-model:value="ltmEditor.form.path" placeholder="例如 backend/src/main/java/**/service/*.java" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-form-item label="Rule">
            <a-textarea v-model:value="ltmEditor.form.rule" :rows="7" placeholder="例如 Java Service 实现类必须通过构造器注入 Mapper；公共方法需要参数校验；数据库写操作使用 @Transactional；不要在 Service 中拼接 SQL。" />
          </a-form-item>
          <a-form-item label="Example">
            <a-textarea v-model:value="ltmEditor.form.example" :rows="8" placeholder="例如 @Service&#10;public class UserServiceImpl implements UserService {&#10;    private final UserMapper userMapper;&#10;&#10;    public UserServiceImpl(UserMapper userMapper) {&#10;        this.userMapper = userMapper;&#10;    }&#10;}" />
          </a-form-item>
        </template>
      </a-form>
    </a-modal>

    <div v-if="runId || modelingJobId" class="log-float">
      <div class="log-float-header">
        <span>{{ logFloatTitle }}</span>
        <a-space size="small">
          <a-button size="small" type="link" @click="refreshLogFloat">刷新日志</a-button>
          <a-button size="small" type="link" danger :disabled="!canStopRun" :loading="stopping" @click="terminateRun">终止任务</a-button>
          <a-button size="small" type="link" @click="logPanelCollapsed = !logPanelCollapsed">{{ logPanelCollapsed ? '展开' : '收起' }}</a-button>
        </a-space>
      </div>
      <pre v-if="!logPanelCollapsed" class="log-float-body">{{ logFloatText }}</pre>
    </div>
  </a-space>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, onMounted, reactive, ref, resolveComponent, watch } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { http } from '../api/http'

const ArtifactTable = defineComponent({
  name: 'ArtifactTable',
  props: {
    items: { type: Array, default: () => [] },
    columns: { type: Array, default: () => [] },
    runId: { type: String, default: '' },
    editable: { type: Boolean, default: false },
    downloadable: { type: Boolean, default: true },
    pagination: { type: [Boolean, Object], default: false },
  },
  emits: ['preview', 'edit'],
  setup(props, { emit }) {
    const ATable = resolveComponent('a-table')
    const ASpace = resolveComponent('a-space')
    const AButton = resolveComponent('a-button')
    const downloadUrl = (record) => `${http.defaults.baseURL}/api/project/runs/${props.runId}/artifacts/${record.artifact_id}/download`
    return () => h(
      ATable,
      {
        dataSource: props.items,
        columns: props.columns,
        pagination: props.pagination,
        size: 'small',
        rowKey: 'artifact_id',
      },
      {
        bodyCell: ({ column, record }) => {
          if (column.key !== 'actions') return null
          return h(ASpace, null, {
            default: () => [
              h(AButton, { size: 'small', onClick: () => emit('preview', record) }, { default: () => '查看' }),
              props.editable ? h(AButton, { size: 'small', type: 'link', onClick: () => emit('edit', record) }, { default: () => '编辑' }) : null,
              props.downloadable ? h('a', { href: downloadUrl(record), target: '_blank' }, '下载') : null,
            ],
          })
        },
      },
    )
  },
})

const route = useRoute()
const PROFILES_KEY = 'ccgmas_llm_profiles'
const ACTIVE_KEY = 'ccgmas_active_profile_id'

const loading = ref(false)
const runningStageRequest = ref('')
const stopping = ref(false)
const artifactsLoading = ref(false)
const inputGenerating = ref(false)
const architectureGenerating = ref(false)
const modelingJobId = ref('')
const modelingStatus = ref('idle')
const modelingLogs = ref([])
const modelingStartedAt = ref(0)
const modelingFinishedAt = ref(0)
const requirementsResult = ref(null)
const modelingNow = ref(Date.now())
const messageText = ref('')
const runId = ref('')
const runStatus = ref('idle')
const runStage = ref('queued')
const runProgress = ref(0)
const pathValidationError = ref('')
const realMetrics = ref({})
const outputs = ref([])
const logs = ref([])
const memory = ref([])
const copaCaseArtifacts = ref([])
const copaCaseArtifactsLoaded = ref(false)
const memoryCopaArtifacts = ref([])
const memoryArtifacts = ref([])
const caseProjectArtifacts = ref([])
const ltmData = reactive({ architecture: [], experience: [] })
const ltmStack = reactive({
  backend_profile_index: null,
  frontend_profile_index: null,
  applying: false,
  appliedCaseDir: '',
  appliedLabel: '',
})
const preview = ref({ title: '', content: '', truncated: false })
const artifactEditor = reactive({
  open: false,
  artifactId: '',
  source: 'run',
  caseDir: '',
  title: '',
  content: '',
  hint: '',
  saving: false,
})
const ltmEditor = reactive({
  open: false,
  title: '',
  category: 'architecture',
  profile_index: 0,
  entry_index: -1,
  editing: false,
  saving: false,
  form: {},
})
const lastRefreshAt = ref('')
const pendingHint = ref('')
const logTail = ref([])
const logPanelCollapsed = ref(false)
const activeKnoTab = ref('input')
let pollTimer = null
let modelingTimer = null
let stableTicks = 0
let lastProgressValue = -1

const datasetItems = ref([])
const caseLoading = ref(false)
const caseItems = ref([])
const casePreview = ref({
  title: '',
  dataset: '',
  caseName: '',
  content: '',
  files: {},
  fileOptions: [],
  activeFile: '',
  editing: false,
  editorContent: '',
  saving: false,
})
const memoryInput = reactive({
  case_dir: '',
  title: '',
  dataset: '',
  caseName: '',
})
const repairSelection = reactive({
  test_artifact_id: '',
})
const modelingOutputs = reactive({
  requirements: { output_dir: '', items: [], key_items: [] },
  architecture: { output_dir: '', items: [], key_items: [] },
})
const modelingCaseOutputs = reactive({
  requirements: { output_dir: '', items: [], key_items: [] },
  architecture: { output_dir: '', items: [], key_items: [] },
})
const modelingCase = reactive({
  case_dir: '',
  title: '',
  dataset: '',
  caseName: '',
  files: {},
  source: '',
})
const isdArtifactEditor = reactive({
  open: false,
  title: '',
  kind: '',
  output_dir: '',
  rel_path: '',
  mapsTo: '',
  content: '',
  editMode: false,
  saving: false,
  source: 'isd',
  dataset: '',
  caseName: '',
})

const inputGenerate = reactive({ case_name: '', description: '' })
const form = reactive({
  case_dir: '',
  test_loop: 0,
  ta_project_root: 'D:/projects/TestAgent',
  prefer_cache: true,
  cache_version: 'v1',
})

const modelProfiles = computed(() => {
  try {
    const arr = JSON.parse(localStorage.getItem(PROFILES_KEY) || '[]')
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
})
const runtimeProfile = ref(window.__RUNTIME_LLM_CONFIG__ || null)
const activeProfileId = computed(() => runtimeProfile.value?.id || localStorage.getItem(ACTIVE_KEY) || modelProfiles.value[0]?.id || '')
const activeProfile = computed(() => runtimeProfile.value || modelProfiles.value.find((p) => p.id === activeProfileId.value) || null)

const statusLabelMap = { idle: '空闲', accepted: '已提交', running: '运行中', finished: '已完成', failed: '执行失败', stopped: '已终止' }
const canStopRun = computed(() => !!runId.value && ['accepted', 'running'].includes(runStatus.value))
const logTailText = computed(() => (logTail.value || []).join('\n') || '暂无关键日志，任务启动后将在这里显示阶段进展')
const modelingStatusLabelMap = { idle: '空闲', accepted: '已提交', running: '运行中', finished: '已完成', failed: '执行失败' }
const modelingElapsedMs = computed(() => {
  if (!modelingStartedAt.value) return 0
  const end = modelingFinishedAt.value || modelingNow.value
  return Math.max(0, end - modelingStartedAt.value)
})
const modelingElapsedLabel = computed(() => formatDuration(modelingElapsedMs.value))
const logFloatTitle = computed(() => {
  if (modelingJobId.value && !runId.value) {
    return `需求建模 · ${modelingStatusLabelMap[modelingStatus.value] || modelingStatus.value} · ${modelingElapsedLabel.value}`
  }
  return `关键日志 · ${statusLabelMap[runStatus.value] || runStatus.value}`
})
const logFloatText = computed(() => {
  if (modelingJobId.value && !runId.value) {
    return (modelingLogs.value || []).join('\n') || '需求建模任务启动后将在这里显示阶段进展'
  }
  return logTailText.value
})

const artifactKind = (artifact) => String(artifact?.kind || '').toLowerCase()
const copaOutputSource = computed(() => copaCaseArtifactsLoaded.value ? copaCaseArtifacts.value : outputs.value)
const copaGrouped = computed(() => ({
  pdm: copaOutputSource.value.filter((x) => artifactKind(x) === 'pdm'),
  cip: copaOutputSource.value.filter((x) => artifactKind(x) === 'cip'),
  ps: copaOutputSource.value.filter((x) => artifactKind(x) === 'ps'),
}))
const caArtifacts = computed(() => outputs.value.filter((x) => ['zip', 'code'].includes(artifactKind(x))))
const runProjectArtifacts = computed(() => [...caArtifacts.value, ...copaGrouped.value.pdm])
const projectArtifacts = computed(() => caseProjectArtifacts.value.length ? caseProjectArtifacts.value : runProjectArtifacts.value)
const compileErrorCount = computed(() => metricValue(realMetrics.value?.compile_error_count))
const canRepairCompile = computed(() => !!runId.value && compileErrorCount.value > 0 && !loading.value)
const memoryGrouped = computed(() => ({
  ltm: memory.value.filter((x) => artifactKind(x) === 'ltm'),
  wm: memory.value.filter((x) => artifactKind(x) === 'wm'),
  ta: memory.value.filter((x) => artifactKind(x) === 'ta'),
}))
const memoryPageGrouped = computed(() => ({
  ltm: memoryArtifacts.value.filter((x) => artifactKind(x) === 'ltm'),
  wm: memoryArtifacts.value.filter((x) => artifactKind(x) === 'wm'),
}))
const ltmProfileOptions = computed(() => {
  const rows = ltmEditor.category === 'architecture' ? ltmData.architecture : ltmData.experience
  return rows.map((x) => ({ label: x.label, value: x.profile_index }))
})
const ltmBackendOptions = computed(() => (ltmData.architecture || [])
  .filter((x) => /java|python/i.test(`${x.label || ''} ${x.language || ''} ${x.version || ''}`))
  .map((x) => ({ label: x.label, value: x.profile_index })))
const ltmFrontendOptions = computed(() => (ltmData.architecture || [])
  .filter((x) => /vue/i.test(`${x.label || ''} ${x.language || ''} ${x.version || ''}`))
  .map((x) => ({ label: x.label, value: x.profile_index })))
const selectedBackendProfile = computed(() => ltmData.architecture.find((x) => x.profile_index === ltmStack.backend_profile_index) || null)
const selectedFrontendProfile = computed(() => ltmData.architecture.find((x) => x.profile_index === ltmStack.frontend_profile_index) || null)
const selectedBackendArchitectureRows = computed(() => selectedBackendProfile.value?.entries || [])
const selectedFrontendArchitectureRows = computed(() => selectedFrontendProfile.value?.entries || [])
const ltmStackLabel = computed(() => {
  const backend = selectedBackendProfile.value?.label || '未选择后端'
  const frontend = selectedFrontendProfile.value?.label || '未选择前端'
  return `${backend} + ${frontend}`
})
const canApplyLtmStack = computed(() => !!form.case_dir && ltmStack.backend_profile_index !== null && ltmStack.frontend_profile_index !== null)
const memoryCopaGrouped = computed(() => ({
  merged: memoryCopaArtifacts.value.filter((x) => x.scope === 'merged' || artifactKind(x) === 'cip_ps'),
  cipModules: memoryCopaArtifacts.value.filter((x) => artifactKind(x) === 'cip' && x.scope !== 'merged'),
  psModules: memoryCopaArtifacts.value.filter((x) => artifactKind(x) === 'ps' && x.scope !== 'merged'),
}))
const codegenPsArtifacts = computed(() => {
  const selectedCasePs = memoryCopaArtifacts.value.filter((x) => artifactKind(x) === 'ps')
  if (selectedCasePs.length) {
    return [
      ...selectedCasePs.filter((x) => x.scope === 'merged'),
      ...selectedCasePs.filter((x) => x.scope !== 'merged'),
    ]
  }
  return copaGrouped.value.ps
})
const validationArtifacts = computed(() => [...(logs.value || []), ...memoryGrouped.value.ta])
const testCaseArtifacts = computed(() => {
  const pattern = /(test|case|pytest|unittest|spec|coverage|测试|用例)/i
  const pool = [...(outputs.value || []), ...(logs.value || []), ...(memory.value || [])]
  return pool.filter((x) => pattern.test(`${x.name || ''} ${x.rel_path || ''} ${x.kind || ''}`))
})
const testCaseOptions = computed(() => testCaseArtifacts.value.map((item) => ({
  label: item.rel_path || item.name,
  value: item.artifact_id,
  title: item.rel_path || item.name,
})))
const selectedTestCaseArtifact = computed(() => {
  if (repairSelection.test_artifact_id) {
    return testCaseArtifacts.value.find((x) => x.artifact_id === repairSelection.test_artifact_id) || null
  }
  return testCaseArtifacts.value[0] || null
})
watch(testCaseArtifacts, (items) => {
  if (!items.length) {
    repairSelection.test_artifact_id = ''
    return
  }
  if (!items.some((x) => x.artifact_id === repairSelection.test_artifact_id)) {
    repairSelection.test_artifact_id = items[0].artifact_id
  }
})
const repairArtifacts = computed(() => [...(logs.value || []), ...memoryGrouped.value.ta])
const taMetrics = computed(() => realMetrics.value?.ta || {})
const taFeatureRows = computed(() => {
  const features = taMetrics.value.features || {}
  return Object.entries(features).map(([feature, row]) => {
    const total = Number(row.test_total || 0)
    const passed = Number(row.test_passed || 0)
    const rate = total > 0 ? `${Math.round((passed / total) * 100)}%` : (row.overall_pass_rate || '-')
    return {
      feature,
      status: row.passed ? '通过' : '未通过',
      passed,
      total,
      rate,
      summary: row.summary || '',
    }
  })
})
const testPassRateLabel = computed(() => {
  const total = Number(taMetrics.value.test_total || 0)
  const passed = Number(taMetrics.value.test_passed || 0)
  if (total > 0) return `${Math.round((passed / total) * 100)}%`
  const raw = realMetrics.value.test_pass_rate ?? realMetrics.value.test_pass ?? realMetrics.value.pass_rate
  if (raw == null || raw === '') return '-'
  const n = Number(raw)
  if (!Number.isFinite(n)) return String(raw)
  return n <= 1 ? `${Math.round(n * 100)}%` : `${n}%`
})
const modelingCaseItems = computed(() => Object.entries(modelingCase.files || {})
  .filter(([name]) => isUserVisibleModelingArtifact(name))
  .map(([name, content]) => caseFileArtifact(name, content)))
const modelingRequirementItems = computed(() => modelingCase.case_dir && modelingCase.source === 'case'
  ? sortModelingArtifacts(modelingCaseItems.value.filter((x) => x.kind === 'requirements'))
  : modelingCase.case_dir && modelingCase.source === 'isd'
    ? sortModelingArtifacts(modelingCaseOutputs.requirements.items)
  : sortModelingArtifacts(modelingOutputs.requirements.items))
const modelingArchitectureItems = computed(() => modelingCase.case_dir && modelingCase.source === 'case'
  ? sortModelingArtifacts(modelingCaseItems.value.filter((x) => x.kind === 'architecture'))
  : modelingCase.case_dir && modelingCase.source === 'isd'
    ? sortModelingArtifacts(modelingCaseOutputs.architecture.items)
  : sortModelingArtifacts(modelingOutputs.architecture.items))
const modelingRequirementsSourceLabel = computed(() => modelingCase.case_dir
  ? `${modelingCase.title} / ${modelingCase.source === 'case' ? '映射后需求产物' : 'Requirements Agent 全量产物'}`
  : (modelingOutputs.requirements.output_dir || '尚未生成需求产物'))
const modelingArchitectureSourceLabel = computed(() => modelingCase.case_dir
  ? `${modelingCase.title} / ${modelingCase.source === 'case' ? '映射后架构产物' : 'Architecture Agent 全量产物'}`
  : (modelingOutputs.architecture.output_dir || '尚未生成架构产物'))
const caseSelectOptions = computed(() => {
  const groups = new Map()
  for (const item of caseItems.value || []) {
    const path = normalizeCasePath(item)
    const dataset = item.dataset || path.replace(/\\/g, '/').split('/').slice(-2, -1)[0] || '未分类'
    const name = normalizeCaseName(item)
    if (!groups.has(dataset)) groups.set(dataset, [])
    groups.get(dataset).push({
      label: name,
      value: path,
      title: dataset ? `${dataset} / ${name}` : name,
    })
  }
  return [...groups.entries()]
    .sort(([a], [b]) => String(a).localeCompare(String(b)))
    .map(([dataset, options]) => ({
      label: dataset,
      options: options.sort((a, b) => String(a.label).localeCompare(String(b.label))),
    }))
})

const artifactColumns = [
  { title: '产物文件', dataIndex: 'name', key: 'name' },
  { title: '操作', key: 'actions', width: 140 },
]

const ltmArchitectureColumns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 140 },
  { title: 'Package', dataIndex: 'package', key: 'package', width: 120 },
  { title: 'Priority', dataIndex: 'priority', key: 'priority', width: 90 },
  { title: 'Description', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '操作', key: 'actions', width: 90 },
]

const ltmExperienceColumns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 170 },
  { title: 'Type', dataIndex: 'type', key: 'type', width: 100 },
  { title: 'Scope', dataIndex: 'scope', key: 'scope', width: 100 },
  { title: 'Match', key: 'match', width: 180 },
  { title: 'Rule', dataIndex: 'rule', key: 'rule', ellipsis: true },
  { title: '操作', key: 'actions', width: 90 },
]

const ltmTypeOptions = [
  { label: 'pattern - 可复用生成规范', value: 'pattern' },
  { label: 'pitfall - 常见错误或反例', value: 'pitfall' },
  { label: 'fix - 修复经验', value: 'fix' },
  { label: 'constraint - 必须遵守的约束', value: 'constraint' },
]

const ltmScopeOptions = [
  { label: 'module - 模块或分层级', value: 'module' },
  { label: 'file - 文件级', value: 'file' },
  { label: 'class - 类级', value: 'class' },
  { label: 'function - 方法或函数级', value: 'function' },
]

const isdArtifactColumns = [
  { title: '产物文件', dataIndex: 'rel_path', key: 'rel_path', ellipsis: true },
  { title: '用途说明', key: 'usage', width: 320 },
  { title: '大小', dataIndex: 'size', key: 'size', width: 90, customRender: ({ text }) => formatBytes(text) },
  { title: '操作', key: 'actions', width: 150 },
]
const simpleArtifactColumns = [
  { title: '输入产物', dataIndex: 'rel_path', key: 'rel_path', ellipsis: true },
  { title: '映射', dataIndex: 'maps_to', key: 'maps_to', width: 140 },
]

function formatBytes(value) {
  const n = Number(value || 0)
  if (n >= 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`
  if (n >= 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${n} B`
}

function metricValue(value) {
  const n = Number(value ?? 0)
  return Object.is(n, -0) || !Number.isFinite(n) ? 0 : n
}

function artifactUsage(record) {
  const name = String(record?.rel_path || record?.name || record?.maps_to || '').toLowerCase()
  if (/schema\.sql$|\/sql\/.*\.sql$/.test(name)) return 'PDM 数据库产物：由问题域模型生成的建表 SQL，展示表结构、字段、主键/外键和约束，可用于检查数据库设计。'
  if (/brd\.md$|businessrequirement|business_requirement/.test(name)) return '业务需求文档：汇总业务目标、范围和干系人诉求，可辅助校准用例与需求边界'
  if (/business_scope/.test(name)) return '业务范围说明：描述系统覆盖与不覆盖的业务边界，用于人工检查需求完整性'
  if (/business_requirements_chapter/.test(name)) return '业务需求章节：展开业务规则和业务目标，可作为 SRS 与 use case 的补充参考'
  if (/data_dictionary/.test(name)) return '数据字典：解释业务数据项、字段含义和取值约束，可辅助校准实体模型'
  if (/data_flow_diagram/.test(name)) return '数据流图：描述数据在角色、功能和存储之间的流转，可辅助检查组件交互'
  if (/dialog_map/.test(name)) return '对话/交互地图：记录用户交互路径和页面/功能衔接，可辅助补充用例流程'
  if (/draft_context_diagram/.test(name)) return '上下文草图：描述系统与外部角色或外部系统的关系，可辅助明确系统边界'
  if (/draft_event_list/.test(name)) return '事件清单：列出业务触发事件和系统响应，可辅助推导功能入口和异常流程'
  if (/feature_tree/.test(name)) return '功能树：按层次组织功能点，可辅助核对模块划分和用例覆盖范围'
  if (/functional_requirements/.test(name)) return '功能需求列表：列出系统应提供的功能能力，可辅助检查 COPA 输入是否遗漏'
  if (/non_functional_requirements/.test(name)) return '非功能需求：描述性能、安全、可用性等约束，可辅助后续代码生成约束'
  if (/survey\.md$/.test(name)) return '调研材料：记录需求调研或背景信息，主要用于人工追溯需求来源'
  if (/usage_scenario/.test(name)) return '使用场景：描述典型业务场景和用户操作路径，可辅助补充 use case'
  if (/user_introduction/.test(name)) return '用户说明：描述目标用户、角色特点和使用背景，可辅助校准参与者定义'
  if (/srs_planning/.test(name)) return 'SRS 规划过程：记录需求规格生成思路，主要用于追溯和人工检查'
  if (/use_case\.md$/.test(name)) return '关键输入：描述参与者、用例流程和约束，用于 COPA 理解业务需求'
  if (/entity_relationship_diagram\.md$|er_diagram|entity.*relationship/.test(name)) return '关键输入：描述实体、字段和关系，用于生成 PDM 数据模型'
  if (/srs\.md$|software_requirement|requirements?/.test(name)) return '需求规格：补充业务规则、非功能需求和边界条件，供 COPA 参考'
  if (/state_transition_diagram/.test(name)) return '状态转换图：描述核心对象状态和事件触发变化，可辅助检查业务流程完整性'
  if (/analysis_task_output/.test(name)) return '架构分析过程：记录架构 Agent 对需求的分析结果，可用于追溯设计来源'
  if (/class_design_structured\.json$|class_diagram|class_design_raw|类图/.test(name)) return '关键输入：描述类、属性、方法和职责，用于生成 CIP 类接口规划'
  if (/class_design_parser_output/.test(name)) return '类设计解析结果：记录类图结构化解析过程，可用于排查类图抽取是否正确'
  if (/component_design\.json$|component_diagram|组件/.test(name)) return '关键输入：描述组件职责和依赖，用于划分 CIP 模块与 PS 工程结构'
  if (/component_parser_output/.test(name)) return '组件解析结果：记录组件设计结构化解析过程，可用于排查组件抽取是否正确'
  if (/extractor_output/.test(name)) return '架构信息抽取结果：记录从需求中抽取出的架构线索，供人工检查设计依据'
  if (/modeling-1\.tech_stack/.test(name)) return '技术栈选择过程：记录架构 Agent 对技术栈的选择依据，当前系统以 LTM 配置为准'
  if (/modeling-2\.architectural_style/.test(name)) return '架构风格选择过程：记录分层、MVC 等架构风格判断，可辅助解释设计方案'
  if (/modeling-3\.static_design/.test(name)) return '静态设计输出：通常包含类图、包图等静态结构，是提取 package diagram 的重要来源'
  if (/modeling-4\.dynamic_design/.test(name)) return '动态设计输出：描述运行时交互、时序或流程，可辅助理解模块协作'
  if (/modeling-5\.deployment_design/.test(name)) return '部署设计输出：描述部署节点和运行环境，主要用于架构说明和人工检查'
  if (/modeling-6\.module_design/.test(name)) return '模块设计输出：描述模块职责和边界，可辅助校准 CIP/PS 模块划分'
  if (/package_diagram|package_design|包图/.test(name)) return '关键输入：描述包、目录和层次，用于生成 PS 项目结构规划'
  if (/tech_stack\.json$/.test(name)) return '内部配置：记录目标技术组合，由 LTM 配置阶段维护，运行时供 KnoMAS 读取'
  if (/report|log|summary|process|trace|output/.test(name)) return '过程产物：用于追溯生成过程和人工检查，不直接作为核心规划输入'
  if (record?.maps_to) return `KnoMAS 输入：映射为 ${record.maps_to}`
  if (record?.key) return 'iSoftDevAgent 生成产物：可作为需求或架构补充参考'
  return '辅助产物：可预览检查，必要时作为人工参考'
}

function modelingArtifactPriority(record) {
  const name = String(record?.rel_path || record?.name || record?.maps_to || '').toLowerCase()
  if (/use_case\.md$/.test(name)) return 10
  if (/entity_relationship_diagram\.md$|er_diagram|entity.*relationship/.test(name)) return 20
  if (/srs\.md$|software_requirement|requirements?/.test(name)) return 30
  if (/class_design_structured\.json$|class_diagram|class_design_raw|类图/.test(name)) return 40
  if (/component_design\.json$|component_diagram|组件/.test(name)) return 50
  if (/package_diagram|package_design|包图/.test(name)) return 60
  if (/tech_stack\.json$/.test(name)) return 70
  if (record?.maps_to) return 80
  if (record?.key) return 90
  return 1000
}

function sortModelingArtifacts(items = []) {
  return [...(items || [])].sort((a, b) => {
    const pa = modelingArtifactPriority(a)
    const pb = modelingArtifactPriority(b)
    if (pa !== pb) return pa - pb
    return String(a?.rel_path || a?.name || '').localeCompare(String(b?.rel_path || b?.name || ''))
  })
}

function isUserVisibleModelingArtifact(name) {
  return !/\.pkl$/i.test(String(name || ''))
}

function isVisibleCaseFile(name) {
  return String(name || '').toLowerCase() !== 'tech_stack.json'
}

function modelingKindForFile(name) {
  const raw = String(name || '').toLowerCase()
  if (/(use_case|requirement|srs|entity_relationship|er_diagram|domain|business|需求|用例)/i.test(raw)) return 'requirements'
  if (/(class|component|package|architecture|diagram|design|tech_stack|架构|类图|组件|包图)/i.test(raw)) return 'architecture'
  return 'requirements'
}

function mappedKnoMasFile(name) {
  const raw = String(name || '')
  const lower = raw.toLowerCase()
  if (/use_case\.md$/.test(lower)) return 'use_case.md'
  if (/entity_relationship_diagram\.md$|er_diagram|entity.*relationship/.test(lower)) return 'entity_relationship_diagram.md'
  if (/class_design_structured\.json$|class_diagram|class_design_raw/.test(lower)) return 'class_diagram.md'
  if (/component_design\.json$|component_diagram/.test(lower)) return 'component_diagram.md'
  if (/package_diagram/.test(lower)) return 'package_diagram.md'
  if (/tech_stack\.json$/.test(lower)) return 'tech_stack.json'
  return ''
}

function parseIsdReportDirs(text = '') {
  const result = { requirements: '', architecture: '' }
  const req = String(text).match(/requirements_output_dir:\s*([^\r\n]+)/i)
  const arch = String(text).match(/architecture_output_dir:\s*([^\r\n]+)/i)
  result.requirements = (req?.[1] || '').trim()
  result.architecture = (arch?.[1] || '').trim()
  if (result.requirements === '-') result.requirements = ''
  if (result.architecture === '-') result.architecture = ''
  return result
}

function caseFileArtifact(name, content) {
  return {
    rel_path: name,
    name,
    source: 'case',
    maps_to: mappedKnoMasFile(name),
    editable: true,
    size: new Blob([String(content || '')]).size,
    kind: modelingKindForFile(name),
  }
}

function artifactEditHint(record) {
  const name = String(record?.rel_path || record?.name || record?.mapsTo || record?.maps_to || '').toLowerCase()
  if (/use_case\.md$/.test(name)) {
    return '编辑提示：该文件是 COPA 的核心需求输入，请保留参与者、用例名称、主流程、异常流程、业务约束和可验证结果。'
  }
  if (/entity_relationship_diagram\.md$|er_diagram|entity.*relationship/.test(name)) {
    return '编辑提示：该文件用于生成 PDM，请明确实体、字段、主键/外键、关系基数和关键数据约束。'
  }
  if (/srs\.md$|software_requirement|requirements?/.test(name)) {
    return '编辑提示：该文件用于补充需求语义，请重点保留功能需求、非功能需求、边界条件和术语定义。'
  }
  if (/class_design_structured\.json$|class_diagram|class_design_raw|类图/.test(name)) {
    return '编辑提示：该文件会影响 CIP，请保证类名、职责、属性、方法签名和类之间关系稳定清晰。'
  }
  if (/component_design\.json$|component_diagram|组件/.test(name)) {
    return '编辑提示：该文件会影响模块划分，请明确每个组件的职责、输入输出和依赖方向。'
  }
  if (/package_diagram|package_design|包图/.test(name)) {
    return '编辑提示：该文件会影响 PS，请按目标语言和 LTM 技术组合描述包/目录层次、分层边界和依赖方向。'
  }
  if (/tech_stack\.json$/.test(name)) {
    return '编辑提示：该文件是 KnoMAS 内部技术配置，通常由 LTM 配置阶段自动维护；手动编辑时请保持合法 JSON，并保留 backend/frontend 的 language 与 version。'
  }
  if (record?.mapsTo || record?.maps_to) {
    return `编辑提示：该产物会映射为 KnoMAS 输入 ${record.mapsTo || record.maps_to}，请保证内容结构完整、术语一致。`
  }
  return ''
}

function ensureDefaultLtmStackSelection() {
  if (ltmStack.backend_profile_index === null && ltmBackendOptions.value.length) {
    ltmStack.backend_profile_index = ltmBackendOptions.value[0].value
  }
  if (ltmStack.frontend_profile_index === null && ltmFrontendOptions.value.length) {
    ltmStack.frontend_profile_index = ltmFrontendOptions.value[0].value
  }
}

function normalizeCasePath(x) {
  return x.case_dir || x.rel_path || x.path || (x.dataset && x.case_name ? `data/cases/${x.dataset}/${x.case_name}` : '')
}

function normalizeCaseName(x) {
  return x.case_name || x.name || (String(normalizeCasePath(x)).split('/').pop() || '')
}

async function loadDatasets() {
  const { data } = await http.get('/api/datasets/knomas/info')
  datasetItems.value = data?.datasets || []
}

async function loadCases() {
  caseLoading.value = true
  try {
    const { data } = await http.get('/api/datasets/knomas/cases', { params: { limit: 5000 } })
    caseItems.value = data?.items || []
  } finally {
    caseLoading.value = false
  }
}

function onPreviewFileChange(fileName) {
  if (!fileName) return
  casePreview.value.editing = false
  casePreview.value.editorContent = ''
  const content = String(casePreview.value.files?.[fileName] || '')
  casePreview.value.content = content ? `# ${fileName}\n\n${content.slice(0, 5000)}` : `# ${fileName}\n\n(文件为空)`
}

function startCaseFileEdit() {
  const fileName = casePreview.value.activeFile
  if (!fileName) return
  casePreview.value.editorContent = String(casePreview.value.files?.[fileName] || '')
  casePreview.value.editing = true
}

function cancelCaseFileEdit() {
  casePreview.value.editing = false
  casePreview.value.editorContent = ''
  onPreviewFileChange(casePreview.value.activeFile)
}

async function saveCaseFileEdit() {
  const fileName = casePreview.value.activeFile
  const dataset = casePreview.value.dataset
  const caseName = casePreview.value.caseName
  if (!dataset || !caseName || !fileName) return
  casePreview.value.saving = true
  try {
    const files = {
      ...(casePreview.value.files || {}),
      [fileName]: casePreview.value.editorContent,
    }
    await http.put(`/api/datasets/knomas/cases/${dataset}/${caseName}`, { files })
    casePreview.value.files = files
    casePreview.value.editing = false
    casePreview.value.editorContent = ''
    onPreviewFileChange(fileName)
    message.success('COPA 输入文件已保存')
  } finally {
    casePreview.value.saving = false
  }
}

async function onCaseChange(path) {
  const item = caseItems.value.find((x) => normalizeCasePath(x) === path)
  if (!item) return
  const dataset = item.dataset || normalizeCaseName(item)
  const caseName = normalizeCaseName(item)
  try {
    const { data } = await http.get(`/api/datasets/knomas/cases/${dataset}/${caseName}`)
    const files = data?.files || {}
    const names = Object.keys(files).filter(isVisibleCaseFile)
    const first = names.includes('isoftdev_generation_report.md') ? 'isoftdev_generation_report.md' : names[0] || ''
    casePreview.value = {
      title: `${dataset}/${caseName}`,
      dataset,
      caseName,
      files,
      fileOptions: names.map((n) => ({ label: n, value: n })),
      activeFile: first,
      content: '',
      editing: false,
      editorContent: '',
      saving: false,
    }
    onPreviewFileChange(first)
    await loadCurrentLtmStack(path)
    await loadCaseCopaArtifacts(path)
  } catch {
    casePreview.value = {
      title: `${dataset}/${caseName}`,
      dataset,
      caseName,
      content: '预览失败',
      files: {},
      fileOptions: [],
      activeFile: '',
      editing: false,
      editorContent: '',
      saving: false,
    }
    copaCaseArtifacts.value = []
    copaCaseArtifactsLoaded.value = false
  }
}

async function loadCaseCopaArtifacts(path = form.case_dir) {
  if (!path) {
    copaCaseArtifacts.value = []
    copaCaseArtifactsLoaded.value = false
    return
  }
  try {
    const { data } = await http.get('/api/project/copa-artifacts', {
      params: { case_dir: path },
    })
    copaCaseArtifacts.value = data?.items || []
    copaCaseArtifactsLoaded.value = true
  } catch {
    copaCaseArtifacts.value = []
    copaCaseArtifactsLoaded.value = false
  }
}

async function loadModelingCaseArtifacts(path) {
  if (!path) {
    modelingCase.case_dir = ''
    modelingCase.title = ''
    modelingCase.dataset = ''
    modelingCase.caseName = ''
    modelingCase.files = {}
    modelingCase.source = ''
    modelingCaseOutputs.requirements = { output_dir: '', items: [], key_items: [] }
    modelingCaseOutputs.architecture = { output_dir: '', items: [], key_items: [] }
    return
  }
  const item = caseItems.value.find((x) => normalizeCasePath(x) === path)
  if (!item) return
  const dataset = item.dataset || normalizeCaseName(item)
  const caseName = normalizeCaseName(item)
  try {
    const { data } = await http.get(`/api/datasets/knomas/cases/${dataset}/${caseName}`)
    modelingCase.case_dir = path
    modelingCase.title = `${dataset}/${caseName}`
    modelingCase.dataset = dataset
    modelingCase.caseName = caseName
    modelingCase.files = data?.files || {}
    const report = modelingCase.files?.['isoftdev_generation_report.md'] || ''
    const dirs = parseIsdReportDirs(report)
    if (dirs.requirements || dirs.architecture) {
      modelingCase.source = 'isd'
      if (dirs.requirements) {
        await loadIsdArtifacts('requirements', dirs.requirements, modelingCaseOutputs)
      } else {
        modelingCaseOutputs.requirements = { output_dir: '', items: [], key_items: [] }
      }
      if (dirs.architecture) {
        await loadIsdArtifacts('architecture', dirs.architecture, modelingCaseOutputs)
      } else {
        modelingCaseOutputs.architecture = { output_dir: '', items: [], key_items: [] }
      }
    } else {
      modelingCase.source = 'case'
    }
  } catch {
    modelingCase.case_dir = path
    modelingCase.title = `${dataset}/${caseName}`
    modelingCase.dataset = dataset
    modelingCase.caseName = caseName
    modelingCase.files = {}
    modelingCase.source = 'case'
    message.error('已有案例产物读取失败')
  }
}

async function onMemoryCaseChange(path) {
  const item = caseItems.value.find((x) => normalizeCasePath(x) === path)
  if (!item) return
  const dataset = item.dataset || normalizeCaseName(item)
  const caseName = normalizeCaseName(item)
  form.case_dir = path
  try {
    await http.get(`/api/datasets/knomas/cases/${dataset}/${caseName}`)
    const { data: copaData } = await http.get('/api/project/copa-artifacts', {
      params: { case_dir: path },
    })
    const { data: projectData } = await http.get('/api/project/code-artifacts', {
      params: { case_dir: path },
    })
    memoryInput.title = `${dataset}/${caseName}`
    memoryInput.dataset = dataset
    memoryInput.caseName = caseName
    memoryCopaArtifacts.value = copaData?.items || []
    caseProjectArtifacts.value = projectData?.items || []
    await loadMemoryArtifacts(path)
  } catch {
    memoryInput.title = `${dataset}/${caseName}`
    memoryInput.dataset = dataset
    memoryInput.caseName = caseName
    memoryCopaArtifacts.value = []
    caseProjectArtifacts.value = []
    await loadMemoryArtifacts('')
    message.error('Memory 输入案例读取失败')
  }
}

async function loadMemoryArtifacts(caseDir = memoryInput.case_dir || '') {
  const [{ data }, { data: ltm }] = await Promise.all([
    http.get('/api/project/memory-artifacts', { params: { case_dir: caseDir } }),
    http.get('/api/project/ltm'),
  ])
  memoryArtifacts.value = data?.items || []
  ltmData.architecture = ltm?.architecture || []
  ltmData.experience = ltm?.experience || []
  ensureDefaultLtmStackSelection()
}

async function applyLtmStackToCase(options = {}) {
  const silent = !!options.silent
  if (!canApplyLtmStack.value) {
    if (!silent) message.warning('请先选择案例和 LTM Profile 组合')
    return false
  }
  if (silent && ltmStack.appliedCaseDir === form.case_dir && ltmStack.appliedLabel === ltmStackLabel.value) {
    return true
  }
  ltmStack.applying = true
  try {
    await http.post('/api/project/ltm-stack/apply', {
      case_dir: form.case_dir,
      backend_profile_index: ltmStack.backend_profile_index,
      frontend_profile_index: ltmStack.frontend_profile_index,
    })
    ltmStack.appliedCaseDir = form.case_dir
    ltmStack.appliedLabel = ltmStackLabel.value
    if (!silent) message.success('LTM Profile 组合已应用到当前案例')
    return true
  } finally {
    ltmStack.applying = false
  }
}

async function loadCurrentLtmStack(path) {
  if (!path) return
  try {
    const { data } = await http.get('/api/project/ltm-stack/current', {
      params: { case_dir: path },
    })
    if (data?.backend_profile_index !== null && data?.backend_profile_index !== undefined) {
      ltmStack.backend_profile_index = data.backend_profile_index
    }
    if (data?.frontend_profile_index !== null && data?.frontend_profile_index !== undefined) {
      ltmStack.frontend_profile_index = data.frontend_profile_index
    }
    if (data?.backend_profile_index !== null && data?.frontend_profile_index !== null) {
      ltmStack.appliedCaseDir = path
      ltmStack.appliedLabel = ltmStackLabel.value
    }
  } catch {
    ensureDefaultLtmStackSelection()
  }
}

async function buildWorkingMemory() {
  if (!memoryInput.case_dir) {
    message.warning('请先选择 Working Memory 输入案例')
    return
  }
  const { data } = await http.post('/api/project/memory/build', {
    case_dir: memoryInput.case_dir,
  })
  memoryArtifacts.value = data?.items || []
  await onMemoryCaseChange(memoryInput.case_dir)
  message.success('Working Memory 已构建')
}

async function loadIsdArtifacts(kind, outputDir, target = modelingOutputs) {
  if (!outputDir) return
  const { data } = await http.get('/api/datasets/knomas/isoftdev/artifacts', {
    params: { kind, output_dir: outputDir },
  })
  target[kind].output_dir = data.output_dir || outputDir
  const resolvedOutputDir = data.output_dir || outputDir
  target[kind].items = (data.items || [])
    .filter((x) => isUserVisibleModelingArtifact(x.rel_path || x.name))
    .map((x) => ({ ...x, source: 'isd', output_dir: resolvedOutputDir }))
  target[kind].key_items = (data.key_items || [])
    .filter((x) => isUserVisibleModelingArtifact(x.rel_path || x.name))
    .map((x) => ({ ...x, source: 'isd', output_dir: resolvedOutputDir }))
}

async function openIsdArtifact(kind, record, editMode = false) {
  const outputDir = record?.output_dir || modelingOutputs[kind]?.output_dir
  if (!outputDir || !record?.rel_path) return
  const { data } = await http.get('/api/datasets/knomas/isoftdev/artifacts/content', {
    params: { kind, output_dir: outputDir, rel_path: record.rel_path },
  })
  isdArtifactEditor.open = true
  isdArtifactEditor.title = `${kind === 'requirements' ? '需求产物' : '架构产物'} / ${record.rel_path}`
  isdArtifactEditor.kind = kind
  isdArtifactEditor.output_dir = outputDir
  isdArtifactEditor.rel_path = record.rel_path
  isdArtifactEditor.mapsTo = record.maps_to || ''
  isdArtifactEditor.content = data.content || ''
  isdArtifactEditor.editMode = editMode && !!record.editable
  isdArtifactEditor.source = 'isd'
  isdArtifactEditor.dataset = ''
  isdArtifactEditor.caseName = ''
}

function openModelingCaseArtifact(kind, record, editMode = false) {
  if (!record?.rel_path || !modelingCase.dataset || !modelingCase.caseName) return
  isdArtifactEditor.open = true
  isdArtifactEditor.title = `${kind === 'requirements' ? '需求产物' : '架构产物'} / ${record.rel_path}`
  isdArtifactEditor.kind = kind
  isdArtifactEditor.output_dir = ''
  isdArtifactEditor.rel_path = record.rel_path
  isdArtifactEditor.mapsTo = record.maps_to || record.rel_path || ''
  isdArtifactEditor.content = String(modelingCase.files?.[record.rel_path] || '')
  isdArtifactEditor.editMode = !!editMode
  isdArtifactEditor.source = 'case'
  isdArtifactEditor.dataset = modelingCase.dataset
  isdArtifactEditor.caseName = modelingCase.caseName
}

function openModelingArtifact(kind, record, editMode = false) {
  if (record?.source === 'case') {
    openModelingCaseArtifact(kind, record, editMode)
    return
  }
  openIsdArtifact(kind, record, editMode)
}

async function saveIsdArtifact() {
  if (!isdArtifactEditor.editMode) {
    isdArtifactEditor.open = false
    return
  }
  isdArtifactEditor.saving = true
  try {
    if (isdArtifactEditor.source === 'case') {
      const files = {
        ...(modelingCase.files || {}),
        [isdArtifactEditor.rel_path]: isdArtifactEditor.content,
      }
      await http.put(`/api/datasets/knomas/cases/${isdArtifactEditor.dataset}/${isdArtifactEditor.caseName}`, { files })
      modelingCase.files = files
    } else {
      await http.put('/api/datasets/knomas/isoftdev/artifacts/content', {
        kind: isdArtifactEditor.kind,
        output_dir: isdArtifactEditor.output_dir,
        rel_path: isdArtifactEditor.rel_path,
        content: isdArtifactEditor.content,
      })
      const target = modelingCase.source === 'isd' && modelingCase.case_dir ? modelingCaseOutputs : modelingOutputs
      await loadIsdArtifacts(isdArtifactEditor.kind, isdArtifactEditor.output_dir, target)
    }
    isdArtifactEditor.open = false
    message.success('产物已保存')
  } finally {
    isdArtifactEditor.saving = false
  }
}

function submitTestCaseGeneration() {
  if (!memoryInput.case_dir) {
    message.warning('请先选择测试输入案例')
    return
  }
  if (!projectArtifacts.value.length) {
    message.warning('当前案例暂无项目代码产物，请先完成代码生成')
    return
  }
  submitStageRun('testgen')
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function formatDuration(ms) {
  const total = Math.floor(Number(ms || 0) / 1000)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  const pad = (n) => String(n).padStart(2, '0')
  return hours > 0 ? `${pad(hours)}:${pad(minutes)}:${pad(seconds)}` : `${pad(minutes)}:${pad(seconds)}`
}

function startModelingTimer() {
  stopModelingTimer()
  modelingStartedAt.value = Date.now()
  modelingFinishedAt.value = 0
  modelingNow.value = Date.now()
  modelingTimer = setInterval(() => {
    modelingNow.value = Date.now()
  }, 1000)
}

function stopModelingTimer() {
  if (modelingTimer) {
    clearInterval(modelingTimer)
    modelingTimer = null
  }
  if (modelingStartedAt.value && !modelingFinishedAt.value) {
    modelingFinishedAt.value = Date.now()
    modelingNow.value = modelingFinishedAt.value
  }
}

async function fetchModelingJobStatus() {
  if (!modelingJobId.value) return null
  const { data } = await http.get(`/api/datasets/knomas/cases/from-input/jobs/${modelingJobId.value}`)
  modelingStatus.value = data.status || modelingStatus.value
  modelingLogs.value = data.logs || []
  return data
}

async function refreshLogFloat() {
  if (modelingJobId.value && !runId.value) {
    await fetchModelingJobStatus()
    return
  }
  await fetchLogTail()
}

async function pollModelingJob(jobId, failureMessage) {
  let data = null
  while (jobId && modelingJobId.value === jobId) {
    const { data: status } = await http.get(`/api/datasets/knomas/cases/from-input/jobs/${jobId}`)
    modelingStatus.value = status.status || 'running'
    modelingLogs.value = status.logs || []
    if (status.status === 'finished') {
      data = status.result || {}
      stopModelingTimer()
      break
    }
    if (status.status === 'failed') {
      stopModelingTimer()
      throw new Error(status.error || failureMessage)
    }
    await sleep(2000)
  }
  return data
}

async function generateRequirements() {
  if (!inputGenerate.case_name.trim()) return message.warning('请填写案例标识')
  if (!inputGenerate.description.trim()) return message.warning('请填写业务需求说明')
  inputGenerating.value = true
  requirementsResult.value = null
  modelingJobId.value = ''
  modelingStatus.value = 'accepted'
  modelingLogs.value = ['需求规格生成任务正在提交...']
  logPanelCollapsed.value = false
  startModelingTimer()
  try {
    const { data: job } = await http.post('/api/datasets/knomas/cases/from-input/requirements/jobs', {
      ...inputGenerate,
      project_name: inputGenerate.case_name,
    })
    modelingJobId.value = job.job_id
    const data = await pollModelingJob(job.job_id, '需求规格生成失败')
    requirementsResult.value = data
    if (data?.requirements_output_dir) {
      await loadIsdArtifacts('requirements', data.requirements_output_dir)
    }
    message.success(`需求规格已生成，耗时 ${modelingElapsedLabel.value}，可以继续生成架构设计`)
  } catch (err) {
    stopModelingTimer()
    throw err
  } finally {
    inputGenerating.value = false
  }
}

async function generateArchitecture() {
  const req = requirementsResult.value
  if (!req?.requirements_output_dir) return message.warning('请先完成需求规格生成')
  architectureGenerating.value = true
  modelingJobId.value = ''
  modelingStatus.value = 'accepted'
  modelingLogs.value = ['架构设计生成任务正在提交...']
  logPanelCollapsed.value = false
  startModelingTimer()
  try {
    const { data: job } = await http.post('/api/datasets/knomas/cases/from-input/architecture/jobs', {
      ...inputGenerate,
      project_name: req.project_name || inputGenerate.case_name,
      case_name: req.case_name || inputGenerate.case_name,
      description: req.description || inputGenerate.description,
      input_file: req.input_file,
      requirements_output_dir: req.requirements_output_dir,
    })
    modelingJobId.value = job.job_id
    const data = await pollModelingJob(job.job_id, '架构设计生成失败')
    if (data?.requirements_output_dir) {
      await loadIsdArtifacts('requirements', data.requirements_output_dir)
    }
    if (data?.architecture_output_dir) {
      await loadIsdArtifacts('architecture', data.architecture_output_dir)
    }
    await loadDatasets()
    await loadCases()
    const targetDataset = data.dataset || 'generated'
    const targetName = data.case_name || inputGenerate.case_name
    const targetCaseDir = data.case_dir || `data/cases/${targetDataset}/${targetName}`
    const created = caseItems.value.find((x) => normalizeCasePath(x) === targetCaseDir)
      || caseItems.value.find((x) => x.dataset === targetDataset && normalizeCaseName(x) === targetName)
      || caseItems.value.find((x) => normalizeCaseName(x) === targetName)
    if (created) {
      form.case_dir = normalizeCasePath(created)
      await onCaseChange(form.case_dir)
    }
    activeKnoTab.value = 'ltm'
    message.success(`架构设计已生成，耗时 ${modelingElapsedLabel.value}，已进入 LTM 配置`)
  } catch (err) {
    stopModelingTimer()
    throw err
  } finally {
    architectureGenerating.value = false
  }
}

async function generateFromInput() {
  await generateRequirements()
  await generateArchitecture()
}

function resetRunView() {
  runId.value = ''
  runStatus.value = 'idle'
  runStage.value = 'queued'
  runProgress.value = 0
  pathValidationError.value = ''
  realMetrics.value = {}
  outputs.value = []
  logs.value = []
  memory.value = []
  copaCaseArtifacts.value = []
  copaCaseArtifactsLoaded.value = false
  caseProjectArtifacts.value = []
  preview.value = { title: '', content: '', truncated: false }
  pendingHint.value = ''
  logTail.value = []
  stableTicks = 0
  lastProgressValue = -1
}

async function submitStageRun(stageName = 'planning', nextTab = '') {
  if (!form.case_dir) return message.warning('请先完成需求建模，或从数据集管理进入已有案例')
  loading.value = true
  runningStageRequest.value = stageName
  try {
    if (stageName === 'planning') {
      ensureDefaultLtmStackSelection()
      await applyLtmStackToCase({ silent: true })
    }
    resetRunView()
    const profile = activeProfile.value
    const payload = {
      run_type: 'knomas',
      run_stage: stageName,
      case_dir: form.case_dir,
      test_loop: form.test_loop,
      ta_project_root: form.ta_project_root,
      model_profile: activeProfileId.value,
      model_name: profile?.model || '',
      model_base_url: profile?.base_url || '',
      model_api_key: profile?.api_key || '',
      prefer_cache: !!form.prefer_cache,
      cache_version: form.cache_version || 'v1',
    }
    const { data } = await http.post('/api/project/run', payload)
    const stageLabel = { planning: 'COPA 规划', codegen: '代码生成', testgen: '测试用例生成', ta: 'TA 修复' }[stageName] || 'KnoMAS'
    messageText.value = `${stageLabel} 任务已提交`
    runId.value = data.run_id
    if (nextTab) activeKnoTab.value = nextTab
    await refreshAll()
    startPolling()
  } finally {
    loading.value = false
    runningStageRequest.value = ''
  }
}

async function submitCompileRepair() {
  if (!canRepairCompile.value) return
  message.info('将基于当前编译反馈继续执行修复流程')
  await submitStageRun('codegen')
}

async function refreshAll() {
  if (!runId.value) return
  artifactsLoading.value = true
  try {
    const [st, ar] = await Promise.all([
      http.get(`/api/project/runs/${runId.value}/status`),
      http.get(`/api/project/runs/${runId.value}/artifacts`),
    ])
    const data = st.data
    runStatus.value = data.status
    runStage.value = data.stage
    runProgress.value = data.progress
    pathValidationError.value = data?.metrics?.path_validation_error || ''
    realMetrics.value = data?.metrics || {}
    outputs.value = ar.data?.outputs || []
    logs.value = ar.data?.logs || []
    memory.value = ar.data?.memory || []
    await fetchLogTail()
    lastRefreshAt.value = new Date().toLocaleTimeString()

    if (runProgress.value === lastProgressValue) stableTicks += 1
    else {
      stableTicks = 0
      lastProgressValue = runProgress.value
    }
    pendingHint.value = ['accepted', 'running'].includes(runStatus.value) && stableTicks >= 2 ? '任务仍在后台运行，请稍候' : ''
    if (['finished', 'failed', 'stopped'].includes(runStatus.value)) stopPolling()
  } finally {
    artifactsLoading.value = false
  }
}

async function terminateRun() {
  if (!canStopRun.value) return
  stopping.value = true
  try {
    const { data } = await http.post(`/api/project/runs/${runId.value}/stop`)
    messageText.value = data?.message || '任务已终止'
    await refreshAll()
    stopPolling()
  } finally {
    stopping.value = false
  }
}

async function fetchLogTail() {
  if (!runId.value) return
  try {
    const { data } = await http.get(`/api/project/runs/${runId.value}/logs/tail`, { params: { limit: 100 } })
    logTail.value = data?.lines || []
  } catch {
    logTail.value = []
  }
}

async function previewArtifact(record) {
  if (!runId.value || !record?.artifact_id) return
  const { data } = await http.get(`/api/project/runs/${runId.value}/artifacts/${record.artifact_id}/preview`)
  preview.value = { title: record.name, content: data.preview, truncated: data.truncated }
}

async function previewCopaArtifact(record) {
  if (form.case_dir && copaCaseArtifacts.value.some((x) => x.artifact_id === record?.artifact_id)) {
    const { data } = await http.get(`/api/project/copa-artifacts/${record.artifact_id}/preview`, {
      params: { case_dir: form.case_dir },
    })
    preview.value = { title: record.name, content: data.preview, truncated: data.truncated }
    return
  }
  await previewArtifact(record)
}

async function previewMemoryCopaArtifact(record) {
  if (!memoryInput.case_dir || !record?.artifact_id) return
  const { data } = await http.get(`/api/project/copa-artifacts/${record.artifact_id}/preview`, {
    params: { case_dir: memoryInput.case_dir },
  })
  preview.value = { title: record.name, content: data.preview, truncated: data.truncated }
}

async function previewCodegenPsArtifact(record) {
  if (memoryInput.case_dir && memoryCopaArtifacts.value.some((x) => x.artifact_id === record?.artifact_id)) {
    await previewMemoryCopaArtifact(record)
    return
  }
  await previewArtifact(record)
}

async function previewProjectArtifact(record) {
  if (memoryInput.case_dir && caseProjectArtifacts.value.some((x) => x.artifact_id === record?.artifact_id)) {
    const { data } = await http.get(`/api/project/code-artifacts/${record.artifact_id}/preview`, {
      params: { case_dir: memoryInput.case_dir },
    })
    preview.value = { title: record.name, content: data.preview, truncated: data.truncated }
    return
  }
  await previewArtifact(record)
}

async function previewMemoryArtifact(record) {
  if (!record?.artifact_id) return
  const { data } = await http.get(`/api/project/memory-artifacts/${record.artifact_id}/preview`, {
    params: { case_dir: memoryInput.case_dir || '' },
  })
  preview.value = { title: record.name, content: data.preview, truncated: data.truncated }
}

async function editArtifact(record, hint = '') {
  if (!runId.value || !record?.artifact_id) return
  const { data } = await http.get(`/api/project/runs/${runId.value}/artifacts/${record.artifact_id}/preview`)
  artifactEditor.open = true
  artifactEditor.artifactId = record.artifact_id
  artifactEditor.source = 'run'
  artifactEditor.caseDir = ''
  artifactEditor.title = `编辑：${record.name}`
  artifactEditor.content = data.preview || ''
  artifactEditor.hint = hint || (data.truncated ? '当前内容为截断预览，请下载完整文件后谨慎编辑。' : '')
}

async function editMemoryArtifact(record, hint = '') {
  if (!record?.artifact_id) return
  const { data } = await http.get(`/api/project/memory-artifacts/${record.artifact_id}/preview`, {
    params: { case_dir: memoryInput.case_dir || '' },
  })
  artifactEditor.open = true
  artifactEditor.artifactId = record.artifact_id
  artifactEditor.source = 'memory'
  artifactEditor.caseDir = memoryInput.case_dir || ''
  artifactEditor.title = `编辑：${record.name}`
  artifactEditor.content = data.preview || ''
  artifactEditor.hint = hint || (data.truncated ? '当前内容为截断预览，请下载完整文件后谨慎编辑。' : '')
}

async function saveArtifactEdit() {
  if (!artifactEditor.artifactId) return
  if (artifactEditor.source !== 'memory' && !runId.value) return
  artifactEditor.saving = true
  try {
    if (artifactEditor.source === 'memory') {
      await http.put(`/api/project/memory-artifacts/${artifactEditor.artifactId}/content`, {
        case_dir: artifactEditor.caseDir,
        content: artifactEditor.content,
      })
      await loadMemoryArtifacts(artifactEditor.caseDir)
    } else {
      await http.put(`/api/project/runs/${runId.value}/artifacts/${artifactEditor.artifactId}/content`, {
        content: artifactEditor.content,
      })
      await refreshAll()
    }
    artifactEditor.open = false
    message.success('产物已保存')
  } finally {
    artifactEditor.saving = false
  }
}

function addLongTermMemory() {
  openLtmEditor('architecture')
}

function openLtmEditor(category, record = null) {
  ltmEditor.category = category
  ltmEditor.editing = !!record
  ltmEditor.entry_index = record?._entry_index ?? -1
  ltmEditor.profile_index = record?._profile_index ?? ((category === 'architecture' ? ltmData.architecture[0]?.profile_index : ltmData.experience[0]?.profile_index) ?? 0)
  ltmEditor.title = `${record ? '编辑' : '新增'} ${category === 'architecture' ? 'Architecture Knowledge' : 'Code Generation Experience'}`
  if (category === 'architecture') {
    ltmEditor.form = {
      id: record?.id || '',
      package: record?.package || '',
      priority: record?.priority ?? 0,
      description: record?.description || '',
      template: record?.template || '',
    }
  } else {
    ltmEditor.form = {
      id: record?.id || '',
      type: record?.type || 'pattern',
      scope: record?.scope || 'module',
      path: Array.isArray(record?.match?.path) ? record.match.path.join(', ') : (record?.match?.path || ''),
      rule: record?.rule || '',
      example: record?.example || '',
    }
  }
  ltmEditor.open = true
}

async function saveLtmEntry() {
  ltmEditor.saving = true
  try {
    const entry = { ...ltmEditor.form }
    if (!ltmEditor.editing) {
      delete entry.id
    }
    const payload = {
      category: ltmEditor.category,
      profile_index: ltmEditor.profile_index,
      entry_index: ltmEditor.entry_index,
      entry,
    }
    const url = '/api/project/ltm/entries'
    if (ltmEditor.editing) {
      await http.put(url, payload)
    } else {
      await http.post(url, payload)
    }
    ltmEditor.open = false
    await loadMemoryArtifacts(memoryInput.case_dir || '')
    message.success('Long-term Memory 已保存')
  } finally {
    ltmEditor.saving = false
  }
}

async function enterMemoryTab() {
  activeKnoTab.value = 'wm'
  if (form.case_dir && memoryInput.case_dir !== form.case_dir) {
    memoryInput.case_dir = form.case_dir
    await onMemoryCaseChange(form.case_dir)
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    refreshAll()
  }, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function syncRuntimeProfile(event) {
  runtimeProfile.value = event?.detail || window.__RUNTIME_LLM_CONFIG__ || null
}

onMounted(async () => {
  syncRuntimeProfile()
  window.addEventListener('runtime-llm-profile-changed', syncRuntimeProfile)
  const queryCaseDir = typeof route.query.case_dir === 'string' ? route.query.case_dir : ''
  const queryTab = typeof route.query.tab === 'string' ? route.query.tab : ''
  await loadDatasets()
  await loadCases()
  await loadMemoryArtifacts('')
  if (queryCaseDir) form.case_dir = queryCaseDir
  if (form.case_dir) await onCaseChange(form.case_dir)
  if (form.case_dir) {
    memoryInput.case_dir = form.case_dir
    await onMemoryCaseChange(form.case_dir)
  }
  if (['input', 'ltm', 'copa', 'wm', 'memory', 'ca', 'testcases', 'repair'].includes(queryTab)) {
    activeKnoTab.value = queryTab === 'memory' ? 'wm' : queryTab
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('runtime-llm-profile-changed', syncRuntimeProfile)
  stopPolling()
  stopModelingTimer()
})
</script>

<style scoped>
.hero-card {
  background: #f7fbff;
  border: 1px solid #e7effa;
  box-shadow: 0 8px 20px rgba(15, 42, 85, 0.05);
}
.hero-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}
.hero-title { font-size: 22px; font-weight: 700; color: #10233f; letter-spacing: 0; }
.hero-sub { margin-top: 6px; color: #52677f; font-size: 13px; }
.hero-pipeline {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
  max-width: 560px;
}
.hero-pipeline span {
  display: inline-flex;
  align-items: center;
  height: 26px;
  padding: 0 10px;
  border: 1px solid #cfe1f5;
  border-radius: 6px;
  background: #fff;
  color: #27527d;
  font-size: 12px;
  font-weight: 600;
}
.workflow-card {
  border: 1px solid #edf2f7;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}
.workflow-card :deep(.ant-card-body) { padding: 18px 20px 20px; }
.top-alert { margin-top: 10px; }
.muted { font-size: 12px; color: #8c8c8c; }
.workflow-tabs :deep(.ant-tabs-nav) {
  margin-bottom: 18px;
  padding: 4px;
  background: #f6f8fb;
  border-radius: 8px;
}
.workflow-tabs :deep(.ant-tabs-tab) {
  margin: 0 4px 0 0;
  padding: 9px 12px;
  border-radius: 6px;
  transition: background 0.2s ease, color 0.2s ease;
}
.workflow-tabs :deep(.ant-tabs-tab-active) {
  background: #fff;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
}
.workflow-tabs :deep(.ant-tabs-ink-bar) { display: none; }
.tab-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid #edf2f7;
  border-radius: 8px;
  background: #fbfdff;
}
.stage-eyebrow {
  margin-bottom: 4px;
  color: #2f6fab;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0;
}
.tab-head h3 { margin: 0 0 5px; font-size: 17px; color: #1f2937; letter-spacing: 0; }
.tab-head p { margin: 0; color: #64748b; font-size: 13px; line-height: 1.6; max-width: 760px; }
.input-form {
  max-width: 1080px;
  padding: 2px 2px 0;
}
.modeling-output-row {
  margin-top: 14px;
}
.stage-section {
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid #e8eef6;
  border-radius: 8px;
  background: #fff;
}
.stage-section + .stage-section {
  margin-top: 12px;
}
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  color: #122033;
  font-size: 14px;
  font-weight: 700;
}
.section-title::before {
  content: "";
  width: 4px;
  height: 16px;
  border-radius: 2px;
  background: #2f6fab;
}
.action-section {
  background: #f8fbff;
}
.compact-metrics :deep(.ant-statistic) {
  min-height: 74px;
}
.artifact-source {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 34px;
  padding: 8px 10px;
  border: 1px solid #edf2f7;
  border-radius: 6px;
  background: #fbfcfe;
  color: #52677f;
  font-size: 12px;
}
.artifact-source span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.artifact-editor-textarea {
  font-family: Consolas, 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.55;
}
.case-editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 10px;
  padding: 8px 10px;
  border: 1px solid #edf2f7;
  border-radius: 6px;
  background: #f8fbff;
  color: #52677f;
  font-size: 12px;
}
.case-editor-toolbar span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.case-editor-toolbar.read-only {
  justify-content: flex-start;
}
.case-editor-textarea {
  margin-top: 10px;
}
.ltm-stack-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 10px;
}
.ltm-structure-preview {
  margin-top: 10px;
  border: 1px solid #edf2f7;
  border-radius: 6px;
  background: #fbfdff;
  padding: 4px 8px 8px;
}
.ltm-knowledge-list :deep(.ant-list-item) {
  display: grid !important;
  grid-template-columns: max-content minmax(0, 1fr);
  justify-content: start !important;
  justify-items: start;
  align-items: start !important;
  gap: 10px;
  padding: 6px 0;
}
.ltm-package-name {
  font-weight: 600;
  color: #23415f;
  padding: 1px 7px;
  border-radius: 4px;
  background: #eef5ff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ltm-package-desc {
  justify-self: stretch;
  min-width: 0;
  width: 100%;
  color: #61758d;
  font-size: 12px;
  line-height: 1.5;
  text-align: left;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.wm-template-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.wm-template-item {
  min-height: 92px;
  padding: 12px;
  border: 1px solid #edf2f7;
  border-radius: 6px;
  background: #fbfcfe;
}
.wm-template-item b {
  display: block;
  margin-bottom: 8px;
  color: #23415f;
}
.wm-template-item span {
  color: #61758d;
  font-size: 12px;
  line-height: 1.55;
}
.repair-testcase-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
}
.repair-testcase-list {
  display: grid;
  gap: 8px;
  max-height: 260px;
  overflow: auto;
  padding-right: 4px;
}
.repair-testcase-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e6eef8;
  border-radius: 6px;
  background: #fff;
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}
.repair-testcase-item:hover {
  border-color: #8bb7ff;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.08);
}
.repair-testcase-item.active {
  border-color: #2563eb;
  background: #f6f9ff;
}
.repair-testcase-main {
  min-width: 0;
}
.repair-testcase-main b,
.repair-testcase-main small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.repair-testcase-main b {
  color: #122033;
  font-size: 13px;
  font-weight: 600;
}
.repair-testcase-main small {
  margin-top: 3px;
  color: #64748b;
  font-size: 12px;
}
@media (max-width: 900px) {
  .wm-template-grid {
    grid-template-columns: 1fr;
  }
  .repair-testcase-toolbar {
    grid-template-columns: 1fr;
  }
}
.input-form :deep(.ant-input),
.input-form :deep(.ant-input-affix-wrapper),
.input-form :deep(textarea.ant-input) {
  border-radius: 6px;
}
.asset-card {
  border: 1px solid #edf2f7;
}
.asset-card :deep(.ant-card-head) {
  min-height: 42px;
  background: #fbfdff;
}
.preview-light {
  max-height: 360px;
  overflow: auto;
  background: #fbfcfe;
  border: 1px solid #edf2f7;
  padding: 12px;
  border-radius: 6px;
  white-space: pre-wrap;
  font-family: Consolas, 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.55;
  color: #263445;
}
.preview-light.large { max-height: 520px; }
.empty-state {
  padding: 48px 12px;
  background: #fbfcfe;
  border: 1px dashed #d8e2ef;
  border-radius: 6px;
  margin-top: 10px;
}
.metric-row { margin-bottom: 14px; }
.memory-input-grid :deep(.ant-col) {
  margin-bottom: 10px;
}
.memory-input-grid :deep(.ant-card) {
  height: 100%;
}
.memory-input-grid :deep(.ant-card-body) {
  padding: 10px;
}
.memory-panel-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  padding: 8px 10px;
  border: 1px solid #edf2f7;
  border-radius: 6px;
  background: #f8fbff;
  color: #52677f;
  font-size: 12px;
}
.memory-panel-actions span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.edit-readme {
  color: #46576b;
  font-size: 13px;
  line-height: 1.7;
}
.edit-readme p {
  margin: 0 0 10px;
}
.edit-readme ul {
  margin: 0;
  padding-left: 18px;
}
.edit-readme li + li {
  margin-top: 6px;
}
.field-label-help {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.help-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border: 1px solid #b8c7dc;
  border-radius: 50%;
  background: #f8fbff;
  color: #2f6fab;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  cursor: help;
}
.metric-row :deep(.ant-col) {
  margin-bottom: 10px;
}
.metric-row :deep(.ant-statistic) {
  min-height: 86px;
  padding: 14px 16px;
  border: 1px solid #edf2f7;
  border-radius: 8px;
  background: #fbfdff;
}
.metric-row :deep(.ant-statistic-title) {
  color: #64748b;
  font-size: 12px;
}
.metric-row :deep(.ant-statistic-content) {
  color: #1f2937;
  font-size: 22px;
}
.workflow-tabs :deep(.ant-collapse) {
  background: transparent;
}
.workflow-tabs :deep(.ant-collapse-item) {
  margin-bottom: 10px;
  border: 1px solid #edf2f7;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}
.workflow-tabs :deep(.ant-collapse-header) {
  align-items: center;
  background: #fbfdff;
  font-weight: 600;
}
.workflow-tabs :deep(.ant-table) {
  border-radius: 6px;
}
.workflow-tabs :deep(.ant-table-thead > tr > th) {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
}
.log-block {
  margin: 0;
  max-height: 360px;
  overflow: auto;
  white-space: pre-wrap;
  background: #111827;
  color: #e5e7eb;
  padding: 12px;
  border-radius: 6px;
  font-family: Consolas, 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
}
.log-float {
  position: fixed;
  right: 20px;
  bottom: 96px;
  width: min(560px, calc(100vw - 40px));
  max-height: 360px;
  background: #111827;
  color: #e5e7eb;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 8px;
  box-shadow: 0 12px 28px rgba(0,0,0,0.28);
  z-index: 20;
  overflow: hidden;
}
.log-float-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  font-size: 13px;
  font-weight: 600;
}
.log-float-body {
  margin: 0;
  padding: 10px;
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
  font-family: Consolas, 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
}
@media (max-width: 768px) {
  .tab-head { flex-direction: column; }
  .hero-main { align-items: flex-start; flex-direction: column; }
  .hero-pipeline { justify-content: flex-start; }
  .workflow-card :deep(.ant-card-body) { padding: 14px; }
}
</style>
