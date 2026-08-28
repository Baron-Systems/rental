<template>
  <!-- Preview mode: read-only display -->
  <span v-if="preview" class="inline px-1 font-semibold text-navy-900" :class="className">
    <template v-if="type === 'select' && options">
      {{ selectedOptionLabel || value || placeholderFallback }}
    </template>
    <template v-else>
      {{ value || placeholderFallback }}
    </template>
  </span>

  <!-- Select dropdown -->
  <span
    v-else-if="type === 'select' && options"
    ref="dropdownRef"
    class="relative inline-block"
    :class="className"
    :style="{ minWidth: width || '120px' }"
  >
    <button
      type="button"
      :dir="dir"
      class="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-sm transition-all border border-dashed border-ivory-400 bg-ivory-100/80 hover:bg-gold-50/60 hover:border-gold-500"
      :class="[
        error ? 'border-red-400 bg-red-50/50' : '',
        readOnly ? 'cursor-default opacity-70' : 'cursor-text',
        inputClassName,
      ]"
      @click="toggleDropdown"
    >
      <span :class="!value ? 'text-navy-400 italic' : ''">{{ selectedOptionLabel || value || placeholder }}</span>
      <svg v-if="!readOnly" class="w-3 h-3 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
      </svg>
    </button>
    <div
      v-if="showDropdown && !readOnly"
      class="absolute z-50 mt-1 max-h-48 min-w-full overflow-auto rounded-lg border border-ivory-300 bg-white shadow-lg"
    >
      <button
        v-for="opt in options"
        :key="opt.value"
        type="button"
        class="block w-full px-3 py-2 text-right text-sm hover:bg-ivory-100"
        :class="value === opt.value ? 'bg-gold-50 text-gold-700 font-medium' : ''"
        @click="selectOption(opt.value)"
      >
        {{ opt.label }}
      </button>
    </div>
    <span v-if="error" class="absolute -bottom-4 right-0 flex items-center gap-1 text-[10px] text-red-600 whitespace-nowrap">
      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
      {{ error }}
    </span>
  </span>

  <!-- Search dropdown -->
  <span
    v-else-if="type === 'search' && searchOptions"
    ref="dropdownRef"
    class="relative inline-block"
    :class="className"
    :style="{ minWidth: width || '160px' }"
  >
    <button
      type="button"
      :dir="dir"
      class="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-sm transition-all border border-dashed border-ivory-400 bg-ivory-100/80 hover:bg-gold-50/60 hover:border-gold-500"
      :class="[
        error ? 'border-red-400 bg-red-50/50' : '',
        readOnly ? 'cursor-default opacity-70' : 'cursor-text',
        inputClassName,
      ]"
      @click="toggleDropdown"
    >
      <span :class="!value ? 'text-navy-400 italic' : ''">{{ selectedSearchLabel || value || placeholder }}</span>
      <svg v-if="!readOnly" class="w-3 h-3 text-navy-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
      </svg>
    </button>
    <div
      v-if="showDropdown && !readOnly"
      class="absolute z-50 mt-1 w-64 overflow-hidden rounded-lg border border-ivory-300 bg-white shadow-lg"
    >
      <input
        ref="searchInputRef"
        type="text"
        v-model="searchQuery"
        placeholder="بحث..."
        :dir="dir"
        class="w-full border-b border-ivory-200 bg-white px-3 py-2 text-sm outline-none"
      />
      <div class="max-h-48 overflow-auto">
        <button
          v-for="opt in filteredSearchOptions"
          :key="opt.value"
          type="button"
          class="block w-full px-3 py-2 text-right text-sm hover:bg-ivory-100"
          :class="value === opt.value ? 'bg-gold-50 text-gold-700 font-medium' : ''"
          @click="selectSearchOption(opt.value)"
        >
          <div>{{ opt.label }}</div>
          <div v-if="opt.meta" class="text-xs text-navy-400">{{ opt.meta }}</div>
        </button>
        <div v-if="filteredSearchOptions.length === 0" class="px-3 py-2 text-sm text-navy-400">لا توجد نتائج</div>
      </div>
    </div>
    <span v-if="error" class="absolute -bottom-4 right-0 flex items-center gap-1 text-[10px] text-red-600 whitespace-nowrap">
      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
      {{ error }}
    </span>
  </span>

  <!-- Text/number/date input -->
  <span
    v-else
    class="relative inline-block"
    :class="className"
    :style="{ minWidth: width || '80px' }"
  >
    <input
      ref="inputRef"
      :type="inputType"
      :inputmode="type === 'number' ? 'decimal' : undefined"
      :value="value || ''"
      :readonly="readOnly"
      :placeholder="placeholder"
      :dir="dir"
      class="inline-block rounded-md px-2 py-0.5 text-sm transition-all border border-dashed border-ivory-400 bg-ivory-100/80 hover:bg-gold-50/60 hover:border-gold-500 h-7 focus:border-gold-500 focus:bg-gold-50/50 focus:ring-2 focus:ring-gold-200/30 focus:outline-none"
      :class="[
        error ? 'border-red-400 bg-red-50/50' : '',
        readOnly ? 'cursor-default opacity-70' : 'cursor-text',
        inputClassName,
      ]"
      :style="{ width: width || 'auto', minWidth: width || '80px' }"
      @input="$emit('update:value', $event.target.value)"
    />
    <span v-if="error" class="absolute -bottom-4 right-0 flex items-center gap-1 text-[10px] text-red-600 whitespace-nowrap">
      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
      {{ error }}
    </span>
  </span>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  value: { type: [String, Number], default: '' },
  placeholder: { type: String, default: '...' },
  type: { type: String, default: 'text' }, // text | number | date | select | search
  options: { type: Array, default: null }, // [{ label, value }]
  searchOptions: { type: Array, default: null }, // [{ label, value, meta? }]
  error: { type: String, default: '' },
  readOnly: { type: Boolean, default: false },
  preview: { type: Boolean, default: false },
  width: { type: String, default: '' },
  className: { type: String, default: '' },
  inputClassName: { type: String, default: '' },
  dir: { type: String, default: 'rtl' },
})

