/**
 * format utilities (RTL / Arabic)
 *
 * Source: TENANTS_MIGRATION_SPEC §41
 * Currency and date formatting helpers for the Vue SPA.
 */

/**
 * Format a money amount as "X,XXX.XX SYMBOL" (RTL).
 * @param {number|string} amount
 * @param {string} currency - currency code/symbol (default 'ILS')
 * @returns {string}
 */
export function formatMoney(amount, currency = 'ILS') {
  if (amount === null || amount === undefined || amount === '') return '—'
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  if (isNaN(num)) return '—'
  const formatted = num.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  return `${formatted} ${currency}`
}

/**
 * Format a date as DD/MM/YYYY.
 * @param {string|Date} date
 * @returns {string}
 */
export function formatDate(date) {
  if (!date) return '—'
  const d = typeof date === 'string' ? new Date(date) : date
  if (isNaN(d.getTime())) return '—'
  const day = String(d.getDate()).padStart(2, '0')
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const year = d.getFullYear()
  return `${day}/${month}/${year}`
}
