import { reactive, computed } from 'vue'
import { frappeRequest } from 'frappe-ui'

const state = reactive({
  user: null,
  account: null,
  loading: true,
  initialized: false,
})

export function useSession() {
  const isLoggedIn = computed(() => !!state.user)
  const isSystemAdmin = computed(() => state.account?.is_system_admin === true)
  const needsSetup = computed(() => isLoggedIn.value && state.account && !state.account.setup_completed && !isSystemAdmin.value)
  const isReady = computed(() => isLoggedIn.value && state.account && (state.account.setup_completed || isSystemAdmin.value))

  async function init() {
    state.loading = true
    try {
      const res = await frappeRequest({
        url: '/api/method/frappe.auth.get_logged_user',
      })
      state.user = res
      await fetchAccount()
    } catch {
      state.user = null
      state.account = null
    } finally {
      state.loading = false
      state.initialized = true
    }
  }

  async function fetchAccount() {
    if (!state.user) {
      state.account = null
      return
    }
    try {
      const res = await frappeRequest({
        url: '/api/method/rental.rental.api.account.get_current_account',
      })
      state.account = res
    } catch {
      state.account = null
    }
  }

  async function login(email, password) {
    const res = await frappeRequest({
      url: '/api/method/login',
      method: 'POST',
      params: { usr: email, pwd: password },
    })
    // Frappe returns "Logged In" for System Users and "No App" for Website Users.
    // frappeRequest throws on failure, so any truthy response means login succeeded.
    const msg = typeof res === 'string' ? res : res?.message
    if (msg === 'Logged In' || msg === 'No App') {
      state.user = email
      await fetchAccount()
      return true
    }
    return false
  }

  async function logout() {
    await frappeRequest({
      url: '/api/method/logout',
      method: 'POST',
    })
    state.user = null
    state.account = null
  }

  async function getSetup() {
    const res = await frappeRequest({
      url: '/api/method/rental.rental.api.setup.get_setup',
    })
    return res?.message !== undefined ? res.message : res
  }

  async function completeSetup(setupData) {
    const res = await frappeRequest({
      url: '/api/method/rental.rental.api.setup.complete_setup',
      method: 'POST',
      params: setupData,
    })
    await fetchAccount()
    return res?.message !== undefined ? res.message : res
  }

  return {
    state,
    isLoggedIn,
    isSystemAdmin,
    needsSetup,
    isReady,
    init,
    fetchAccount,
    login,
    logout,
    getSetup,
    completeSetup,
  }
}
