<script setup lang="ts">
/**
 * The bot's animated button icons: on or off, how many of its buttons found an animated icon, a refusal from
 * Telegram (the owner has no Premium) and the custom emoji sets they come from (advanced).
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'
import { apiErrorMessage } from '@/core/api/client'
import { telegramBotApi, type IconsInfo } from '@/features/telegram-bot/api'

const props = defineProps<{ icons: IconsInfo }>()
const emit = defineEmits<{ saved: [icons: IconsInfo] }>()
const { t } = useI18n()
const toast = useToast()

const enabled = ref(props.icons.enabled)
const sets = ref(props.icons.sets)
const saving = ref(false)
const showSets = ref(false)
watch(
  () => props.icons,
  (icons) => {
    enabled.value = icons.enabled
    sets.value = icons.sets
  },
)

const coverage = computed(() => {
  const { found, needed } = props.icons
  return found != null && needed ? { found, needed, percent: Math.round((found / needed) * 100) } : null
})
const setsChanged = computed(() => sets.value.trim() !== props.icons.sets.trim())

/** The bot's home, as Telegram draws it: colours from the button styles, the icons moving when they are on. */
const preview = computed(() => [
  [
    { emoji: '👥', label: t('tgBot.icons.preview.users'), kind: 'primary' },
    { emoji: '➕', label: t('tgBot.icons.preview.new'), kind: 'success' },
  ],
  [
    { emoji: '📊', label: t('tgBot.icons.preview.status'), kind: 'plain' },
    { emoji: '🗑', label: t('tgBot.icons.preview.delete'), kind: 'danger' },
  ],
])

