<script setup lang="ts">
/**
 * Pages of a long list: a bar to drag through them (far left: the first page, far right: the last, in every
 * language), the page numbers around the current one, Previous / Next and a "page [n] of N" field to jump to.
 * `first` is the index of the first row shown (as PrimeVue's paginators keep it).
 */
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  rows: number
  totalRecords: number
  /** Previous / Next, a page number or a typed page scroll the window to the top (phones: the list is above). */
  scrollTopOnStep?: boolean
}>()
const first = defineModel<number>('first', { required: true })

const { t } = useI18n()

const pages = computed(() => Math.max(1, Math.ceil(props.totalRecords / Math.max(1, props.rows))))
/** 1-based. */
const page = computed(() => Math.min(pages.value, Math.floor(first.value / Math.max(1, props.rows)) + 1))
const shownFrom = computed(() => (props.totalRecords ? first.value + 1 : 0))
const shownTo = computed(() => Math.min(props.totalRecords, first.value + props.rows))

const root = ref<HTMLElement | null>(null)

/**
 * 'bar': the bar, « and » — the pager stays where it is on screen while the rows above it change (a list that
 * measures its rows while they are swapped can make the browser drop the scroll to the top for a moment).
 * 'step': Previous / Next, a page number, a typed page — to the top when `scrollTopOnStep`, else as 'bar'.
 */
async function go(n: number, how: 'bar' | 'step' = 'bar') {
  const target = Math.min(pages.value, Math.max(1, Math.round(n)))
  if (target === page.value) return
  const toTop = how === 'step' && props.scrollTopOnStep
  const before = root.value?.getBoundingClientRect().top ?? 0
  first.value = (target - 1) * props.rows
  await nextTick()
  if (toTop) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } else if (root.value) {
    const moved = root.value.getBoundingClientRect().top - before
    if (Math.abs(moved) > 1) window.scrollBy({ top: moved, behavior: 'instant' as ScrollBehavior })
  }
}

// --- the bar ---
const dragging = ref(false)
const percent = computed(() => (pages.value > 1 ? ((page.value - 1) / (pages.value - 1)) * 100 : 0))
function onSlide(event: Event) {
  void go(Number((event.target as HTMLInputElement).value))
}

// --- page numbers: the first, the last and the ones next to the current page, "…" between ---
const links = computed<(number | null)[]>(() => {
  const n = pages.value
  const cur = page.value
  const keep = new Set([1, n, cur - 1, cur, cur + 1].filter((p) => p >= 1 && p <= n))
  // near an end, show three in a row there instead of a lone "…"
  if (cur <= 3) [2, 3].forEach((p) => p <= n && keep.add(p))
  if (cur >= n - 2) [n - 1, n - 2].forEach((p) => p >= 1 && keep.add(p))
  const sorted = [...keep].sort((a, b) => a - b)
  const out: (number | null)[] = []
  sorted.forEach((p, i) => {
    const prev = sorted[i - 1]
    if (prev !== undefined && p - prev === 2) out.push(prev + 1)
    else if (prev !== undefined && p - prev > 2) out.push(null)
    out.push(p)
  })
  return out
})

// --- "page [n] of N" ---
const typed = ref('')
watch(page, (p) => (typed.value = String(p)), { immediate: true })
function onType(event: Event) {
  const input = event.target as HTMLInputElement
  const digits = input.value
    .replace(/[۰-۹]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/[٠-٩]/g, (d) => String(d.charCodeAt(0) - 0x0660))
    .replace(/\D/g, '')
  if (digits !== input.value) input.value = digits
  typed.value = digits
}
function commitTyped() {
  const n = Number.parseInt(typed.value, 10)
  if (Number.isFinite(n)) void go(n, 'step')
  typed.value = String(page.value)
}
</script>