const emit = defineEmits(['update:value'])

const showDropdown = ref(false)
const searchQuery = ref('')
const dropdownRef = ref(null)
const searchInputRef = ref(null)
const inputRef = ref(null)

const placeholderFallback = computed(() => `<span class="text-navy-400 italic">${props.placeholder}</span>`)

const inputType = computed(() => (props.type === 'date' ? 'date' : 'text'))

const selectedOptionLabel = computed(() => {
  if (!props.options) return ''
  const opt = props.options.find((o) => o.value === props.value)
  return opt ? opt.label : ''
})

const selectedSearchLabel = computed(() => {
  if (!props.searchOptions) return ''
  const opt = props.searchOptions.find((o) => o.value === props.value)
  return opt ? opt.label : ''
})

const filteredSearchOptions = computed(() => {
  if (!props.searchOptions) return []
  if (!searchQuery.value) return props.searchOptions
  const q = searchQuery.value.toLowerCase()
  return props.searchOptions.filter(
    (o) =>
      o.label.toLowerCase().includes(q) ||
      (o.meta && o.meta.toLowerCase().includes(q))
  )
})

function toggleDropdown() {
  if (props.readOnly) return
  showDropdown.value = !showDropdown.value
  if (showDropdown.value && props.type === 'search') {
    nextTick(() => {
      searchInputRef.value?.focus()
    })
  }
}

function selectOption(value) {
  emit('update:value', value)
  showDropdown.value = false
}

function selectSearchOption(value) {
  emit('update:value', value)
  showDropdown.value = false
  searchQuery.value = ''
}

function handleClickOutside(e) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target)) {
    showDropdown.value = false
  }
}

onMounted(() => {
  document.addEventListener('mousedown', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleClickOutside)
})
</script>
