<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const firstName = computed(() => (auth.currentUser?.displayName ?? '伙伴').split(' ')[0])
const actions = [
  { label: '开始一段对话', detail: '让 Agent 帮你整理、检索或执行', path: '/app/assistant', accent: 'primary', icon: '✦' },
  { label: '查看知识库', detail: '浏览群组中的文档与证据', path: '/app/documents', accent: 'quiet', icon: '▤' },
  { label: '进入问答', detail: '用带引用的检索回答验证想法', path: '/app/qa', accent: 'quiet', icon: '⌕' },
]
</script>

<template>
  <div class="overview-page">
    <section class="overview-hero"><div><span class="eyebrow">GOOD TO SEE YOU</span><h1>你好，{{ firstName }}。<br><em>今天想推进什么？</em></h1><p>Skyper 会把上下文、证据和工具调用放在同一个可追踪的对话里。</p></div><div class="overview-hero__stamp"><span class="stamp-dot" /><span>RUN SPACE</span><strong>READY</strong><small>your private agent surface</small></div></section>
    <section class="overview-actions"><button v-for="action in actions" :key="action.label" class="overview-action" :class="`overview-action--${action.accent}`" @click="router.push(action.path)"><span class="overview-action__icon">{{ action.icon }}</span><span><b>{{ action.label }}</b><small>{{ action.detail }}</small></span><span class="overview-action__arrow">→</span></button></section>
    <section class="overview-grid"><article class="overview-card overview-card--trace"><div class="card-head"><span class="eyebrow">AGENT TRACE</span><span class="card-link" @click="router.push('/app/assistant')">打开 Agent <b>↗</b></span></div><div class="trace-title">一条清晰的<br><strong>思考路径。</strong></div><div class="trace-steps"><div><i class="trace-node trace-node--done" /><span>context loaded</span><b>01</b></div><div><i class="trace-node trace-node--active" /><span>tool policy ready</span><b>02</b></div><div><i class="trace-node" /><span>waiting for you</span><b>03</b></div></div></article><article class="overview-card overview-card--quality"><div class="card-head"><span class="eyebrow">RELIABILITY LAYER</span><span class="quality-score">A-</span></div><h3>每次改动，<br><em>都有回归。</em></h3><p>离线评测器会检查工具选择、参数、权限和确认链路，避免“看起来能跑”成为唯一标准。</p><div class="quality-bar"><span /><span /><span /><span /><span /></div><small>5 个核心场景 · Python / pytest</small></article></section>
    <section class="overview-note"><span class="note-mark">i</span><p>提示：你可以在左下角主题面板上传背景图。图片留在本机浏览器，换一张图就换一个工作氛围。</p></section>
  </div>
</template>

