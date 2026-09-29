<template>
  <div class="legacy-frame">
    <Transition name="legacy-fade">
      <div v-if="loading" class="legacy-frame__loading" aria-live="polite">
        <i class="pi pi-spin pi-spinner" />
        <span>{{ t('legacy.loading') }}</span>
      </div>
    </Transition>
    <iframe ref="frame" class="legacy-frame__iframe" :class="{ 'legacy-frame__iframe--loading': loading }" :title="t('legacy.title')" @load="onLoad" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useLayout } from '@/core/layout/sakai/composables/layout'

/**
 * Classic (v1) admin pages the new UI has not replaced yet, shown inside the new shell.
 * `/legacy/<classic path>?<query>` ⇄ iframe `/<classic path>?<query>&darkmode=…`.
 * The classic page hides its own menu when it detects the frame (templates/master.html).
 */

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { isDarkTheme } = useLayout()

const frame = ref<HTMLIFrameElement | null>(null)
const loading = ref(true)
/** Classic path+query currently shown (without darkmode), to tell our own route syncs from real navigation. */
let shown = ''

const target = computed(() => {
  const raw = route.params.path
  const path = `/${Array.isArray(raw) ? raw.join('/') : String(raw ?? '')}`
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(route.query)) {
    if (key === 'darkmode') continue
    for (const item of Array.isArray(value) ? value : [value]) if (item != null) query.append(key, String(item))
  }
  const search = query.toString()
  return search ? `${path}?${search}` : path
})

function withTheme(pathAndQuery: string): string {
  const url = new URL(pathAndQuery, window.location.origin)
  // The classic UI keeps darkmode in the session; passing it every time keeps both UIs matched.
  url.searchParams.set('darkmode', isDarkTheme.value ? 'true' : 'false')
  return url.pathname + url.search
}

function stripTheme(location: Location): string {
  const url = new URL(location.href)
  url.searchParams.delete('darkmode')
  return url.pathname + url.search
}

function open(pathAndQuery: string) {
  if (!frame.value) return
  loading.value = true
  shown = pathAndQuery
  frame.value.src = withTheme(pathAndQuery)
}

function onLoad() {
  loading.value = false
  let location: Location | undefined
  try {
    location = frame.value?.contentWindow?.location
  } catch {
    return // navigated off-origin: nothing to sync
  }
  if (!location || location.href === 'about:blank') return
  // A page of the new UI inside the frame: show it as the whole page instead.
  if (/\/admin\/v2(\/|$)/.test(location.pathname)) {
    window.location.href = location.href
    return
  }
  const current = stripTheme(location)
  document.title = frame.value?.contentDocument?.title || document.title
  if (current !== shown) {
    // The user navigated inside the classic page: reflect it in the address bar (no reload).
    shown = current
    void router.replace(`/legacy${current}`)
  }
}

watch(target, (next) => {
  if (next !== shown) open(next)
})
watch(isDarkTheme, () => open(shown || target.value))
onMounted(() => open(target.value))
</script>

<style scoped>
.legacy-frame {
  position: relative;
  height: calc(100vh - 9rem);
  min-height: 28rem;
  border-radius: 14px;
  overflow: hidden;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
}
.legacy-frame__iframe {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  background: transparent;
  transition: opacity 0.25s ease;
}
.legacy-frame__iframe--loading {
  opacity: 0.35;
}
.legacy-frame__loading {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  color: var(--p-text-muted-color);
  pointer-events: none;
}
.legacy-frame__loading i {
  font-size: 1.75rem;
  color: var(--p-primary-color);
}
.legacy-fade-enter-active,
.legacy-fade-leave-active {
  transition: opacity 0.2s ease;
}
.legacy-fade-enter-from,
.legacy-fade-leave-to {
  opacity: 0;
}
@media (max-width: 991px) {
  /* Edge to edge under the topbar: no border, radius, margin or padding. */
  .legacy-frame {
    height: calc(100vh - 4rem);
    height: calc(100dvh - 4rem);
    min-height: 0;
    margin: 0;
    border: 0;
    border-radius: 0;
  }
}
</style>

<style>
/* While a classic page is framed on mobile, the shell drops its padding and footer around it. */
@media (max-width: 991px) {
  .layout-wrapper .layout-main-container:has(.legacy-frame) {
    padding: 4rem 0 0 0;
  }
  .layout-main-container:has(.legacy-frame) .layout-main {
    padding: 0;
  }
  .layout-main-container:has(.legacy-frame) .layout-footer {
    display: none;
  }
}
</style>
