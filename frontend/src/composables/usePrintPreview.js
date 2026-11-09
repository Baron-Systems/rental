/**
 * usePrintPreview — in-app print preview overlay (replaces window.open print popups).
 *
 * Callers pass a full HTML document string; <PrintPreview /> (mounted once in App.vue)
 * renders it in an iframe over the current page with a print button and an X to close,
 * so printing never navigates away from the app (important in the installed PWA).
 */
import { reactive } from 'vue'

const state = reactive({ html: '', title: '' })

export function usePrintPreview() {
  function show(html, title = 'معاينة الطباعة') {
    state.title = title
    state.html = html
  }
  function close() {
    state.html = ''
  }
  return { state, show, close }
}
