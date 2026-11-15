<script setup lang="ts">
/**
 * The Update card's version box, in the style of iOS's Software Update: the panel as an app (its icon, name and
 * version, the channel), and under a hairline the answer of the check (the button sits beside Update): checking, a
 * newer release (which one), up to date, or could not check. A footnote says when the panel last looked.
 */
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import UpdateGlyph from '@/shared/components/UpdateGlyph.vue'
import { loadPanelUpdate, panelCheck, panelUpdate } from '@/shared/composables/usePanelUpdate'

const { t, locale } = useI18n()

const status = computed(() => panelUpdate.value)
/** "Up to date" only after the admin asked; a new version whenever it is known */
const state = computed<'checking' | 'new' | 'ok' | 'warn' | null>(() => {
  if (panelCheck.checking) return 'checking'
  if (status.value?.outdated) return 'new'
  if (!panelCheck.asked) return null
  if (panelCheck.failed || status.value?.error) return 'warn'
  return 'ok'
})

const checkedAgo = computed(() => {
  const at = status.value?.checked_at
  if (!at) return ''
  const diff = at - Date.now() / 1000
  const rtf = new Intl.RelativeTimeFormat(locale.value, { numeric: 'auto' })
  for (const [unit, size] of [
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ] as const)
    if (Math.abs(diff) >= size) return rtf.format(Math.round(diff / size), unit)
  return rtf.format(0, 'minute')
})

onMounted(() => void loadPanelUpdate())
</script>

<template>
  <section class="pv" :class="state ? `pv--${state}` : ''">
    <div class="pv__group">
      <div class="pv__app">
        <span class="pv__icon" aria-hidden="true">
          <svg viewBox="0 0 32 32">
            <rect x="7" y="17" width="4.4" height="8" rx="2.2" fill="#fff" fill-opacity="0.75" />
            <rect x="13.8" y="12" width="4.4" height="13" rx="2.2" fill="#fff" fill-opacity="0.88" />
            <rect x="20.6" y="7" width="4.4" height="18" rx="2.2" fill="#fff" />
          </svg>
        </span>
        <div class="pv__app-text">
          <b>{{ t('apply.version.app') }}</b>
          <span
            >{{ t('apply.version.current') }} <bdi class="pv__number" dir="ltr">{{ status?.current ?? '—' }}</bdi></span
          >
        </div>
        <span v-if="status" class="pv__channel" :class="`pv__channel--${status.channel}`">{{ t(`apply.version.channel.${status.channel}`) }}</span>
      </div>

      <Transition name="pv-row">
        <div v-if="state" :key="state" class="pv__status">
          <span class="pv__glyph">
            <UpdateGlyph v-if="state === 'checking'" kind="check" spinning size="1.35rem" class="pv__spin" />
            <UpdateGlyph v-else :kind="state" size="1.9rem" />
          </span>
          <div class="pv__status-text">
            <template v-if="state === 'checking'">
              <b>{{ t('apply.version.checking') }}</b>
            </template>
            <template v-else-if="state === 'new'">
              <b
                >{{ t('apply.version.newTitle') }} <bdi class="pv__new-number" dir="ltr">{{ status?.latest }}</bdi></b
              >
              <span>{{ t('apply.version.newHint') }}</span>
            </template>
            <template v-else-if="state === 'ok'">
              <b>{{ t('apply.version.latest') }}</b>
              <span>{{ t('apply.version.latestHint', { version: status?.current }) }}</span>
            </template>
            <template v-else>
              <b>{{ t('apply.version.failed') }}</b>
              <span>{{ t('apply.version.failedHint') }}</span>
            </template>
          </div>
          <span v-if="state === 'new'" class="pv__badge">{{ t('apply.version.newBadge') }}</span>
        </div>
      </Transition>
    </div>
    <p class="pv__foot">
      {{ t('apply.version.daily') }}<template v-if="checkedAgo"> · {{ t('apply.version.lastChecked', { when: checkedAgo }) }}</template>
    </p>
  </section>
</template>

