import { reactive } from 'vue'

const state = reactive({
  open: false,
  title: '',
  message: '',
  variant: 'warning',
  confirmLabel: '',
  resolve: null,
  // Prompt state
  promptOpen: false,
  promptTitle: '',
  promptMessage: '',
  promptInputLabel: '',
  promptVariant: 'warning',
  promptValue: '',
  promptResolve: null,
})

export function useConfirm() {
  function confirm(options = {}) {
    return new Promise((resolve) => {
      state.open = true
      state.title = options.title || 'تأكيد'
      state.message = options.message || 'هل أنت متأكد؟'
      state.variant = options.variant || 'warning'
      state.confirmLabel = options.confirmLabel || ''
      state.resolve = resolve
    })
  }

  function resolveConfirm(value) {
    state.open = false
    if (state.resolve) {
      state.resolve(value)
      state.resolve = null
    }
  }

  function prompt(options = {}) {
    return new Promise((resolve) => {
      state.promptOpen = true
      state.promptTitle = options.title || 'إدخال'
      state.promptMessage = options.message || ''
      state.promptInputLabel = options.inputLabel || ''
      state.promptVariant = options.variant || 'warning'
      state.promptValue = ''
      state.promptResolve = resolve
    })
  }

  function resolvePrompt(value) {
    state.promptOpen = false
    if (state.promptResolve) {
      state.promptResolve(value)
      state.promptResolve = null
    }
  }

  return { state, confirm, resolveConfirm, prompt, resolvePrompt }
}

export const confirmState = state
