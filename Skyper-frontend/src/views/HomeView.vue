<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import SkyperIcon from '@/components/SkyperIcon.vue'

const router = useRouter()
const auth = useAuthStore()
function enterWorkspace() {
  if (auth.isAuthenticated) return router.push(auth.homePath)
  ElMessage.info('请先登录')
  return router.push({ path: '/login', query: { reason: 'login-required' } })
}
const steps = [
  {
    title: '汇集团队知识',
    text: '上传文档、组织小组，让分散的资料进入同一个知识空间。',
    icon: 'documents',
  },
  {
    title: '用问题连接答案',
    text: '通过智能助手和知识库检索，梳理思路、查找信息、推进任务。',
    icon: 'assistant',
  },
  {
    title: '让结论有据可查',
    text: '从回答回到原始文档，查看引用片段与工具调用过程。',
    icon: 'shield',
  },
]
const capabilities = [
  {
    title: '智能对话',
    text: '整理想法、拆解问题，在连续对话中推进工作。',
    icon: 'assistant',
    tag: '思考与行动',
  },
  {
    title: '知识库问答',
    text: '结合语义与关键词检索，让答案关联到具体证据。',
    icon: 'qa',
    tag: '检索与理解',
  },
  {
    title: '文档空间',
    text: '集中上传、处理和浏览资料，建立团队知识基础。',
    icon: 'documents',
    tag: '资料与沉淀',
  },
  {
    title: '小组协作',
    text: '组织成员与知识范围，让共享和权限清晰可控。',
    icon: 'groups',
    tag: '成员与权限',
  },
]
</script>

<template>
  <div class="skyper-landing">
    <a class="skip-link" href="#home-content">跳到页面内容</a>
    <header class="landing-nav">
      <a href="#" class="skyper-brand" aria-label="Skyper 首页"
        ><span class="skyper-brand__mark">S</span
        ><span
          ><b>skyper<span class="brand-period">.</span></b
          ><small>智能知识工作台</small></span
        ></a
      >
      <nav class="landing-nav__links" aria-label="首页导航">
        <a href="#method">工作方式</a><a href="#capabilities">核心能力</a
        ><a href="#reliability">可信协作</a>
      </nav>
      <RouterLink class="landing-login" to="/login"
        >登录 <SkyperIcon name="arrow" :size="17"
      /></RouterLink>
    </header>
    <main id="home-content">
      <section class="landing-hero">
        <div class="landing-hero__copy">
          <span class="eyebrow"><span class="eyebrow-dot" /> 连接知识 · 协同思考 · 推进行动</span>
          <h1>让知识流动，<br />让协作<em>更进一步。</em></h1>
          <p>
            把文档、问答和智能助手放进同一个工作台。<br
              class="desktop-break"
            />从一个问题出发，找到有出处的答案，开启有方向的行动。
          </p>
          <div class="hero-buttons">
            <button class="hero-primary" @click="enterWorkspace">
              打开工作区 <SkyperIcon name="arrow" /></button
            ><a class="hero-secondary" href="#capabilities"
              >了解核心能力 <span aria-hidden="true">↓</span></a
            >
          </div>
          <div class="hero-assurances">
            <span><SkyperIcon name="check" :size="17" /> 回答可追溯</span
            ><span><SkyperIcon name="check" :size="17" /> 权限有边界</span
            ><span><SkyperIcon name="check" :size="17" /> 团队共协作</span>
          </div>
        </div>
        <div class="knowledge-map" aria-label="知识协作流程示意">
          <div class="map-heading">
            <span>你的知识，自成体系</span><span class="map-badge">流程示意</span>
          </div>
          <div class="map-sources">
            <span><SkyperIcon name="documents" /> 项目文档</span
            ><span><SkyperIcon name="groups" /> 团队资料</span
            ><span><SkyperIcon name="overview" /> 业务知识</span>
          </div>
          <div class="map-connectors" aria-hidden="true"><span /><span /><span /></div>
          <div class="map-core">
            <span class="map-core__icon"><SkyperIcon name="assistant" :size="32" /></span>
            <div>
              <b>Skyper 智能知识引擎</b>
              <p>理解问题 · 检索证据 · 连接工具</p>
            </div>
            <span class="map-core__decoration" aria-hidden="true">✧</span>
          </div>
          <div class="map-output-connector" aria-hidden="true">↓</div>
          <div class="map-answer">
            <div class="map-answer__title">
              <SkyperIcon name="shield" :size="20" /><b>每一个答案，都有迹可循</b>
            </div>
            <p>从资料中提炼要点，让结论与来源一起呈现。</p>
            <div class="map-citations">
              <span>文档引用</span><span>执行记录</span><span>协作上下文</span>
            </div>
          </div>
          <div class="map-foot"><span class="eyebrow-dot" /> 知识有序，行动有据</div>
        </div>
      </section>
      <section id="method" class="landing-section landing-method">
        <div class="section-heading">
          <div>
            <span class="eyebrow">工作方式</span>
            <h2>从资料到答案，再到行动。</h2>
          </div>
          <p>三个环节，串起一条清晰的工作路径。</p>
        </div>
        <div class="method-grid">
          <article v-for="(step, index) in steps" :key="step.title">
            <span class="step-number">0{{ index + 1 }}</span
            ><SkyperIcon :name="step.icon" :size="28" />
            <h3>{{ step.title }}</h3>
            <p>{{ step.text }}</p>
          </article>
        </div>
      </section>
      <section id="capabilities" class="landing-section landing-capabilities">
        <div class="section-heading">
          <div>
            <span class="eyebrow">核心能力</span>
            <h2>一个工作台，承接每一步。</h2>
          </div>
          <p>把常用功能放在一起，让专注自然发生。</p>
        </div>
        <div class="capability-grid">
          <article v-for="item in capabilities" :key="item.title">
            <span class="feature-icon"><SkyperIcon :name="item.icon" :size="26" /></span
            ><span class="feature-tag">{{ item.tag }}</span>
            <h3>{{ item.title }}</h3>
            <p>{{ item.text }}</p>
          </article>
        </div>
      </section>
      <section id="reliability" class="landing-reliability">
        <div class="reliability-title">
          <SkyperIcon name="shield" :size="32" />
          <div>
            <span class="eyebrow">可信协作</span>
            <h2>效率之外，更重视可靠。</h2>
          </div>
        </div>
        <div class="reliability-points">
          <p><b>证据可核验</b><span>关联原文，追溯回答来源</span></p>
          <p><b>操作可确认</b><span>重要写操作执行前先确认</span></p>
          <p><b>范围可管理</b><span>按角色与小组组织访问权限</span></p>
        </div>
      </section>
    </main>
    <footer class="landing-footer">
      <span><b>skyper.</b> 智能知识工作台</span><span>让每一份知识，发挥更大的价值。</span
      ><a href="#">返回顶部 ↑</a>
    </footer>
  </div>
</template>
