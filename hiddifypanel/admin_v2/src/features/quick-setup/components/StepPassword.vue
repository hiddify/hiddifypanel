<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Password from 'primevue/password'
import { apiErrorMessage } from '@/core/api/client'
import { quickSetupApi } from '@/features/quick-setup/api'
import PasswordRules from '@/shared/components/PasswordRules.vue'
import { MIN_PASSWORD, isStrongPassword } from '@/shared/utils/password-strength'

const emit = defineEmits<{ error: [message: string] }>()

// Strong passwords only (same rule as the server).
const MIN = MIN_PASSWORD
const { t } = useI18n()
const password = ref('')
const confirm = ref('')
const touched = ref(false)

const weak = computed(() => password.value.length > 0 && !isStrongPassword(password.value))
const mismatch = computed(() => confirm.value.length > 0 && confirm.value !== password.value)
const valid = computed(() => isStrongPassword(password.value) && confirm.value === password.value)

async function submit(): Promise<boolean> {
  touched.value = true
  if (!valid.value) return false
  try {
    await quickSetupApi.password(password.value)
    return true
  } catch (err) {
    emit('error', apiErrorMessage(err))
    return false
  }
}

defineExpose({ submit })
</script>

<template>
  <form class="flex flex-col gap-5 qs-narrow" autocomplete="off" @submit.prevent>
    <div class="qs-callout">
      <i class="pi pi-shield" />
      <span>{{ t('quickSetup.password.why') }}</span>
    </div>

    <div class="flex flex-col gap-2">
      <label for="qs-password" class="qs-label">{{ t('quickSetup.password.label') }}</label>
      <Password
        v-model="password"
        input-id="qs-password"
        toggle-mask
        :feedback="true"
        :prompt-label="t('quickSetup.password.prompt', { min: MIN })"
        :weak-label="t('quickSetup.password.weak')"
        :medium-label="t('quickSetup.password.medium')"
        :strong-label="t('quickSetup.password.strong')"
        :invalid="touched && (weak || !password)"
        fluid
        :input-props="{ autocomplete: 'new-password' }"
      />
      <PasswordRules :password="password" />
    </div>

    <div class="flex flex-col gap-2">
      <label for="qs-password-confirm" class="qs-label">{{ t('quickSetup.password.confirm') }}</label>
      <Password
        v-model="confirm"
        input-id="qs-password-confirm"
        toggle-mask
        :feedback="false"
        :invalid="touched && (mismatch || !confirm)"
        fluid
        :input-props="{ autocomplete: 'new-password' }"
      />
      <small v-if="touched && (mismatch || !confirm)" class="qs-error">{{ t('quickSetup.password.mismatch') }}</small>
      <small v-else-if="valid" class="qs-ok"><i class="pi pi-check-circle" /> {{ t('quickSetup.password.ok') }}</small>
    </div>
  </form>
</template>
