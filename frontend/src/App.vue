<template>
  <div v-if="session.state.loading" class="flex items-center justify-center h-screen" style="background: linear-gradient(135deg, #0a1530 0%, #0f1f42 50%, #060d1f 100%);">
    <div class="text-center">
      <div class="inline-flex w-16 h-16 rounded-2xl items-center justify-center mb-4 shadow-soft-lg" style="background: linear-gradient(135deg, #e3b94b, #d4a02c);">
        <svg class="w-8 h-8 text-navy-900 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
        </svg>
      </div>
      <p class="text-gold-400/70 text-sm font-medium">جاري التحميل...</p>
    </div>
  </div>

  <!-- No account linked -->
  <div v-else-if="session.state.account?.needs_account" class="min-h-screen flex items-center justify-center p-4" dir="rtl" style="background: linear-gradient(135deg, #0a1530 0%, #0f1f42 50%, #060d1f 100%);">
    <div class="absolute top-0 left-0 w-96 h-96 rounded-full opacity-10 blur-3xl" style="background: radial-gradient(circle, #d4a02c, transparent);"></div>
    <div class="relative w-full max-w-md text-center animate-scale-in">
      <div class="inline-flex w-16 h-16 rounded-2xl items-center justify-center mb-6 shadow-soft-lg" style="background: linear-gradient(135deg, #e3b94b, #d4a02c);">
        <svg class="w-8 h-8 text-navy-900" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
      </div>
      <h1 class="text-2xl font-bold text-white mb-3">لا يوجد حساب مرتبط</h1>
      <p class="text-gold-400/70 text-sm mb-2">حسابك لا يملك حساب إيجار مرتبط بعد.</p>
      <p class="text-gold-400/50 text-xs mb-8">يرجى التواصل مع مدير النظام لإنشاء حساب إيجار وربطه بحسابك.</p>
      <button class="btn-premium btn-gold w-full" @click="handleLogout">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
        العودة إلى تسجيل الدخول
      </button>
    </div>
  </div>

  <!-- Account disabled -->
  <div v-else-if="session.state.account?.account_disabled" class="min-h-screen flex items-center justify-center p-4" dir="rtl" style="background: linear-gradient(135deg, #0a1530 0%, #0f1f42 50%, #060d1f 100%);">
    <div class="relative w-full max-w-md text-center animate-scale-in">
      <div class="inline-flex w-16 h-16 rounded-2xl items-center justify-center mb-6 bg-red-500/20">
        <svg class="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/></svg>
      </div>
      <h1 class="text-2xl font-bold text-white mb-3">الحساب معطّل</h1>
      <p class="text-gold-400/70 text-sm mb-8">حساب الإيجار الخاص بك معطّل. يرجى التواصل مع مدير النظام.</p>
      <button class="btn-premium btn-gold w-full" @click="handleLogout">العودة إلى تسجيل الدخول</button>
    </div>
  </div>

  <router-view v-else />
  <ToastContainer />
  <ConfirmDialog />
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useSession } from '@/composables/useSession'
import ToastContainer from '@/components/ui/ToastContainer.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'

const session = useSession()
const router = useRouter()

async function handleLogout() {
  await session.logout()
  router.push({ name: 'Login' })
}
</script>
