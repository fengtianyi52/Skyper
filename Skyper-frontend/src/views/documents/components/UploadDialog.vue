<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { uploadDocument } from '@/api/document'
import { extractApiError } from '@/api/http'

const props = defineProps<{ visible: boolean; groupId: number | null; groupLabel: string }>()
const emit = defineEmits<{ 'update:visible': [val: boolean]; uploaded: [] }>()
type UploadState = 'queued' | 'uploading' | 'success' | 'duplicate' | 'error' | 'invalid'
interface UploadItem {
  id: number
  file: File
  state: UploadState
  progress: number
  error: string
}
const MAX_FILE_SIZE = 30 * 1024 * 1024
const allowedExts = [
  '.txt',
  '.md',
  '.pdf',
  '.doc',
  '.docx',
  '.ppt',
  '.pptx',
  '.xls',
  '.xlsx',
  '.png',
  '.jpg',
  '.jpeg',
  '.webp',
  '.bmp',
]
const items = ref<UploadItem[]>([])
const loading = ref(false)
const dragging = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
let nextId = 0
const queued = computed(() => items.value.filter((item) => item.state === 'queued'))
const failed = computed(() => items.value.filter((item) => item.state === 'error'))
const invalidCount = computed(() => items.value.filter((item) => item.state === 'invalid').length)
const successCount = computed(() => items.value.filter((item) => item.state === 'success').length)
const duplicateCount = computed(
  () => items.value.filter((item) => item.state === 'duplicate').length,
)
const totalSize = computed(() => items.value.reduce((total, item) => total + item.file.size, 0))
const labels: Record<UploadState, string> = {
  queued: '等待上传',
  uploading: '上传中',
  success: '上传成功',
  duplicate: '文件已存在',
  error: '上传失败',
  invalid: '无法上传',
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      items.value = []
      dragging.value = false
      nextTick(() => fileInputRef.value?.click())
    }
  },
)

function validateFile(file: File): string {
  if (file.size > MAX_FILE_SIZE)
    return '单个文件不能超过 30 MB（31,457,280 字节），请压缩或拆分后重新选择。'
  if (file.size === 0) return '不能上传空文件，请检查文件内容。'
  const ext = file.name.includes('.') ? '.' + file.name.split('.').pop()?.toLowerCase() : ''
  if (!allowedExts.includes(ext)) return `不支持的文件类型；支持 ${allowedExts.join('、')}`
  return ''
}

function addFiles(files: FileList | File[]) {
  if (loading.value) return
  for (const file of Array.from(files)) {
    if (
      items.value.some(
        (item) =>
          item.file.name === file.name &&
          item.file.size === file.size &&
          item.file.lastModified === file.lastModified,
      )
    )
      continue
    const error = validateFile(file)
    items.value.push({
      id: ++nextId,
      file,
      state: error ? 'invalid' : 'queued',
      progress: 0,
      error,
    })
  }
}

function onFilePicked(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files) addFiles(input.files)
  input.value = ''
}

function onDrop(event: DragEvent) {
  dragging.value = false
  if (event.dataTransfer?.files) addFiles(event.dataTransfer.files)
}

function pickFiles() {
  if (!loading.value) fileInputRef.value?.click()
}

function removeItem(id: number) {
  if (!loading.value) items.value = items.value.filter((item) => item.id !== id)
}

async function uploadItems(batch: UploadItem[]) {
  if (loading.value || props.groupId === null || !batch.length) return
  const groupId = props.groupId
  loading.value = true
  let changed = false
  try {
    // One request/transaction per file keeps memory bounded and failures independent.
    for (const item of batch) {
      item.state = 'uploading'
      item.progress = 0
      item.error = ''
      try {
        const result = await uploadDocument({
          groupId,
          file: item.file,
          onProgress: (loaded, total) => {
            if (total) item.progress = Math.min(100, Math.round((loaded / total) * 100))
          },
        })
        item.state = result.isDuplicate ? 'duplicate' : 'success'
        item.progress = 100
        changed = true
      } catch (error) {
        item.state = 'error'
        item.error = extractApiError(error, '上传失败，请重试；若持续失败，请查看后端日志。')
      }
    }
  } finally {
    loading.value = false
    if (changed) emit('uploaded')
  }
}