<style scoped>
.pv {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
/* iOS's inset grouped cell: a soft fill, round corners, a hairline between rows */
.pv__group {
  position: relative;
  overflow: hidden;
  border-radius: 1.15rem;
  background: color-mix(in srgb, var(--p-text-color) 4.5%, transparent);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.45),
    inset 0 0 0 0.5px color-mix(in srgb, var(--p-text-color) 9%, transparent);
  transition:
    background 0.45s,
    box-shadow 0.45s;
}
html.app-dark .pv__group {
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.06),
    inset 0 0 0 0.5px rgb(255 255 255 / 0.08);
}
.pv--new .pv__group {
  background: radial-gradient(130% 120% at 100% 100%, color-mix(in srgb, #22c55e 16%, transparent), transparent 62%), color-mix(in srgb, var(--p-text-color) 4%, transparent);
}
.pv__app {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0.85rem;
}
/* the panel as an app: a squircle with its bars, lit from above */
.pv__icon {
  position: relative;
  display: grid;
  place-items: center;
  flex: none;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 28%;
  background: linear-gradient(160deg, #60a5fa 0%, #3b5bdb 55%, #4338ca 100%);
  box-shadow:
    0 6px 14px -6px rgb(59 91 219 / 0.6),
    inset 0 0 0 0.5px rgb(0 0 0 / 0.12);
  overflow: hidden;
}
.pv__icon::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgb(255 255 255 / 0.35), transparent 50%);
}
.pv__icon svg {
  position: relative;
  z-index: 1;
  width: 1.75rem;
  height: 1.75rem;
}
.pv__app-text {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  line-height: 1.3;
}
.pv__app-text b {
  font-size: 0.95rem;
  font-weight: 650;
  letter-spacing: -0.01em;
}
.pv__app-text span {
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.pv__number {
  font-weight: 650;
  color: var(--p-text-color);
  font-variant-numeric: tabular-nums;
}
.pv__channel {
  flex: none;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 650;
  color: #0a84ff;
  background: color-mix(in srgb, #0a84ff 13%, transparent);
}
.pv__channel--beta {
  color: #ff9f0a;
  background: color-mix(in srgb, #ff9f0a 15%, transparent);
}
/* the check's answer, under an inset hairline (from the text on, as iOS draws it) */
.pv__status {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.7rem 0.85rem 0.75rem;
}
.pv__status::before {
  content: '';
  position: absolute;
  top: 0;
  inset-inline: 4.35rem 0;
  border-top: 0.5px solid color-mix(in srgb, var(--p-text-color) 12%, transparent);
}
.pv__glyph {
  display: grid;
  place-items: center;
  flex: none;
  width: 2.75rem;
}
.pv__spin {
  color: var(--p-text-muted-color);
}
.pv__status-text {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
  line-height: 1.35;
}
.pv__status-text b {
  font-size: 0.88rem;
  font-weight: 650;
}
.pv__status-text span {
  font-size: 0.76rem;
  color: var(--p-text-muted-color);
}
.pv__new-number {
  color: #16a34a;
  font-variant-numeric: tabular-nums;
}
html.app-dark .pv__new-number {
  color: #4ade80;
}
.pv__badge {
  flex: none;
  padding: 0.18rem 0.6rem;
  border-radius: 999px;
  font-size: 0.68rem;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(180deg, #34d058, #16a34a);
  box-shadow:
    0 4px 10px -4px rgb(22 163 74 / 0.7),
    inset 0 1px 0 rgb(255 255 255 / 0.35);
  animation: pv-badge 2.4s ease-in-out infinite;
}
@keyframes pv-badge {
  50% {
    box-shadow:
      0 4px 14px -2px rgb(22 163 74 / 0.75),
      inset 0 1px 0 rgb(255 255 255 / 0.35);
  }
}
/* iOS's footnote under a group */
.pv__foot {
  margin: 0;
  padding-inline: 0.85rem;
  font-size: 0.7rem;
  line-height: 1.4;
  color: var(--p-text-muted-color);
}
.pv-row-enter-active {
  transition:
    opacity 0.35s ease,
    transform 0.5s cubic-bezier(0.32, 0.72, 0, 1);
}
.pv-row-leave-active {
  position: absolute;
  inset-inline: 0;
  bottom: 0;
  transition: opacity 0.12s ease;
}
.pv-row-enter-from {
  opacity: 0;
  transform: translateY(-6px);
}
.pv-row-leave-to {
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .pv-row-enter-active {
    transition: none;
  }
  .pv__badge {
    animation: none;
  }
}
</style>
