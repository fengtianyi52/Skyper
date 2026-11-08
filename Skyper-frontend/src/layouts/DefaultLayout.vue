<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import SkyperThemePanel from '@/components/SkyperThemePanel.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const theme = useThemeStore()

const mainNav = [
  { key: 'overview', label: '总览', path: '/app/overview', icon: '◈' },
  { key: 'assistant', label: 'Skyper Agent', path: '/app/assistant', icon: '✦' },
  { key: 'qa', label: '知识库问答', path: '/app/qa', icon: '⌕' },
  { key: 'documents', label: '文档空间', path: '/app/documents', icon: '▤' },
  { key: 'groups', label: '协作小组', path: '/app/groups', icon: '◎' },
]
const adminNav = [
  { key: 'admin-insights', label: '运行洞察', path: '/app/admin/insights', icon: '⌁' },
  { key: 'admin-assistant', label: '管理 Agent', path: '/app/admin/assistant', icon: '⚙' },
  { key: 'admin-documents', label: '文档管理', path: '/app/admin/documents', icon: '▤' },
  { key: 'admin-groups', label: '群组管理', path: '/app/admin/groups', icon: '◎' },
  { key: 'admin-qa', label: '问答历史', path: '/app/admin/qa', icon: '⌕' },
  { key: 'admin-users', label: '用户管理', path: '/app/admin/users', icon: '♙' },
  { key: 'admin-metrics', label: '使用统计', path: '/app/admin/metrics', icon: '◈' },
  { key: 'admin-health', label: '系统健康', path: '/app/admin/health', icon: '♡' },
  { key: 'admin-models', label: '模型配置', path: '/app/admin/models', icon: '◇' },
  { key: 'admin-audit', label: '审计日志', path: '/app/admin/audit', icon: '≡' },
  { key: 'admin-api-tokens', label: 'API 令牌', path: '/app/admin/api-tokens', icon: '⌘' },
]
const activeKey = computed(() => {
  const match = [...mainNav, ...adminNav].find((item) => route.path === item.path || route.path.startsWith(`${item.path}/`))
  return match?.key ?? 'overview'
})
const displayNav = computed(() => (auth.isAdmin ? adminNav : mainNav))
onMounted(() => theme.apply())
function go(path: string) { router.push(path) }
async function logout() { await auth.logout(); router.push('/') }
</script>

<template>
  <div class="skyper-shell">
    <aside class="skyper-sidebar">
      <button class="skyper-brand" aria-label="回到工作区首页" @click="go(auth.homePath)">
        <span class="skyper-brand__mark">S</span><span><b>skyper</b><small>agent workspace</small></span>
      </button>
      <div class="skyper-sidebar__section"><span class="skyper-sidebar__label">WORKSPACE</span>
        <button v-for="item in displayNav" :key="item.key" class="skyper-nav" :class="{ active: activeKey === item.key }" @click="go(item.path)">
          <span class="skyper-nav__icon">{{ item.icon }}</span><span>{{ item.label }}</span>
        </button>
      </div>
      <div class="skyper-sidebar__footer">
        <SkyperThemePanel />
        <button class="skyper-profile" @click="go('/app/settings')"><span class="skyper-avatar">{{ (auth.currentUser?.displayName ?? 'S').slice(0, 1) }}</span><span class="skyper-profile__text"><b>{{ auth.currentUser?.displayName ?? '访客' }}</b><small>{{ auth.isAdmin ? 'ADMIN' : 'MEMBER' }}</small></span><span class="skyper-profile__arrow">↗</span></button>
        <button class="skyper-logout" @click="logout">退出当前工作区</button>
      </div>
    </aside>
    <main class="skyper-main">
      <header class="skyper-topbar"><div><span class="topbar-kicker">{{ auth.isAdmin ? 'ADMIN CONTROL' : 'PERSONAL WORKSPACE' }}</span><span class="topbar-path">/ {{ activeKey }}</span></div><div class="topbar-actions"><span class="live-dot" /><span>服务在线</span><span class="topbar-date">{{ new Date().toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) }}</span></div></header>
      <div class="skyper-main__content"><router-view /></div>
    </main>
  </div>
</template>
