<script setup lang="ts">
/**
 * Asks once (dashboard) to link this admin's Telegram when the panel has a bot and the admin has not
 * linked it. "Not now" (or connecting) is remembered in this browser, so it never asks again here.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { telegramInfo } from '@/core/panelShell'

const KEY = 'hiddify.admin.telegramPrompt'
const { t } = useI18n()
const visible = ref(false)
let timer: number | undefined

function seen(): boolean {
  try {
    return localStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}
function remember() {
  try {
    localStorage.setItem(KEY, '1')
  } catch {
    /* private mode: it may ask again next time */
  }
}

function close() {
  remember()
  visible.value = false
}

function connect() {
  remember()
  visible.value = false
  if (telegramInfo.value) window.location.href = telegramInfo.value.connect_url
}

onMounted(() => {
  const info = telegramInfo.value
  if (!info || info.connected || seen()) return
  // Let the dashboard appear first.
  timer = window.setTimeout(() => (visible.value = true), 1200)
})
onBeforeUnmount(() => window.clearTimeout(timer))

const benefits = ['notify', 'backup', 'manage'] as const
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    :draggable="false"
    :closable="false"
    :show-header="false"
    class="tgp"
    :style="{ width: 'min(26rem, calc(100vw - 1.5rem))' }"
    @update:visible="(v: boolean) => !v && close()"
  >
    <div v-if="telegramInfo" class="tgp__body">
      <span class="tgp__logo" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="34" height="34"><path fill="currentColor" d="M9.04 15.6 8.9 19.4c.4 0 .58-.17.8-.38l1.9-1.82 3.94 2.88c.72.4 1.24.19 1.43-.67l2.6-12.18c.24-1.07-.38-1.5-1.08-1.24L3.2 11.66c-1.04.4-1.03.98-.18 1.25l3.92 1.22 9.1-5.74c.43-.27.82-.12.5.17z" /></svg>
      </span>
      <h3 class="tgp__title">{{ t('telegram.promptTitle') }}</h3>
      <p class="tgp__lead">{{ t('telegram.promptLead', { bot: '@' + telegramInfo.bot_username }) }}</p>
      <ul class="tgp__list">
        <li v-for="b in benefits" :key="b"><i class="pi pi-check-circle" />{{ t(`telegram.benefit.${b}`) }}</li>
      </ul>
      <div class="tgp__actions">
        <Button :label="t('telegram.connect')" icon="pi pi-send" class="tgp__connect" @click="connect" />
        <Button :label="t('telegram.notNow')" severity="secondary" text @click="close" />
      </div>
      <small class="tgp__later">{{ t('telegram.later') }}</small>
    </div>
  </Dialog>
</template>

<style scoped>
.tgp__body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.7rem;
  padding: 1.5rem 0.4rem 0.6rem;
  text-align: center;
}
.tgp__logo {
  width: 4.2rem;
  height: 4.2rem;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  background: linear-gradient(160deg, #37bbfe, #007dbb);
  box-shadow: 0 10px 28px rgba(34, 158, 217, 0.35);
  animation: tgp-pop 0.5s cubic-bezier(0.3, 1.6, 0.5, 1) both;
}
.tgp__title {
  margin: 0.3rem 0 0;
  font-size: 1.2rem;
  font-weight: 700;
}
.tgp__lead {
  margin: 0;
  font-size: 0.9rem;
  color: var(--p-text-muted-color);
}
.tgp__list {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin: 0.3rem 0;
  padding: 0;
  list-style: none;
  text-align: start;
  font-size: 0.88rem;
}
.tgp__list li {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}
.tgp__list i {
  margin-top: 0.15rem;
  color: #229ed9;
}
.tgp__actions {
  display: flex;
  flex-direction: column;
  align-self: stretch;
  gap: 0.35rem;
  margin-top: 0.4rem;
}
.tgp__connect {
  background: #229ed9;
  border-color: #229ed9;
}
.tgp__later {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}
@keyframes tgp-pop {
  from {
    transform: scale(0.5);
    opacity: 0;
  }
  to {
    transform: none;
    opacity: 1;
  }
}
@media (prefers-reduced-motion: reduce) {
  .tgp__logo {
    animation: none;
  }
}
</style>
