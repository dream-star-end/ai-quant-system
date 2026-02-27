<template>
  <div style="width:380px;">
    <div style="text-align:center;margin-bottom:32px;">
      <div style="font-size:42px;margin-bottom:8px;">📈</div>
      <h1 style="font-size:24px;font-weight:700;color:var(--q-blue);">AI Quant System</h1>
      <p style="color:var(--q-text-secondary);margin-top:4px;">智能量化交易平台</p>
    </div>

    <div class="q-card">
      <el-tabs v-model="mode" stretch>
        <el-tab-pane label="登录" name="login" />
        <el-tab-pane label="注册" name="register" />
      </el-tabs>

      <el-form :model="form" size="large" @submit.prevent="handleSubmit" style="margin-top:16px;">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" />
        </el-form-item>
        <el-form-item v-if="mode === 'register'">
          <el-input v-model="form.email" placeholder="邮箱" prefix-icon="Message" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" placeholder="密码" prefix-icon="Lock" type="password" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" style="width:100%;" :loading="loading" native-type="submit">
            {{ mode === 'login' ? '登录' : '注册' }}
          </el-button>
        </el-form-item>
      </el-form>

      <div style="text-align:center;">
        <el-button text type="info" @click="$router.push('/')">跳过，先看看</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const mode = ref('login')
const loading = ref(false)
const form = ref({ username: '', email: '', password: '' })

async function handleSubmit() {
  loading.value = true
  try {
    if (mode.value === 'login') {
      await userStore.login(form.value.username, form.value.password)
    } else {
      await userStore.register(form.value.username, form.value.email, form.value.password)
    }
    ElMessage.success(mode.value === 'login' ? '登录成功' : '注册成功')
    router.push('/')
  } catch(e) {
    ElMessage.error(e.message)
  }
  loading.value = false
}
</script>
