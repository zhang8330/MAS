<template>
  <a-card title="系统状态" :bordered="false">
    <a-space direction="vertical" style="width: 100%">
      <a-button type="primary" @click="checkHealth" :loading="loading">检查后端健康状态</a-button>
      <a-alert v-if="result" type="success" :message="result" show-icon />
    </a-space>
  </a-card>
</template>

<script setup>
import { ref } from 'vue'
import { http } from '../api/http'

const loading = ref(false)
const result = ref('')

const checkHealth = async () => {
  loading.value = true
  try {
    const { data } = await http.get('/health')
    result.value = `${data.service} - ${data.status}`
  } finally {
    loading.value = false
  }
}
</script>
