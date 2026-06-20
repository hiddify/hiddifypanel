<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
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
