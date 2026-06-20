<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useLayout } from './composables/layout'

defineOptions({ name: 'AppMenuItem' })

const { layoutState, isDesktop } = useLayout()
const route = useRoute()

const props = defineProps<{
  item: Record<string, unknown>
  root?: boolean
  parentPath?: string | null
}>()

const fullPath = computed(() => {
  const path = props.item.path as string | undefined
  if (!path) return null
  return props.parentPath ? props.parentPath + path : path
})

function menuItemKey(item: Record<string, unknown>): string {
  return String(item.path ?? item.to ?? item.label ?? '')
}

function childRoutes(item: Record<string, unknown>): string[] {
  const children = (item.items as Array<{ to?: string }> | undefined) ?? []
  return children.map((c) => c.to).filter((to): to is string => Boolean(to))
}

function routeMatchesMenu(path: string): boolean {
  return route.path === path || route.path.startsWith(`${path}/`)
}

const isActive = computed(() => {
  const item = props.item
  if (item.items) {
    const key = menuItemKey(item)
    if (layoutState.activePath === key) return true
    return childRoutes(item).some((to) => routeMatchesMenu(to))
  }
  if (item.to) {
    return routeMatchesMenu(String(item.to))
  }
  if (item.path) {
    return layoutState.activePath?.startsWith(fullPath.value ?? '') ?? false
  }
  return false
})

function itemClick(event: Event, item: Record<string, unknown>) {
  if (item.disabled) {
    event.preventDefault()
    return
  }
  if (typeof item.command === 'function') {
    ;(item.command as (e: { originalEvent: Event; item: unknown }) => void)({ originalEvent: event, item })
  }
  if (item.items) {
    event.preventDefault()
    const key = menuItemKey(item)
    layoutState.activePath = isActive.value && layoutState.activePath === key ? null : key
    layoutState.menuHoverActive = true
  } else {
    layoutState.overlayMenuActive = false
    layoutState.mobileMenuActive = false
    layoutState.menuHoverActive = false
  }
}

function onMouseEnter() {
  if (isDesktop() && props.root && props.item.items && layoutState.menuHoverActive) {
    layoutState.activePath = menuItemKey(props.item)
  }
}
</script>

<template>
  <li :class="{ 'layout-root-menuitem': root, 'active-menuitem': isActive }">
    <div v-if="root && item.visible !== false" class="layout-menuitem-root-text">{{ item.label }}</div>
    <a
      v-if="(!item.to || item.items) && item.visible !== false"
      :href="(item.url as string) || '#'"
      :class="item.class as string"
      :target="item.target as string"
      tabindex="0"
      @click="itemClick($event, item)"
      @mouseenter="onMouseEnter"
    >
      <i :class="item.icon" class="layout-menuitem-icon" />
      <span class="layout-menuitem-text">{{ item.label }}</span>
      <span v-if="item.badge" class="layout-menuitem-badge">{{ item.badge }}</span>
      <i v-if="item.items" class="pi pi-fw pi-angle-down layout-submenu-toggler" />
    </a>
    <router-link
      v-if="item.to && !item.items && item.visible !== false"
      :to="item.to as string"
      :class="item.class as string"
      active-class="active-route"
      tabindex="0"
      @click="itemClick($event, item)"
      @mouseenter="onMouseEnter"
    >
      <i :class="item.icon" class="layout-menuitem-icon" />
      <span class="layout-menuitem-text">{{ item.label }}</span>
      <span v-if="item.badge" class="layout-menuitem-badge">{{ item.badge }}</span>
    </router-link>
    <Transition v-if="item.items && item.visible !== false" name="layout-submenu">
      <ul v-show="root ? true : isActive" class="layout-submenu">
        <AppMenuItem
          v-for="child in (item.items as Record<string, unknown>[])"
          :key="String(child.label) + '_' + String(child.to ?? child.path)"
          :item="child"
          :root="false"
          :parent-path="fullPath"
        />
      </ul>
    </Transition>
  </li>
</template>
