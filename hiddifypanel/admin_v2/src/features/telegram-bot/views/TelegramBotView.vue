<script setup lang="ts">
/**
 * The panel's Telegram bot (owner only): is it alive and does Telegram reach this panel, a test message to the
 * admin's own chat, setting the webhook again, and the animated button icons. The token itself is in Settings.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import PageHeader from '@/shared/components/PageHeader.vue'
import TelegramConnect from '@/shared/components/TelegramConnect.vue'
import { apiErrorMessage } from '@/core/api/client'
import BotIconsCard from '@/features/telegram-bot/components/BotIconsCard.vue'
import { telegramBotApi, type BotState, type IconsInfo } from '@/features/telegram-bot/api'

const { t, locale } = useI18n()
const toast = useToast()

const state = ref<BotState | null>(null)
const loading = ref(true)
const refreshing = ref(false)
const loadError = ref<string | null>(null)
const testing = ref(false)
const hooking = ref(false)

type Health = 'ok' | 'warn' | 'bad' | 'off'

/** One word for the whole bot, the colour of the pill under its name. */
const health = computed<{ kind: Health; label: string }>(() => {
  const s = state.value
  if (!s?.configured) return { kind: 'off', label: t('tgBot.status.off') }
  if (s.error === 'token_rejected') return { kind: 'bad', label: t('tgBot.status.tokenRejected') }
  if (s.error || !s.bot) return { kind: 'bad', label: t('tgBot.status.unreachable') }
  if (!s.webhook?.matches) return { kind: 'warn', label: t('tgBot.status.webhook') }
  if (s.webhook.last_error && s.webhook.pending > 0) return { kind: 'warn', label: t('tgBot.status.delayed') }
  return { kind: 'ok', label: t('tgBot.status.ok') }
})

const botLink = computed(() => (state.value?.bot?.username ? `https://t.me/${state.value.bot.username}` : ''))
const initial = computed(() => (state.value?.bot?.name || 'B').trim().charAt(0).toUpperCase())

function ago(iso: string | null): string {
  if (!iso) return ''
  const seconds = (new Date(iso).getTime() - Date.now()) / 1000
  const rtf = new Intl.RelativeTimeFormat(locale.value, { numeric: 'auto' })
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ]
  const [unit, size] = units.find(([, s]) => Math.abs(seconds) >= s) ?? ['minute', 60]
  return rtf.format(Math.round(seconds / size), unit)
}

