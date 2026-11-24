<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { register as registerApi } from '@/api/auth'
import { extractApiError } from '@/api/http'
import SkyperIcon from '@/components/SkyperIcon.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const isRegister = ref(false)
const form = reactive({ loginId: '', password: '', username: '', email: '', displayName: '' })
const loading = ref(false)
const errorMsg = ref('')
const registered = ref(false)
const loginRequired = computed(() => route.query.reason === 'login-required')
const requestedPath = computed(() => {
  const value = route.query.redirect
  return typeof value === 'string' && value.startsWith('/app/') ? value : undefined
})
function switchMode() {
  isRegister.value = !isRegister.value
  form.password = ''
  errorMsg.value = ''
}
async function submit() {
  if (loading.value) return
  errorMsg.value = ''
  loading.value = true
  try {
    if (isRegister.value) {
      await registerApi({
        username: form.username.trim(),
        email: form.email.trim(),
        displayName: form.displayName.trim() || form.username.trim(),
        password: form.password,
      })
      form.loginId = form.username.trim()
      registered.value = true
      isRegister.value = false
    }
    await auth.login({ loginId: form.loginId.trim(), password: form.password })
    const failure = await router.push(auth.resolveLandingPath(requestedPath.value))
    if (failure) errorMsg.value = '登录成功，但工作区打开失败，请刷新页面后重试'
  } catch (err) {
    errorMsg.value = extractApiError(
      err,
      isRegister.value ? '注册失败，请稍后重试' : '登录失败，请检查账号和密码',
    )
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <RouterLink to="/" class="login-back">← 返回首页</RouterLink>
    <div class="login-layout">
      <section class="login-intro">
        <RouterLink to="/" class="skyper-brand"
          ><span class="skyper-brand__mark">S</span
          ><span
            ><b>skyper<span class="brand-period">.</span></b
            ><small>智能知识工作台</small></span
          ></RouterLink
        >
        <span class="eyebrow">知识有序 · 协作有据</span>
        <h1>回到你的空间，<br />继续每一个好想法。</h1>
        <p>连接资料、问题与行动。<br />在清晰、可信的工作台里，推进重要的事。</p>
        <div class="login-benefits">
          <span><SkyperIcon name="documents" /> 汇聚团队知识</span
          ><span><SkyperIcon name="qa" /> 追溯答案来源</span
          ><span><SkyperIcon name="groups" /> 让协作更有序</span>
        </div>
      </section>
      <section class="login-card" :aria-label="isRegister ? '创建账号' : '账号登录'">
        <div v-if="loginRequired" class="login-notice" role="status">
          <SkyperIcon name="shield" :size="21" />
          <div><b>请先登录</b><span>登录后即可进入工作区。</span></div>
        </div>
        <h2>{{ isRegister ? '创建你的账号' : '欢迎回来' }}</h2>
        <p class="login-subtitle">
          {{ isRegister ? '注册 Skyper，开启知识协作。' : '使用你的账号登录 Skyper。' }}
        </p>
        <p v-if="registered" class="registered-notice" role="status">
          账号已创建，可以使用该账号登录。
        </p>
        <form class="login-form" @submit.prevent="submit">
          <template v-if="isRegister">
            <label class="input-group" for="register-username"
              ><span>用户名</span
              ><input
                id="register-username"
                v-model="form.username"
                required
                pattern="[a-zA-Z0-9_-]+"
                autocomplete="username"
                placeholder="字母、数字、下划线或短横线"
            /></label>
            <label class="input-group" for="register-email"
              ><span>邮箱</span
              ><input
                id="register-email"
                v-model="form.email"
                required
                type="email"
                autocomplete="email"
                placeholder="请输入邮箱地址"
            /></label>
            <label class="input-group" for="register-display-name"
              ><span>显示名称 <small>选填</small></span
              ><input
                id="register-display-name"
                v-model="form.displayName"
                autocomplete="nickname"
                placeholder="你希望如何被称呼"
            /></label>
          </template>
          <label v-else class="input-group" for="login-id"
            ><span>账号</span
            ><input
              id="login-id"
              v-model="form.loginId"
              required
              autocomplete="username"
              placeholder="用户名或邮箱"
          /></label>
          <label class="input-group" for="account-password"
            ><span>密码</span
            ><input
              id="account-password"
              v-model="form.password"
              required
              type="password"
              :autocomplete="isRegister ? 'new-password' : 'current-password'"
              :placeholder="isRegister ? '请设置密码' : '请输入密码'"
          /></label>
          <p v-if="errorMsg" class="form-error" role="alert">{{ errorMsg }}</p>
          <button type="submit" class="hero-primary login-submit" :disabled="loading">
            {{ loading ? '正在处理…' : isRegister ? '创建账号并进入工作区' : '登录'
            }}<SkyperIcon v-if="!loading" name="arrow" :size="19" />
          </button>
        </form>
        <p class="login-footer">
          {{ isRegister ? '已有账号？' : '还没有账号？'
          }}<button :disabled="loading" @click="switchMode">
            {{ isRegister ? '返回登录' : '创建账号' }}
          </button>
        </p>
      </section>
    </div>
    <p class="login-bottom">Skyper · 让每一份知识，发挥更大的价值。</p>
  </main>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 28px var(--page-gutter);
  background: radial-gradient(ellipse at 20% 40%, #e7efff, transparent 60%), #f6f9fd;
}
.login-back {
  align-self: flex-start;
  color: var(--text-secondary);
  font-size: 14px;
  padding: 8px 0;
}
.login-back:hover {
  color: var(--skyper-accent);
}
.login-layout {
  width: min(1120px, 100%);
  margin: auto;
  padding: 50px 0;
  display: grid;
  grid-template-columns: 1fr 440px;
  gap: 70px;
  align-items: center;
}
.login-intro > .eyebrow {
  margin-top: 58px;
}
.login-intro h1 {
  font-size: clamp(28px, 3vw, 44px);
  line-height: 1.6;
  margin: 16px 0;
}
.login-intro > p {
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.9;
}
.login-benefits {
  display: flex;
  flex-wrap: wrap;
  gap: 22px;
  margin-top: 38px;
  padding-top: 24px;
  border-top: 2px solid var(--skyper-line);
  font-size: 13px;
}
.login-benefits span {
  display: flex;
  gap: 8px;
  align-items: center;
}
.login-benefits svg {
  color: var(--skyper-accent);
  width: 19px;
}
.login-card {
  background: white;
  border: 1.5px solid var(--skyper-line);
  border-top: 4px solid var(--skyper-accent);
  border-radius: 14px;
  padding: 32px;
  box-shadow: var(--shadow-xl);
}
.login-card h2 {
  font-size: 28px;
}
.login-subtitle {
  margin: 8px 0 26px;
  color: var(--text-secondary);
  font-size: 14px;
}
.login-notice {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 1.5px solid #abc4ed;
  background: #edf4ff;
  color: #254f91;
  margin-bottom: 24px;
  border-radius: 8px;
}
.login-notice b,
.login-notice span {
  display: block;
}
.login-notice b {
  font-size: 15px;
}
.login-notice span {
  font-size: 12px;
  margin-top: 2px;
}
.registered-notice {
  color: #236e50;
  font-size: 13px;
  margin-bottom: 16px;
}
.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.input-group {
  display: flex;
  flex-direction: column;
  gap: 7px;
  font-size: 14px;
  font-weight: 600;
}
.input-group small {
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 400;
}
.input-group input {
  width: 100%;
  padding: 12px 14px;
  border: 1.5px solid #afbed3;
  border-radius: 7px;
  color: var(--text-primary);
  background: white;
  font-size: 14px;
}
.input-group input::placeholder {
  color: #697a90;
}
.input-group input:focus {
  border-color: var(--skyper-accent);
  outline: 3px solid #2458c61a;
  outline-offset: 0;
}
.form-error {
  padding: 10px 12px;
  border-radius: 6px;
  background: #fff1f0;
  color: #af2929;
  font-size: 13px;
}
.login-submit {
  width: 100%;
  margin-top: 6px;
}
.login-submit:disabled {
  opacity: 0.65;
  transform: none;
}
.login-footer {
  display: flex;
  justify-content: center;
  gap: 5px;
  margin-top: 26px;
  padding-top: 20px;
  border-top: 1.5px solid var(--border-default);
  font-size: 13px;
  color: var(--text-secondary);
}
.login-footer button {
  background: none;
  color: var(--skyper-accent);
  font-size: 13px;
  font-weight: 700;
}
.login-bottom {
  color: var(--text-secondary);
  text-align: center;
  font-size: 12px;
  padding-top: 20px;
}
@media (max-width: 900px) {
  .login-layout {
    grid-template-columns: 1fr;
    max-width: 480px;
    gap: 30px;
    padding: 24px 0;
  }
  .login-intro > .eyebrow,
  .login-intro > h1,
  .login-intro > p,
  .login-benefits {
    display: none;
  }
  .login-card {
    padding: 26px;
  }
}
</style>
