<template>
  <div class="relative">
    <button
      type="button"
      class="input-premium text-right w-full flex items-center justify-between"
      :class="{ 'cursor-not-allowed opacity-50': disabled }"
      :disabled="disabled"
      @click="!disabled && (open = !open)"
    >
      <span :class="selectedLabel ? 'text-navy-800' : 'text-navy-400'">{{ selectedLabel || placeholder }}</span>
      <svg class="w-4 h-4 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
    </button>

    <input v-if="required && !modelValue" type="hidden" required :value="modelValue" />

    <div v-if="open" class="absolute z-30 mt-1 w-full card-premium overflow-hidden">
      <div class="p-2 border-b border-ivory-300/60 relative">
        <input
          ref="searchInput"
          v-model="search"
          type="text"
          class="input-premium pr-9 text-sm"
          placeholder="البحث عن مستأجر..."
          @input="onSearchInput"
        />
        <svg class="absolute left-5 top-1/2 -translate-y-1/2 w-4 h-4 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
      </div>

      <div class="max-h-64 overflow-y-auto">
        <div v-if="searching" class="px-4 py-3 text-sm text-navy-400 inline-flex items-center gap-2">
          <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
          جاري البحث...
        </div>
        <div v-else-if="!results.length" class="px-4 py-3 text-sm text-navy-400">لا توجد نتائج</div>
        <button
          v-for="item in results"
          :key="item.name"
          type="button"
          class="w-full text-right px-4 py-2.5 hover:bg-gold-50/50 transition-colors border-b border-ivory-300/40 last:border-0"
          @mousedown.prevent="selectItem(item)"
        >
          <p class="text-sm font-medium text-navy-800">{{ item.full_name || item.name }}</p>
        </button>
      </div>
    </div>

    <button
      v-if="modelValue && clearable"
      class="absolute left-2 top-1/2 -translate-y-1/2 text-navy-400 hover:text-navy-700"
      @click="clear"
    >✕</button>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { callApi, extractError } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'

const props = defineProps({
  modelValue: { type: String, default: '' },
  valueLabel: { type: String, default: '' },
  placeholder: { type: String, default: 'اختر المستأجر' },
  disabled: { type: Boolean, default: false },
  required: { type: Boolean, default: false },
  includeInactive: { type: Boolean, default: false },
  clearable: { type: Boolean, default: true },
})
const emit = defineEmits(['update:modelValue', 'select'])

const toast = useToast()
const open = ref(false)
const search = ref('')
const results = ref([])
const searching = ref(false)
const selectedLabel = ref('')
const searchInput = ref(null)
let debounceTimer = null

watch(open, async (v) => {
  if (v) {
    // Fetch on open with empty search
    search.value = ''
    results.value = []
    await fetchTenants('')
    await nextTick()
    searchInput.value?.focus()
  }
})

watch(() => props.modelValue, async (v) => {
  if (!v) {
    selectedLabel.value = ''
  } else if (props.valueLabel) {
    // Honor explicit label from parent (source: valueLabel || value)
    selectedLabel.value = props.valueLabel
  } else if (!selectedLabel.value) {
    // Resolve label for pre-selected value
    try {
      const res = await callApi('rental.rental.api.tenant.get_tenants', { search: '', simple: 1, include_inactive: props.includeInactive ? 1 : 0, limit: 100 })
      const list = Array.isArray(res) ? res : (res.tenants || [])
      const found = list.find(t => t.name === v)
      if (found) selectedLabel.value = found.full_name
    } catch { /* ignore */ }
  }
})

watch(() => props.valueLabel, (v) => {
  if (props.modelValue && v) selectedLabel.value = v
})

function onSearchInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => fetchTenants(search.value), 300)
}

async function fetchTenants(query) {
  searching.value = true
  try {
    const res = await callApi('rental.rental.api.tenant.get_tenants', {
      search: query || undefined,
      simple: 1,
      include_inactive: props.includeInactive ? 1 : 0,
      limit: 20,
    })
    results.value = Array.isArray(res) ? res : (res.tenants || [])
  } catch (e) {
    toast.error(extractError(e))
  } finally {
    searching.value = false
  }
}

function selectItem(item) {
  selectedLabel.value = item.full_name || item.name
  open.value = false
  emit('update:modelValue', item.name)
  emit('select', item)
}

function clear() {
  selectedLabel.value = ''
  emit('update:modelValue', '')
  emit('select', null)
}
</script>
