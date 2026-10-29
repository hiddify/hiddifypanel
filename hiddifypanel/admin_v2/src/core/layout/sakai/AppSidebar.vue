<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppMenu from './AppMenu.vue'
import { useLayout } from './composables/layout'

const { layoutState, isDesktop, hasOpenOverlay } = useLayout()
const route = useRoute()
const sidebarRef = ref<HTMLElement | null>(null)
let outsideClickListener: ((event: MouseEvent) => void) | null = null

watch(
  () => route.path,
  (newPath) => {
    layoutState.activePath = isDesktop() ? null : newPath
    layoutState.overlayMenuActive = false
    layoutState.mobileMenuActive = false
    layoutState.menuHoverActive = false
  },
  { immediate: true },
)

/**
 * The open page's entry in the menu, in view: a reload starts the menu scrolled to the top, so it is brought to the
 * middle then (and when the phone's menu opens); after a move from within a page, only when it is out of view.
 */
function revealActive(center: boolean, tries = 30) {
  const box = sidebarRef.value
  const items = box?.querySelectorAll<HTMLElement>('a.active-route')
  // The menu can fill in a moment after the page (the admin's own pages): wait for the entry a few frames.
  if (!box || !items?.length) {
    if (tries > 0) requestAnimationFrame(() => revealActive(center, tries - 1))
    return
  }
  if (box.scrollHeight <= box.clientHeight) return
  const item = items[items.length - 1]!
  const top = item.getBoundingClientRect().top - box.getBoundingClientRect().top + box.scrollTop
  const bottom = top + item.offsetHeight
  if (!center && top >= box.scrollTop && bottom <= box.scrollTop + box.clientHeight) return
  box.scrollTo({ top: center ? top - (box.clientHeight - item.offsetHeight) / 2 : top < box.scrollTop ? top - 16 : bottom - box.clientHeight + 16 })
}

onMounted(() => revealActive(true))
watch(
  () => route.path,
  () => void nextTick(() => revealActive(false)),
)
watch(
  () => layoutState.mobileMenuActive || layoutState.overlayMenuActive,
  (open) => open && void nextTick(() => revealActive(true)),
)

watch(hasOpenOverlay, (open) => {
  if (!isDesktop()) return
  if (open) bindOutsideClickListener()
  else unbindOutsideClickListener()
})

function bindOutsideClickListener() {
  if (outsideClickListener) return
  outsideClickListener = (event: MouseEvent) => {
    const target = event.target as Node
    const topbarButtonEl = document.querySelector('.layout-menu-button')
    if (
      sidebarRef.value &&
      !sidebarRef.value.contains(target) &&
      topbarButtonEl &&
      !topbarButtonEl.contains(target)
    ) {
      layoutState.overlayMenuActive = false
    }
  }
  document.addEventListener('click', outsideClickListener)
}

function unbindOutsideClickListener() {
  if (!outsideClickListener) return
  document.removeEventListener('click', outsideClickListener)
  outsideClickListener = null
}

onBeforeUnmount(unbindOutsideClickListener)
</script>

<template>
  <div ref="sidebarRef" class="layout-sidebar">
    <AppMenu />
  </div>
</template>
