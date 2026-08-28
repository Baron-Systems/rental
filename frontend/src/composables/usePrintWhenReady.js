/**
 * usePrintWhenReady composable
 *
 * Source: TENANTS_MIGRATION_SPEC §41
 * Provides a helper to open a print window with HTML content and trigger window.print().
 */

import { useToast } from './useToast'

export function usePrintWhenReady() {
  const toast = useToast()

  function openPrintWindow(htmlContent, options = {}) {
    const width = options.width || 900
    const height = options.height || 700
    const w = window.open('', '_blank', `width=${width},height=${height}`)
    if (!w) {
      toast.error('يرجى السماح بالنوافذ المنبثقة للطباعة')
      return null
    }
    w.document.write(htmlContent)
    w.document.close()
    return w
  }

  function printHtml(htmlContent, options = {}) {
    const w = openPrintWindow(htmlContent, options)
    if (w) {
      // Auto-trigger print after content is written
      w.onload = () => {
        w.focus()
        w.print()
      }
    }
    return w
  }

  return {
    openPrintWindow,
    printHtml,
  }
}
