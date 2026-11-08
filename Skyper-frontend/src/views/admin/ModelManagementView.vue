<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http, { type ApiResponse, extractApiError } from '@/api/http'

type ModelType = 'chat' | 'embedding' | 'mineru'
interface ModelConfigItem {
  id: number; modelType: ModelType; displayName: string; baseUrl: string; apiKey: string;
  modelName: string; apiFormat: string; parameters: Record<string, unknown> | null;
  isActive: boolean; fallbackConfigId: number | null;
}
interface Provider {
  id: string; label: string; protocol: string; baseUrl: string;
  chatModels: string[]; embeddingModels: string[]; docs: string; hint: string;
}
interface TestResult { ok: boolean; message: string; dimensions?: number }
const labels: Record<ModelType, string> = { chat: '聊天大模型', embedding: '嵌入大模型', mineru: 'MinerU 文档解析' }
const types: ModelType[] = ['chat', 'embedding', 'mineru']
const configs = ref<ModelConfigItem[]>([])
const providers = ref<Provider[]>([])
const selectedId = ref<number | null>(null)
const selected = computed(() => configs.value.find(c => c.id === selectedId.value))
const loading = ref(false)
const busy = ref(false)
const protocolLabels: Record<string, string> = { openai: 'OpenAI 兼容', anthropic: 'Anthropic Messages', dashscope: 'DashScope 原生文本向量', dashscope_mm: 'DashScope 原生多模态向量' }

async function loadAll() {
  loading.value = true
  try {
    const results = await Promise.all(types.map(modelType => http.get<ApiResponse<ModelConfigItem[]>>('/admin/model-configs', { params: { modelType } })))
    configs.value = results.flatMap(r => r.data.data ?? [])
    providers.value = (await http.get<ApiResponse<Provider[]>>('/admin/model-providers')).data.data
    if (!configs.value.some(c => c.id === selectedId.value)) selectedId.value = configs.value.find(c => c.isActive)?.id ?? configs.value[0]?.id ?? null
  } catch (error) { ElMessage.error(extractApiError(error, '加载模型失败')) }
  finally { loading.value = false }
}

const editingId = ref<number | null>(null)
const dialog = ref(false)
const form = reactive({ modelType: 'chat' as ModelType, provider: 'dashscope', displayName: '', baseUrl: '', apiKey: '', modelName: '', apiFormat: 'openai', dimensions: undefined as number | undefined, temperature: undefined as number | undefined, maxTokens: undefined as number | undefined })
const activateAfterSave = ref(true)
const advanced = ref(false)
const testing = ref(false)
const discovering = ref(false)
const saving = ref(false)
const testResult = ref<TestResult | null>(null)
const formError = ref('')
const discoveryMessage = ref('')
const discovered = ref<string[]>([])
const extraParameters = ref<Record<string, unknown>>({})
const provider = computed(() => providers.value.find(p => p.id === form.provider))
const providerOptions = computed(() => providers.value.filter(p => form.modelType === 'embedding'
  ? !['anthropic', 'dashscope-anthropic', 'deepseek', 'moonshot', 'xai'].includes(p.id)
  : !['dashscope-native', 'dashscope-mm'].includes(p.id)))
const modelOptions = computed(() => [...new Set([...discovered.value, ...(form.modelType === 'embedding' ? provider.value?.embeddingModels ?? [] : provider.value?.chatModels ?? [])])])
const protocols = computed(() => form.modelType === 'embedding' ? ['openai', 'dashscope', 'dashscope_mm'] : ['openai', 'anthropic'])
function suggestModels(query: string, done: (items: { value: string }[]) => void) {
  done(modelOptions.value.filter(id => id.toLowerCase().includes(query.toLowerCase())).slice(0, 100).map(value => ({ value })))
}

