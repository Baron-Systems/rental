<template>
  <div class="min-h-screen flex items-center justify-center p-4" dir="rtl" style="background: #012350;">
    <!-- Decorative gold orbs -->
    <div class="absolute top-0 left-0 w-96 h-96 rounded-full opacity-10 blur-3xl" style="background: radial-gradient(circle, #b38942, transparent);"></div>
    <div class="absolute bottom-0 right-0 w-96 h-96 rounded-full opacity-10 blur-3xl" style="background: radial-gradient(circle, #c89a55, transparent);"></div>

    <div class="relative w-full max-w-md animate-scale-in">
      <!-- Logo -->
      <div class="text-center mb-8">
        <img
          src="/images/albaron-logo-login.png"
          alt="AL BARON"
          class="object-contain w-[240px] max-w-[80%] h-auto mx-auto mb-4"
        />
        <h1 class="text-2xl font-bold text-white tracking-tight">نظام الإيجار</h1>
        <p class="text-gold-400/70 text-sm font-medium mt-1">تسجيل الدخول إلى حسابك</p>
      </div>

      <!-- Card -->
      <div class="card-premium p-8">
        <form @submit.prevent="handleLogin" class="space-y-5">
          <FormField label="البريد الإلكتروني" required>
            <input v-model="email" type="email" dir="ltr" required class="input-premium" placeholder="example@email.com" />
          </FormField>
          <FormField label="كلمة المرور" required>
            <input v-model="password" type="password" dir="ltr" required class="input-premium" placeholder="••••••••" />
          </FormField>

          <div v-if="error" class="text-red-600 text-sm bg-red-50 border border-red-200 px-4 py-3 rounded-xl flex items-center gap-2">
            <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            {{ error }}
          </div>

          <button type="submit" class="btn-premium btn-gold w-full" :disabled="loading">
            <span v-if="loading" class="w-4 h-4 border-2 border-navy-900/30 border-t-navy-900 rounded-full animate-spin"></span>
            {{ loading ? 'جاري الدخول...' : 'تسجيل الدخول' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import FormField from '@/components/ui/FormField.vue'
import { useSession } from '@/composables/useSession'
import { extractError } from '@/composables/useApi'

const router = useRouter()
const session = useSession()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    const success = await session.login(email.value, password.value)
    if (success) {
      if (session.needsSetup.value) {
        router.push({ name: 'Setup' })
      } else {
        router.push({ name: 'Dashboard' })
      }
    } else {
      error.value = 'فشل تسجيل الدخول. تحقق من بياناتك.'
    }
  } catch (e) {
    error.value = extractError(e)
  } finally {
    loading.value = false
  }
}
</script>
