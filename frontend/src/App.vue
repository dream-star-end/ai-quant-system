<template>
  <div v-if="$route.meta.hide" class="login-layout">
    <router-view />
  </div>
  <div v-else class="app-layout">
    <aside class="app-sidebar">
      <div class="logo">
        <span>📈</span> AI Quant
      </div>
      <nav class="nav-menu">
        <router-link
          v-for="r in navRoutes"
          :key="r.path"
          :to="r.path"
          class="nav-item"
          :class="{ active: $route.path === r.path }"
        >
          <el-icon><component :is="r.meta.icon" /></el-icon>
          {{ r.meta.title }}
        </router-link>
      </nav>
      <div style="padding: 12px 8px; border-top: 1px solid var(--q-border);">
        <div v-if="userStore.isLoggedIn" class="nav-item" @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          退出 ({{ userStore.user?.username }})
        </div>
        <router-link v-else to="/login" class="nav-item">
          <el-icon><User /></el-icon>
          登录 / 注册
        </router-link>
      </div>
    </aside>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { routes } from './router'
import { useUserStore } from './stores/user'

const router = useRouter()
const userStore = useUserStore()
const navRoutes = computed(() => routes.filter(r => !r.meta?.hide))

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.login-layout {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--q-bg);
}
</style>