function chooseProvider() {
  if (!provider.value) return
  form.apiFormat = provider.value.protocol
  form.baseUrl = provider.value.baseUrl
  form.modelName = ''
  form.dimensions = undefined
  form.temperature = undefined
  form.maxTokens = undefined
  discovered.value = []
  discoveryMessage.value = ''
  extraParameters.value = {}
}
function openForm(type: ModelType, item?: ModelConfigItem) {
  editingId.value = item?.id ?? null
  form.modelType = type
  form.provider = 'dashscope'
  form.apiKey = ''
  form.displayName = ''
  chooseProvider()
  if (item) {
    form.provider = providers.value.find(p => p.baseUrl === item.baseUrl && p.protocol === item.apiFormat)?.id ?? 'custom'
    form.displayName = item.displayName
    form.baseUrl = item.baseUrl
    form.apiKey = item.apiKey
    form.modelName = item.modelName
    form.apiFormat = item.apiFormat
    extraParameters.value = { ...(item.parameters ?? {}) }
    form.dimensions = (item.parameters?.dimensions as number) || undefined
    form.temperature = item.parameters?.temperature as number | undefined
    form.maxTokens = (item.parameters?.maxTokens ?? item.parameters?.max_tokens) as number | undefined
  } else if (type === 'mineru') {
    form.baseUrl = 'https://mineru.net'; form.modelName = 'vlm'; form.displayName = labels.mineru
  }
  activateAfterSave.value = item?.isActive ?? !configs.value.some(c => c.modelType === type && c.isActive)
  advanced.value = Boolean(item) || type === 'mineru'
  testResult.value = null
  formError.value = ''
  dialog.value = true
}
function payload() {
  const parameters: Record<string, unknown> = { ...extraParameters.value }
  for (const key of ['verified_dimensions', 'verifiedDimensions', 'dimensions', 'temperature', 'max_tokens', 'maxTokens']) delete parameters[key]
  if (form.modelType === 'embedding' && form.dimensions) parameters.dimensions = form.dimensions
  if (form.modelType === 'chat') {
    if (form.temperature !== undefined) parameters.temperature = form.temperature
    if (form.maxTokens) parameters.max_tokens = form.maxTokens
  }
  return { modelType: form.modelType, displayName: form.displayName.trim() || form.modelName.trim(), baseUrl: form.baseUrl.trim(), apiKey: form.apiKey.trim(), modelName: form.modelName.trim(), apiFormat: form.apiFormat, parameters }
}
watch(() => JSON.stringify(payload()), () => { testResult.value = null; formError.value = '' })
watch(() => [form.baseUrl, form.apiKey, form.apiFormat], () => { discovered.value = []; discoveryMessage.value = '' })
function valid() {
  if (!form.baseUrl.trim() || !form.apiKey.trim() || !form.modelName.trim()) {
    formError.value = '请填写 API 地址、API Key 和精确模型 ID。'
    return false
  }
  return true
}
async function discover() {
  if (!form.baseUrl || !form.apiKey) { formError.value = '请先填写 API 地址与 Key'; return }
  discovering.value = true
  discoveryMessage.value = ''
  try {
    const result = (await http.post<ApiResponse<{ ok: boolean; message: string; models: string[] }>>('/admin/model-configs/discover', payload(), { timeout: 40000 })).data.data
    discoveryMessage.value = result.message
    discovered.value = result.models
  } catch (error) { discoveryMessage.value = extractApiError(error, '读取列表失败；可手动输入模型 ID') }
  finally { discovering.value = false }
}
async function testConnection() {
  if (!valid()) return false
  testing.value = true
  formError.value = ''
  testResult.value = null
  try {
    testResult.value = (await http.post<ApiResponse<TestResult>>('/admin/model-configs/test', payload(), { timeout: 90000 })).data.data
    return testResult.value.ok
  } catch (error) { testResult.value = { ok: false, message: extractApiError(error, '测试失败') }; return false }
  finally { testing.value = false }
}
async function saveModel() {
  if (!valid()) return
  saving.value = true
  formError.value = ''
  try {
    if (!testResult.value?.ok && !await testConnection()) return
    const response = editingId.value
      ? await http.put<ApiResponse<{id: number}>>('/admin/model-configs/' + editingId.value, payload(), { timeout: 90000 })
      : await http.post<ApiResponse<{id: number}>>('/admin/model-configs', payload(), { timeout: 90000 })
    const id = response.data.data.id
    editingId.value = id
    selectedId.value = id
    if (activateAfterSave.value) await http.patch('/admin/model-configs/' + id + '/activate', {}, { timeout: 90000 })
    dialog.value = false
    ElMessage.success(activateAfterSave.value ? '验证通过，已保存并启用' : '验证通过，已保存')
    await loadAll()
  } catch (error) { formError.value = extractApiError(error, '保存或启用失败'); await loadAll() }
  finally { saving.value = false }
}
async function activateSelected() {
  if (!selected.value) return
  busy.value = true
  try { await http.patch('/admin/model-configs/' + selected.value.id + '/activate', {}, { timeout: 90000 }); await loadAll(); ElMessage.success('已启用') }
  catch(error) { ElMessage.error(extractApiError(error, '启用失败')) }
  finally { busy.value = false }
}
async function deleteSelected() {
  if (!selected.value) return
  try { await ElMessageBox.confirm('确定删除配置「' + selected.value.displayName + '」？', '删除配置', { type: 'warning' }) }
  catch { return }
  try { await http.delete('/admin/model-configs/' + selected.value.id); await loadAll() }
  catch(error) { ElMessage.error(extractApiError(error, '删除失败')) }
}
const fallbackDialog = ref(false)
const fallbackId = ref<number | null>(null)
const fallbackOptions = computed(() => configs.value.filter(c => c.id !== selected.value?.id && c.modelType === selected.value?.modelType))
async function saveFallback() {
  try { await http.patch('/admin/model-configs/' + selected.value!.id + '/fallback', { fallbackConfigId: fallbackId.value }); fallbackDialog.value = false; await loadAll() }
  catch(error) { ElMessage.error(extractApiError(error, '设置失败')) }
}
onMounted(loadAll)
</script>