async function load(quiet = false) {
  if (quiet) refreshing.value = true
  else loading.value = true
  loadError.value = null
  try {
    state.value = await telegramBotApi.state()
  } catch (e) {
    loadError.value = apiErrorMessage(e)
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

async function sendTest() {
  testing.value = true
  try {
    const res = await telegramBotApi.test()
    if (res.ok) toast.add({ severity: 'success', summary: t('tgBot.test.sent'), detail: t('tgBot.test.sentHint'), life: 4000 })
    else toast.add({ severity: 'warn', summary: t('tgBot.test.failed'), detail: t(`tgBot.test.error.${res.error ?? 'unreachable'}`), life: 7000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: t('tgBot.test.failed'), detail: apiErrorMessage(e), life: 7000 })
  } finally {
    testing.value = false
  }
}

async function setWebhook() {
  hooking.value = true
  try {
    const res = await telegramBotApi.setWebhook()
    state.value = { ...res.state, icons: state.value?.icons ?? res.state.icons }
    if (res.ok) toast.add({ severity: 'success', summary: t('tgBot.webhook.done'), life: 3500 })
    else toast.add({ severity: 'warn', summary: t('tgBot.webhook.failed'), detail: t('tgBot.webhook.failedHint'), life: 7000 })
  } catch (e) {
    toast.add({ severity: 'error', summary: t('tgBot.webhook.failed'), detail: apiErrorMessage(e), life: 7000 })
  } finally {
    hooking.value = false
  }
}

function onIcons(icons: IconsInfo) {
  if (state.value) state.value = { ...state.value, icons }
}

/** Back from the bot after pressing Start: is this admin connected now? */
function onConnectCheck() {
  void load(true)
}

onMounted(() => load())
</script>

<template>
  <div class="tb-page">
    <PageHeader :title="t('tgBot.title')" :subtitle="t('tgBot.subtitle')" />

    <div v-if="loading" class="tb-grid">
      <Skeleton height="11rem" border-radius="22px" class="tb-span" />
      <Skeleton height="16rem" border-radius="22px" />
      <Skeleton height="16rem" border-radius="22px" />
    </div>

    <Message v-else-if="loadError" severity="error" :closable="false">
      <div class="flex items-center gap-3 flex-wrap">
        <span>{{ loadError }}</span>
        <Button :label="t('common.retry')" icon="pi pi-refresh" size="small" severity="secondary" @click="load()" />
      </div>
    </Message>

    <!-- No bot yet: how to make one -->
    <section v-else-if="state && !state.configured" class="tb-card tb-empty">
      <span class="tb-empty__logo" aria-hidden="true"><i class="pi pi-telegram" /></span>
      <h3>{{ t('tgBot.empty.title') }}</h3>
      <p>{{ t('tgBot.empty.lead') }}</p>
      <ol class="tb-steps">
        <li><span>1</span>{{ t('tgBot.empty.step1') }}</li>
        <li><span>2</span>{{ t('tgBot.empty.step2') }}</li>
        <li><span>3</span>{{ t('tgBot.empty.step3') }}</li>
      </ol>
      <div class="tb-empty__actions">
        <Button as="a" href="https://t.me/BotFather" target="_blank" rel="noopener" :label="t('tgBot.empty.openFather')" icon="pi pi-external-link" severity="secondary" outlined />
        <Button as="router-link" :to="{ path: '/settings', query: { category: 'telegram' } }" :label="t('tgBot.empty.toSettings')" icon="pi pi-cog" />
      </div>
    </section>

    <div v-else-if="state" class="tb-grid">
      <!-- The bot -->
      <section class="tb-card tb-hero tb-span" :class="`tb-hero--${health.kind}`">
        <div class="tb-hero__avatar" aria-hidden="true">{{ initial }}</div>
        <div class="tb-hero__body">
          <h3 class="tb-hero__name">{{ state.bot?.name || t('tgBot.unnamed') }}</h3>
          <a v-if="botLink" :href="botLink" target="_blank" rel="noopener" class="tb-hero__user" dir="ltr">@{{ state.bot?.username }}</a>
          <span class="tb-pill" :class="`tb-pill--${health.kind}`"><span class="tb-pill__dot" />{{ health.label }}</span>
        </div>
        <div class="tb-hero__actions">
          <Button v-if="botLink" as="a" :href="botLink" target="_blank" rel="noopener" :label="t('tgBot.open')" icon="pi pi-telegram" class="tb-tg-btn" />
          <Button :label="t('tgBot.refresh')" icon="pi pi-refresh" severity="secondary" outlined :loading="refreshing" @click="load(true)" />
          <Button as="router-link" :to="{ path: '/settings', query: { category: 'telegram' } }" :label="t('tgBot.tokenLabel')" icon="pi pi-key" severity="secondary" text />
        </div>
        <p v-if="state.error" class="tb-hero__error"><i class="pi pi-exclamation-circle" />{{ t(`tgBot.error.${state.error}`) }}</p>
      </section>

      <!-- Health -->
      <section v-if="state.bot" class="tb-card">
        <header class="tb-card__head">
          <span class="tb-card__icon tb-card__icon--health"><i class="pi pi-heart" /></span>
          <div>
            <h3 class="tb-card__title">{{ t('tgBot.health.title') }}</h3>
            <p class="tb-card__sub">{{ t('tgBot.health.sub') }}</p>
          </div>
        </header>

        <ul class="tb-rows">
          <li class="tb-row">
            <i class="tb-row__mark pi" :class="state.webhook?.matches ? 'pi-check-circle tb-ok' : 'pi-times-circle tb-bad'" />
            <div class="tb-row__text">
              <b>{{ t('tgBot.health.webhook') }}</b>
              <small v-if="state.webhook?.matches">{{ t('tgBot.health.webhookOk', { domain: state.webhook.domain }) }}</small>
              <small v-else-if="!state.webhook?.domain">{{ t('tgBot.health.noDomain') }}</small>
              <small v-else>{{ state.webhook?.set ? t('tgBot.health.webhookElsewhere') : t('tgBot.health.webhookMissing') }}</small>
            </div>
            <Button
              v-if="!state.webhook?.matches && state.webhook?.domain"
              :label="t('tgBot.webhook.fix')"
              size="small"
              :loading="hooking"
              @click="setWebhook"
            />
          </li>
          <li class="tb-row">
            <i class="tb-row__mark pi" :class="state.webhook?.pending ? 'pi-clock tb-warn' : 'pi-check-circle tb-ok'" />
            <div class="tb-row__text">
              <b>{{ t('tgBot.health.pending') }}</b>
              <small>{{ state.webhook?.pending ? t('tgBot.health.pendingN', { n: state.webhook.pending }) : t('tgBot.health.pendingNone') }}</small>
            </div>
          </li>
          <li v-if="state.webhook?.last_error" class="tb-row">
            <i class="tb-row__mark pi pi-exclamation-triangle tb-warn" />
            <div class="tb-row__text">
              <b>{{ t('tgBot.health.lastError') }} <span class="tb-row__when">{{ ago(state.webhook.last_error_at) }}</span></b>
              <code dir="ltr">{{ state.webhook.last_error }}</code>
            </div>
          </li>
          <li class="tb-row">
            <i class="tb-row__mark pi pi-users tb-info" />
            <div class="tb-row__text">
              <b>{{ t('tgBot.health.people') }}</b>
              <small>{{ t('tgBot.health.peopleN', { admins: state.admins_connected, users: state.users_connected }) }}</small>
            </div>
          </li>
        </ul>

        <Button v-if="state.webhook?.matches" :label="t('tgBot.webhook.again')" icon="pi pi-sync" severity="secondary" text size="small" class="tb-again" :loading="hooking" @click="setWebhook" />
      </section>

      <!-- This admin's chat -->
      <section v-if="state.bot" class="tb-card">
        <header class="tb-card__head">
          <span class="tb-card__icon tb-card__icon--chat"><i class="pi pi-comments" /></span>
          <div>
            <h3 class="tb-card__title">{{ t('tgBot.test.title') }}</h3>
            <p class="tb-card__sub">{{ state.me_connected ? t('tgBot.test.sub') : t('tgBot.test.connectFirst') }}</p>
          </div>
        </header>
        <template v-if="state.me_connected">
          <p class="tb-linked">
            <i class="pi pi-check-circle tb-ok" />
            <span>{{ t('tgBot.test.linked') }} <b dir="ltr">@{{ state.bot.username }}</b></span>
          </p>
          <Button :label="t('tgBot.test.send')" icon="pi pi-send" class="tb-main-btn" :loading="testing" @click="sendTest" />
        </template>
        <TelegramConnect v-else :connected="false" show-qr @check="onConnectCheck" />
      </section>

      <!-- Animated icons -->
      <BotIconsCard v-if="state.bot" class="tb-span" :icons="state.icons" @saved="onIcons" />
    </div>
  </div>
</template>

<style scoped>
.tb-page {
  max-width: 64rem;
}
.tb-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  align-items: start;
}
.tb-span {
  grid-column: 1 / -1;
}
@media (max-width: 860px) {
  .tb-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

.tb-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 22px;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  animation: tb-in 0.4s ease both;
}
@keyframes tb-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
}
@media (prefers-reduced-motion: reduce) {
  .tb-card {
    animation: none;
  }
}
.tb-card__head {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.tb-card__icon {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 13px;
  color: #fff;
  font-size: 1.1rem;
}
.tb-card__icon--health {
  background: linear-gradient(145deg, #ff6b81, #ef4444);
}
.tb-card__icon--chat {
  background: linear-gradient(145deg, #3fc1ff, #229ed9);
}
.tb-card__title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.tb-card__sub {
  margin: 0.15rem 0 0;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

/* The bot */
.tb-hero {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 1rem 1.25rem;
  background:
    radial-gradient(circle at 0% 0%, color-mix(in srgb, #229ed9 16%, transparent), transparent 60%),
    var(--p-content-background);
}
.tb-hero__avatar {
  display: grid;
  place-items: center;
  width: 4.5rem;
  height: 4.5rem;
  border-radius: 50%;
  background: linear-gradient(160deg, #5ac8fa, #229ed9 55%, #1c7fc0);
  color: #fff;
  font-size: 1.9rem;
  font-weight: 600;
  box-shadow: 0 8px 22px -10px color-mix(in srgb, #229ed9 80%, transparent);
}
.tb-hero__body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.3rem;
  min-width: 0;
}
.tb-hero__name {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}
.tb-hero__user {
  color: #229ed9;
  font-weight: 500;
  text-decoration: none;
}
.tb-hero__user:hover {
  text-decoration: underline;
}
.tb-hero__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
}
.tb-hero__error {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  padding: 0.7rem 0.9rem;
  border-radius: 14px;
  background: color-mix(in srgb, var(--p-red-500) 10%, transparent);
  color: var(--p-red-600);
  font-size: 0.9rem;
}
.app-dark .tb-hero__error {
  color: var(--p-red-300);
}
@media (max-width: 640px) {
  .tb-hero {
    grid-template-columns: auto minmax(0, 1fr);
  }
  .tb-hero__actions {
    grid-column: 1 / -1;
    justify-content: flex-start;
  }
}
.tb-tg-btn {
  --p-button-primary-background: #229ed9;
  --p-button-primary-border-color: #229ed9;
  --p-button-primary-hover-background: #1c8cc2;
  --p-button-primary-hover-border-color: #1c8cc2;
  --p-button-primary-active-background: #187aa9;
  --p-button-primary-color: #fff;
  --p-button-primary-hover-color: #fff;
}

/* The status pill */
.tb-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  background: color-mix(in srgb, var(--pill) 14%, transparent);
  color: var(--pill);
}
.tb-pill__dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: currentColor;
}
.tb-pill--ok {
  --pill: #22c55e;
}
.tb-pill--ok .tb-pill__dot {
  animation: tb-pulse 2s ease-in-out infinite;
}
.tb-pill--warn {
  --pill: #f59e0b;
}
.tb-pill--bad {
  --pill: #ef4444;
}
.tb-pill--off {
  --pill: var(--text-color-secondary);
}
@keyframes tb-pulse {
  50% {
    box-shadow: 0 0 0 4px color-mix(in srgb, currentColor 25%, transparent);
  }
}
@media (prefers-reduced-motion: reduce) {
  .tb-pill--ok .tb-pill__dot {
    animation: none;
  }
}

/* Grouped rows (iOS settings style) */
.tb-rows {
  list-style: none;
  margin: 0;
  padding: 0;
  border-radius: 16px;
  background: var(--p-content-hover-background, var(--surface-ground));
  overflow: hidden;
}
.tb-row {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.8rem 0.95rem;
}
.tb-row + .tb-row {
  border-top: 1px solid var(--p-content-border-color);
}
.tb-row__mark {
  flex-shrink: 0;
  font-size: 1.15rem;
}
.tb-row__text {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  flex: 1;
  min-width: 0;
}
.tb-row__text small {
  color: var(--text-color-secondary);
  overflow-wrap: anywhere;
}
.tb-row__text code {
  font-size: 0.78rem;
  color: var(--text-color-secondary);
  overflow-wrap: anywhere;
  text-align: start;
}
.tb-row__when {
  font-weight: 400;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}
.tb-ok {
  color: #22c55e;
}
.tb-warn {
  color: #f59e0b;
}
.tb-bad {
  color: #ef4444;
}
.tb-info {
  color: #229ed9;
}
.tb-again {
  align-self: flex-start;
}
.tb-main-btn {
  align-self: stretch;
}
.tb-linked {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin: 0;
  padding: 0.8rem 0.95rem;
  border-radius: 16px;
  background: color-mix(in srgb, #22c55e 9%, transparent);
}
.tb-linked i {
  font-size: 1.15rem;
}

/* No bot yet */
.tb-empty {
  align-items: center;
  text-align: center;
  padding: 2rem 1.25rem;
}
.tb-empty h3 {
  margin: 0;
  font-size: 1.25rem;
}
.tb-empty p {
  margin: 0;
  color: var(--text-color-secondary);
  max-width: 32rem;
}
.tb-empty__logo {
  display: grid;
  place-items: center;
  width: 4.5rem;
  height: 4.5rem;
  border-radius: 50%;
  background: linear-gradient(160deg, #5ac8fa, #229ed9);
  color: #fff;
  font-size: 2rem;
}
.tb-steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  text-align: start;
}
.tb-steps li {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}
.tb-steps span {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 1.6rem;
  height: 1.6rem;
  border-radius: 50%;
  background: color-mix(in srgb, #229ed9 15%, transparent);
  color: #229ed9;
  font-weight: 700;
  font-size: 0.85rem;
}
.tb-empty__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.6rem;
}
</style>