function close() {
  if (!loading.value) emit('update:visible', false)
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    :close-on-click-modal="false"
    :close-on-press-escape="!loading"
    :show-close="!loading"
    width="min(680px, 94vw)"
    top="7vh"
    @update:model-value="
      (value: boolean) => {
        if (!value) close()
      }
    "
  >
    <template #header>
      <span class="upload-dialog__eyebrow">上传文档</span>
      <h2 class="upload-dialog__title">批量上传文档</h2>
    </template>
    <div class="upload-dialog">
      <p class="upload-dialog__group">
        目标群组：<strong>{{ groupLabel }}</strong>
      </p>
      <div
        class="upload-dialog__zone"
        :class="{ 'is-dragging': dragging, 'is-disabled': loading }"
        role="button"
        :tabindex="loading ? -1 : 0"
        :aria-disabled="loading"
        aria-label="选择多个文件或拖拽文件"
        @click="pickFiles"
        @keydown.enter.prevent="pickFiles"
        @keydown.space.prevent="pickFiles"
        @drop.prevent="onDrop"
        @dragover.prevent="dragging = !loading"
        @dragleave.prevent="dragging = false"
      >
        <svg
          width="30"
          height="30"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <path d="M12 3v12" />
        </svg>
        <strong>{{ items.length ? '继续添加文件' : '点击选择多个文件，或拖拽到这里' }}</strong>
        <span>支持 TXT · MD · PDF · Word · PPT · Excel · 图片</span>
        <span>每个文件不超过 30 MB，支持一次选择多个文件</span>
      </div>
      <input
        ref="fileInputRef"
        type="file"
        multiple
        :accept="allowedExts.join(',')"
        :disabled="loading"
        class="upload-dialog__file-input"
        @change="onFilePicked"
      />
      <template v-if="items.length">
        <div class="upload-dialog__summary">
          <span>已选择 {{ items.length }} 个文件 · 共 {{ formatSize(totalSize) }}</span
          ><button
            type="button"
            class="upload-dialog__link"
            :disabled="loading"
            @click="items = []"
          >
            清空列表
          </button>
        </div>
        <ul class="upload-dialog__files" aria-label="文件上传队列">
          <li
            v-for="item in items"
            :key="item.id"
            class="upload-dialog__file"
            :class="'is-' + item.state"
          >
            <div class="upload-dialog__file-heading">
              <span class="upload-dialog__file-name" :title="item.file.name">{{
                item.file.name
              }}</span
              ><span class="upload-dialog__file-size">{{ formatSize(item.file.size) }}</span>
              <button
                v-if="!loading && !['success', 'duplicate'].includes(item.state)"
                type="button"
                class="upload-dialog__link"
                :aria-label="'移除 ' + item.file.name"
                @click="removeItem(item.id)"
              >
                移除
              </button>
            </div>
            <div class="upload-dialog__file-status">
              <span
                >{{ labels[item.state]
                }}{{
                  item.state === 'uploading'
                    ? item.progress === 100
                      ? ' · 等待服务器确认'
                      : ` · ${item.progress}%`
                    : ''
                }}</span
              >
              <button
                v-if="item.state === 'error'"
                type="button"
                class="upload-dialog__link"
                :disabled="loading"
                :aria-label="'重试 ' + item.file.name"
                @click="uploadItems([item])"
              >
                重试
              </button>
            </div>
            <div
              v-if="item.state === 'uploading'"
              class="upload-dialog__track"
              role="progressbar"
              :aria-label="item.file.name + ' 上传进度'"
              :aria-valuenow="item.progress"
              :aria-valuemin="0"
              :aria-valuemax="100"
            >
              <div :style="{ width: item.progress + '%' }" />
            </div>
            <p v-if="item.error" class="upload-dialog__error">{{ item.error }}</p>
          </li>
        </ul>
        <p class="upload-dialog__result" role="status">
          成功 {{ successCount }} · 已存在 {{ duplicateCount }} · 上传失败 {{ failed.length }} ·
          无效 {{ invalidCount }} · 待上传 {{ queued.length }}
        </p>
        <p class="upload-dialog__hint">
          上传成功后后台会继续解析；解析与向量化结果请在文档列表查看。失败文件不会中断其他文件上传。
        </p>
      </template>
      <p v-if="groupId === null" class="upload-dialog__error">请先选择目标群组。</p>
      <div class="upload-dialog__actions">
        <button
          type="button"
          class="upload-dialog__btn upload-dialog__btn--primary"
          :disabled="loading || !queued.length || groupId === null"
          @click="uploadItems([...queued])"
        >
          {{ loading ? '上传中…' : `开始上传${queued.length ? `（${queued.length}）` : ''}` }}
        </button>
        <button
          v-if="failed.length"
          type="button"
          class="upload-dialog__btn"
          :disabled="loading || groupId === null"
          @click="uploadItems([...failed])"
        >
          重试失败（{{ failed.length }}）
        </button>
        <button type="button" class="upload-dialog__btn" :disabled="loading" @click="close">
          关闭
        </button>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
.upload-dialog {
  display: flex;
  flex-direction: column;
  gap: 14px;
  color: var(--text-primary);
}
.upload-dialog__eyebrow {
  color: var(--brand-primary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
}
.upload-dialog__title {
  margin: 6px 0 0;
  color: var(--text-primary);
  font-size: 23px;
}
.upload-dialog__group {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
}
.upload-dialog__group strong {
  color: var(--text-primary);
}
.upload-dialog__zone {
  display: flex;
  align-items: center;
  flex-direction: column;
  gap: 10px;
  padding: 22px 12px;
  border: 1px dashed var(--border-default);
  border-radius: 12px;
  cursor: pointer;
  color: var(--text-secondary);
  background: var(--surface-white);
  transition:
    border-color 0.2s,
    background 0.2s;
  text-align: center;
}
.upload-dialog__zone strong {
  color: var(--text-primary);
  font-size: 15px;
}
.upload-dialog__zone span {
  font-size: 12px;
}
.upload-dialog__zone svg {
  color: var(--brand-primary);
}
.upload-dialog__zone:hover,
.upload-dialog__zone:focus-visible,
.upload-dialog__zone.is-dragging {
  border-color: var(--brand-primary);
  background: var(--surface-accent);
}
.upload-dialog__zone.is-disabled {
  opacity: 0.6;
  cursor: wait;
}
.upload-dialog__file-input {
  display: none;
}
.upload-dialog__summary,
.upload-dialog__file-heading,
.upload-dialog__file-status {
  display: flex;
  align-items: center;
  gap: 12px;
}
.upload-dialog__summary {
  justify-content: space-between;
  color: var(--text-secondary);
  font-size: 12px;
}
.upload-dialog__files {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 32vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.upload-dialog__file {
  padding: 12px;
  border: 1.5px solid var(--border-default);
  border-radius: 9px;
}
.upload-dialog__file-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
  font-size: 13px;
}
.upload-dialog__file-size {
  white-space: nowrap;
  color: var(--text-secondary);
  font-size: 12px;
}
.upload-dialog__file-status {
  margin-top: 7px;
  justify-content: space-between;
  color: var(--text-secondary);
  font-size: 12px;
}
.is-success .upload-dialog__file-status,
.is-duplicate .upload-dialog__file-status {
  color: var(--success, #16a34a);
}
.is-error .upload-dialog__file-status,
.is-invalid .upload-dialog__file-status,
.upload-dialog__error {
  color: var(--danger, #dc2626);
}
.upload-dialog__error {
  margin: 7px 0 0;
  font-size: 12px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}
.upload-dialog__track {
  margin-top: 8px;
  height: 4px;
  border-radius: 3px;
  background: var(--border-default);
  overflow: hidden;
}
.upload-dialog__track > div {
  height: 100%;
  background: var(--brand-primary);
  transition: width 0.2s;
}
.upload-dialog__result {
  margin: 0;
  font-size: 12px;
  line-height: 1.7;
}
.upload-dialog__hint {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
}
.upload-dialog__link {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--brand-primary);
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
}
.upload-dialog__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
  padding-top: 5px;
}
.upload-dialog__btn {
  border: 1.5px solid var(--border-default);
  border-radius: 8px;
  padding: 10px 16px;
  background: var(--surface-white);
  color: var(--text-primary);
  cursor: pointer;
  font-weight: 600;
}
.upload-dialog__btn--primary {
  background: var(--brand-primary);
  border-color: var(--brand-primary);
  color: white;
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
