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
    if (opts.autoToast) console.error(`API ${method} failed:`, err)
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
 *
 * ``frappeRequest`` (from frappe-ui) parses Frappe's ``_server_messages``
 * string into an ``err.messages`` array of already-extracted message strings.
 * It does NOT set ``err._server_messages`` on the Error object, so we must
 * check ``err.messages`` first (matching the old program's behaviour where
 * ``data.error`` contained the user-facing Arabic message directly).
 */
export function extractError(err) {
  if (!err) return 'حدث خطأ غير متوقع'
  if (typeof err === 'string') return cleanError(err)

  let raw = null

  // frappeRequest sets `err.messages` (array of parsed message strings)
  if (err.messages && Array.isArray(err.messages) && err.messages.length) {
    raw = err.messages[0]
  }

  if (!raw && err._server_messages && Array.isArray(err._server_messages) && err._server_messages.length) {
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
// Source: utils.ts:53-66 formatCurrency — exact match
export function formatMoney(amount, currency = 'ILS') {
  if (amount === null || amount === undefined) return '-'
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  if (isNaN(num)) return '-'
  const formatted = num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  // Source: utils.ts:30-35 currencySymbols — exact match, no extra currencies
  const symbols = { ILS: '₪', USD: '$', EUR: '€', JOD: 'JD' }
  const sym = symbols[currency] || ''
  return `${formatted} ${sym}`
}

/**
 * Format a date string (YYYY-MM-DD) to DD/MM/YYYY.
 */
// Source: utils.ts:68-76 formatDate — returns '-' for falsy, DD/MM/YYYY format
export function formatDate(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = d.getFullYear()
  return `${day}/${month}/${year}`
}
