<template>
  <a-layout style="min-height:100vh">
    <a-layout-sider width="220" :style="{background:'#001529'}">
      <div class="logo">
        <div class="logo-name">MAS</div>
        <div class="logo-sub">Multi-Agent System</div>
      </div>
      <a-menu v-model:selectedKeys="selectedKeys" theme="dark" mode="inline" :style="{background:'#001529'}" @click="onMenuClick">
        <a-menu-item key="/run"><template #icon><PlayCircleOutlined /></template>KnoMAS代码生成</a-menu-item>
        <a-menu-item key="/ccgmas"><template #icon><DeploymentUnitOutlined /></template>CCGMAS代码迁移</a-menu-item>
        <a-menu-item key="/datasets"><template #icon><DatabaseOutlined /></template>数据集管理</a-menu-item>
        <a-menu-item key="/glossary"><template #icon><BookOutlined /></template>名词解释</a-menu-item>
      </a-menu>
    </a-layout-sider>

    <a-layout>
      <a-layout-header :style="{background:'#fff',padding:'0 24px',height:'56px',lineHeight:'56px',borderBottom:'1px solid #f0f0f0',display:'flex',alignItems:'center',justifyContent:'space-between'}">
        <span style="font-size:15px;font-weight:500;color:#1d1d1f">{{ pageTitle }}</span>
        <a-space>
          <a-select v-model:value="activeProfileId" style="width:300px" :options="profileOptions" placeholder="请选择 API 配置" />
          <a-button size="small" @click="managerOpen = true">API配置管理</a-button>
        </a-space>
      </a-layout-header>

      <a-layout-content :style="{margin:'20px 24px',minHeight:'calc(100vh - 96px)'}">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>

  <a-modal v-model:open="managerOpen" title="API 配置管理" :footer="null" width="760">
    <a-space style="margin-bottom:10px">
      <a-button type="primary" @click="newProfile">新增配置</a-button>
    </a-space>
    <a-table :data-source="profiles" :pagination="false" row-key="id" size="small">
      <a-table-column title="名称" data-index="name" key="name" />
      <a-table-column title="Provider" data-index="provider" key="provider" width="120" />
      <a-table-column title="Model" data-index="model" key="model" width="180" />
      <a-table-column title="Base URL" data-index="base_url" key="base_url" />
      <a-table-column title="操作" key="action" width="190">
        <template #default="{ record }">
          <a-space>
            <a-button size="small" @click="editProfile(record)">编辑</a-button>
            <a-button size="small" type="link" @click="useProfile(record.id)">设为当前</a-button>
            <a-button size="small" danger @click="removeProfile(record.id)">删除</a-button>
          </a-space>
        </template>
      </a-table-column>
    </a-table>
  </a-modal>

  <a-modal v-model:open="editorOpen" :title="editingId ? '编辑配置' : '新增配置'" ok-text="保存" cancel-text="取消" @ok="saveProfile">
    <a-form layout="vertical">
      <a-form-item label="名称"><a-input v-model:value="editor.name" placeholder="如：DashScope-GLM5" /></a-form-item>
      <a-form-item label="Provider">
        <a-select v-model:value="editor.provider">
          <a-select-option value="dashscope">dashscope</a-select-option>
          <a-select-option value="openai">openai-compatible</a-select-option>
          <a-select-option value="custom">custom</a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="Base URL"><a-input v-model:value="editor.base_url" placeholder="https://.../v1" /></a-form-item>
      <a-form-item label="API Key"><a-input-password v-model:value="editor.api_key" /></a-form-item>
      <a-form-item label="Model"><a-input v-model:value="editor.model" placeholder="如 glm-5" /></a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup>
import { computed, ref, reactive, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlayCircleOutlined, DeploymentUnitOutlined, DatabaseOutlined, BookOutlined } from '@ant-design/icons-vue'
import { applyApiConfig } from './api/http'

const route = useRoute()
const router = useRouter()
const selectedKeys = ref([route.path])
watch(() => route.path, (p) => { selectedKeys.value = [p] })

const pageTitle = computed(() => ({
  '/glossary': '名词解释',
  '/run': 'KnoMAS代码生成',
  '/ccgmas': 'CCGMAS代码迁移',
  '/datasets': '数据集管理',
}[route.path] || 'ArchMAS'))

const onMenuClick = ({ key }) => router.push(key)

const PROFILES_KEY = 'ccgmas_llm_profiles'
const ACTIVE_KEY = 'ccgmas_active_profile_id'
const profiles = ref([])
const activeProfileId = ref('')

const profileOptions = computed(() => profiles.value.map(p => ({ value: p.id, label: `${p.name} | ${p.model}` })))

function syncRuntimeProfile() {
  const p = profiles.value.find(x => x.id === activeProfileId.value) || null
  window.__RUNTIME_LLM_CONFIG__ = p ? {
    id: p.id,
    name: p.name,
    provider: p.provider,
    base_url: p.base_url,
    api_key: p.api_key,
    model: p.model,
  } : null
  window.dispatchEvent(new CustomEvent('runtime-llm-profile-changed', { detail: window.__RUNTIME_LLM_CONFIG__ }))

  if (p) {
    applyApiConfig({
      backendBaseUrl: 'http://localhost:8000',
      baseUrl: p.base_url,
      apiKey: p.api_key,
      model: p.model,
    })
  }
}

watch(activeProfileId, (id) => {
  localStorage.setItem(ACTIVE_KEY, id || '')
  syncRuntimeProfile()
})

const managerOpen = ref(false)
const editorOpen = ref(false)
const editingId = ref('')
const editor = reactive({ id:'', name:'', provider:'dashscope', base_url:'', api_key:'', model:'' })

function newProfile() {
  editingId.value = ''
  Object.assign(editor, { id:'', name:'', provider:'dashscope', base_url:'', api_key:'', model:'' })
  editorOpen.value = true
}

function editProfile(p) {
  editingId.value = p.id
  Object.assign(editor, p)
  editorOpen.value = true
}

function saveProfile() {
  if (!editor.name || !editor.base_url || !editor.api_key || !editor.model) return message.warning('请完整填写配置项')
  if (!editor.base_url.startsWith('http://') && !editor.base_url.startsWith('https://')) return message.warning('Base URL 必须是 http/https')

  if (editingId.value) {
    profiles.value = profiles.value.map(p => p.id === editingId.value ? { ...editor, id: editingId.value } : p)
  } else {
    const id = `p_${Date.now()}`
    profiles.value.push({ ...editor, id })
    activeProfileId.value = id
  }
  localStorage.setItem(PROFILES_KEY, JSON.stringify(profiles.value))
  editorOpen.value = false
  syncRuntimeProfile()
  message.success('配置已保存')
}

function removeProfile(id) {
  profiles.value = profiles.value.filter(p => p.id !== id)
  localStorage.setItem(PROFILES_KEY, JSON.stringify(profiles.value))
  if (activeProfileId.value === id) activeProfileId.value = profiles.value[0]?.id || ''
  syncRuntimeProfile()
}

function useProfile(id) {
  activeProfileId.value = id
  message.success('已切换当前配置')
}

onMounted(() => {
  try { profiles.value = JSON.parse(localStorage.getItem(PROFILES_KEY) || '[]') } catch { profiles.value = [] }
  activeProfileId.value = localStorage.getItem(ACTIVE_KEY) || profiles.value[0]?.id || ''
  syncRuntimeProfile()
})
</script>
