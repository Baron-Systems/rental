<template>
  <Teleport to="body">
    <!-- Confirm Dialog -->
    <transition name="modal">
      <div v-if="confirmState.open" class="fixed inset-0 z-[90] flex items-center justify-center p-4" dir="rtl">
        <div class="absolute inset-0 bg-navy-950/50 backdrop-blur-sm" @click="onCancel"></div>
        <div class="relative card-premium w-full max-w-md overflow-hidden animate-scale-in">
          <div class="p-6">
            <div class="flex items-start gap-4">
              <div class="w-12 h-12 rounded-xl flex items-center justify-center shrink-0" :class="iconClass">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path v-if="confirmState.variant === 'danger'" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                  <path v-else-if="confirmState.variant === 'warning'" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                  <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
              </div>
              <div class="flex-1">
                <h3 class="text-base font-bold text-navy-900 mb-1">{{ confirmState.title }}</h3>
                <p class="text-sm text-navy-500">{{ confirmState.message }}</p>
              </div>
            </div>
          </div>
          <div class="flex items-center justify-end gap-2 px-6 py-4 border-t border-ivory-300/60 bg-ivory-50/50">
            <button class="btn-premium btn-outline" @click="onCancel">إلغاء</button>
            <button class="btn-premium" :class="confirmBtnClass" @click="onConfirm">
              {{ confirmState.confirmLabel || 'تأكيد' }}
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Prompt Dialog -->
    <transition name="modal">
      <div v-if="confirmState.promptOpen" class="fixed inset-0 z-[90] flex items-center justify-center p-4" dir="rtl">
        <div class="absolute inset-0 bg-navy-950/50 backdrop-blur-sm" @click="onPromptCancel"></div>
        <div class="relative card-premium w-full max-w-md overflow-hidden animate-scale-in">
          <div class="p-6">
            <div class="flex items-start gap-4">
              <div class="w-12 h-12 rounded-xl flex items-center justify-center shrink-0" :class="promptIconClass">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
              </div>
              <div class="flex-1">
                <h3 class="text-base font-bold text-navy-900 mb-1">{{ confirmState.promptTitle }}</h3>
                <p v-if="confirmState.promptMessage" class="text-sm text-navy-500 mb-3">{{ confirmState.promptMessage }}</p>
                <div v-if="confirmState.promptInputLabel" class="text-sm font-semibold text-navy-700 mb-1.5">{{ confirmState.promptInputLabel }}</div>
                <input
                  ref="promptInputRef"
                  v-model="confirmState.promptValue"
                  type="text"
                  class="input-premium"
                  @keyup.enter="onPromptConfirm"
                />
              </div>
            </div>
          </div>
          <div class="flex items-center justify-end gap-2 px-6 py-4 border-t border-ivory-300/60 bg-ivory-50/50">
            <button class="btn-premium btn-outline" @click="onPromptCancel">إلغاء</button>
            <button class="btn-premium" :class="promptBtnClass" @click="onPromptConfirm">تأكيد</button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { confirmState, useConfirm } from '@/composables/useConfirm'

const { resolveConfirm, resolvePrompt } = useConfirm()
const promptInputRef = ref(null)

const iconClass = computed(() => ({
  danger: 'bg-red-50 text-red-600',
  warning: 'bg-amber-50 text-amber-600',
  info: 'bg-navy-50 text-navy-600',
}[confirmState.variant] || 'bg-navy-50 text-navy-600'))

const confirmBtnClass = computed(() => ({
  danger: 'btn-danger',
  warning: 'btn-gold',
  info: 'btn-navy',
}[confirmState.variant] || 'btn-navy'))

const promptIconClass = computed(() => ({
  danger: 'bg-red-50 text-red-600',
  warning: 'bg-amber-50 text-amber-600',
  info: 'bg-navy-50 text-navy-600',
}[confirmState.promptVariant] || 'bg-amber-50 text-amber-600'))

const promptBtnClass = computed(() => ({
  danger: 'btn-danger',
  warning: 'btn-gold',
  info: 'btn-navy',
}[confirmState.promptVariant] || 'btn-gold'))

watch(() => confirmState.promptOpen, async (v) => {
  if (v) {
    await nextTick()
    promptInputRef.value?.focus()
  }
})

function onConfirm() { resolveConfirm(true) }
function onCancel() { resolveConfirm(false) }
function onPromptConfirm() {
  const val = confirmState.promptValue.trim()
  resolvePrompt(val || null)
}
function onPromptCancel() { resolvePrompt(null) }
</script>

<style scoped>
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