<template>
  <div class="mm-page" v-loading="loading">
    <aside class="mm-side">
      <header class="mm-side__head"><h2>模型配置</h2><p>官方 API · 自定义兼容接口</p></header>
      <div class="mm-group">
        <div class="mm-group__label">已配置 <span class="mm-count">{{ configs.length }}</span></div>
        <template v-for="type in types" :key="type">
          <div v-if="configs.some(c => c.modelType === type)" class="mm-sub-label">{{ labels[type] }}</div>
          <button v-for="c in configs.filter(c => c.modelType === type)" :key="c.id" class="mm-item" :class="{'is-active': selectedId === c.id}" @click="selectedId = c.id">
            <span class="mm-item__name">{{ c.displayName }}</span><span v-if="c.isActive" class="mm-item__badge">使用中</span>
          </button>
        </template>
      </div>
      <div class="mm-group"><div class="mm-group__label">添加配置</div><button v-for="type in types" :key="type" class="mm-item mm-item--add" @click="openForm(type)">＋ {{ labels[type] }}</button></div>
    </aside>
    <main class="mm-detail">
      <template v-if="selected">
        <div class="mm-detail__head"><h2>{{ selected.displayName }} <span v-if="selected.isActive" class="mm-item__badge">使用中</span></h2>
          <div class="setup-actions"><el-button @click="openForm(selected.modelType, selected)">编辑 / 测试</el-button><el-button v-if="!selected.isActive" :loading="busy" @click="activateSelected">启用</el-button><el-button type="danger" plain @click="deleteSelected">删除</el-button></div>
        </div>
        <dl class="setup-details">
          <dt>类型</dt><dd>{{ labels[selected.modelType] }}</dd>
          <dt>模型 ID</dt><dd>{{ selected.modelName }}</dd>
          <dt>协议</dt><dd>{{ protocolLabels[selected.apiFormat] ?? selected.apiFormat }}</dd>
          <dt>API 地址</dt><dd>{{ selected.baseUrl }}</dd>
          <dt>API Key</dt><dd>已保存 · ••••••••</dd>
          <dt>参数</dt><dd>{{ JSON.stringify(selected.parameters ?? {}) }}</dd>
          <template v-if="selected.modelType === 'chat'"><dt>备用模型</dt><dd>{{ configs.find(c => c.id === selected?.fallbackConfigId)?.displayName ?? '未设置' }} <el-button link type="primary" @click="fallbackId = selected.fallbackConfigId; fallbackDialog = true">设置</el-button></dd></template>
        </dl>
        <el-alert title="保存成功不等于可以调用；新版保存前会验证真实响应。更改参数、地址或密钥后需重新测试。" type="info" :closable="false" />
      </template>
      <div v-else class="mm-detail__empty"><h2>连接你的模型服务</h2><p>选择厂商、填写密钥，再选择或输入模型 ID。</p><el-button type="primary" @click="openForm('chat')">配置聊天模型</el-button></div>
      <section class="provider-catalog"><h3>服务商与模型目录</h3><p>预设核对：2026-10-27。点击「获取最新模型」可读取账户的实时列表；不提供列表的接口可手动输入 ID。厂商按其规则计费。</p>
        <div class="provider-grid"><button v-for="p in providers" :key="p.id" @click="openForm(p.protocol.startsWith('dashscope') ? 'embedding' : 'chat'); form.provider = p.id; chooseProvider()"><b>{{ p.label }}</b><small>{{ [...p.chatModels, ...p.embeddingModels].slice(0, 3).join(' · ') || '在线获取模型 / 输入模型 ID' }}</small></button></div>
      </section>
    </main>
    <el-dialog v-model="dialog" class="model-setup-dialog" :title="(editingId ? '编辑' : '添加') + labels[form.modelType]" width="680px" :close-on-click-modal="false" :close-on-press-escape="!saving" :show-close="!saving">
      <el-form label-position="top" @submit.prevent>
        <template v-if="form.modelType !== 'mineru'">
          <el-form-item label="1. 服务商 / 接入方式"><el-select v-model="form.provider" style="width:100%" :disabled="testing || saving" @change="chooseProvider"><el-option v-for="p in providerOptions" :key="p.id" :label="p.label" :value="p.id" /></el-select></el-form-item>
          <p class="setup-help">{{ provider?.hint }}</p>
          <el-form-item label="2. API Key"><el-input v-model="form.apiKey" type="password" show-password autocomplete="off" :disabled="testing || saving" placeholder="粘贴该服务商 / 区域的 API Key" /></el-form-item>
          <el-form-item label="3. 模型 ID（可搜索、选择或直接输入）"><el-autocomplete v-model="form.modelName" :fetch-suggestions="suggestModels" style="width:100%" :disabled="testing || saving" placeholder="输入厂商提供的精确模型 ID" /></el-form-item>
          <el-button :loading="discovering" :disabled="testing || saving || !['openai','anthropic'].includes(form.apiFormat)" @click="discover">获取最新模型</el-button>
          <p v-if="discoveryMessage" class="setup-help">{{ discoveryMessage }}</p>
          <p class="setup-help">模型 ID 区分大小写；显示名称不是模型 ID。Embedding 必须选择支持文本向量的模型。</p>
        </template>
        <template v-else><el-form-item label="MinerU Token"><el-input v-model="form.apiKey" type="password" show-password /></el-form-item><el-form-item label="模型"><el-input v-model="form.modelName" placeholder="vlm / pipeline" /></el-form-item></template>
        <el-form-item label="显示名称（选填）"><el-input v-model="form.displayName" placeholder="默认使用模型 ID" :disabled="testing || saving" /></el-form-item>
        <el-checkbox v-model="advanced">接口地址与高级设置</el-checkbox>
        <div v-if="advanced || form.provider === 'custom'" class="setup-advanced">
          <el-form-item v-if="form.modelType !== 'mineru'" label="协议"><el-select v-model="form.apiFormat" :disabled="testing || saving"><el-option v-for="p in protocols" :key="p" :label="protocolLabels[p]" :value="p" /></el-select></el-form-item>
          <el-form-item label="API Base URL / 完整端点"><el-input v-model="form.baseUrl" :disabled="testing || saving" placeholder="https://your-provider.example/v1" /></el-form-item>
          <p class="setup-help">OpenAI 的 /chat/completions、/embeddings 完整地址会自动规范化，避免重复拼接。仅在确认地址可信时填写密钥。</p>
          <el-form-item v-if="form.modelType === 'embedding'" label="请求向量维度（选填，留空使用模型默认并自动检测）"><el-input-number v-model="form.dimensions" :min="1" :max="16000" :disabled="testing || saving" /></el-form-item>
          <template v-if="form.modelType === 'chat'"><el-form-item label="Temperature（选填，默认由模型决定）"><el-input-number v-model="form.temperature" :min="0" :max="2" :step="0.1" :disabled="testing || saving" /></el-form-item><el-form-item label="最大输出 Token（选填）"><el-input-number v-model="form.maxTokens" :min="1" :disabled="testing || saving" /></el-form-item></template>
        </div>
        <p class="setup-help" v-if="!advanced && form.provider !== 'custom'">{{ protocolLabels[form.apiFormat] }} · {{ form.baseUrl }}</p>
        <el-checkbox v-model="activateAfterSave" :disabled="saving">保存后启用</el-checkbox>
        <p class="setup-help">测试会发送一条简短请求，按服务商规则计费。已有向量数据时，更换不同维度需先重建索引。</p>
      </el-form>
      <p v-if="formError" class="form-error" role="alert">{{ formError }}</p>
      <div v-if="testResult" class="test-msg" :class="{ok: testResult.ok, fail: !testResult.ok}" role="status">{{ testResult.message }}</div>
      <template #footer><el-button :disabled="testing || saving" @click="dialog = false">取消</el-button><el-button :loading="testing" :disabled="saving || discovering" @click="testConnection">测试连接</el-button><el-button type="primary" :loading="saving" :disabled="testing || discovering" @click="saveModel">验证并保存</el-button></template>
    </el-dialog>
    <el-dialog v-model="fallbackDialog" title="备用聊天模型" width="480px"><el-select v-model="fallbackId" clearable style="width:100%"><el-option v-for="c in fallbackOptions" :key="c.id" :label="c.displayName" :value="c.id" /></el-select><template #footer><el-button @click="saveFallback">保存</el-button></template></el-dialog>
  </div>