<template>
  <div ref="root" class="pager-box">
  <nav class="pager" :aria-label="t('pager.label')">
    <div class="pager__report">{{ t('pager.report', { first: shownFrom, last: shownTo, total: totalRecords }) }}</div>

    <!-- Left to right in every language: the first page on the left, the last on the right -->
    <div class="pager__scrub" dir="ltr">
      <button type="button" class="pager__end" :disabled="page === 1" :aria-label="t('pager.first')" :title="t('pager.first')" @click="go(1)">
        <i class="pi pi-angle-double-left" />
      </button>
      <div class="pager__track" :class="{ 'pager__track--drag': dragging }" :style="{ '--pager-p': percent / 100 }">
        <div class="pager__fill" />
        <input
          class="pager__range"
          type="range"
          min="1"
          :max="pages"
          step="1"
          :value="page"
          :aria-label="t('pager.slider')"
          :aria-valuetext="t('pager.pageOf', { page, pages })"
          @input="onSlide"
          @pointerdown="dragging = true"
          @pointerup="dragging = false"
          @pointercancel="dragging = false"
          @blur="dragging = false"
        />
        <span class="pager__bubble" aria-hidden="true">{{ page }}</span>
      </div>
      <button type="button" class="pager__end" :disabled="page === pages" :aria-label="t('pager.last')" :title="t('pager.last')" @click="go(pages)">
        <i class="pi pi-angle-double-right" />
      </button>
    </div>

    <div class="pager__links">
      <template v-for="(p, i) in links" :key="p ?? `gap-${i}`">
        <span v-if="p === null" class="pager__gap" aria-hidden="true">…</span>
        <button
          v-else
          type="button"
          class="pager__link"
          :class="{ 'pager__link--on': p === page }"
          :aria-current="p === page ? 'page' : undefined"
          :aria-label="t('pager.pageOf', { page: p, pages })"
          @click="go(p, 'step')"
        >
          {{ p }}
        </button>
      </template>
    </div>

    <div class="pager__steps">
      <button type="button" class="pager__step" :disabled="page === 1" @click="go(page - 1, 'step')">
        <i class="pi pi-angle-left pager__dir" />{{ t('pager.prev') }}
      </button>
      <label class="pager__jump">
        <input
          class="pager__jump-input"
          type="text"
          inputmode="numeric"
          enterkeyhint="go"
          autocomplete="off"
          :value="typed"
          :size="Math.max(String(pages).length, 1)"
          :aria-label="t('pager.jump')"
          @input="onType"
          @keydown.enter.prevent="commitTyped"
          @blur="commitTyped"
        />
        <span class="pager__of">{{ t('pager.of', { pages }) }}</span>
      </label>
      <button type="button" class="pager__step" :disabled="page === pages" @click="go(page + 1, 'step')">
        {{ t('pager.next') }}<i class="pi pi-angle-right pager__dir" />
      </button>
    </div>
  </nav>
  </div>
</template>

<style scoped>
/* the box is the container: the layout follows the width the list has, not the window */
.pager-box {
  container-type: inline-size;
}
.pager {
  --pager-h: 2.5rem;
  --pager-radius: 12px;
  --pager-border: var(--p-content-border-color);
  --pager-raised: var(--p-content-background);
  --pager-sunken: var(--p-content-hover-background);
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  grid-template-areas:
    'report scrub steps'
    'links links links';
  align-items: center;
  gap: 0.85rem 1rem;
  padding: 0.9rem 1rem 1rem;
  border-top: 1px solid var(--pager-border);
  font-size: 0.875rem;
  color: var(--p-text-color);
}
.pager__report {
  grid-area: report;
  color: var(--p-text-muted-color);
  font-variant-numeric: tabular-nums;
}
.pager__scrub {
  grid-area: scrub;
  /* a quarter of the window: long enough to aim, short enough to read as a control */
  width: max(14rem, 25vw);
  max-width: 100%;
  justify-self: center;
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.pager__links {
  grid-area: links;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: 0.4rem;
}
.pager__steps {
  grid-area: steps;
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* --- buttons --- */
.pager button {
  font: inherit;
  color: inherit;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.pager button:disabled {
  opacity: 0.4;
  cursor: default;
}
.pager button:focus-visible,
.pager__jump-input:focus-visible {
  outline: 2px solid var(--p-primary-color);
  outline-offset: 2px;
}
.pager__end {
  display: grid;
  place-items: center;
  flex: none;
  width: 2rem;
  height: 2rem;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--p-text-muted-color) !important;
}
.pager__end:hover:not(:disabled) {
  background: var(--pager-sunken);
  color: var(--p-primary-color) !important;
}
.pager__link,
.pager__step {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  min-width: var(--pager-h);
  height: var(--pager-h);
  padding: 0 0.75rem;
  border: 1px solid var(--pager-border);
  border-radius: var(--pager-radius);
  background: var(--pager-raised);
  font-variant-numeric: tabular-nums;
  transition:
    background 0.15s,
    border-color 0.15s,
    color 0.15s,
    transform 0.1s;
}
.pager__link:hover:not(.pager__link--on),
.pager__step:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--p-primary-color) 45%, var(--pager-border));
  color: var(--p-primary-color);
}
.pager__link:active,
.pager__step:active:not(:disabled) {
  transform: scale(0.96);
}
.pager__link--on {
  border-color: transparent;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color) !important;
  font-weight: 700;
  box-shadow: 0 6px 16px -8px color-mix(in srgb, var(--p-primary-color) 80%, transparent);
}
.pager__step {
  padding: 0 1rem;
  font-weight: 500;
}
.pager__gap {
  min-width: 1.5rem;
  text-align: center;
  color: var(--p-text-muted-color);
  letter-spacing: 0.1em;
}
/* Previous / Next point the way the page reads */
html[dir='rtl'] .pager__dir {
  transform: scaleX(-1);
}

