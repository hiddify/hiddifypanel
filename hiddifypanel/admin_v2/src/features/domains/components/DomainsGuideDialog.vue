<script setup lang="ts">
/**
 * Shown once (this browser) on the Domains page: how to reorder domains, as a spotlight. A small list drawn like the
 * real rows loops: a finger takes row 3 by its handle and drags it to the top, the others move down, the numbers stay
 * (1 · 2 · 3 again); three steps are lit with it. "Got it" and it does not come back.
 */
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'

const visible = defineModel<boolean>('visible', { required: true })
const emit = defineEmits<{ gotIt: [] }>()
const { t } = useI18n()

const ROWS = [
  { key: 'a', icon: 'pi pi-server', color: 'var(--p-green-500, #22c55e)', width: 62 },
  { key: 'b', icon: 'pi pi-cloud', color: 'var(--p-orange-500, #f97316)', width: 48 },
  { key: 'c', icon: 'pi pi-link', color: 'var(--p-blue-500, #3b82f6)', width: 56 },
]
const steps = ['grab', 'drag', 'order'] as const

function gotIt() {
  visible.value = false
  emit('gotIt')
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    modal
    :closable="false"
    :close-on-escape="false"
    :show-header="false"
    :draggable="false"
    :style="{ width: 'min(27rem, calc(100vw - 1.5rem))' }"
    class="dg"
  >
    <div class="dg__body">
      <span class="dg__badge" aria-hidden="true"><i class="pi pi-sort-alt" /></span>
      <h3 class="dg__title">{{ t('domains.guide.title') }}</h3>
      <p class="dg__lead">{{ t('domains.guide.lead') }}</p>

      <!-- The list, drawn like the page's rows; it follows the page's direction (mirrored in Persian) -->
      <div class="dg__stage" aria-hidden="true">
        <div class="dg__list">
          <span v-for="n in 3" :key="n" class="dg__n" :style="{ '--slot': n - 1 }">{{ n }}</span>
          <div v-for="(r, i) in ROWS" :key="r.key" class="dg__row" :class="`dg__row--${r.key}`" :style="{ '--slot': i, '--kind': r.color }">
            <span class="dg__grip"><i class="pi pi-bars" /><span v-if="r.key === 'c'" class="dg__finger" /></span>
            <span class="dg__gap" />
            <span class="dg__icon"><i :class="r.icon" /></span>
            <span class="dg__lines">
              <span class="dg__name" :style="{ width: `${r.width}%` }" />
              <span class="dg__chip" />
            </span>
          </div>
        </div>
      </div>

      <ol class="dg__steps">
        <li v-for="(s, i) in steps" :key="s" :style="{ '--i': i }">
          <span>{{ i + 1 }}</span>
          <div>
            <b>{{ t(`domains.guide.${s}Title`) }}</b>
            <small>{{ t(`domains.guide.${s}Text`) }}</small>
          </div>
        </li>
      </ol>

      <Button :label="t('domains.guide.gotIt')" icon="pi pi-check" class="dg__got" autofocus @click="gotIt" />
    </div>
  </Dialog>
</template>

<style scoped>
.dg__body {
  --dur: 9s;
  --row: 2.6rem;
  --step: calc(var(--row) + 0.45rem);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 0.25rem 0.1rem 0.1rem;
  text-align: center;
}
.dg__badge {
  display: grid;
  place-items: center;
  width: 3.1rem;
  height: 3.1rem;
  border-radius: 50%;
  font-size: 1.3rem;
  color: #fff;
  background: linear-gradient(135deg, var(--p-indigo-400, #818cf8), var(--p-indigo-600, #4f46e5));
  box-shadow: 0 10px 24px -10px var(--p-indigo-500, #6366f1);
}
.dg__title {
  margin: 0;
  font-size: 1.12rem;
  font-weight: 700;
}
.dg__lead {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.6;
  color: var(--p-text-muted-color);
}

/* --- the scene: 9 s, row "c" (3rd) taken to the top and dropped; rows a and b move down one place --- */
.dg__stage {
  width: 100%;
  padding: 0.9rem 0.9rem 1rem;
  border-radius: 16px;
  background:
    radial-gradient(120% 100% at 50% 0%, color-mix(in srgb, var(--p-indigo-500, #6366f1) 14%, transparent), transparent 70%),
    var(--p-content-hover-background, rgba(127, 127, 127, 0.07));
}
.dg__list {
  position: relative;
  height: calc(var(--step) * 3 - 0.45rem);
}
/* The numbers stay where they are: after the move the rows read 1 · 2 · 3 again */
.dg__n {
  position: absolute;
  inset-inline-start: 2.05rem;
  top: calc(var(--step) * var(--slot) + (var(--row) - 1.35rem) / 2);
  z-index: 2;
  display: grid;
  place-items: center;
  width: 1.35rem;
  height: 1.35rem;
  border-radius: 50%;
  font-size: 0.68rem;
  font-weight: 700;
  color: #fff;
  background: var(--p-indigo-500, #6366f1);
}
.dg__row {
  position: absolute;
  inset-inline: 0;
  top: calc(var(--step) * var(--slot));
  height: var(--row);
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding-inline: 0.35rem 0.6rem;
  border-radius: 11px;
  border: 1px solid var(--p-content-border-color);
  border-inline-start: 3px solid var(--kind);
  background: var(--p-content-background);
  text-align: start;
}
.dg__row--a,
.dg__row--b {
  animation: dg-down var(--dur) infinite;
}
.dg__row--c {
  z-index: 1;
  animation: dg-up var(--dur) infinite;
}
.dg__grip {
  display: grid;
  place-items: center;
  width: 1.3rem;
  font-size: 0.78rem;
  color: var(--p-text-muted-color);
}
.dg__row--c .dg__grip {
  animation: dg-grip var(--dur) infinite;
}
.dg__gap {
  width: 1.35rem;
}
.dg__icon {
  display: grid;
  place-items: center;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 8px;
  font-size: 0.8rem;
  color: var(--kind);
  background: color-mix(in srgb, var(--kind) 14%, transparent);
}
.dg__lines {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.dg__name {
  height: 0.42rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--p-text-color) 28%, transparent);
}
.dg__chip {
  width: 2.2rem;
  height: 0.32rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--kind) 45%, transparent);
}
/* the finger, a touch point on row 3's handle (it moves with the row): lands, holds, lets go */
.dg__grip {
  position: relative;
}
.dg__finger {
  position: absolute;
  z-index: 3;
  inset: 50% auto auto 50%;
  margin: -0.75rem 0 0 -0.75rem;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  background: color-mix(in srgb, var(--p-indigo-500, #6366f1) 30%, transparent);
  border: 2px solid color-mix(in srgb, var(--p-indigo-500, #6366f1) 70%, transparent);
  box-shadow: 0 2px 8px -2px rgb(15 23 42 / 35%);
  pointer-events: none;
  animation: dg-finger var(--dur) infinite ease-in-out;
}
@keyframes dg-up {
  0%, 22% { transform: none; box-shadow: none; }
  28% { transform: scale(1.03); box-shadow: 0 12px 24px -12px rgb(15 23 42 / 45%); }
  58% { transform: translateY(calc(var(--step) * -2)) scale(1.03); box-shadow: 0 12px 24px -12px rgb(15 23 42 / 45%); }
  64%, 92% { transform: translateY(calc(var(--step) * -2)); box-shadow: 0 0 0 2px var(--p-indigo-400, #818cf8); }
  100% { transform: none; box-shadow: none; }
}
@keyframes dg-down {
  0%, 30% { transform: none; }
  58%, 92% { transform: translateY(var(--step)); }
  100% { transform: none; }
}
@keyframes dg-grip {
  0%, 18% { color: var(--p-text-muted-color); }
  22%, 62% { color: var(--p-indigo-500, #6366f1); }
  66%, 100% { color: var(--p-text-muted-color); }
}
@keyframes dg-finger {
  0%, 8% { opacity: 0; transform: translate(0.6rem, 0.8rem) scale(1.2); }
  16% { opacity: 1; transform: none; }
  22%, 58% { opacity: 1; transform: scale(0.82); }
  64% { opacity: 1; transform: none; }
  74%, 100% { opacity: 0; transform: translate(0.6rem, 0.8rem); }
}

/* --- the steps, lit in thirds with the scene --- */
.dg__steps {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  width: 100%;
  margin: 0;
  padding: 0;
  list-style: none;
  text-align: start;
}
.dg__steps li {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.45rem 0.6rem;
  border-radius: 10px;
  animation: dg-step var(--dur) infinite;
  animation-delay: calc(var(--dur) * var(--i) / 3);
}
.dg__steps li > span {
  flex: none;
  display: grid;
  place-items: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 700;
  color: #fff;
  background: var(--p-indigo-500, #6366f1);
}
.dg__steps b {
  display: block;
  font-size: 0.88rem;
}
.dg__steps small {
  display: block;
  font-size: 0.78rem;
  line-height: 1.5;
  color: var(--p-text-muted-color);
}
@keyframes dg-step {
  0%, 33% { background: color-mix(in srgb, var(--p-indigo-500, #6366f1) 12%, transparent); }
  34%, 100% { background: transparent; }
}
.dg__got {
  width: 100%;
}
@media (prefers-reduced-motion: reduce) {
  .dg__row,
  .dg__grip,
  .dg__finger,
  .dg__steps li {
    animation: none !important;
  }
  .dg__finger {
    display: none;
  }
}
</style>
