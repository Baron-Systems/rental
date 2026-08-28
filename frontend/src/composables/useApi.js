import { frappeRequest } from 'frappe-ui'

/**
 * Call a whitelisted rental API method.
 * @param {string} method - e.g. 'rental.rental.api.tenant.get_tenants'
 * @param {object} params
 * @param {object} options - { method: 'POST'|'GET', autoToast: true }
 */
export async function callApi(method, params = {}, options = {}) {
  const opts = { method: 'POST', autoToast: true, ...options }
  try {
    const res = await frappeRequest({
      url: `/api/method/${method}`,
      method: opts.method,
      params,
    })
    // Frappe returns { message: ... } for whitelisted methods
    return res?.message !== undefined ? res.message : res
  } catch (err) {
    const msg = err?.message || err?._server_messages?.[0] || 'حدث خطأ غير متوقع'
    if (opts.autoToast) console.error(`API ${method} failed:`, msg)
    throw err
  }
}

/**
 * Clean raw error text by removing API paths and technical exception names.
 */
function cleanError(raw) {
  if (!raw) return 'حدث خطأ غير متوقع'
  let s = String(raw)

  // Remove API method paths like /api/method/rental.rental.api.receipt.create_receipt
  s = s.replace(/\/api\/method\/[\w.]+/g, '')

  // Remove common Frappe exception class names
  const exceptions = [
    'ValidationError', 'DoesNotExistError', 'PermissionError',
    'AuthenticationError', 'AuthorizationError', 'NotImplementedError',
    'DuplicateEntryError', 'LinkExistsError', 'MandatoryError',
    'CancelledError', 'TimestampMismatchError', 'ImportError',
    'IntegrityError', 'AttributeError', 'TypeError', 'ValueError',
    'FrappeException',
  ]
  s = s.replace(new RegExp('\\b(' + exceptions.join('|') + ')\\b', 'g'), '')

  // Normalize whitespace and leading/trailing punctuation
  s = s.replace(/\s+/g, ' ').replace(/^[\s:.,;\-—–]+|[\s:.,;\-—–]+$/g, '').trim()
  if (!s) return 'حدث خطأ غير متوقع'
  return s
}

/**
 * Extract a user-friendly Arabic error message from a Frappe error.
 */
export function extractError(err) {
  if (!err) return 'حدث خطأ غير متوقع'
  if (typeof err === 'string') return cleanError(err)

  let raw = null

  // Frappe sends user-facing messages in _server_messages first
  if (err._server_messages && Array.isArray(err._server_messages) && err._server_messages.length) {
    try {
      const first = JSON.parse(err._server_messages[0])
      raw = first.message || first
    } catch {
      raw = err._server_messages[0]
    }
  }
  if (!raw && err._error_message) raw = err._error_message
  if (!raw && err.message) raw = err.message

  return cleanError(raw)
}

/**
 * Format a number as currency with the given symbol (default ILS ₪).
 */
export function formatMoney(amount, currency = 'ILS') {
  if (amount === null || amount === undefined) return '—'
  const num = Number(amount) || 0
  const formatted = num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  const symbols = { ILS: '₪', USD: '$', EUR: '€', JOD: 'د.أ', SAR: 'ر.س', AED: 'د.إ' }
  const sym = symbols[currency] || currency
  return `${formatted} ${sym}`
}

/**
 * Format a date string (YYYY-MM-DD) to DD/MM/YYYY.
 */
export function formatDate(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = d.getFullYear()
  return `${day}/${month}/${year}`
}
