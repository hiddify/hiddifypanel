<template>
  <div class="account-page">
    <PageHeader :title="t('account.title')" :subtitle="t('account.subtitle')" />

    <div v-if="loading" class="account-grid">
      <Skeleton height="16rem" border-radius="16px" />
      <Skeleton height="16rem" border-radius="16px" />
    </div>

    <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <template v-else-if="me">
      <!-- Identity -->
      <section class="account-hero">
        <span class="account-hero__avatar" :class="{ 'account-hero__avatar--super': isSuper }">
          <i class="pi" :class="isSuper ? 'pi-crown' : 'pi-user'" />
        </span>
        <div class="min-w-0 flex-1">
          <div class="account-hero__name">{{ me.name }}</div>
          <div class="account-hero__meta">
            <span class="account-mode" :class="`account-mode--${me.mode}`">{{ t(`admins.mode.${me.mode}`) }}</span>
            <span v-if="me.parent_name" class="text-muted-color"><i class="pi pi-sitemap" /> {{ t('account.under', { name: me.parent_name }) }}</span>
            <span v-if="me.can_add_admin" class="text-muted-color"><i class="pi pi-user-plus" /> {{ t('account.canAddAdmins') }}</span>
          </div>
        </div>
        <Button
          :icon="copied ? 'pi pi-check' : 'pi pi-copy'"
          :label="copied ? t('common.copied') : t('account.copyLink')"
          severity="secondary"
          outlined
          class="account-hero__copy"
          @click="copyLink"
        />
      </section>

      <div class="account-grid">
        <!-- Limits -->
        <section class="account-card">
          <header class="account-card__head">
            <span class="account-card__icon"><i class="pi pi-gauge" /></span>
            <div>
              <h3 class="account-card__title">{{ t('account.limitsTitle') }}</h3>
              <p class="account-card__sub">{{ isSuper ? t('account.noLimits') : t('account.limitsSub') }}</p>
            </div>
          </header>

          <div v-if="isSuper" class="account-unlimited">
            <span class="account-unlimited__sign">∞</span>
            <span>{{ t('account.superText') }}</span>
          </div>

          <UsageMeters :stats="me.stats" :limits="me.limits" large />

          <dl class="account-facts">
            <div>
              <dt><i class="pi pi-sitemap" />{{ t('account.subAdmins') }}</dt>
              <dd>{{ formatCount(me.sub_admins) }}</dd>
            </div>
          </dl>
          <Message v-if="nearLimit" severity="warn" :closable="false" size="small">{{ t('account.nearLimit') }}</Message>
        </section>

        <!-- Password -->
        <section class="account-card">
          <header class="account-card__head">
            <span class="account-card__icon account-card__icon--key"><i class="pi pi-key" /></span>
            <div>
              <h3 class="account-card__title">{{ t('account.passwordTitle') }}</h3>
              <p class="account-card__sub">{{ me.has_password ? t('account.passwordSub') : t('account.noPasswordSub') }}</p>
            </div>
          </header>

          <form class="account-form" @submit.prevent="savePassword">
            <!-- Lets password managers pair the new password with this account -->
            <input type="text" name="username" autocomplete="username" :value="me.uuid" hidden readonly />
            <div v-if="me.has_password" class="account-form__field">
              <label for="current-password" class="font-medium">{{ t('account.current') }}</label>
              <Password v-model="current" input-id="current-password" :feedback="false" toggle-mask fluid :invalid="wrongCurrent" :input-props="{ autocomplete: 'current-password' }" />
              <small v-if="wrongCurrent" class="account-form__error">{{ t('account.wrongCurrent') }}</small>
            </div>
            <div class="account-form__field">
              <div class="flex items-center justify-between gap-2">
                <label for="new-password" class="font-medium">{{ t('account.new') }}</label>
                <Button type="button" size="small" text icon="pi pi-sparkles" :label="t('account.generate')" @click="generate" />
              </div>
              <Password
                v-model="next"
                input-id="new-password"
                toggle-mask
                fluid
                :invalid="tooShort"
                :prompt-label="t('account.strength.prompt')"
                :weak-label="t('account.strength.weak')"
                :medium-label="t('account.strength.medium')"
                :strong-label="t('account.strength.strong')"
                :input-props="{ autocomplete: 'new-password' }"
              />
              <small :class="tooShort ? 'account-form__error' : 'text-muted-color'">{{ t('account.minLength', { n: MIN_PASSWORD }) }}</small>
            </div>
            <div class="account-form__field">
              <label for="repeat-password" class="font-medium">{{ t('account.repeat') }}</label>
              <Password v-model="repeat" input-id="repeat-password" :feedback="false" toggle-mask fluid :invalid="mismatch" :input-props="{ autocomplete: 'new-password' }" />
              <small v-if="mismatch" class="account-form__error">{{ t('account.mismatch') }}</small>
            </div>
            <Message severity="secondary" :closable="false" size="small" icon="pi pi-info-circle">{{ t('account.loginHint') }}</Message>
            <Button type="submit" icon="pi pi-check" :label="t('account.save')" :loading="saving" :disabled="!canSave" class="self-end" />
          </form>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Password from 'primevue/password'
import Skeleton from 'primevue/skeleton'
import PageHeader from '@/shared/components/PageHeader.vue'
import { apiErrorMessage } from '@/core/api/client'
import { formatCount } from '@/shared/utils/format-metrics'
import UsageMeters from '@/features/admins/components/UsageMeters.vue'
import { adminsApi, meterTone, type MyAccount } from '@/features/admins/api'

