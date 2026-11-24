<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useThemeStore } from '@/stores/theme'

const theme = useThemeStore()
const fileInput = ref<HTMLInputElement | null>(null)

function chooseImage() {
  fileInput.value?.click()
}

function handleImage(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('请选择图片文件')
    return
  }
  if (file.size > 4 * 1024 * 1024) {
    ElMessage.warning('图片请控制在 4MB 以内')
    return
  }
  const reader = new FileReader()
  reader.onload = () => theme.setBackground(String(reader.result))
  reader.readAsDataURL(file)
  input.value = ''
}

function clearImage() {
  theme.setBackground(null)
}
function updateDim(event: Event) {
  theme.setDim(Number((event.target as HTMLInputElement).value))
}
</script>

<template>
  <section class="theme-panel">
    <div class="theme-panel__head">
      <div>
        <span class="eyebrow">个性化工作台</span>
        <h3>把工作台变成你的空间</h3>
      </div>
      <span class="theme-panel__status"><i /> 本地保存</span>
    </div>
    <p class="theme-panel__copy">
      上传一张图片作为背景。图片只保存在当前浏览器，不会上传到服务器。
    </p>
    <div class="theme-swatches">
      <button
        class="swatch swatch--cyan"
        :class="{ active: theme.accent === 'cyan' }"
        title="澄蓝"
        aria-label="澄蓝主题"
        :aria-pressed="theme.accent === 'cyan'"
        @click="theme.setAccent('cyan')"
      />
      <button
        class="swatch swatch--violet"
        :class="{ active: theme.accent === 'violet' }"
        title="雅紫"
        aria-label="雅紫主题"
        :aria-pressed="theme.accent === 'violet'"
        @click="theme.setAccent('violet')"
      />
      <button
        class="swatch swatch--lime"
        :class="{ active: theme.accent === 'lime' }"
        title="松绿"
        aria-label="松绿主题"
        :aria-pressed="theme.accent === 'lime'"
        @click="theme.setAccent('lime')"
      />
      <button class="theme-action" @click="chooseImage">上传背景</button>
      <button
        v-if="theme.backgroundImage"
        class="theme-action theme-action--quiet"
        @click="clearImage"
      >
        移除图片
      </button>
    </div>
    <label class="dim-control"
      ><span>浅色遮罩强度</span
      ><input :value="theme.dim" type="range" min="0.08" max="0.75" step="0.01" @input="updateDim"
    /></label>
    <input ref="fileInput" type="file" accept="image/*" hidden @change="handleImage" />
  </section>
</template>
