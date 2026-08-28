/**
 * useTenant composable
 *
 * Source: TENANTS_MIGRATION_SPEC §41
 * Fetches a single tenant with balance and statement.
 */

import { ref } from 'vue'
import { callApi, extractError } from './useApi'
import { useToast } from './useToast'

export function useTenant() {
  const toast = useToast()

  const tenant = ref(null)
  const statement = ref(null)
  const loading = ref(false)
  const statementLoading = ref(false)

  async function fetchTenant(id) {
    loading.value = true
    try {
      tenant.value = await callApi('rental.rental.api.tenant.get_tenant', { name: id })
      statement.value = tenant.value.statement
      return tenant.value
    } catch (e) {
      toast.error(extractError(e))
      return null
    } finally {
      loading.value = false
    }
  }

  async function fetchStatement(id, { contract, page = 1, print: printMode = false } = {}) {
    statementLoading.value = true
    try {
      statement.value = await callApi('rental.rental.api.tenant.get_tenant_statement_api', {
        name: id,
        contract: contract || undefined,
        page,
        print: printMode ? 1 : undefined,
      })
      return statement.value
    } catch (e) {
      toast.error(extractError(e))
      return null
    } finally {
      statementLoading.value = false
    }
  }

  return {
    tenant,
    statement,
    loading,
    statementLoading,
    fetchTenant,
    fetchStatement,
  }
}
