<script setup lang="ts">
/**
 * Link this admin to the panel's Telegram bot: a button that opens the bot with the admin's start code,
 * a QR code to scan from a phone, and the current state. Nothing is shown when no bot is set up.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import HiddifyQrCode from '@/shared/components/HiddifyQrCode.vue'
import { telegramInfo } from '@/core/panelShell'

const props = defineProps<{ connected?: boolean; showQr?: boolean }>()
const emit = defineEmits<{ opened: []; check: [] }>()
const { t } = useI18n()

const info = computed(() => telegramInfo.value)
const isConnected = computed(() => props.connected ?? info.value?.connected ?? false)

function open() {
  if (!info.value) return
  // tg:// opens the app; the t.me link is the fallback (desktop without the app).
  window.location.href = info.value.connect_url
  emit('opened')
}
</script>

<template>
  <div v-if="info" class="tgc" :class="{ 'tgc--on': isConnected }">
    <div class="tgc__main">
      <span class="tgc__logo" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="22" height="22"><path fill="currentColor" d="M9.04 15.6 8.9 19.4c.4 0 .58-.17.8-.38l1.9-1.82 3.94 2.88c.72.4 1.24.19 1.43-.67l2.6-12.18c.24-1.07-.38-1.5-1.08-1.24L3.2 11.66c-1.04.4-1.03.98-.18 1.25l3.92 1.22 9.1-5.74c.43-.27.82-.12.5.17z" /></svg>
      </span>
      <div class="tgc__text">
        <b>{{ isConnected ? t('telegram.connectedTitle') : t('telegram.connectTitle') }}</b>
        <small>{{ isConnected ? t('telegram.connectedHint', { bot: '@' + info.bot_username }) : t('telegram.connectHint', { bot: '@' + info.bot_username }) }}</small>
      </div>
      <span v-if="isConnected" class="tgc__badge"><i class="pi pi-check" />{{ t('telegram.connected') }}</span>
    </div>

    <div class="tgc__actions">
      <Button :label="isConnected ? t('telegram.reconnect') : t('telegram.connect')" icon="pi pi-send" :outlined="isConnected" class="tgc__btn" @click="open" />
      <a :href="info.web_url" target="_blank" rel="noopener" class="tgc__web">{{ t('telegram.openWeb') }}</a>
      <Button v-if="!isConnected" :label="t('telegram.check')" icon="pi pi-refresh" text size="small" severity="secondary" @click="emit('check')" />
    </div>

    <div v-if="showQr && !isConnected" class="tgc__qr">
      <HiddifyQrCode :value="info.web_url" :size="132" />
      <small>{{ t('telegram.scan') }}</small>
    </div>
  </div>
</template>

<style scoped>
.tgc {
  --tg: #229ed9;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 1rem 1.1rem;
  border-radius: 16px;
  border: 1px solid color-mix(in srgb, var(--tg) 35%, var(--p-content-border-color));
  background: linear-gradient(135deg, color-mix(in srgb, var(--tg) 10%, transparent), transparent 70%), var(--p-content-background);
}
.tgc--on {
  --tg: var(--p-green-500, #22c55e);
}
.tgc__main {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  min-width: 0;
}
.tgc__logo {
  flex-shrink: 0;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  background: linear-gradient(160deg, #37bbfe, #007dbb);
  box-shadow: 0 6px 16px rgba(34, 158, 217, 0.3);
}
.tgc__text {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
  flex: 1;
}
.tgc__text b {
  font-size: 0.98rem;
}
.tgc__text small {
  font-size: 0.8rem;
  line-height: 1.4;
  color: var(--p-text-muted-color);
}
.tgc__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.1rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--p-green-600, #16a34a);
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 14%, transparent);
}
.tgc__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.9rem;
}
.tgc__btn:not(.p-button-outlined) {
  background: #229ed9;
  border-color: #229ed9;
}
.tgc__web {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.tgc__web:hover {
  color: var(--p-primary-color);
}
.tgc__qr {
  display: flex;
  align-items: center;
  gap: 0.9rem;
}
.tgc__qr small {
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
@media (max-width: 640px) {
  .tgc__qr {
    display: none; /* on the phone itself the button is enough */
  }
}
</style>
