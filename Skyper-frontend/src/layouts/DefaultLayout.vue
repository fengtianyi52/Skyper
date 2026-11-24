<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import SkyperThemePanel from '@/components/SkyperThemePanel.vue'
import SkyperIcon from '@/components/SkyperIcon.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const showTheme = ref(false)
const mainGroups = [
  {
    label: '工作空间',
    items: [
      { label: '总览', path: '/app/overview', icon: 'overview' },
      { label: '智能助手', path: '/app/assistant', icon: 'assistant' },
      { label: '知识库问答', path: '/app/qa', icon: 'qa' },
    ],
  },
  {
    label: '知识协作',
    items: [
      { label: '文档空间', path: '/app/documents', icon: 'documents' },
      { label: '协作小组', path: '/app/groups', icon: 'groups' },
    ],
  },
]
const adminGroups = [
  {
    label: '运行中心',
    items: [
      { label: '运行洞察', path: '/app/admin/insights', icon: 'chart' },
      { label: '管理助手', path: '/app/admin/assistant', icon: 'assistant' },
      { label: '使用统计', path: '/app/admin/metrics', icon: 'chart' },
    ],
  },
  {
    label: '内容与成员',
    items: [
      { label: '文档管理', path: '/app/admin/documents', icon: 'documents' },
      { label: '群组管理', path: '/app/admin/groups', icon: 'groups' },
      { label: '问答历史', path: '/app/admin/qa', icon: 'qa' },
      { label: '用户管理', path: '/app/admin/users', icon: 'groups' },
    ],
  },
  {
    label: '系统管理',
    items: [
      { label: '系统健康', path: '/app/admin/health', icon: 'shield' },
      { label: '模型配置', path: '/app/admin/models', icon: 'settings' },
      { label: '审计日志', path: '/app/admin/audit', icon: 'documents' },
      { label: 'API 令牌', path: '/app/admin/api-tokens', icon: 'shield' },
    ],
  },
]
const navGroups = computed(() => (auth.isAdmin ? adminGroups : mainGroups))
function isActive(path: string) {
  return route.path === path || route.path.startsWith(path + '/')
}
async function logout() {
  await auth.logout()
  await router.push('/')
}
</script>

<template>
  <div class="skyper-shell">
    <a class="skip-link" href="#workspace-content">跳到页面内容</a>
    <header class="workspace-header">
      <div class="workspace-brandbar">
        <RouterLink :to="auth.homePath" class="skyper-brand" aria-label="回到工作区首页">
          <span class="skyper-brand__mark">S</span>
          <span
            ><b>skyper<span class="brand-period">.</span></b
            ><small>智能知识工作台</small></span
          >
        </RouterLink>
        <span class="workspace-identity">{{ auth.isAdmin ? '管理工作台' : '个人工作台' }}</span>
        <div class="workspace-account">
          <button class="toolbar-button" @click="showTheme = true">
            <SkyperIcon name="settings" :size="18" /><span>外观设置</span>
          </button>
          <RouterLink to="/app/settings" class="skyper-profile" aria-label="个人资料与账号设置">
            <span class="skyper-avatar">{{
              (auth.currentUser?.displayName || '用户').slice(0, 1)
            }}</span>
            <span class="skyper-profile__text"
              ><b>{{ auth.currentUser?.displayName || '用户' }}</b
              ><small>{{ auth.isAdmin ? '管理员' : '成员' }}</small></span
            >
          </RouterLink>
          <button class="toolbar-button logout-button" @click="logout">退出登录</button>
        </div>
      </div>
      <nav
        class="workspace-navigation"
        :class="{ 'workspace-navigation--admin': auth.isAdmin }"
        aria-label="工作台功能导航"
      >
        <div v-for="group in navGroups" :key="group.label" class="workspace-nav-group">
          <span class="workspace-nav-group__label">{{ group.label }}</span>
          <div class="workspace-nav-group__items">
            <RouterLink
              v-for="item in group.items"
              :key="item.path"
              :to="item.path"
              class="skyper-nav"
              :class="{ active: isActive(item.path) }"
              :aria-current="isActive(item.path) ? 'page' : undefined"
            >
              <SkyperIcon :name="item.icon" :size="19" /><span>{{ item.label }}</span>
            </RouterLink>
          </div>
        </div>
      </nav>
    </header>
    <main id="workspace-content" class="skyper-main" tabindex="-1">
      <div class="skyper-main__content"><router-view /></div>
    </main>
    <el-drawer v-model="showTheme" title="外观设置" size="min(420px, 100vw)" :append-to-body="true">
      <SkyperThemePanel />
    </el-drawer>
  </div>
</template>