/* --- "page [n] of N" --- */
.pager__jump {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-muted-color);
  white-space: nowrap;
}
.pager__jump-input {
  min-width: var(--pager-h);
  height: var(--pager-h);
  padding: 0 0.5rem;
  border: 1px solid var(--pager-border);
  border-radius: var(--pager-radius);
  background: var(--pager-sunken);
  color: var(--p-text-color);
  font: inherit;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  text-align: center;
  box-sizing: content-box;
  max-width: 6ch;
}
.pager__jump-input:focus {
  border-color: var(--p-primary-color);
  background: var(--pager-raised);
}

/* --- the bar --- */
.pager__track {
  --thumb: 1.35rem;
  position: relative;
  flex: 1;
  height: 2rem;
  display: flex;
  align-items: center;
}
.pager__track::before,
.pager__fill {
  content: '';
  position: absolute;
  left: 0;
  height: 0.4rem;
  border-radius: 999px;
  pointer-events: none;
}
.pager__track::before {
  right: 0;
  background: var(--pager-sunken);
  box-shadow: inset 0 0 0 1px var(--pager-border);
}
.pager__fill {
  width: calc(var(--thumb) / 2 + (100% - var(--thumb)) * var(--pager-p));
  background: linear-gradient(90deg, color-mix(in srgb, var(--p-primary-color) 55%, transparent), var(--p-primary-color));
}
.pager__range {
  position: relative;
  width: 100%;
  height: 100%;
  margin: 0;
  background: transparent;
  cursor: pointer;
  touch-action: none;
  -webkit-appearance: none;
  appearance: none;
}
.pager__range::-webkit-slider-runnable-track {
  height: 100%;
  background: transparent;
}
.pager__range::-moz-range-track {
  height: 100%;
  background: transparent;
}
.pager__range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: var(--thumb);
  height: var(--thumb);
  margin-top: calc((2rem - var(--thumb)) / 2);
  border: 3px solid var(--p-primary-color);
  border-radius: 999px;
  background: var(--p-content-background);
  box-shadow: 0 2px 8px -2px rgb(0 0 0 / 35%);
  transition: transform 0.15s, box-shadow 0.15s;
}
.pager__range::-moz-range-thumb {
  box-sizing: border-box;
  width: var(--thumb);
  height: var(--thumb);
  border: 3px solid var(--p-primary-color);
  border-radius: 999px;
  background: var(--p-content-background);
  box-shadow: 0 2px 8px -2px rgb(0 0 0 / 35%);
  transition: transform 0.15s, box-shadow 0.15s;
}
.pager__range:hover::-webkit-slider-thumb,
.pager__track--drag .pager__range::-webkit-slider-thumb {
  transform: scale(1.15);
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--p-primary-color) 18%, transparent), 0 2px 8px -2px rgb(0 0 0 / 35%);
}
.pager__range:hover::-moz-range-thumb,
.pager__track--drag .pager__range::-moz-range-thumb {
  transform: scale(1.15);
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--p-primary-color) 18%, transparent), 0 2px 8px -2px rgb(0 0 0 / 35%);
}
.pager__range:focus-visible {
  outline: none;
}
.pager__range:focus-visible::-webkit-slider-thumb {
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--p-primary-color) 35%, transparent);
}
/* the page under the thumb while it is dragged or keyed */
.pager__bubble {
  position: absolute;
  bottom: calc(100% + 0.2rem);
  left: calc(var(--thumb) / 2 + (100% - var(--thumb)) * var(--pager-p));
  min-width: 2rem;
  padding: 0.2rem 0.5rem;
  border-radius: 8px;
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
  font-size: 0.8rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  text-align: center;
  pointer-events: none;
  opacity: 0;
  transform: translate(-50%, 4px) scale(0.9);
  transition: opacity 0.15s, transform 0.15s;
}
.pager__bubble::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  border: 5px solid transparent;
  border-top-color: var(--p-primary-color);
  transform: translateX(-50%);
}
.pager__track--drag .pager__bubble,
.pager__range:focus-visible + .pager__bubble {
  opacity: 1;
  transform: translate(-50%, 0) scale(1);
}

/* Medium: the report and the steps on top, the bar (still a quarter of the window) centred under them */
@container (max-width: 900px) {
  .pager {
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas:
      'report steps'
      'scrub scrub'
      'links links';
  }
}
/* Narrow (a phone, a narrow card): one part per row, Previous · page · Next at the bottom */
@container (max-width: 560px) {
  .pager {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      'report'
      'scrub'
      'links'
      'steps';
    padding-inline: 0.75rem;
  }
  .pager__scrub {
    width: 100%;
  }
  .pager__steps {
    justify-content: space-between;
  }
  .pager__step {
    flex: 1;
    max-width: 9rem;
  }
}
@media (prefers-reduced-motion: reduce) {
  .pager * {
    transition: none !important;
  }
}
</style>
