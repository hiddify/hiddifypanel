<script setup lang="ts">
/**
 * Asks once (dashboard) to link this admin's Telegram when the panel has a bot and the admin has not
 * linked it, as a spotlight: a looping animation of the bot — its menu, the users with their usage, a user
 * created from the chat. "Not now" (or connecting) is remembered in this browser, so it never asks again here.
 * While it is due, the dashboard's install guide waits (telegramPromptDue): one spotlight at a time.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { telegramInfo } from '@/core/panelShell'
import { telegramPromptDue, TELEGRAM_PROMPT_KEY as KEY } from '@/shared/composables/useSpotlights'

const { t } = useI18n()
const visible = ref(false)
let timer: number | undefined

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
  if (!telegramPromptDue()) return
  // Let the dashboard appear first.
  timer = window.setTimeout(() => (visible.value = true), 1200)
})
onBeforeUnmount(() => window.clearTimeout(timer))

const steps = ['stepStart', 'stepUsers', 'stepCreate'] as const
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    :draggable="false"
    :closable="false"
    :show-header="false"
    class="tgp"
    :style="{ width: 'min(27rem, calc(100vw - 1.5rem))' }"
    @update:visible="(v: boolean) => !v && close()"
  >
    <div v-if="telegramInfo" class="tgp__body">
      <span class="tgp__logo" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="34" height="34"><path fill="currentColor" d="M9.04 15.6 8.9 19.4c.4 0 .58-.17.8-.38l1.9-1.82 3.94 2.88c.72.4 1.24.19 1.43-.67l2.6-12.18c.24-1.07-.38-1.5-1.08-1.24L3.2 11.66c-1.04.4-1.03.98-.18 1.25l3.92 1.22 9.1-5.74c.43-.27.82-.12.5.17z" /></svg>
      </span>
      <h3 class="tgp__title">{{ t('telegram.promptTitle') }}</h3>
      <p class="tgp__lead">{{ t('telegram.promptLead', { bot: '@' + telegramInfo.bot_username }) }}</p>
      <!-- The bot, as a looping chat (the same drawing in every language) -->
      <div class="tgs" dir="ltr" aria-hidden="true">
        <div class="tgs__phone">
          <div class="tgs__head"><span class="tgs__avatar" />@{{ telegramInfo.bot_username }}</div>
          <div class="tgs__chat">
            <!-- 1. /start: the admin menu -->
            <div class="tgs__scene tgs__scene--1">
              <div class="tgs__msg tgs__msg--me">/start</div>
              <div class="tgs__msg tgs__msg--bot">
                <b><i class="pi pi-user ui-emoji-icon" />Admin</b>
                <div class="tgs__kb"><span class="tgs__key tgs__key--users"><i class="pi pi-users ui-emoji-icon" />Users</span><span class="tgs__key"><i class="pi pi-plus ui-emoji-icon" />New user</span><span class="tgs__key"><i class="pi pi-save ui-emoji-icon" />Backup</span><span class="tgs__key"><i class="pi pi-chart-bar ui-emoji-icon" />Status</span></div>
              </div>
            </div>
            <!-- 2. the users, with their usage -->
            <div class="tgs__scene tgs__scene--2">
              <div class="tgs__msg tgs__msg--bot tgs__users">
                <b><i class="pi pi-users ui-emoji-icon" />Users</b>
                <span v-for="(w, i) in [70, 35, 90]" :key="i" class="tgs__user"><span class="tgs__uname" /><span class="tgs__ubar"><i :style="{ width: `${w}%` }" /></span><span class="tgs__uedit"><i class="pi pi-pencil ui-emoji-icon" /></span></span>
              </div>
            </div>
            <!-- 3. a new user, created in the chat -->
            <div class="tgs__scene tgs__scene--3">
              <div class="tgs__msg tgs__msg--me"><i class="pi pi-plus ui-emoji-icon" />30 GB · 30 days</div>
              <div class="tgs__msg tgs__msg--bot"><b><i class="pi pi-check-circle ui-emoji-icon ui-emoji-icon--success" />User created</b><span class="tgs__link"><i class="pi pi-link ui-emoji-icon" />link</span></div>
            </div>
          </div>
          <span class="tgs__finger">●</span>
        </div>
      </div>
      <ol class="tgs__steps">
        <li v-for="(s, i) in steps" :key="s" :style="{ '--i': i }"><span>{{ i + 1 }}</span>{{ t(`telegram.${s}`) }}</li>
      </ol>
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

/* --- the bot, looped: 9 s, three scenes of 3 s (menu, users, a new user) --- */
.tgs {
  --tg: #229ed9;
  --dur: 9s;
  position: relative;
  width: 100%;
  height: 13rem;
  display: grid;
  place-items: center;
  overflow: hidden;
  border-radius: 16px;
  background: radial-gradient(120% 100% at 50% 0%, rgb(34 158 217 / 16%), transparent 70%), var(--p-content-hover-background);
}
.tgs__phone {
  position: relative;
  width: 9.6rem;
  height: 12rem;
  overflow: hidden;
  border: 0.35rem solid #1f2937;
  border-radius: 1.4rem;
  background: #dbe7ef;
  box-shadow: 0 14px 30px -14px rgb(0 0 0 / 55%);
  text-align: start;
}
.tgs__head {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.55rem 0.45rem 0.35rem;
  background: #fff;
  color: #111827;
  font-size: 0.48rem;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
}
.tgs__avatar {
  flex: none;
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
  background: linear-gradient(160deg, #37bbfe, #007dbb);
}
.tgs__chat {
  position: relative;
  height: calc(100% - 1.7rem);
}
.tgs__scene {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 0.3rem;
  padding: 0.4rem;
  font-size: 0.46rem;
  color: #111827;
  opacity: 0;
}
.tgs__scene--1 { animation: tgs-1 var(--dur) infinite; }
.tgs__scene--2 { animation: tgs-2 var(--dur) infinite; }
.tgs__scene--3 { animation: tgs-3 var(--dur) infinite; }
.tgs__msg {
  max-width: 92%;
  padding: 0.3rem 0.4rem;
  border-radius: 0.55rem;
  box-shadow: 0 1px 1px rgb(0 0 0 / 10%);
}
.tgs__msg--me {
  align-self: flex-end;
  background: #e1ffc7;
}
.tgs__msg--bot {
  align-self: flex-start;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  background: #fff;
}
.tgs__kb {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.18rem;
}
.tgs__key {
  padding: 0.18rem 0.15rem;
  border-radius: 0.3rem;
  text-align: center;
  white-space: nowrap;
  font-weight: 700;
  color: #0b6e99;
  background: rgb(34 158 217 / 12%);
}
.tgs__key--users { animation: tgs-key-users var(--dur) infinite; }
.tgs__users {
  width: 92%;
}
.tgs__user {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
.tgs__uname {
  width: 1.6rem;
  height: 0.28rem;
  border-radius: 999px;
  background: rgb(17 24 39 / 18%);
}
.tgs__ubar {
  flex: 1;
  height: 0.25rem;
  border-radius: 999px;
  overflow: hidden;
  background: rgb(17 24 39 / 10%);
}
.tgs__ubar i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #34d399, #10b981);
}
.tgs__uedit {
  font-size: 0.42rem;
}
.tgs__link {
  padding: 0.15rem 0.3rem;
  border-radius: 0.3rem;
  font-weight: 700;
  color: #0b6e99;
  background: rgb(34 158 217 / 12%);
}
.tgs__finger {
  position: absolute;
  z-index: 5;
  font-size: 0.85rem;
  line-height: 1;
  color: rgb(17 24 39 / 55%);
  pointer-events: none;
  animation: tgs-finger var(--dur) infinite ease-in-out;
}
@keyframes tgs-1 {
  0%, 2% { opacity: 0; transform: translateY(6px); }
  6%, 30% { opacity: 1; transform: none; }
  34%, 64% { opacity: 0; }
  68%, 100% { opacity: 0; }
}
@keyframes tgs-2 {
  0%, 32% { opacity: 0; transform: translateY(6px); }
  37%, 62% { opacity: 1; transform: none; }
  66%, 100% { opacity: 0; }
}
@keyframes tgs-3 {
  0%, 65% { opacity: 0; transform: translateY(6px); }
  70%, 96% { opacity: 1; transform: none; }
  100% { opacity: 0; }
}
@keyframes tgs-key-users {
  0%, 22% { box-shadow: none; }
  25%, 31% { box-shadow: 0 0 0 2px rgb(34 158 217 / 55%); }
  33%, 100% { box-shadow: none; }
}
/* (in the phone) the "Users" key, then send: a new user */
@keyframes tgs-finger {
  0%, 10% { left: 60%; top: 92%; opacity: 0; transform: scale(1); }
  14% { opacity: 1; }
  23% { left: 28%; top: 68%; transform: scale(1); }
  26% { transform: scale(0.7); }
  30% { left: 28%; top: 68%; transform: scale(1); }
  52% { left: 82%; top: 93%; opacity: 1; }
  58% { left: 82%; top: 93%; transform: scale(0.7); }
  62% { transform: scale(1); }
  72%, 100% { left: 70%; top: 98%; opacity: 0; }
}
.tgs__steps {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  width: 100%;
  margin: 0;
  padding: 0;
  list-style: none;
  text-align: start;
}
.tgs__steps li {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.4rem 0.55rem;
  border-radius: 10px;
  font-size: 0.86rem;
  color: var(--p-text-muted-color);
  animation: tgs-step var(--dur, 9s) infinite;
  animation-delay: calc(9s * var(--i) / 3);
}
.tgs__steps li span {
  flex: none;
  display: grid;
  place-items: center;
  width: 1.45rem;
  height: 1.45rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  color: #fff;
  background: #229ed9;
}
@keyframes tgs-step {
  0%, 33% { background: rgb(34 158 217 / 12%); color: var(--p-text-color); }
  34%, 100% { background: transparent; color: var(--p-text-muted-color); }
}
@media (prefers-reduced-motion: reduce) {
  .tgs *,
  .tgs__steps li {
    animation: none !important;
  }
  .tgs__scene--1 {
    opacity: 1;
  }
  .tgs__finger {
    display: none;
  }
}
</style>
