import { defineStore } from 'pinia'

const STORAGE_KEY = 'skyper_theme'

interface ThemeState {
  backgroundImage: string | null
  accent: 'cyan' | 'violet' | 'lime'
  dim: number
}

const defaults: ThemeState = { backgroundImage: null, accent: 'cyan', dim: 0.32 }

function readTheme(): ThemeState {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null')
    return { ...defaults, ...(value ?? {}) }
  } catch {
    return { ...defaults }
  }
}

export const useThemeStore = defineStore('theme', {
  state: (): ThemeState => readTheme(),
  actions: {
    persist() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.$state))
      this.apply()
    },
    setBackground(image: string | null) {
      this.backgroundImage = image
      this.persist()
    },
    setAccent(accent: ThemeState['accent']) {
      this.accent = accent
      this.persist()
    },
    setDim(dim: number) {
      this.dim = Math.min(0.75, Math.max(0.08, dim))
      this.persist()
    },
    apply() {
      const root = document.documentElement
      root.style.setProperty('--skyper-accent', this.accent === 'violet' ? '#a78bfa' : this.accent === 'lime' ? '#b7f36b' : '#67e8f9')
      root.style.setProperty('--skyper-bg-image', this.backgroundImage ? `url(${this.backgroundImage})` : 'none')
      root.style.setProperty('--skyper-bg-dim', String(this.dim))
    },
  },
})

