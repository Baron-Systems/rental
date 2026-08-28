import { reactive } from 'vue'

const state = reactive({
  toasts: [],
})

let idCounter = 0

function push(message, type = 'info', duration = 4500) {
  const id = ++idCounter
  state.toasts.push({ id, message, type })
  if (duration > 0) {
    setTimeout(() => dismiss(id), duration)
  }
  return id
}

function dismiss(id) {
  const idx = state.toasts.findIndex(t => t.id === id)
  if (idx >= 0) state.toasts.splice(idx, 1)
}

export function useToast() {
  return {
    state,
    success: (msg, dur) => push(msg, 'success', dur),
    error: (msg, dur) => push(msg, 'error', dur ?? 6000),
    info: (msg, dur) => push(msg, 'info', dur),
    warning: (msg, dur) => push(msg, 'warning', dur),
    dismiss,
  }
}