async function save(input: { enabled?: boolean; sets?: string }) {
  saving.value = true
  try {
    const icons = await telegramBotApi.saveIcons(input)
    emit('saved', icons)
    toast.add({ severity: 'success', summary: t('tgBot.icons.saved'), life: 2500 })
  } catch (e) {
    enabled.value = props.icons.enabled
    toast.add({ severity: 'error', summary: t('tgBot.icons.saveFailed'), detail: apiErrorMessage(e), life: 6000 })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="tb-icons">
    <header class="tb-icons__head">
      <span class="tb-icons__icon" aria-hidden="true"><i class="pi pi-sparkles" /></span>
      <div class="flex-1 min-w-0">
        <h3 class="tb-icons__title">{{ t('tgBot.icons.title') }}</h3>
        <p class="tb-icons__sub">{{ t('tgBot.icons.sub') }}</p>
      </div>
      <ToggleSwitch v-model="enabled" input-id="tb-icons-on" :disabled="saving" :aria-label="t('tgBot.icons.title')" @update:model-value="(on: boolean) => save({ enabled: on })" />
    </header>

    <div class="tb-icons__body">
      <!-- What it looks like in the chat -->
      <div class="tb-preview" :class="{ 'tb-preview--live': enabled && !icons.refused }" aria-hidden="true">
        <div v-for="(row, i) in preview" :key="i" class="tb-preview__row">
          <span v-for="b in row" :key="b.label" class="tb-preview__btn" :class="`tb-preview__btn--${b.kind}`">
            <span class="tb-preview__emoji">{{ b.emoji }}</span>{{ b.label }}
          </span>
        </div>
      </div>

      <div class="tb-icons__info">
        <p class="tb-icons__note" :class="{ 'tb-icons__note--warn': enabled }"><i class="pi pi-star-fill" />{{ t('tgBot.icons.premium') }}</p>

        <Message v-if="icons.refused" severity="warn" :closable="false" class="tb-icons__msg">
          <div class="flex flex-col gap-2">
            <span>{{ t('tgBot.icons.refused') }}</span>
            <Button :label="t('tgBot.icons.tryAgain')" icon="pi pi-refresh" size="small" severity="secondary" class="self-start" :loading="saving" @click="save({ enabled: true })" />
          </div>
        </Message>

        <div v-else-if="enabled && coverage" class="tb-cover">
          <div class="tb-cover__line">
            <span>{{ t('tgBot.icons.coverage', { found: coverage.found, needed: coverage.needed }) }}</span>
            <b>{{ coverage.percent }}%</b>
          </div>
          <div class="tb-cover__bar"><span :style="{ inlineSize: `${coverage.percent}%` }" /></div>
          <p v-if="icons.missing.length" class="tb-cover__missing">
            {{ t('tgBot.icons.missing') }} <span class="tb-cover__emoji">{{ icons.missing.join(' ') }}</span>
          </p>
        </div>
        <p v-else-if="enabled && icons.found == null" class="tb-icons__hint">{{ t('tgBot.icons.notChecked') }}</p>

        <Button
          :label="t('tgBot.icons.sets')"
          :icon="showSets ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
          icon-pos="right"
          severity="secondary"
          text
          size="small"
          class="self-start"
          :aria-expanded="showSets"
          @click="showSets = !showSets"
        />
        <div v-if="showSets" class="tb-sets">
          <label for="tb-icon-sets" class="tb-icons__hint">{{ t('tgBot.icons.setsHint') }}</label>
          <Textarea id="tb-icon-sets" v-model="sets" rows="3" auto-resize dir="ltr" :placeholder="icons.default_sets.join(', ')" class="w-full" />
          <div class="flex gap-2 flex-wrap">
            <Button :label="t('common.save')" icon="pi pi-check" size="small" :disabled="!setsChanged" :loading="saving" @click="save({ sets })" />
            <Button v-if="icons.sets" :label="t('tgBot.icons.useDefault')" size="small" severity="secondary" text :disabled="saving" @click="save({ sets: '' })" />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.tb-icons {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 22px;
  background:
    radial-gradient(circle at 100% 0%, color-mix(in srgb, #a855f7 12%, transparent), transparent 55%),
    var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.tb-icons__head {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.tb-icons__icon {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 13px;
  background: linear-gradient(145deg, #c084fc, #8b5cf6);
  color: #fff;
  font-size: 1.1rem;
}
.tb-icons__title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
}
.tb-icons__sub,
.tb-icons__hint {
  margin: 0.15rem 0 0;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}
.tb-icons__body {
  display: grid;
  grid-template-columns: minmax(0, 18rem) minmax(0, 1fr);
  gap: 1.25rem;
  align-items: start;
}
@media (max-width: 720px) {
  .tb-icons__body {
    grid-template-columns: minmax(0, 1fr);
  }
}
.tb-icons__info {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-width: 0;
}
.tb-icons__note {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}
.tb-icons__note i {
  margin-top: 0.15rem;
  color: #a855f7;
}
.tb-icons__note--warn {
  padding: 0.6rem 0.75rem;
  border-radius: 12px;
  background: color-mix(in srgb, #f59e0b 12%, transparent);
  color: var(--text-color);
}
.tb-icons__note--warn i {
  color: #f59e0b;
}
.tb-icons__msg {
  margin: 0;
}

/* A chat's inline keyboard */
.tb-preview {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.75rem;
  border-radius: 18px;
  background: linear-gradient(160deg, color-mix(in srgb, #229ed9 14%, var(--p-content-background)), color-mix(in srgb, #8b5cf6 10%, var(--p-content-background)));
}
.tb-preview__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.35rem;
}
.tb-preview__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  min-width: 0;
  padding: 0.5rem 0.4rem;
  border-radius: 10px;
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #fff;
  background: color-mix(in srgb, #64748b 55%, transparent);
  backdrop-filter: blur(6px);
}
.tb-preview__btn--primary {
  background: #3390ec;
}
.tb-preview__btn--success {
  background: #34c759;
}
.tb-preview__btn--danger {
  background: #ff3b30;
}
.tb-preview__emoji {
  display: inline-block;
}
.tb-preview--live .tb-preview__emoji {
  animation: tb-wiggle 2.4s ease-in-out infinite;
}
.tb-preview--live .tb-preview__row:nth-child(2) .tb-preview__emoji {
  animation-delay: 0.6s;
}
@keyframes tb-wiggle {
  0%,
  60%,
  100% {
    transform: none;
  }
  70% {
    transform: scale(1.25) rotate(-10deg);
  }
  80% {
    transform: scale(1.15) rotate(8deg);
  }
  90% {
    transform: scale(1.05);
  }
}
@media (prefers-reduced-motion: reduce) {
  .tb-preview--live .tb-preview__emoji {
    animation: none;
  }
}

/* Coverage */
.tb-cover {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.875rem;
}
.tb-cover__line {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}
.tb-cover__bar {
  height: 0.45rem;
  border-radius: 999px;
  background: var(--p-content-border-color);
  overflow: hidden;
}
.tb-cover__bar span {
  display: block;
  block-size: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #8b5cf6, #c084fc);
  transition: inline-size 0.5s ease;
}
.tb-cover__missing {
  margin: 0.2rem 0 0;
  color: var(--text-color-secondary);
  font-size: 0.8rem;
}
.tb-cover__emoji {
  letter-spacing: 0.15em;
}
.tb-sets {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
</style>