</template>
<style scoped>
.mm-page {
  display: flex;
  gap: 10px;
  height: calc(100vh - 80px);
  padding: 10px;
}

/* ── 左侧 ── */
.mm-side {
  width: 260px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid var(--border-default);
  border-radius: 22px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.mm-side__head {
  padding: 20px 18px 14px;
}

.mm-side__head h2 {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
  color: var(--text-primary);
}

.mm-side__head p {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--text-muted);
}

.mm-side__empty {
  padding: 20px 18px;
  font-size: 12px;
  color: var(--text-muted);
}

.mm-group {
  padding: 8px 10px 4px;
}

.mm-group__label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.mm-count {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: var(--text-muted);
}

.mm-sub-label {
  padding: 10px 10px 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.mm-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 2px 0;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-primary);
  transition: background 0.15s ease;
}

.mm-item:hover {
  background: var(--surface-muted);
}

.mm-item.is-active {
  background: rgba(74, 144, 217, 0.1);
  color: var(--brand-primary);
  font-weight: 600;
}

.mm-item--add {
  color: var(--text-secondary);
}

.mm-item--add:hover {
  color: var(--brand-primary);
}

.mm-item__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mm-item__badge {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-accent));
  padding: 2px 8px;
  border-radius: 100px;
}

/* ── 右侧 ── */
.mm-detail {
  flex: 1;
  min-width: 0;
  background: #fff;
  border: 1px solid var(--border-default);
  border-radius: 22px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  overflow-y: auto;
  padding: 18px;
}