const MIN_PASSWORD = 8

const { t } = useI18n()
const toast = useToast()

const me = ref<MyAccount | null>(null)
const loading = ref(true)
const loadError = ref<string | null>(null)
const copied = ref(false)

const current = ref('')
const next = ref('')
const repeat = ref('')
const wrongCurrent = ref(false)
const saving = ref(false)

const isSuper = computed(() => me.value?.mode === 'super_admin')
const nearLimit = computed(() => {
  const m = me.value
  if (!m?.limits) return false
  return [
    meterTone(m.stats.online, m.limits.max_online_users),
    meterTone(m.stats.active, m.limits.max_active_users),
    meterTone(m.stats.total, m.limits.max_users),
    meterTone(m.stats.usage_GB, m.limits.max_total_usage_GB),
  ].some((tone) => tone === 'danger')
})
const tooShort = computed(() => next.value.length > 0 && next.value.length < MIN_PASSWORD)
const mismatch = computed(() => repeat.value.length > 0 && repeat.value !== next.value)
const canSave = computed(
  () => next.value.length >= MIN_PASSWORD && repeat.value === next.value && (!me.value?.has_password || current.value.length > 0) && !saving.value,
)

function generate() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
  const bytes = crypto.getRandomValues(new Uint32Array(16))
  const password = Array.from(bytes, (n) => alphabet[n % alphabet.length]).join('')
  next.value = password
  repeat.value = password
  void navigator.clipboard?.writeText(password).then(() => toast.add({ severity: 'info', summary: t('account.generatedCopied'), life: 3000 }))
}

async function copyLink() {
  if (!me.value) return
  await navigator.clipboard.writeText(me.value.admin_link)
  copied.value = true
  window.setTimeout(() => (copied.value = false), 2000)
}

async function load() {
  loading.value = true
  loadError.value = null
  try {
    me.value = await adminsApi.me()
  } catch (err) {
    loadError.value = apiErrorMessage(err) || t('common.loadFailed')
  } finally {
    loading.value = false
  }
}

async function savePassword() {
  if (!canSave.value) return
  saving.value = true
  wrongCurrent.value = false
  try {
    await adminsApi.changeMyPassword(current.value, next.value)
    toast.add({ severity: 'success', summary: t('account.saved'), life: 4000 })
    current.value = next.value = repeat.value = ''
    if (me.value) me.value.has_password = true
  } catch (err) {
    const code = (err as { response?: { data?: { code?: string } } })?.response?.data?.code
    if (code === 'wrong_current') wrongCurrent.value = true
    else toast.add({ severity: 'error', summary: t('common.saveFailed'), detail: apiErrorMessage(err), life: 6000 })
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.account-hero {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem;
  padding: 1.1rem 1.25rem;
  margin-bottom: 1rem;
  border-radius: 18px;
  border: 1px solid var(--p-content-border-color);
  background:
    radial-gradient(120% 140% at 0% 0%, color-mix(in srgb, var(--p-primary-color) 14%, transparent), transparent 60%),
    var(--p-content-background);
}
.account-hero__avatar {
  width: 3.4rem;
  height: 3.4rem;
  flex-shrink: 0;
  border-radius: 16px;
  display: grid;
  place-items: center;
  font-size: 1.4rem;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 16%, transparent);
}
.account-hero__avatar--super {
  color: var(--p-amber-600, #d97706);
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 18%, transparent);
}
.account-hero__name {
  font-size: 1.25rem;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.account-hero__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 1rem;
  margin-top: 0.3rem;
  font-size: 0.85rem;
}
.account-hero__meta i {
  font-size: 0.75rem;
}
.account-mode {
  --mode-color: var(--p-sky-500, #0ea5e9);
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--mode-color);
  background: color-mix(in srgb, var(--mode-color) 12%, transparent);
}
.account-mode--super_admin {
  --mode-color: var(--p-amber-600, #d97706);
}
.account-mode--admin {
  --mode-color: var(--p-violet-500, #8b5cf6);
}

.account-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr));
  gap: 1rem;
  align-items: start;
}
.account-card {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
  padding: 1.25rem;
  border-radius: 16px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  animation: account-in 0.4s ease both;
}
.account-card + .account-card {
  animation-delay: 80ms;
}
.account-card__head {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.account-card__icon {
  width: 2.6rem;
  height: 2.6rem;
  flex-shrink: 0;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
}
.account-card__icon--key {
  color: var(--p-amber-600, #d97706);
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 14%, transparent);
}
.account-card__title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.account-card__sub {
  margin: 0.15rem 0 0;
  font-size: 0.85rem;
  color: var(--p-text-muted-color);
}
.account-unlimited {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 8%, transparent);
}
.account-unlimited__sign {
  font-size: 2rem;
  line-height: 1;
  color: var(--p-amber-600, #d97706);
}
.account-facts {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.75rem;
  margin: 0;
  padding-top: 1rem;
  border-top: 1px solid var(--p-content-border-color);
}
.account-facts dt {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
  margin-bottom: 0.2rem;
}
.account-facts dt i {
  font-size: 0.72rem;
}
.account-facts dd {
  margin: 0;
  font-weight: 600;
}
.account-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.account-form__field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.account-form__error {
  color: var(--p-red-500, #ef4444);
}
@keyframes account-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@media (max-width: 640px) {
  .account-hero {
    padding: 1rem;
  }
  .account-hero__copy {
    width: 100%;
  }
  .account-card {
    padding: 1rem;
  }
}
@media (prefers-reduced-motion: reduce) {
  .account-card {
    animation: none;
  }
}
</style>
