<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import LoginModal from '@/components/LoginModal.vue'

const router = useRouter()
const auth = useAuthStore()
const showLogin = ref(false)
function enter() { auth.isAuthenticated ? router.push('/app/overview') : (showLogin.value = true) }
</script>

<template>
  <div class="skyper-landing">
    <LoginModal v-model:visible="showLogin" />
    <nav class="landing-nav"><button class="skyper-brand landing-brand" @click="router.push('/')"><span class="skyper-brand__mark">S</span><span><b>skyper</b><small>agent workspace</small></span></button><div class="landing-nav__links"><a href="#method">方法</a><a href="#capabilities">能力</a><a href="#reliability">可靠性</a></div><button class="landing-login" @click="enter">{{ auth.isAuthenticated ? '进入工作区' : '登录' }} <span>↗</span></button></nav>
    <section class="landing-hero"><div class="hero-orbit hero-orbit--one" /><div class="hero-orbit hero-orbit--two" /><div class="landing-hero__copy"><span class="eyebrow">RAG / AGENT / EVALUATION</span><h1>让知识成为<br><em>可协作的行动力。</em></h1><p>Skyper 把私有文档、检索证据和 Agent 工具串成一个可观察、可验证的工作台。每一次回答，都能追溯；每一次改动，都能回归。</p><div class="hero-buttons"><button class="hero-primary" @click="enter">打开工作区 <span>→</span></button><button class="hero-secondary" @click="router.push('/login')">查看登录</button></div></div><div class="landing-hero__signal"><div class="signal-head"><span>LIVE TRACE</span><span class="signal-status"><i /> healthy</span></div><div class="signal-line"><b>01</b><span class="signal-bar signal-bar--long" /><small>retrieval</small></div><div class="signal-line"><b>02</b><span class="signal-bar signal-bar--mid" /><small>tool policy</small></div><div class="signal-line"><b>03</b><span class="signal-bar signal-bar--short" /><small>answer</small></div><div class="signal-foot">agent run <strong>#SKY-2048</strong><span>82ms</span></div></div></section>
    <section id="method" class="landing-method"><div class="section-intro"><span class="eyebrow">DESIGNED FOR THE WHOLE LOOP</span><h2>从“能回答”到<br><strong>知道为什么。</strong></h2></div><div class="method-grid"><article><span>01</span><h3>Bring your context</h3><p>上传文档、创建小组，让知识在正确的权限边界内进入检索空间。</p></article><article><span>02</span><h3>Let agents act</h3><p>通过 LangGraph 编排工具调用，支持流式事件和高风险操作确认。</p></article><article id="reliability"><span>03</span><h3>Prove the behavior</h3><p>Python 评测器记录工具、参数、权限和确认结果，回归测试不再靠感觉。</p></article></div></section>
    <section id="capabilities" class="landing-strip"><span class="eyebrow">A QUIETLY POWERFUL WORKSPACE</span><div><b>Hybrid retrieval</b><b>Evidence citations</b><b>Human confirmation</b><b>Offline regression</b></div></section>
    <footer class="landing-footer"><span>skyper / agent workspace</span><span>Built on FastAPI · Vue · LangGraph</span></footer>
  </div>
</template>

