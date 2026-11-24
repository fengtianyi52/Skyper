<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import SkyperIcon from '@/components/SkyperIcon.vue'

const auth = useAuthStore()
const displayName = computed(() => auth.currentUser?.displayName || '伙伴')
const actions = [
  {
    label: '智能助手',
    detail: '整理思路，开启新的对话',
    path: '/app/assistant',
    icon: 'assistant',
  },
  { label: '知识库问答', detail: '提出问题，查找有据可依的答案', path: '/app/qa', icon: 'qa' },
  {
    label: '文档空间',
    detail: '管理资料，积累团队知识',
    path: '/app/documents',
    icon: 'documents',
  },
  { label: '协作小组', detail: '连接成员，共享知识与进展', path: '/app/groups', icon: 'groups' },
]
</script>

<template>
  <div class="overview-page">
    <section class="overview-hero">
      <div>
        <span class="eyebrow">工作台总览</span>
        <h1>你好，{{ displayName }}。<br /><em>今天，从一个好问题开始。</em></h1>
        <p>你的资料、思路与协作，都在这里有序展开。</p>
        <RouterLink to="/app/assistant" class="hero-primary"
          >开始对话 <SkyperIcon name="arrow" :size="20"
        /></RouterLink>
      </div>
      <div class="overview-illustration" aria-hidden="true">
        <div class="overview-illustration__orbit" />
        <span class="illustration-tile illustration-tile--document"
          ><SkyperIcon name="documents" :size="30" />团队知识</span
        ><span class="illustration-center"><SkyperIcon name="assistant" :size="48" /></span
        ><span class="illustration-tile illustration-tile--answer"
          ><SkyperIcon name="shield" :size="28" />可信答案</span
        ><span class="illustration-caption">连接知识，推进每一次协作</span>
      </div>
    </section>
    <section class="overview-section" aria-labelledby="quick-title">
      <div class="section-heading">
        <h2 id="quick-title">常用工作入口</h2>
        <span>从你要做的事开始</span>
      </div>
      <div class="overview-actions">
        <RouterLink
          v-for="action in actions"
          :key="action.path"
          :to="action.path"
          class="overview-action"
          ><span class="feature-icon"><SkyperIcon :name="action.icon" :size="27" /></span>
          <h3>{{ action.label }}</h3>
          <p>{{ action.detail }}</p>
          <span class="action-link">立即打开 <SkyperIcon name="arrow" :size="18" /></span
        ></RouterLink>
      </div>
    </section>
    <section class="overview-grid">
      <article class="overview-card">
        <div class="section-heading">
          <div>
            <span class="eyebrow">快速上手</span>
            <h2>让知识开始发挥作用</h2>
          </div>
          <SkyperIcon name="documents" :size="28" />
        </div>
        <div class="onboarding-steps">
          <RouterLink to="/app/groups"
            ><span>01</span>
            <div>
              <b>加入或创建协作小组</b>
              <p>确定共享成员与知识范围。</p>
            </div>
            <SkyperIcon name="arrow" :size="20" /></RouterLink
          ><RouterLink to="/app/documents"
            ><span>02</span>
            <div>
              <b>上传并整理文档</b>
              <p>将需要检索的资料加入知识库。</p>
            </div>
            <SkyperIcon name="arrow" :size="20" /></RouterLink
          ><RouterLink to="/app/qa"
            ><span>03</span>
            <div>
              <b>提问，并查看原文依据</b>
              <p>从答案进入引用片段，核实信息。</p>
            </div>
            <SkyperIcon name="arrow" :size="20"
          /></RouterLink>
        </div>
      </article>
      <article class="overview-card overview-card--guide">
        <span class="eyebrow">使用建议</span>
        <h2>问题越具体，<br />思路越清晰。</h2>
        <p>
          告诉助手你的目标、已有资料和预期结果。需要查询文档时，先选择对应的知识库，再检查回答中的引用。
        </p>
        <div class="example-prompt">
          <span>试着这样问</span>
          <p>“请根据项目文档，整理实施步骤和注意事项，并列出对应的原文依据。”</p>
        </div>
        <RouterLink to="/app/assistant" class="action-link"
          >前往智能助手 <SkyperIcon name="arrow" :size="18"
        /></RouterLink>
      </article>
    </section>
    <div class="overview-note">
      <SkyperIcon name="settings" :size="19" />
      <p>在右上角「外观设置」中更换主题色或背景图片。背景图片仅保存在当前浏览器。</p>
    </div>
  </div>
</template>
