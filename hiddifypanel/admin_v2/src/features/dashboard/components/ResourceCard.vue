<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import ResourceGauge from './ResourceGauge.vue'
import Sparkline from './Sparkline.vue'

const props = withDefaults(
  defineProps<{
    title: string
    icon: string
    accent: string
    percent: number
    /** Headline reading, e.g. `3.5 / 7.8 GB`. */
    value: string
    caption?: string
    gaugeValue?: string
    gaugeCaption?: string
    sparkline?: number[]
    autoColor?: boolean
    defaultExpanded?: boolean
  }>(),
  { sparkline: () => [], autoColor: true, defaultExpanded: false },
)

const { t } = useI18n()
const expanded = ref(props.defaultExpanded)
</script>

<template>
  <section class="resource" :class="{ 'resource--open': expanded }" :style="{ '--res-accent': accent }">
    <div class="resource__accent" />
    <div class="resource__head">
      <ResourceGauge
        :percent="percent"
        :color="accent"
        :value="gaugeValue"
        :caption="gaugeCaption"
        :auto-color="autoColor"
        :size="84"
      />
      <div class="resource__info">
        <div class="resource__titles">
          <span class="resource__icon"><i :class="icon" /></span>
          <h3 class="resource__title">{{ title }}</h3>
        </div>
        <p class="resource__value">{{ value }}</p>
        <p v-if="caption" class="resource__caption">{{ caption }}</p>
      </div>
      <Button
        v-if="$slots.detail"
        class="resource__toggle"
        :icon="expanded ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
        :aria-label="expanded ? t('dashboard.collapse') : t('dashboard.expand')"
        severity="secondary"
        text
        rounded
        @click="expanded = !expanded"
      />
    </div>
    <Sparkline
      v-if="sparkline.length > 1"
      :values="sparkline"
      :color="accent"
      :height="38"
      class="resource__spark"
    />
    <div class="resource__detail" :class="{ 'resource__detail--open': expanded }">
      <div class="resource__detail-inner">
        <slot name="detail" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.resource {
  --res-accent: var(--p-primary-color);
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--p-content-border-color);
  border-radius: 1rem;
  background:
    radial-gradient(130% 130% at 0% 0%, color-mix(in srgb, var(--res-accent) 10%, transparent) 0%, transparent 60%),
    var(--p-content-background);
  box-shadow: 0 1px 2px rgb(0 0 0 / 4%), 0 10px 26px -20px rgb(15 23 42 / 35%);
  transition: box-shadow 0.2s ease;
}
.resource--open {
  box-shadow: 0 1px 2px rgb(0 0 0 / 5%), 0 22px 44px -26px rgb(15 23 42 / 45%);
}
.resource__accent {
  height: 3px;
  background: linear-gradient(90deg, var(--res-accent), color-mix(in srgb, var(--res-accent) 25%, transparent));
}
.resource__head {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1rem 0.5rem 1.1rem;
}
.resource__info {
  flex: 1;
  min-width: 0;
}
.resource__titles {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.resource__icon {
  color: var(--res-accent);
  font-size: 0.9rem;
}
.resource__title {
  margin: 0;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--p-text-muted-color);
}
.resource__value {
  margin: 0.35rem 0 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--p-text-color);
  font-variant-numeric: tabular-nums;
}
.resource__caption {
  margin: 0.2rem 0 0;
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.resource__toggle {
  align-self: flex-start;
}
.resource__spark {
  margin-top: -0.25rem;
}
.resource__detail {
  max-height: 0;
  overflow: hidden;
  opacity: 0;
  transition: max-height 0.35s ease, opacity 0.25s ease;
}
.resource__detail--open {
  /* generous cap so tall details (many CPU cores) still fit, then scroll */
  max-height: 60rem;
  overflow-y: auto;
  opacity: 1;
}
.resource__detail-inner {
  padding: 0.75rem 1.1rem 1.1rem;
  border-top: 1px solid var(--p-content-border-color);
  margin-top: 0.5rem;
}
</style>
