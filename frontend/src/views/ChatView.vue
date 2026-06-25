<template>
  <a-card title="对话测试" :bordered="false">
    <a-space direction="vertical" style="width: 100%" size="large">
      <a-input-textarea v-model:value="message" :rows="4" placeholder="输入消息" />
      <a-button type="primary" @click="send" :loading="loading">发送</a-button>
      <a-typography-paragraph v-if="reply">{{ reply }}</a-typography-paragraph>
    </a-space>
  </a-card>
</template>

<script setup>
import { ref } from 'vue'
import { http } from '../api/http'

const message = ref('')
const reply = ref('')
const loading = ref(false)

const send = async () => {
  if (!message.value.trim()) return
  loading.value = true
  try {
    const { data } = await http.post('/api/chat', { message: message.value })
    reply.value = data.reply
  } finally {
    loading.value = false
  }
}
</script>