.mm-detail__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border-default);
}

.mm-detail__title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.mm-detail__name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.mm-detail__model {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--text-muted);
}

.mm-detail__badge {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-accent));
  padding: 3px 10px;
  border-radius: 100px;
}

.mm-detail__actions {
  flex-shrink: 0;
}

.mm-fields {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px 0;
}

.mm-field {
  display: grid;
  grid-template-columns: 104px 1fr;
  gap: 12px;
  align-items: baseline;
}

.mm-field__label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.mm-field__value {
  font-size: 13.5px;
  color: var(--text-primary);
  word-break: break-all;
  display: flex;
  align-items: center;
  gap: 8px;
}

.mm-field__value--mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--text-secondary);
}

.mm-key-toggle {
  display: inline-flex;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px;
}

.mm-key-toggle:hover {
  color: var(--text-primary);
}

/* ── 可用模型表格 ── */
.mm-models {
  margin-top: 16px;
}

.mm-models__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.mm-models__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary);
}

.mm-models__filter-hint {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-muted);
}

.mm-model-name {
  font-weight: 600;
  color: var(--text-primary);
}

.mm-model-tag {
  margin-left: 8px;
  padding: 1px 7px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  background: var(--surface-muted);
  border-radius: 100px;
}

.mm-model-raw {
  margin-left: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--text-muted);
}

.mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
}

.mm-detail__empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.mm-detail__empty-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.mm-detail__empty-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.mm-hint {
  margin: 0 0 12px 110px;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

.mm-fallback-none {
  color: var(--text-muted);
}

.form-error {
  margin: 0 0 10px 110px;
  font-size: 12px;
  color: #dc2626;
}

.test-msg {
  margin: 0 0 10px 110px;
  font-size: 12px;
}

.test-msg.ok {
  color: #16a34a;
}

.test-msg.fail {
  color: #dc2626;
}

.mm-item { width: 100%; border: 0; text-align: left; background: transparent; }
.setup-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.setup-details { display: grid; grid-template-columns: 100px minmax(0,1fr); gap: 16px; padding: 24px 0; }
.setup-details dt { color: #64748b; font-size: 13px; }
.setup-details dd { margin: 0; overflow-wrap: anywhere; font-size: 14px; }
.mm-detail, .setup-details dd, .mm-detail h2, .provider-catalog h3 { color: #1e293b; }
.setup-help { font-size: 12px; line-height: 1.7; color: #64748b; overflow-wrap: anywhere; }
.setup-advanced { padding: 16px; margin: 16px 0; background: #f8fafc; border-radius: 10px; }
.provider-catalog { margin-top: 32px; border-top: 1px solid #e2e8f0; padding-top: 24px; }
.provider-catalog p { color: #64748b; font-size: 13px; line-height: 1.7; }
.provider-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(230px,1fr)); gap: 12px; }
.provider-grid button { text-align: left; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; color: #1e293b; }
.provider-grid small { display: block; margin-top: 8px; color: #64748b; overflow-wrap: anywhere; }
:global(.model-setup-dialog .el-dialog__body) { max-height: 65vh; overflow-y: auto; padding-right: 8px; }
</style>
