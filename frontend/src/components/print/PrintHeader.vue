<template>
  <div class="print-header" dir="rtl">
    <div class="brand">
      <img v-if="lessor?.logo" :src="lessor.logo" alt="logo" class="logo" />
      <div class="brand-text">
        <h1>{{ lessor?.name || 'نظام إدارة الإيجارات' }}</h1>
        <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
      </div>
    </div>
    <div class="meta">
      <p>تاريخ الطباعة: {{ printedAt }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useSession } from '@/composables/useSession'

const props = defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  lessor: { type: Object, default: () => ({}) },
})

const session = useSession()
const lessor = computed(() => props.lessor || session.state.account?.settings || {})
const printedAt = computed(() => new Date().toLocaleDateString('en-GB'))
</script>

<style scoped>
.print-header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #1a2238; padding-bottom: 12px; margin-bottom: 8px; }
.brand { display: flex; gap: 12px; align-items: center; }
.logo { width: 56px; height: 56px; object-fit: contain; }
.brand-text h1 { font-size: 18px; margin: 0; color: #1a2238; }
.subtitle { font-size: 13px; color: #64748b; margin: 2px 0 0; }
.meta { font-size: 12px; color: #64748b; text-align: left; }
@media print { .print-header { print-color-adjust: exact; } }
</style>
