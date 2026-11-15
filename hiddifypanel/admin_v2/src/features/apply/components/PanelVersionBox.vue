<script setup lang="ts">
/**
 * The Update card's version box: the panel's version and its channel, a "Check for updates" button, and the answer
 * under the version: a newer release (which one) or "the latest version". The server looks once a day by itself.
 */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import UpdateGlyph from '@/shared/components/UpdateGlyph.vue'
import { loadPanelUpdate, panelUpdate } from '@/shared/composables/usePanelUpdate'

const { t, locale } = useI18n()
const checking = ref(false)
/** The admin asked: "the latest version" is said only then (a new version is said whenever it is known) */
const asked = ref(false)
const failed = ref(false)

const status = computed(() => panelUpdate.value)
const result = computed<'new' | 'ok' | 'warn' | null>(() => {
  if (checking.value) return null
  if (status.value?.outdated) return 'new'
  if (!asked.value) return null
  if (failed.value || status.value?.error) return 'warn'
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

async function check() {
  checking.value = true
  failed.value = false
  // at least a beat of the turning arrows: an answer from cache is instant
  const [answer] = await Promise.all([loadPanelUpdate(true), new Promise((done) => setTimeout(done, 700))])
  failed.value = !answer
  asked.value = true
  checking.value = false
}

onMounted(() => void loadPanelUpdate())
</script>

<template>
  <div class="pv" :class="{ 'pv--new': result === 'new' }">
    <div class="pv__row">
      <div class="pv__current">
        <span class="pv__label">{{ t('apply.version.current') }}</span>
        <span class="pv__number" dir="ltr">{{ status?.current ?? '—' }}</span>
        <span v-if="status" class="pv__channel" :class="`pv__channel--${status.channel}`">{{ t(`apply.version.channel.${status.channel}`) }}</span>
      </div>
      <button type="button" class="pv__check" :disabled="checking" @click="check">
        <UpdateGlyph kind="check" :spinning="checking" size="1rem" />
        <span>{{ checking ? t('apply.version.checking') : t('apply.version.check') }}</span>
      </button>
    </div>

    <Transition name="pv-news" mode="out-in">
      <div v-if="result === 'new'" key="new" class="pv__news pv__news--new">
        <UpdateGlyph kind="new" size="2rem" />
        <div class="pv__news-text">
          <b>{{ t('apply.version.newAvailable') }}</b>
          <span>
            <span class="pv__pill" dir="ltr">{{ status?.latest }}</span>
            {{ t('apply.version.newHint') }}
          </span>
        </div>
      </div>
      <div v-else-if="result === 'ok'" key="ok" class="pv__news pv__news--ok">
        <UpdateGlyph kind="ok" size="2rem" />
        <div class="pv__news-text">
          <b>{{ t('apply.version.latest') }}</b>
          <span>{{ t('apply.version.latestHint', { version: status?.current }) }}</span>
        </div>
      </div>
      <div v-else-if="result === 'warn'" key="warn" class="pv__news pv__news--warn">
        <UpdateGlyph kind="warn" size="2rem" />
        <div class="pv__news-text">
          <b>{{ t('apply.version.failed') }}</b>
          <span>{{ t('apply.version.failedHint') }}</span>
        </div>
      </div>
    </Transition>

    <p v-if="checkedAgo" class="pv__when">{{ t('apply.version.checkedAgo', { when: checkedAgo }) }}</p>
  </div>
</template>

<style scoped>
.pv {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.75rem 0.85rem;
  border-radius: 14px;
  background: color-mix(in srgb, var(--p-text-color) 4%, transparent);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--p-text-color) 6%, transparent);
  transition:
    background 0.4s,
    box-shadow 0.4s;
}
.pv--new {
  background: color-mix(in srgb, #22c55e 7%, transparent);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, #22c55e 30%, transparent);
}
.pv__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem 0.75rem;
}
.pv__current {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 0.25rem 0.5rem;
  min-width: 0;
}
.pv__label {
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.pv__number {
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  font-variant-numeric: tabular-nums;
}
.pv__channel {
  align-self: center;
  padding: 0.05rem 0.45rem;
  border-radius: 999px;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #2563eb;
  background: color-mix(in srgb, #3b82f6 13%, transparent);
}
.pv__channel--beta {
  color: #c2410c;
  background: color-mix(in srgb, #f97316 14%, transparent);
}
.pv__check {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.42rem 0.8rem;
  border: 0;
  border-radius: 999px;
  color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 11%, transparent);
  font: inherit;
  font-size: 0.8rem;
  font-weight: 650;
  cursor: pointer;
  transition:
    background 0.2s,
    transform 0.25s cubic-bezier(0.32, 0.72, 0, 1);
}
.pv__check:hover:not(:disabled) {
  background: color-mix(in srgb, var(--p-primary-color) 18%, transparent);
}
.pv__check:active:not(:disabled) {
  transform: scale(0.95);
}
.pv__check:disabled {
  cursor: progress;
  opacity: 0.85;
}
.pv__news {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.6rem 0.7rem;
  border-radius: 12px;
}
.pv__news--new {
  background: linear-gradient(135deg, color-mix(in srgb, #22c55e 16%, transparent), color-mix(in srgb, #22c55e 5%, transparent));
}
.pv__news--ok {
  background: color-mix(in srgb, #3b82f6 9%, transparent);
}
.pv__news--warn {
  background: color-mix(in srgb, #f59e0b 11%, transparent);
}
.pv__news-text {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}
.pv__news-text b {
  font-size: 0.9rem;
  color: var(--p-text-color);
}
.pv__pill {
  display: inline-block;
  margin-inline-end: 0.25rem;
  padding: 0 0.5rem;
  border-radius: 999px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: #fff;
  background: linear-gradient(180deg, #4ade80, #16a34a);
  box-shadow: 0 3px 8px -3px rgb(22 163 74 / 60%);
}
.pv__when {
  margin: 0;
  font-size: 0.7rem;
  color: var(--p-text-muted-color);
}
.pv-news-enter-active {
  transition:
    opacity 0.35s ease,
    transform 0.5s cubic-bezier(0.32, 0.72, 0, 1);
}
.pv-news-leave-active {
  transition: opacity 0.15s ease;
}
.pv-news-enter-from {
  opacity: 0;
  transform: translateY(-6px) scale(0.97);
}
.pv-news-leave-to {
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .pv-news-enter-active {
    transition: none;
  }
}
</style>
